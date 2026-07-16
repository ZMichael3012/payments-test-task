import asyncio
import random
from datetime import UTC, datetime, timedelta

import httpx
from dependency_injector.wiring import Provide, inject
from faststream import Depends
from faststream.rabbit import RabbitMessage
from sqlalchemy import select, update

from src.core.config.di_container import Container
from src.core.config.logging import get_logger
from src.core.config.settings import settings
from src.core.infrastructure.broker.broker import (
    DEAD_LETTER_QUEUE,
    EXCHANGE_NAME,
    PAYMENTS_PROCESS_QUEUE,
    RETRY_QUEUE,
    broker,
)
from src.core.webhook import sign_payload
from src.modules.payments.consts import PaymentStatus
from src.modules.payments.infrastructure.database.model import Payment
from src.modules.payments.schemas import PaymentPayload

logger = get_logger(__name__)

WEBHOOK_TIMEOUT = 10


async def _simulate_gateway() -> bool:
    await asyncio.sleep(random.uniform(2, 5))
    return random.randint(0, 9) < 9


async def _send_webhook(url: str, payload: dict) -> None:
    _, headers = sign_payload(payload)
    async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        except Exception as exc:
            logger.error(str(exc), exc_info=True)
            return
    logger.info("webhook_delivered", url=url)


@broker.subscriber(queue=PAYMENTS_PROCESS_QUEUE, exchange=EXCHANGE_NAME)
@inject
async def process_message(
    body: PaymentPayload,
    msg: RabbitMessage,
    session_factory=Depends(Provide[Container.session_factory]),
):
    retry_count = int(msg.headers.get("x-retry-count", 0))

    if retry_count >= settings.max_retries:
        logger.warning("max_retries_exceeded", retry_count=retry_count)
        await broker.publish(
            message=body.model_dump(mode="json"),
            routing_key=DEAD_LETTER_QUEUE,
            headers={**(msg.headers or {}), "x-final-reason": "max-retries-exceeded"},
        )
        return

    payment_id = body.payment_id

    try:
        async with session_factory() as db:
            payment: Payment | None = await db.scalar(select(Payment).where(Payment.id == payment_id))

            if payment is None:
                logger.error("payment_not_found", payment_id=str(payment_id))
                return

            if payment.status != PaymentStatus.PENDING:
                logger.info("payment_already_processed", payment_id=str(payment_id))
                return

            success = await _simulate_gateway()
            new_status = PaymentStatus.SUCCEEDED if success else PaymentStatus.FAILED
            now = datetime.now(UTC)

            await db.execute(
                update(Payment).where(Payment.id == payment_id).values(status=new_status, processed_at=now)
            )
            await db.commit()

        logger.info("payment_processed", payment_id=str(payment_id), status=new_status)

        if payment.webhook_url:
            await _send_webhook(
                payment.webhook_url,
                {
                    "payment_id": str(payment.id),
                    "status": new_status,
                    "processed_at": now.isoformat(),
                },
            )

    except Exception as exc:
        delay_ms = settings.retry_delay_ms * (2**retry_count)

        logger.warning("message_processing_error", error=str(exc), retry_count=retry_count + 1, next_delay_ms=delay_ms)

        headers = dict(msg.headers or {})
        headers["x-retry-count"] = retry_count + 1

        await broker.publish(
            message=body.model_dump(mode="json"),
            routing_key=RETRY_QUEUE,
            headers=headers,
            expiration=timedelta(milliseconds=delay_ms),
        )
