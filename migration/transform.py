"""
Step 2: Normalize and deduplicate raw Sheets data.
Reads from migration/raw_data/*.json
Outputs migration/clean_data/*.json
"""
import json
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator
from thefuzz import fuzz

_HERE = Path(__file__).parent
RAW_DIR = _HERE / "raw_data"
CLEAN_DIR = _HERE / "clean_data"
DEDUP_THRESHOLD = 85  # fuzzy match threshold for client deduplication


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


class RawDeal(BaseModel):
    client_identifier: str
    deal_type: str
    principal: float
    markup: float | None = 0.0
    duration_months: int
    start_date: str | None = None
    status: str = "active"


def find_duplicate_clients(clients: list[dict]) -> dict[int, int]:
    """Returns a mapping of duplicate index → canonical index."""
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
                print(
                    f"Dedup: [{j}] '{c2['full_name']}' → [{i}] '{c1['full_name']}' "
                    f"(score={name_score}, phone_match={phone_match})"
                )
    return duplicates


def transform() -> dict:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    raw_files = list(RAW_DIR.glob("*.json"))
    if not raw_files:
        print("No raw data files found. Run extract.py first.")
        return {}

    all_data = {}
    for f in raw_files:
        all_data[f.stem] = json.loads(f.read_text())

    print(f"Loaded sheets: {list(all_data.keys())}")

    clients_raw = _find_clients_sheet(all_data)
    deals_raw = _find_deals_sheet(all_data)

    clean_clients = []
    seen_phones: set[str] = set()
    for row in clients_raw:
        try:
            c = RawClient(
                full_name=str(row.get("ФИО") or row.get("full_name") or "").strip(),
                phone=str(row.get("Телефон") or row.get("phone") or "").strip(),
                passport=str(row.get("Паспорт") or row.get("passport") or "").strip() or None,
                address=str(row.get("Адрес") or row.get("address") or "").strip() or None,
            )
            if not c.full_name or not c.phone:
                print(f"Skipping client with missing name/phone: {row}")
                continue
            clean_clients.append({"id": str(uuid.uuid4()), **c.model_dump()})
        except Exception as exc:
            print(f"Client parse error: {exc} — row: {row}")

    # Deduplicate
    dup_map = find_duplicate_clients(clean_clients)
    unique_clients = [c for i, c in enumerate(clean_clients) if i not in dup_map]
    print(f"Clients: {len(clients_raw)} raw → {len(clean_clients)} parsed → {len(unique_clients)} unique")

    clean_data = {"clients": unique_clients, "deals": deals_raw}
    (CLEAN_DIR / "clean.json").write_text(json.dumps(clean_data, ensure_ascii=False, indent=2))
    print(f"Clean data written to {CLEAN_DIR / 'clean.json'}")
    return clean_data


def _find_clients_sheet(all_data: dict) -> list[dict]:
    for key in all_data:
        if "клиент" in key.lower() or "client" in key.lower():
            return all_data[key]
    return list(all_data.values())[0] if all_data else []


def _find_deals_sheet(all_data: dict) -> list[dict]:
    for key in all_data:
        if "сделк" in key.lower() or "deal" in key.lower() or "займ" in key.lower():
            return all_data[key]
    return []


if __name__ == "__main__":
    transform()
