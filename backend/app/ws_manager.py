from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserRole


class ConnectionManager:
    def __init__(self) -> None:
        self.active: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active[user_id] = websocket

    def disconnect(self, user_id: int) -> None:
        self.active.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict) -> None:
        ws = self.active.get(user_id)
        if ws is not None:
            await ws.send_json(message)

    async def broadcast_to_available_drivers(self, db: Session, message: dict) -> None:
        driver_ids = db.scalars(
            select(User.id).where(
                User.role == UserRole.driver, User.is_available.is_(True)
            )
        ).all()
        for driver_id in driver_ids:
            await self.send_to_user(driver_id, message)


manager = ConnectionManager()
