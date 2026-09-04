from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.email_utils import send_verification_email
from app.models import User
from app.schemas import (
    EmailVerifyRequest,
    RegisterOut,
    ResendPinRequest,
    TokenOut,
    UserLogin,
    UserOut,
    UserRegister,
)
from app.security import (
    create_access_token,
    generate_pin,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=RegisterOut)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.phone == payload.phone)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El teléfono ya está registrado")
    if db.scalar(select(User).where(User.email == payload.email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")
    if db.scalar(select(User).where(User.cedula == payload.cedula)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "La cédula ya está registrada")

    pin = generate_pin()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.EMAIL_PIN_EXPIRE_MINUTES
    )

    user = User(
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        cedula=payload.cedula,
        email=payload.email,
        role=payload.role,
        vehicle_plate=payload.vehicle_plate,
        email_verified=False,
        email_verification_pin=pin,
        email_verification_expires_at=expires_at,
        terms_accepted_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    send_verification_email(user.email, user.full_name, pin)

    return RegisterOut(
        message="Registro creado. Revisa tu correo para verificar tu cuenta.",
        phone=user.phone,
        email=user.email,
    )


@router.post("/verify-email", response_model=TokenOut)
def verify_email(payload: EmailVerifyRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    if user.email_verified:
        token = create_access_token(user.id)
        return TokenOut(access_token=token, user=UserOut.model_validate(user))

    if (
        user.email_verification_pin != payload.pin
        or user.email_verification_expires_at is None
        or user.email_verification_expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Código inválido o expirado")

    user.email_verified = True
    user.email_verification_pin = None
    user.email_verification_expires_at = None
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/resend-pin", status_code=status.HTTP_204_NO_CONTENT)
def resend_pin(payload: ResendPinRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    if user.email_verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El correo ya está verificado")

    pin = generate_pin()
    user.email_verification_pin = pin
    user.email_verification_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.EMAIL_PIN_EXPIRE_MINUTES
    )
    db.commit()

    send_verification_email(user.email, user.full_name, pin)


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Teléfono o contraseña inválidos")
    if not user.email_verified:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Debes verificar tu correo antes de iniciar sesión"
        )

    token = create_access_token(user.id)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
