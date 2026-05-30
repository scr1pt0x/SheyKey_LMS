"""
Step 2: Normalize and deduplicate raw Sheets data.
Reads from migration/raw_data/*.json
Outputs migration/clean_data/*.json
"""
import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator, model_validator
from thefuzz import fuzz

_HERE = Path(__file__).parent
RAW_DIR = _HERE / "raw_data"
CLEAN_DIR = _HERE / "clean_data"
DEDUP_THRESHOLD = 85


# ─── Client model ─────────────────────────────────────────────────────────────

class RawClient(BaseModel):
    full_name: str
    phone: str
    passport: str | None = None
    address: str | None = None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v: Any) -> str:
        if not v:
            return ""
        clean = re.sub(r"[^\d]", "", str(v))
        if len(clean) == 10:
            clean = "7" + clean
        elif len(clean) == 11 and clean[0] == "8":
            clean = "7" + clean[1:]
        return "+" + clean


# ─── Deal model ───────────────────────────────────────────────────────────────

DEAL_TYPE_ALIASES = {
    "murabaha": ["мурабаха", "murabaha", "мурабах", "мурабаа"],
    "ijara": ["иджара", "ijara", "иджар", "аренда"],
}

DEAL_STATUS_ALIASES = {
    "active": ["активна", "активная", "active", "в работе", "открыта"],
    "closed": ["закрыта", "закрытая", "closed", "погашена", "завершена"],
    "overdue": ["просрочена", "просроченная", "overdue", "просрочка"],
}


def _detect_deal_type(raw: str) -> str:
    r = raw.strip().lower()
    for deal_type, aliases in DEAL_TYPE_ALIASES.items():
        if any(a in r for a in aliases):
            return deal_type
    return "murabaha"


def _detect_deal_status(raw: str | None) -> str:
    if not raw:
        return "active"
    r = raw.strip().lower()
    for status, aliases in DEAL_STATUS_ALIASES.items():
        if any(a in r for a in aliases):
            return status
    return "active"


def _parse_date(raw: Any) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _parse_number(raw: Any) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    clean = re.sub(r"[^\d.,]", "", str(raw)).replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None


class RawDeal(BaseModel):
    client_identifier: str       # phone or full_name to link to client
    deal_type: str = "murabaha"
    principal: float
    markup: float = 0.0
    monthly_rent: float | None = None
    buyout_amount: float | None = None
    duration_months: int
    start_date: str | None = None
    status: str = "active"
    paid_installments: int = 0   # number of installments already paid


# ─── Sheet detection ──────────────────────────────────────────────────────────

def _find_clients_sheet(all_data: dict) -> list[dict]:
    for key in all_data:
        if any(w in key.lower() for w in ["клиент", "client", "физ"]):
            return all_data[key]
    return list(all_data.values())[0] if all_data else []


def _find_deals_sheet(all_data: dict) -> list[dict]:
    for key in all_data:
        if any(w in key.lower() for w in ["сделк", "deal", "займ", "договор", "кредит", "финанс"]):
            return all_data[key]
    return []


DEAL_COLUMN_ALIASES = {
    "client_identifier": ["клиент", "фио", "имя", "телефон", "client", "borrower", "заёмщик"],
    "deal_type":        ["тип", "type", "вид сделки", "продукт"],
    "principal":        ["сумма", "основной долг", "principal", "amount", "тело"],
    "markup":           ["наценка", "markup", "маржа", "доход"],
    "monthly_rent":     ["аренда", "ежемесячный платёж", "rent", "платёж"],
    "buyout_amount":    ["выкуп", "buyout", "стоимость выкупа"],
    "duration_months":  ["срок", "мес", "months", "duration", "период"],
    "start_date":       ["дата начала", "дата выдачи", "start", "выдан", "дата"],
    "status":           ["статус", "status", "состояние"],
    "paid_installments":["оплачено", "выплачено", "paid", "кол-во платежей"],
}


def _detect_deal_column(header: str) -> str | None:
    h = header.strip().lower()
    for field, aliases in DEAL_COLUMN_ALIASES.items():
        if any(a in h for a in aliases):
            return field
    return None


def _parse_deals(rows: list[dict], clients_by_phone: dict, clients_by_name: dict) -> list[dict]:
    if not rows:
        return []

    parsed = []
    for row in rows:
        try:
            # Build field map from row keys
            field_map: dict[str, Any] = {}
            for header, value in row.items():
                field = _detect_deal_column(str(header))
                if field and field not in field_map:
                    field_map[field] = value

            if "principal" not in field_map:
                continue

            principal = _parse_number(field_map.get("principal"))
            if not principal:
                continue

            duration = int(_parse_number(field_map.get("duration_months")) or 12)
            markup = _parse_number(field_map.get("markup")) or 0.0
            monthly_rent = _parse_number(field_map.get("monthly_rent"))
            buyout = _parse_number(field_map.get("buyout_amount"))
            start_date = _parse_date(field_map.get("start_date"))
            status = _detect_deal_status(str(field_map.get("status", "")))
            deal_type = _detect_deal_type(str(field_map.get("deal_type", "murabaha")))
            paid_installments = int(_parse_number(field_map.get("paid_installments")) or 0)

            # Link to client
            client_raw = str(field_map.get("client_identifier", "")).strip()
            client_id = None

            # Try phone match first
            phone_clean = re.sub(r"[^\d]", "", client_raw)
            if phone_clean:
                if phone_clean.startswith("7") and len(phone_clean) == 11:
                    phone_key = "+" + phone_clean
                elif len(phone_clean) == 10:
                    phone_key = "+7" + phone_clean
                else:
                    phone_key = "+" + phone_clean
                client_id = clients_by_phone.get(phone_key)

            # Fallback: fuzzy name match
            if not client_id:
                best_score = 0
                for name, cid in clients_by_name.items():
                    score = fuzz.token_sort_ratio(client_raw.lower(), name.lower())
                    if score > best_score and score >= 70:
                        best_score = score
                        client_id = cid

            if not client_id:
                print(f"Пропуск сделки: не найден клиент '{client_raw}'")
                continue

            parsed.append({
                "id": str(uuid.uuid4()),
                "client_id": client_id,
                "deal_type": deal_type,
                "principal": principal,
                "markup": markup,
                "monthly_rent": monthly_rent,
                "buyout_amount": buyout,
                "duration_months": duration,
                "start_date": start_date,
                "status": status,
                "paid_installments": paid_installments,
            })
        except Exception as exc:
            print(f"Ошибка парсинга сделки: {exc} — строка: {row}")

    print(f"Сделок распознано: {len(parsed)}/{len(rows)}")
    return parsed


# ─── Main transform ───────────────────────────────────────────────────────────

def find_duplicate_clients(clients: list[dict]) -> dict[int, int]:
    duplicates: dict[int, int] = {}
    for i, c1 in enumerate(clients):
        if i in duplicates:
            continue
        for j, c2 in enumerate(clients):
            if j <= i or j in duplicates:
                continue
            name_score = fuzz.token_sort_ratio(c1["full_name"], c2["full_name"])
            phone_match = c1["phone"] and c2["phone"] and c1["phone"] == c2["phone"]
            if name_score >= DEDUP_THRESHOLD or phone_match:
                duplicates[j] = i
                print(f"Деdup: [{j}] '{c2['full_name']}' → [{i}] '{c1['full_name']}' (score={name_score})")
    return duplicates


def transform() -> dict:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    raw_files = list(RAW_DIR.glob("*.json"))
    if not raw_files:
        print("Нет файлов в raw_data. Сначала запустите extract.py")
        return {}

    all_data: dict[str, list[dict]] = {}
    for f in raw_files:
        all_data[f.stem] = json.loads(f.read_text())

    print(f"Загружены листы: {list(all_data.keys())}")

    clients_raw = _find_clients_sheet(all_data)
    deals_raw = _find_deals_sheet(all_data)

    # Parse clients
    clean_clients = []
    seen_phones: set[str] = set()
    for row in clients_raw:
        try:
            c = RawClient(
                full_name=str(row.get("ФИО") or row.get("full_name") or row.get("Имя") or "").strip(),
                phone=str(row.get("Телефон") or row.get("phone") or "").strip(),
                passport=str(row.get("Паспорт") or row.get("passport") or "").strip() or None,
                address=str(row.get("Адрес") or row.get("address") or "").strip() or None,
            )
            if not c.full_name or not c.phone:
                continue
            clean_clients.append({"id": str(uuid.uuid4()), **c.model_dump()})
        except Exception as exc:
            print(f"Клиент пропущен: {exc}")

    dup_map = find_duplicate_clients(clean_clients)
    unique_clients = [c for i, c in enumerate(clean_clients) if i not in dup_map]
    print(f"Клиенты: {len(clients_raw)} сырых → {len(unique_clients)} уникальных")

    # Build lookup maps for deal→client matching
    clients_by_phone = {c["phone"]: c["id"] for c in unique_clients if c.get("phone")}
    clients_by_name = {c["full_name"]: c["id"] for c in unique_clients}

    # Parse deals
    clean_deals = _parse_deals(deals_raw, clients_by_phone, clients_by_name)

    clean_data = {"clients": unique_clients, "deals": clean_deals}
    (CLEAN_DIR / "clean.json").write_text(json.dumps(clean_data, ensure_ascii=False, indent=2))
    print(f"Результат записан в {CLEAN_DIR / 'clean.json'}")
    print(f"Итого: {len(unique_clients)} клиентов, {len(clean_deals)} сделок")
    return clean_data


if __name__ == "__main__":
    transform()
