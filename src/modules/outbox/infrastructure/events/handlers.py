import asyncio
from datetime import UTC, datetime, timedelta

import asyncpg
from dependency_injector.wiring import Provide, inject
from sqlalchemy import cast, select, update
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.config.di_container import Container
from src.core.config.logging import get_logger
from src.core.config.settings import settings
from src.core.infrastructure.broker.broker import EXCHANGE_NAME, PAYMENTS_PROCESS_QUEUE, broker
from src.modules.outbox.infrastructure.database.model import OutboxEvent
from src.modules.payments.consts import PaymentStatus
from src.modules.payments.infrastructure.database.model import Payment

logger = get_logger(__name__)

POLL_INTERVAL = 30

_notify_event: asyncio.Event = asyncio.Event()


@inject
async def _publish_pending(
    session_factory: async_sessionmaker[AsyncSession] = Provide[Container.session_factory],
) -> int:
    async with session_factory() as db:
        result = await db.execute(
            select(OutboxEvent)
            .where(OutboxEvent.published == False)  # noqa: E712
            .order_by(OutboxEvent.created_at)
            .limit(100)
            .with_for_update(skip_locked=True)
        )
        events = result.scalars().all()

        if not events:
            return 0

        for ev in events:
            await broker.publish(
                message=ev.payload,
                routing_key=PAYMENTS_PROCESS_QUEUE,
                exchange=EXCHANGE_NAME,
                headers={"event_type": ev.event_type},
            )
            await db.execute(
                update(OutboxEvent)
                .where(OutboxEvent.id == ev.id)
                .values(published=True, published_at=datetime.now(UTC))
            )
            logger.info("outbox_event_published", event_id=str(ev.id))

        await db.commit()
        return len(events)


@inject
async def _recover_stuck_payments(
    session_factory: async_sessionmaker[AsyncSession] = Provide[Container.session_factory],
) -> int:
    threshold = datetime.now(UTC) - timedelta(minutes=5)

    async with session_factory() as db:
        result = await db.execute(
            select(OutboxEvent)
            .join(Payment, Payment.id == cast(OutboxEvent.payload["payment_id"].astext, UUID))
            .where(
                OutboxEvent.published, OutboxEvent.published_at <= threshold, Payment.status == PaymentStatus.PENDING
            )
            .order_by(OutboxEvent.published_at)
            .limit(100)
            .with_for_update(skip_locked=True)
        )
        stuck_events = result.scalars().all()

        if not stuck_events:
            return 0

        for ev in stuck_events:
            await broker.publish(
                message=ev.payload,
                routing_key=PAYMENTS_PROCESS_QUEUE,
                exchange=EXCHANGE_NAME,
                headers={"event_type": ev.event_type},
            )

            await db.execute(update(OutboxEvent).where(OutboxEvent.id == ev.id).values(published_at=datetime.now(UTC)))
            logger.warning("stuck_outbox_event_republished", event_id=str(ev.id))

        await db.commit()
        return len(stuck_events)


def _on_notify(conn, pid, channel, payload):
    logger.debug("pg_notify_received", channel=channel, payload=payload)
    _notify_event.set()


async def listen_loop():
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        await conn.add_listener("payments_outbox", _on_notify)
        logger.info("pg_listen_started", channel="payments_outbox")
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        await conn.remove_listener("payments_outbox", _on_notify)
        await conn.close()
        raise


async def publish_loop():
    while True:
        try:
            published_count = await _publish_pending()
            recovered_count = await _recover_stuck_payments()
            if published_count == 100 or recovered_count == 100:
                continue
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("outbox_publish_error", error=str(exc))
            await asyncio.sleep(5)
            continue

        try:
            _notify_event.clear()
            await asyncio.wait_for(_notify_event.wait(), timeout=POLL_INTERVAL)
        except TimeoutError:
            logger.debug("outbox_fallback_poll")
