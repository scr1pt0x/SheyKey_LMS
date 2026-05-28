"""
Step 1: Extract raw data from Google Sheets.
Run: python extract.py
Requires: GOOGLE_SERVICE_ACCOUNT_JSON env var or credentials file.
"""
import json
import os
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "")
_HERE = Path(__file__).parent
SERVICE_ACCOUNT_FILE = os.environ.get(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    str(_HERE / "service_account.json"),
)
OUTPUT_DIR = _HERE / "raw_data"


def extract() -> dict[str, list[dict]]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    result: dict[str, list[dict]] = {}

    for worksheet in spreadsheet.worksheets():
        title = worksheet.title
        records = worksheet.get_all_records()
        result[title] = records
        output_path = OUTPUT_DIR / f"{title}.json"
        output_path.write_text(json.dumps(records, ensure_ascii=False, indent=2))
        print(f"Extracted sheet '{title}': {len(records)} rows → {output_path}")

    return result


if __name__ == "__main__":
    extract()
