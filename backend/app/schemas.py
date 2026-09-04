from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models import TripStatus, UserRole


class UserRegister(BaseModel):
    phone: str
    password: str
    full_name: str
    cedula: str
    email: EmailStr
    role: UserRole
    vehicle_plate: str | None = None
    terms_accepted: bool

    @field_validator("cedula")
    @classmethod
    def cedula_must_be_numeric(cls, value: str) -> str:
        value = value.strip()
        if not value.isdigit():
            raise ValueError("La cédula debe contener solo números")
        return value

    @field_validator("terms_accepted")
    @classmethod
    def terms_must_be_accepted(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Debes aceptar los Términos y Condiciones")
        return value


class UserLogin(BaseModel):
    phone: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    full_name: str
    cedula: str
    email: str
    email_verified: bool
    role: UserRole
    is_available: bool
    vehicle_plate: str | None = None


class RegisterOut(BaseModel):
    message: str
    phone: str
    email: str


class EmailVerifyRequest(BaseModel):
    phone: str
    pin: str


class ResendPinRequest(BaseModel):
    phone: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AvailabilityUpdate(BaseModel):
    is_available: bool


class TripCreate(BaseModel):
    pickup_address: str
    pickup_lat: float | None = None
    pickup_lng: float | None = None
    dropoff_address: str | None = None
    dropoff_lat: float | None = None
    dropoff_lng: float | None = None


class TripStatusUpdate(BaseModel):
    status: TripStatus


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    passenger_id: int
    driver_id: int | None
    status: TripStatus
    pickup_address: str
    pickup_lat: float | None
    pickup_lng: float | None
    dropoff_address: str | None
    dropoff_lat: float | None
    dropoff_lng: float | None
    requested_at: datetime
    accepted_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    passenger_name: str | None = None
    driver_name: str | None = None
