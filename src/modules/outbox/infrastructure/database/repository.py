from sqlalchemy.ext.asyncio import AsyncSession


class OutboxRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
