import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from src.modules.payments.consts import Currency, PaymentStatus


class PaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: Currency
    description: str | None = None
    metadata: dict[str, Any] | None = None
    webhook_url: HttpUrl | None = None


class PaymentResponse(BaseModel):
    payment_id: uuid.UUID
    status: PaymentStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentDetail(BaseModel):
    id: uuid.UUID
    amount: Decimal
    currency: str
    description: str | None
    metadata: dict[str, Any] | None = None
    status: PaymentStatus
    webhook_url: str | None
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class PaymentPayload(BaseModel):
    payment_id: uuid.UUID
