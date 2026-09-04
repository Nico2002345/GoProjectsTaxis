import enum
from datetime import datetime, timezone

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    passenger = "passenger"
    driver = "driver"


class TripStatus(str, enum.Enum):
    requested = "requested"
    accepted = "accepted"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class OfferStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    declined = "declined"
    voided = "voided"
    error = "error"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"))
    is_available: Mapped[bool] = mapped_column(default=False)
    vehicle_plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    cedula: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email_verified: Mapped[bool] = mapped_column(default=False)
    email_verification_pin: Mapped[str | None] = mapped_column(String(6), nullable=True)
    email_verification_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    trips_as_passenger: Mapped[list["Trip"]] = relationship(
        back_populates="passenger", foreign_keys="Trip.passenger_id"
    )
    trips_as_driver: Mapped[list["Trip"]] = relationship(
        back_populates="driver", foreign_keys="Trip.driver_id"
    )


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    passenger_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[TripStatus] = mapped_column(
        Enum(TripStatus, name="trip_status"), default=TripStatus.requested
    )

    pickup_address: Mapped[str] = mapped_column(String(255))
    pickup_lat: Mapped[float | None] = mapped_column(nullable=True)
    pickup_lng: Mapped[float | None] = mapped_column(nullable=True)
    dropoff_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dropoff_lat: Mapped[float | None] = mapped_column(nullable=True)
    dropoff_lng: Mapped[float | None] = mapped_column(nullable=True)

    offered_fare_cents: Mapped[int] = mapped_column(default=0)
    agreed_fare_cents: Mapped[int | None] = mapped_column(nullable=True)

    requested_at: Mapped[datetime] = mapped_column(default=utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)

    passenger: Mapped["User"] = relationship(
        back_populates="trips_as_passenger", foreign_keys=[passenger_id]
    )
    driver: Mapped["User | None"] = relationship(
        back_populates="trips_as_driver", foreign_keys=[driver_id]
    )
    offers: Mapped[list["TripOffer"]] = relationship(back_populates="trip")


class TripOffer(Base):
    __tablename__ = "trip_offers"
    __table_args__ = (UniqueConstraint("trip_id", "driver_id", name="uq_trip_offer_driver"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    fare_cents: Mapped[int]
    status: Mapped[OfferStatus] = mapped_column(
        Enum(OfferStatus, name="trip_offer_status"), default=OfferStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(nullable=True)

    trip: Mapped["Trip"] = relationship(back_populates="offers")
    driver: Mapped["User"] = relationship()


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), index=True)
    reference: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    wompi_transaction_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    amount_in_cents: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3), default="COP")
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"), default=PaymentStatus.pending
    )
    checkout_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)

    trip: Mapped["Trip"] = relationship()
