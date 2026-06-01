import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from backend.models.deal import DealStatus, DealType
from backend.models.payment import PaymentStatus


class MurabahaParams(BaseModel):
    product_category: str = Field(..., pattern="^(consumer|phones|auto)$")
    tariff: str = Field(
        ...,
        pattern="^(NO_DOWNPAYMENT|NO_GUARANTOR|ONE_GUARANTOR|TWO_GUARANTORS)$",
    )
    down_payment_pct: int = Field(..., ge=0, le=90)
    principal: Decimal = Field(..., gt=0)
    markup: Decimal = Field(..., ge=0)
    duration_months: int = Field(..., ge=1, le=360)
    start_date: date
    item_qty: int = Field(default=1, ge=1, le=999)
    payday: int = Field(default=1, ge=1, le=28)
    pledge: str = Field(default="Нет", pattern="^(Да|Нет)$")
    guarantor_name: str | None = Field(default=None, max_length=255)
    guarantor_phone: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_guarantor(self) -> "MurabahaParams":
        if self.tariff in ("ONE_GUARANTOR", "TWO_GUARANTORS"):
            if not (self.guarantor_name or "").strip():
                raise ValueError("Укажите ФИО поручителя")
            if not (self.guarantor_phone or "").strip():
                raise ValueError("Укажите телефон поручителя")
        return self


class MurabahaQuoteResponse(BaseModel):
    product_category: str
    tariff: str
    principal: Decimal
    markup: Decimal
    total: Decimal
    down_payment_pct: int
    down_payment_amount: Decimal
    financed_amount: Decimal
    monthly_payment: Decimal
    duration_months: int
    rate_per_month_pct: Decimal


class MurabahaTariffOption(BaseModel):
    key: str
    label: str
    enabled: bool
    amount_min: int
    amount_max: int


class MurabahaTariffOptionsResponse(BaseModel):
    category: str
    category_label: str
    terms_min: int
    terms_max: int
    special_requirements: list[str]
    tariffs: list[MurabahaTariffOption]
    default_tariff: str | None


class IjaraParams(BaseModel):
    monthly_rent: Decimal = Field(..., gt=0)
    duration_months: int = Field(..., ge=1, le=360)
    start_date: date
    buyout_amount: Decimal | None = Field(None, ge=0)


class DealCreate(BaseModel):
    client_id: uuid.UUID
    type: DealType
    responsible_manager_id: uuid.UUID | None = None
    product_description: str | None = Field(None, max_length=2000)
    murabaha: MurabahaParams | None = None
    ijara: IjaraParams | None = None

    @model_validator(mode="after")
    def validate_params(self) -> "DealCreate":
        if self.type == DealType.murabaha and self.murabaha is None:
            raise ValueError("murabaha params are required for Murabaha deal")
        if self.type == DealType.ijara and self.ijara is None:
            raise ValueError("ijara params are required for Ijara deal")
        return self


class DealUpdate(BaseModel):
    product_description: str | None = Field(None, max_length=2000)
    murabaha: MurabahaParams | None = None
    ijara: IjaraParams | None = None


class ScheduleItemResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    installment_number: int
    due_date: date
    amount: Decimal
    paid_amount: Decimal
    status: PaymentStatus
    installment_type: str


class DealResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    client_id: uuid.UUID
    manager_id: uuid.UUID
    type: DealType
    status: DealStatus
    principal: Decimal
    markup: Decimal
    total: Decimal
    duration_months: int
    start_date: date | None
    end_date: date | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    rejection_comment: str | None
    product_description: str | None = None
    purchase_summary: str | None = None
    manager_name: str | None = None
    params: dict[str, object] | None = None
    created_at: datetime
    updated_at: datetime
    payment_schedules: list[ScheduleItemResponse] = []


class DealListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    client_id: uuid.UUID
    manager_id: uuid.UUID
    type: DealType
    status: DealStatus
    total: Decimal
    duration_months: int
    start_date: date | None
    product_description: str | None = None
    purchase_summary: str | None = None
    manager_name: str | None = None
    client_name: str | None = None
    created_at: datetime
