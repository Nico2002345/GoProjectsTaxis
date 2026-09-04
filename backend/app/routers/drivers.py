from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.schemas import AvailabilityUpdate, UserOut
from app.security import get_current_user

router = APIRouter(prefix="/api/drivers", tags=["drivers"])


@router.patch("/me/availability", response_model=UserOut)
def update_availability(
    payload: AvailabilityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.driver:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only drivers can set availability")

    current_user.is_available = payload.is_available
    db.commit()
    db.refresh(current_user)
    return current_user
