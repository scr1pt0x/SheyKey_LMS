"""Murabaha tariff calculator — rules ported from sheykey.com/scripts/script.js."""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.settings import SettingKey, SystemSetting

THRESHOLD_TERM = 6
MARKUP_TOLERANCE_RUB = Decimal("1")

TARIFF_ORDER = ("ONE_GUARANTOR", "TWO_GUARANTORS", "NO_DOWNPAYMENT", "NO_GUARANTOR")


class ProductCategory(str, Enum):
    consumer = "consumer"
    phones = "phones"
    auto = "auto"


class MurabahaTariff(str, Enum):
    NO_DOWNPAYMENT = "NO_DOWNPAYMENT"
    NO_GUARANTOR = "NO_GUARANTOR"
    ONE_GUARANTOR = "ONE_GUARANTOR"
    TWO_GUARANTORS = "TWO_GUARANTORS"


TARIFF_LABELS: dict[str, str] = {
    MurabahaTariff.NO_DOWNPAYMENT.value: "Без взноса",
    MurabahaTariff.NO_GUARANTOR.value: "Без поручителя",
    MurabahaTariff.ONE_GUARANTOR.value: "С 1 поручителем",
    MurabahaTariff.TWO_GUARANTORS.value: "С 2 поручителями",
}

CATEGORY_LABELS: dict[str, str] = {
    ProductCategory.consumer.value: "Потребительские товары",
    ProductCategory.phones.value: "Телефоны",
    ProductCategory.auto.value: "Автомобили",
}


def _category_config() -> dict[str, dict[str, Any]]:
    return {
        ProductCategory.consumer.value: {
            "terms": {"min": 3, "max": 12},
            "limits": {
                MurabahaTariff.NO_DOWNPAYMENT.value: {"min": 10_000, "max": 60_000},
                MurabahaTariff.NO_GUARANTOR.value: {"min": 10_000, "max": 80_000},
                MurabahaTariff.ONE_GUARANTOR.value: {"min": 10_000, "max": 300_000},
                MurabahaTariff.TWO_GUARANTORS.value: {"min": 300_000, "max": 1_000_000},
            },
            "disabled_tariffs": [],
            "special_req": [],
        },
        ProductCategory.phones.value: {
            "terms": {"min": 3, "max": 10},
            "limits": {
                MurabahaTariff.NO_DOWNPAYMENT.value: {"min": 10_000, "max": 60_000},
                MurabahaTariff.ONE_GUARANTOR.value: {"min": 10_000, "max": 300_000},
            },
            "disabled_tariffs": [
                MurabahaTariff.NO_GUARANTOR.value,
                MurabahaTariff.TWO_GUARANTORS.value,
            ],
            "special_req": ["Для телефонов нужен поручитель из близких родственников"],
        },
        ProductCategory.auto.value: {
            "terms": {"min": 3, "max": 12},
            "limits": {
                MurabahaTariff.ONE_GUARANTOR.value: {"min": 200_000, "max": 500_000},
                MurabahaTariff.TWO_GUARANTORS.value: {"min": 500_000, "max": 1_500_000},
            },
            "disabled_tariffs": [
                MurabahaTariff.NO_DOWNPAYMENT.value,
                MurabahaTariff.NO_GUARANTOR.value,
            ],
            "special_req": [],
        },
    }


@dataclass
class MurabahaRateSettings:
    with_down_pct: Decimal = Decimal("4")
    without_down_pct: Decimal = Decimal("5")
    auto_pct: Decimal = Decimal("3.3")


@dataclass
class MurabahaQuote:
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


def _parse_pct(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str) and value.replace(".", "", 1).isdigit():
        return Decimal(value)
    return Decimal(str(value))


async def load_murabaha_rate_settings(db: AsyncSession) -> MurabahaRateSettings:
    keys = [
        SettingKey.MURABAHA_RATE_WITH_DOWN_PCT,
        SettingKey.MURABAHA_RATE_WITHOUT_DOWN_PCT,
        SettingKey.MURABAHA_RATE_AUTO_PCT,
    ]
    rows = await db.execute(select(SystemSetting.key, SystemSetting.value).where(SystemSetting.key.in_(keys)))
    raw = {k: v for k, v in rows.all()}
    defaults = SettingKey.DEFAULTS
    return MurabahaRateSettings(
        with_down_pct=_parse_pct(
            raw.get(SettingKey.MURABAHA_RATE_WITH_DOWN_PCT, defaults[SettingKey.MURABAHA_RATE_WITH_DOWN_PCT])
        ),
        without_down_pct=_parse_pct(
            raw.get(
                SettingKey.MURABAHA_RATE_WITHOUT_DOWN_PCT,
                defaults[SettingKey.MURABAHA_RATE_WITHOUT_DOWN_PCT],
            )
        ),
        auto_pct=_parse_pct(
            raw.get(SettingKey.MURABAHA_RATE_AUTO_PCT, defaults[SettingKey.MURABAHA_RATE_AUTO_PCT])
        ),
    )


def get_category_config(category: str) -> dict[str, Any]:
    cfg = _category_config().get(category)
    if not cfg:
        raise ValueError(f"Неизвестная категория товара: {category}")
    return cfg


def min_down_payment_pct(category: str, term_months: int, tariff: str) -> int:
    if tariff == MurabahaTariff.NO_DOWNPAYMENT.value:
        return 0
    return 25 if term_months > THRESHOLD_TERM else 20


def max_down_payment_pct() -> int:
    return 90


def allowed_tariffs_for_amount(category: str, amount: int | float | Decimal) -> list[str]:
    cat = get_category_config(category)
    disabled = set(cat.get("disabled_tariffs") or [])
    amount_f = float(amount)
    allowed: list[str] = []
    for key in MurabahaTariff:
        t = key.value
        if t in disabled:
            continue
        lim = cat["limits"].get(t)
        if not lim:
            continue
        if lim["min"] <= amount_f <= lim["max"]:
            allowed.append(t)
    return allowed


def pick_default_tariff(category: str, amount: int | float | Decimal) -> str | None:
    allowed = allowed_tariffs_for_amount(category, amount)
    for pref in TARIFF_ORDER:
        if pref in allowed:
            return pref
    return allowed[0] if allowed else None


def rate_per_month(
    category: str,
    tariff: str,
    rates: MurabahaRateSettings | None = None,
) -> Decimal:
    rates = rates or MurabahaRateSettings()
    if category == ProductCategory.auto.value:
        return rates.auto_pct / Decimal("100")
    if tariff == MurabahaTariff.NO_DOWNPAYMENT.value:
        return rates.without_down_pct / Decimal("100")
    return rates.with_down_pct / Decimal("100")


def _round_markup(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def compute_murabaha_quote(
    *,
    category: str,
    amount: int | float | Decimal,
    term_months: int,
    tariff: str,
    down_payment_pct: int,
    rates: MurabahaRateSettings | None = None,
) -> MurabahaQuote:
    cat = get_category_config(category)
    terms = cat["terms"]
    if term_months < terms["min"] or term_months > terms["max"]:
        raise ValueError(f"Срок должен быть от {terms['min']} до {terms['max']} мес.")

    allowed = allowed_tariffs_for_amount(category, amount)
    if tariff not in allowed:
        raise ValueError("Тариф недоступен для выбранной суммы и категории")

    min_down = min_down_payment_pct(category, term_months, tariff)
    max_down = max_down_payment_pct()
    if down_payment_pct < min_down or down_payment_pct > max_down:
        raise ValueError(f"Взнос должен быть от {min_down}% до {max_down}%")

    if tariff == MurabahaTariff.NO_DOWNPAYMENT.value and down_payment_pct != 0:
        raise ValueError("Для тарифа «Без взноса» взнос должен быть 0%")

    price = Decimal(str(amount))
    rate = rate_per_month(category, tariff, rates)
    markup = _round_markup(price * rate * Decimal(term_months))
    total = price + markup
    down_amount = (total * Decimal(down_payment_pct) / Decimal("100")).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    financed = max(Decimal("0"), total - down_amount)
    monthly = Decimal(str(math.ceil(float(financed) / term_months)))

    rate_pct = rate * Decimal("100")

    return MurabahaQuote(
        product_category=category,
        tariff=tariff,
        principal=price,
        markup=markup,
        total=total,
        down_payment_pct=down_payment_pct,
        down_payment_amount=down_amount,
        financed_amount=financed,
        monthly_payment=monthly,
        duration_months=term_months,
        rate_per_month_pct=rate_pct,
    )


def validate_murabaha_deal(
    *,
    category: str,
    amount: Decimal,
    term_months: int,
    tariff: str,
    down_payment_pct: int,
    principal: Decimal,
    markup: Decimal,
    rates: MurabahaRateSettings | None = None,
) -> MurabahaQuote:
    quote = compute_murabaha_quote(
        category=category,
        amount=amount,
        term_months=term_months,
        tariff=tariff,
        down_payment_pct=down_payment_pct,
        rates=rates,
    )
    if principal != quote.principal:
        raise ValueError("Стоимость товара не совпадает с расчётом тарифа")
    if abs(markup - quote.markup) > MARKUP_TOLERANCE_RUB:
        raise ValueError(
            f"Наценка должна быть {quote.markup} ₽ (допуск ±{MARKUP_TOLERANCE_RUB} ₽)"
        )
    return quote


def tariff_options_payload(category: str, amount: int | float | Decimal) -> dict:
    cat = get_category_config(category)
    allowed_set = set(allowed_tariffs_for_amount(category, amount))
    options = []
    for key in MurabahaTariff:
        t = key.value
        lim = cat["limits"].get(t)
        if not lim:
            continue
        options.append(
            {
                "key": t,
                "label": TARIFF_LABELS[t],
                "enabled": t in allowed_set,
                "amount_min": lim["min"],
                "amount_max": lim["max"],
            }
        )
    return {
        "category": category,
        "category_label": CATEGORY_LABELS.get(category, category),
        "terms_min": cat["terms"]["min"],
        "terms_max": cat["terms"]["max"],
        "special_requirements": cat.get("special_req") or [],
        "tariffs": options,
        "default_tariff": pick_default_tariff(category, amount),
    }
