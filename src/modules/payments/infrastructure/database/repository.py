import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.payments.infrastructure.database.model import Payment


class PaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.db.scalar(select(Payment).where(Payment.id == payment_id))

    async def get_by_idempotency_key(self, idempotency_key: uuid.UUID) -> Payment | None:
        return await self.db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
