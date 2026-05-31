"""Human-readable deal purchase labels for UI."""
from decimal import Decimal

from backend.models.deal import Deal, DealType


def deal_params_dict(deal: Deal) -> dict:
    return {p.key: p.value for p in deal.params}


def deal_purchase_summary(
    deal_type: str | DealType,
    principal: Decimal | float,
    product_description: str | None = None,
    params: dict | None = None,
) -> str:
    if product_description and str(product_description).strip():
        return str(product_description).strip()

    type_val = deal_type.value if isinstance(deal_type, DealType) else str(deal_type)
    principal_dec = Decimal(str(principal))

    if type_val == DealType.murabaha.value:
        return f"Мурабаха · товар {principal_dec:,.2f} ₽".replace(",", " ")

    if type_val == DealType.ijara.value:
        monthly = None
        if params:
            raw = params.get("monthly_rent")
            if raw is not None:
                monthly = Decimal(str(raw))
        if monthly is not None:
            return f"Иджара · аренда {monthly:,.2f} ₽/мес.".replace(",", " ")
        return "Иджара (лизинг)"

    return type_val


def deal_purchase_summary_from_deal(deal: Deal) -> str:
    return deal_purchase_summary(
        deal.type,
        deal.principal,
        deal.product_description,
        deal_params_dict(deal) if deal.params else None,
    )
