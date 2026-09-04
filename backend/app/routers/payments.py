import hashlib
from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Payment, PaymentStatus, Trip, User, UserRole
from app.schemas import PaymentCheckoutRequest, PaymentOut
from app.security import get_current_user
from app.ws_manager import manager

router = APIRouter(prefix="/api/payments", tags=["payments"])

CHECKOUT_BASE_URL = "https://checkout.wompi.co/p/"

# Wompi's transaction.status values map 1:1 onto our PaymentStatus names.
_WOMPI_STATUS_MAP = {
    "APPROVED": PaymentStatus.approved,
    "DECLINED": PaymentStatus.declined,
    "VOIDED": PaymentStatus.voided,
    "ERROR": PaymentStatus.error,
}


def _integrity_signature(reference: str, amount_in_cents: int, currency: str) -> str:
    raw = f"{reference}{amount_in_cents}{currency}{settings.WOMPI_INTEGRITY_SECRET}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _resolve_path(data: dict, path: str):
    value = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return ""
        value = value[part]
    return value


def _event_checksum(body: dict) -> str:
    signature = body.get("signature", {})
    properties = signature.get("properties", [])
    data = body.get("data", {})
    concatenated = "".join(str(_resolve_path(data, prop)) for prop in properties)
    concatenated += str(body.get("timestamp", ""))
    concatenated += settings.WOMPI_EVENTS_SECRET or ""
    return hashlib.sha256(concatenated.encode()).hexdigest()


@router.post("/checkout", response_model=PaymentOut)
def create_checkout(
    payload: PaymentCheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.passenger:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only passengers can pay for a trip")

    trip = db.get(Trip, payload.trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    if trip.passenger_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your trip")
    if trip.status != "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Trip is not completed yet")
    if trip.agreed_fare_cents is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Trip has no agreed fare")

    reference = f"trip-{trip.id}-{uuid4().hex[:8]}"
    amount_in_cents = trip.agreed_fare_cents
    currency = "COP"
    signature = _integrity_signature(reference, amount_in_cents, currency)

    query = urlencode(
        {
            "public-key": settings.WOMPI_PUBLIC_KEY,
            "currency": currency,
            "amount-in-cents": amount_in_cents,
            "reference": reference,
            "signature:integrity": signature,
        }
    )
    checkout_url = f"{CHECKOUT_BASE_URL}?{query}"

    payment = Payment(
        trip_id=trip.id,
        reference=reference,
        amount_in_cents=amount_in_cents,
        currency=currency,
        status=PaymentStatus.pending,
        checkout_url=checkout_url,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return payment


@router.get("/{trip_id}", response_model=PaymentOut)
def get_payment(
    trip_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found")
    if current_user.id not in (trip.passenger_id, trip.driver_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your trip")

    payment = db.scalar(
        select(Payment)
        .where(Payment.trip_id == trip_id)
        .order_by(Payment.created_at.desc())
    )
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No payment for this trip")
    return payment


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def wompi_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.json()

    if _event_checksum(body) != body.get("signature", {}).get("checksum"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid signature")

    transaction = body.get("data", {}).get("transaction", {})
    reference = transaction.get("reference")
    wompi_status = transaction.get("status")

    payment = db.scalar(select(Payment).where(Payment.reference == reference))
    if payment is None:
        return {"received": True}

    payment.wompi_transaction_id = transaction.get("id")
    payment.status = _WOMPI_STATUS_MAP.get(wompi_status, PaymentStatus.error)
    if payment.status == PaymentStatus.approved:
        payment.paid_at = datetime.now(timezone.utc)
    db.commit()

    trip = db.get(Trip, payment.trip_id)
    if trip is not None:
        payment_out = PaymentOut.model_validate(payment).model_dump(mode="json")
        for uid in {trip.passenger_id, trip.driver_id} - {None}:
            await manager.send_to_user(uid, {"type": "payment_updated", "payment": payment_out})

    return {"received": True}
