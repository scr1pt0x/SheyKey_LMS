"""Build DOCX replacements and generate Murabaha contract documents."""
from __future__ import annotations

import io
import tempfile
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.client import Client
from backend.models.deal import Deal, DealType
from backend.models.settings import SystemSetting
from backend.services.murabaha_bot_schedule import generate_bot_payment_schedule
from backend.services.murabaha_docx_generator import generate_contract_and_schedule
from backend.services.murabaha_tariff_service import MurabahaTariff

GUARANTOR_TARIFFS = frozenset(
    {MurabahaTariff.ONE_GUARANTOR.value, MurabahaTariff.TWO_GUARANTORS.value}
)


def _params_dict(deal: Deal) -> dict:
    return {p.key: p.value for p in deal.params} if deal.params else {}


def _int_param(params: dict, key: str, default: int) -> int:
    val = params.get(key)
    if val is None:
        return default
    return int(val)


def _str_param(params: dict, key: str, default: str = "") -> str:
    val = params.get(key)
    if val is None:
        return default
    return str(val)


def schedule_rows_for_deal(
    total: int,
    advance: int,
    duration_months: int,
    start_date: date,
    payday: int,
) -> list[dict]:
    return generate_bot_payment_schedule(
        start_date=start_date,
        term=duration_months,
        payday=payday,
        cost=total,
        advance=advance,
    )


async def load_murabaha_seller_fio(db: AsyncSession) -> str:
    row = (
        await db.execute(
            select(SystemSetting.value).where(SystemSetting.key == "murabaha_seller_fio")
        )
    ).scalar_one_or_none()
    if isinstance(row, str) and row.strip():
        return row.strip()
    return "SheyKey Finance"


def build_murabaha_replacements(
    deal: Deal,
    client: Client,
    seller_fio: str,
) -> dict:
    params = _params_dict(deal)
    qty = _int_param(params, "item_qty", 1)
    principal = int(Decimal(str(deal.principal)))
    markup = int(Decimal(str(deal.markup)))
    total_sebestoim = principal * qty
    total_nacenka = markup * qty
    polnaya = int(Decimal(str(deal.total)))
    advance = int(Decimal(str(params.get("down_payment_amount", 0) or 0)))
    payday = _int_param(params, "payday", deal.start_date.day if deal.start_date else 1)
    pledge = _str_param(params, "pledge", "Нет")
    tariff = _str_param(params, "tariff", "")
    guarantor_name = _str_param(params, "guarantor_name", "—")
    guarantor_phone = _str_param(params, "guarantor_phone", "—")
    if tariff in GUARANTOR_TARIFFS and guarantor_name == "—":
        guarantor_name = ""
        guarantor_phone = ""

    start = deal.start_date or date.today()
    contract_number = _str_param(params, "contract_number", "0-00/00/00")
    data_dogovora = start.strftime("%d.%m.%Y")

    schedule = schedule_rows_for_deal(polnaya, advance, deal.duration_months, start, payday)
    ejemes = schedule[0]["amount"] if schedule else 0
    ostatok = max(0, polnaya - advance)

    repl: dict = {
        "{{nomer_dogovora}}": contract_number,
        "{{data_dogovora}}": data_dogovora,
        "{{fio_prodavca}}": seller_fio,
        "{{fio_pokupatelya}}": client.full_name,
        "{{tel_pokupatelya}}": client.phone,
        "{{fio_poruchitelya1}}": guarantor_name or "—",
        "{{tel_poruchit1}}": guarantor_phone or "—",
        "{{pokupaemy_tov}}": deal.product_description or "—",
        "{{kolichestvo_tov}}": qty,
        "{{polnaya_stoimost_tov}}": polnaya,
        "{{sebestoimost_tovara}}": total_sebestoim,
        "{{nacenka_tov}}": total_nacenka,
        "{{pervi_vznos}}": advance,
        "{{srok_dogov}}": deal.duration_months,
        "{{ejemes_oplata}}": ejemes,
        "{{data_opl}}": payday,
        "{{zalog}}": pledge,
        "{{ostatok_dolga}}": ostatok,
        "contract_number": contract_number,
    }

    for i in range(1, 13):
        if i <= len(schedule):
            row = schedule[i - 1]
            repl[f"{{{{data_plateja{i}}}}}"] = row["date"]
            repl[f"{{{{summa_plateja{i}}}}}"] = row["amount"]
            repl[f"{{{{ostatok_posle_plateja{i}}}}}"] = row["balance"]
        else:
            repl[f"{{{{data_plateja{i}}}}}"] = ""
            repl[f"{{{{summa_plateja{i}}}}}"] = ""
            repl[f"{{{{ostatok_posle_plateja{i}}}}}"] = ""

    return repl


async def load_deal_for_documents(db: AsyncSession, deal_id) -> tuple[Deal, Client]:
    result = await db.execute(
        select(Deal)
        .where(Deal.id == deal_id)
        .options(selectinload(Deal.params), selectinload(Deal.client))
    )
    deal = result.scalar_one_or_none()
    if not deal:
        raise ValueError("Сделка не найдена")
    if deal.type != DealType.murabaha:
        raise ValueError("Документы DOCX доступны только для Мурабаха")
    client = deal.client or await db.get(Client, deal.client_id)
    if not client:
        raise ValueError("Клиент не найден")
    return deal, client


def generate_murabaha_docx_zip(repl: dict) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        contract_path, schedule_path = generate_contract_and_schedule(repl, out_dir)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(contract_path, contract_path.name)
            zf.write(schedule_path, schedule_path.name)
        return buf.getvalue()


async def generate_murabaha_docx_for_deal(db: AsyncSession, deal_id) -> bytes:
    deal, client = await load_deal_for_documents(db, deal_id)
    seller = await load_murabaha_seller_fio(db)
    repl = build_murabaha_replacements(deal, client, seller)
    return generate_murabaha_docx_zip(repl)
