from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

from src.core.config.settings import settings
from src.modules.payments.infrastructure.database.uow import PaymentUnitOfWork
from src.modules.payments.services.payment import PaymentService

_POOL_SIZE: int = settings.db_pool_size
_MAX_OVERFLOW: int = settings.db_max_overflow
_POOL_TIMEOUT: int = settings.db_pool_timeout
_POOL_RECYCLE: int = settings.db_pool_recycle


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    engine = providers.Singleton(
        create_async_engine,
        url=config.db.url,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=_POOL_SIZE,
        max_overflow=_MAX_OVERFLOW,
        pool_timeout=_POOL_TIMEOUT,
        pool_recycle=_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=False,
    )

    session_factory = providers.Singleton(
        async_sessionmaker,
        bind=engine,
        expire_on_commit=False,
    )

    payment_uow = providers.Factory(
        PaymentUnitOfWork,
        session_factory=session_factory,
    )

    payment_service = providers.Factory(
        PaymentService,
        uow=payment_uow,
    )
