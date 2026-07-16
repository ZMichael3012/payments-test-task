import uuid

from sqlalchemy.exc import IntegrityError

from src.modules.outbox.consts import OutboxEventType
from src.modules.outbox.infrastructure.database.model import OutboxEvent
from src.modules.payments.consts import PaymentStatus
from src.modules.payments.infrastructure.database.model import Payment
from src.modules.payments.infrastructure.database.uow import PaymentUnitOfWork
from src.modules.payments.schemas import PaymentCreate


class PaymentService:
    def __init__(self, uow: PaymentUnitOfWork) -> None:
        self._uow = uow

    async def get_payment(self, payment_id: uuid.UUID) -> Payment | None:
        async with self._uow:
            return await self._uow.payments.get_by_id(payment_id)

    async def create_payment(self, data: PaymentCreate, idempotency_key: uuid.UUID) -> Payment:
        async with self._uow:
            existing_payment = await self._uow.payments.get_by_idempotency_key(idempotency_key)
            if existing_payment:
                return existing_payment

            payment = Payment(
                id=uuid.uuid4(),
                amount=data.amount,
                currency=data.currency.value,
                description=data.description,
                idempotency_key=idempotency_key,
                metadata_=data.metadata,
                status=PaymentStatus.PENDING,
                webhook_url=str(data.webhook_url) if data.webhook_url else None,
            )
            event = OutboxEvent(
                id=uuid.uuid4(),
                event_type=OutboxEventType.PAYMENT_CREATED,
                payload={"payment_id": str(payment.id)},
                published=False,
            )

            try:
                async with self._uow.begin_nested():
                    self._uow.payments.db.add(payment)
                    self._uow.outbox.db.add(event)

                    await self._uow.flush()
            except IntegrityError:
                existing_payment = await self._uow.payments.get_by_idempotency_key(idempotency_key)
                if existing_payment is None:
                    raise
                return existing_payment

            await self._uow.commit()

            return payment
