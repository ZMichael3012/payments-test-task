from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.infrastructure.database.uow import AbstractUnitOfWork
from src.modules.outbox.infrastructure.database.repository import OutboxRepository
from src.modules.payments.infrastructure.database.repository import PaymentRepository


class PaymentUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __aenter__(self) -> "PaymentUnitOfWork":
        self._session: AsyncSession = self._session_factory()

        self.payments = PaymentRepository(self._session)
        self.outbox = OutboxRepository(self._session)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def flush(self) -> None:
        await self._session.flush()

    def begin_nested(self):
        return self._session.begin_nested()
