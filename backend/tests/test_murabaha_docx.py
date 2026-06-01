from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from backend.models.client import Client
from backend.models.deal import Deal, DealStatus, DealType
from backend.models.deal import DealParam
from backend.services.murabaha_contract_service import (
    build_murabaha_replacements,
    generate_murabaha_docx_zip,
)
from backend.services.murabaha_docx_generator import TEMPLATE_CONTRACT, TEMPLATE_SCHEDULE


@pytest.mark.skipif(
    not TEMPLATE_CONTRACT.is_file() or not TEMPLATE_SCHEDULE.is_file(),
    reason="DOCX templates not present",
)
def test_generate_murabaha_docx_zip_smoke():
    deal = Deal(
        id=uuid4(),
        client_id=uuid4(),
        manager_id=uuid4(),
        type=DealType.murabaha,
        status=DealStatus.draft,
        principal=Decimal("50000"),
        markup=Decimal("12000"),
        total=Decimal("62000"),
        duration_months=6,
        start_date=date(2025, 6, 15),
        product_description="Телефон",
    )
    deal.params = [
        DealParam(deal_id=deal.id, key="contract_number", value="1-25/06/15"),
        DealParam(deal_id=deal.id, key="down_payment_amount", value="12400"),
        DealParam(deal_id=deal.id, key="payday", value=15),
        DealParam(deal_id=deal.id, key="pledge", value="Нет"),
        DealParam(deal_id=deal.id, key="tariff", value="NO_GUARANTOR"),
        DealParam(deal_id=deal.id, key="item_qty", value=1),
    ]
    client = Client(
        id=deal.client_id,
        manager_id=deal.manager_id,
        full_name="Иванов Иван",
        phone="+79001234567",
    )
    repl = build_murabaha_replacements(deal, client, "SheyKey Finance")
    data = generate_murabaha_docx_zip(repl)
    assert len(data) > 1000
    assert data[:2] == b"PK"
