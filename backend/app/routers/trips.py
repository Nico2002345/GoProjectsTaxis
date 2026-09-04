from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OfferStatus, Trip, TripOffer, TripStatus, User, UserRole
from app.schemas import TripCreate, TripOfferCreate, TripOfferOut, TripOut, TripStatusUpdate
from app.security import get_current_user
from app.ws_manager import manager

router = APIRouter(prefix="/api/trips", tags=["trips"])

ACTIVE_STATUSES = (
    TripStatus.requested,
    TripStatus.accepted,
    TripStatus.in_progress,
)

# Valid forward transitions a caller may request via POST /trips/{id}/status.
ALLOWED_TRANSITIONS = {
    TripStatus.accepted: {TripStatus.in_progress, TripStatus.cancelled},
    TripStatus.requested: {TripStatus.cancelled},
    TripStatus.in_progress: {TripStatus.completed},
}


def _offer_to_out(offer: TripOffer) -> TripOfferOut:
    out = TripOfferOut.model_validate(offer)
    out.driver_name = offer.driver.full_name if offer.driver else None
    return out


def _to_out(trip: Trip, include_offers: bool = False) -> TripOut:
    out = TripOut.model_validate(trip)
    out.passenger_name = trip.passenger.full_name if trip.passenger else None
    out.driver_name = trip.driver.full_name if trip.driver else None
    if include_offers:
        offers = sorted(trip.offers, key=lambda o: o.created_at)
        out.offers = [_offer_to_out(o) for o in offers]
    return out


@router.post("", response_model=TripOut)
async def create_trip(
    payload: TripCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.passenger:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only passengers can request trips")

    existing = db.scalar(
        select(Trip).where(
            Trip.passenger_id == current_user.id, Trip.status.in_(ACTIVE_STATUSES)
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have an active trip")

    trip = Trip(passenger_id=current_user.id, **payload.model_dump())
    db.add(trip)
    db.commit()
    db.refresh(trip)

    trip_out = _to_out(trip)
    await manager.broadcast_to_available_drivers(
        db, {"type": "trip_requested", "trip": trip_out.model_dump(mode="json")}
    )
    return trip_out


@router.get("/active", response_model=TripOut)
def get_active_trip(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    column = Trip.passenger_id if current_user.role == UserRole.passenger else Trip.driver_id
    trip = db.scalar(
        select(Trip)
        .where(column == current_user.id, Trip.status.in_(ACTIVE_STATUSES))
        .order_by(Trip.requested_at.desc())
    )
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active trip")
    return _to_out(trip, include_offers=current_user.role == UserRole.passenger)


@router.get("/available", response_model=list[TripOut])
def list_available_trips(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if current_user.role != UserRole.driver:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only drivers can list requests")

    trips = db.scalars(
        select(Trip).where(Trip.status == TripStatus.requested).order_by(Trip.requested_at)
    ).all()
    return [_to_out(t) for t in trips]


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(
    trip_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    is_participant = current_user.id in (trip.passenger_id, trip.driver_id)
    has_offer = (
        not is_participant
        and db.scalar(
            select(TripOffer.id).where(
                TripOffer.trip_id == trip_id, TripOffer.driver_id == current_user.id
            )
        )
        is not None
    )
    if not is_participant and not has_offer:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your trip")
    return _to_out(trip, include_offers=current_user.id == trip.passenger_id)


@router.post("/{trip_id}/offers", response_model=TripOfferOut)
async def create_offer(
    trip_id: int,
    payload: TripOfferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.driver:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only drivers can make offers")

    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    if trip.status != TripStatus.requested:
        raise HTTPException(status.HTTP_409_CONFLICT, "Trip is no longer open for offers")

    existing = db.scalar(
        select(TripOffer).where(
            TripOffer.trip_id == trip_id, TripOffer.driver_id == current_user.id
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You already made an offer on this trip")

    fare_cents = (
        payload.fare_cents if payload.fare_cents is not None else trip.offered_fare_cents
    )
    offer = TripOffer(trip_id=trip_id, driver_id=current_user.id, fare_cents=fare_cents)
    db.add(offer)
    db.commit()
    db.refresh(offer)

    offer_out = _offer_to_out(offer)
    await manager.send_to_user(
        trip.passenger_id,
        {
            "type": "trip_offer_created",
            "trip_id": trip.id,
            "offer": offer_out.model_dump(mode="json"),
        },
    )
    return offer_out


@router.get("/{trip_id}/offers", response_model=list[TripOfferOut])
def list_offers(
    trip_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    if current_user.id != trip.passenger_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your trip")

    offers = db.scalars(
        select(TripOffer).where(TripOffer.trip_id == trip_id).order_by(TripOffer.created_at)
    ).all()
    return [_offer_to_out(o) for o in offers]


@router.post("/{trip_id}/offers/{offer_id}/select", response_model=TripOut)
async def select_offer(
    trip_id: int,
    offer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    if current_user.id != trip.passenger_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your trip")

    offer = db.get(TripOffer, offer_id)
    if offer is None or offer.trip_id != trip_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer not found")
    if offer.status != OfferStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "Offer is no longer available")

    result = db.execute(
        update(Trip)
        .where(Trip.id == trip_id, Trip.status == TripStatus.requested)
        .values(
            driver_id=offer.driver_id,
            status=TripStatus.accepted,
            agreed_fare_cents=offer.fare_cents,
            accepted_at=datetime.now(timezone.utc),
        )
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Trip already resolved")

    now = datetime.now(timezone.utc)
    offer.status = OfferStatus.accepted
    offer.responded_at = now

    other_offers = db.scalars(
        select(TripOffer).where(
            TripOffer.trip_id == trip_id,
            TripOffer.id != offer.id,
            TripOffer.status == OfferStatus.pending,
        )
    ).all()
    rejected_driver_ids = []
    for other in other_offers:
        other.status = OfferStatus.rejected
        other.responded_at = now
        rejected_driver_ids.append(other.driver_id)

    winner = db.get(User, offer.driver_id)
    if winner is not None:
        winner.is_available = False

    db.commit()

    trip = db.get(Trip, trip_id)
    trip_out = _to_out(trip, include_offers=True)

    await manager.send_to_user(
        offer.driver_id, {"type": "trip_updated", "trip": trip_out.model_dump(mode="json")}
    )
    for driver_id in rejected_driver_ids:
        await manager.send_to_user(
            driver_id, {"type": "trip_offer_rejected", "trip_id": trip.id}
        )
    await manager.broadcast_to_available_drivers(
        db, {"type": "trip_closed", "trip_id": trip.id}
    )

    return trip_out


@router.post("/{trip_id}/status", response_model=TripOut)
async def update_trip_status(
    trip_id: int,
    payload: TripStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    if current_user.id not in (trip.passenger_id, trip.driver_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your trip")

    allowed = ALLOWED_TRANSITIONS.get(trip.status, set())
    if payload.status not in allowed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot move trip from {trip.status.value} to {payload.status.value}",
        )
    if payload.status == TripStatus.in_progress and current_user.id != trip.driver_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the driver can start the trip")
    if payload.status == TripStatus.completed and current_user.id != trip.driver_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the driver can complete the trip")

    now = datetime.now(timezone.utc)
    trip.status = payload.status
    if payload.status == TripStatus.in_progress:
        trip.started_at = now
    elif payload.status == TripStatus.completed:
        trip.completed_at = now
    elif payload.status == TripStatus.cancelled:
        trip.cancelled_at = now
        if trip.driver_id is not None:
            driver = db.get(User, trip.driver_id)
            if driver is not None:
                driver.is_available = True

    db.commit()
    db.refresh(trip)

    trip_out = _to_out(trip)
    for uid in {trip.passenger_id, trip.driver_id} - {current_user.id, None}:
        await manager.send_to_user(uid, {"type": "trip_updated", "trip": trip_out.model_dump(mode="json")})
    return trip_out
