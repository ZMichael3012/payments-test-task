import uuid

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header, HTTPException, status

from src.core.config.di_container import Container
from src.modules.payments.consts import PaymentStatus
from src.modules.payments.schemas import PaymentCreate, PaymentDetail, PaymentResponse
from src.modules.payments.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PaymentResponse,
)
@inject
async def create_payment_endpoint(
    data: PaymentCreate,
    idempotency_key: uuid.UUID = Header(..., alias="Idempotency-Key"),
    service: PaymentService = Depends(Provide[Container.payment_service]),
):
    payment = await service.create_payment(data, idempotency_key)

    return PaymentResponse(
        payment_id=payment.id,
        status=PaymentStatus(payment.status),
        created_at=payment.created_at,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentDetail,
)
@inject
async def get_payment_endpoint(
    payment_id: uuid.UUID,
    service: PaymentService = Depends(Provide[Container.payment_service]),
):
    payment = await service.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentDetail(
        id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.metadata_,  # type: ignore
        status=PaymentStatus(payment.status),
        webhook_url=payment.webhook_url,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )
