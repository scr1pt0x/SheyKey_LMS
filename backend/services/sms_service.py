"""SMS.ru integration for sending SMS to clients."""
import httpx

from backend.core.config import settings

SMS_RU_BASE_URL = "https://sms.ru/sms/send"


async def _get_sms_credentials() -> tuple[str, str | None]:
    """
    Returns (api_key, sender_name).
    Prefers values from system_settings (DB) over .env,
    so the director can change them via UI without redeploying.
    """
    try:
        from sqlalchemy import select
        from backend.core.database import AsyncSessionLocal
        from backend.models.settings import SystemSetting

        async with AsyncSessionLocal() as db:
            rows = await db.execute(
                select(SystemSetting.key, SystemSetting.value)
                .where(SystemSetting.key.in_(["sms_api_key", "sms_from"]))
            )
            db_settings = {r[0]: r[1] for r in rows.all()}

        api_key = db_settings.get("sms_api_key") or settings.SMS_RU_API_KEY
        sender = db_settings.get("sms_from") or settings.SMS_RU_FROM or None
        return api_key, sender
    except Exception:
        return settings.SMS_RU_API_KEY, settings.SMS_RU_FROM or None


async def send_sms(phone: str, message: str) -> dict:
    """
    Send an SMS via SMS.ru REST API.
    Raises RuntimeError on API-level errors.
    """
    api_key, sender_name = await _get_sms_credentials()
    if not api_key:
        raise RuntimeError("SMS.ru API key not configured")

    clean_phone = phone.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    if not clean_phone.startswith("7"):
        clean_phone = "7" + clean_phone.lstrip("8")

    params: dict = {
        "api_id": api_key,
        "to": clean_phone,
        "msg": message,
        "json": 1,
    }
    if sender_name:
        params["from"] = sender_name

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(SMS_RU_BASE_URL, data=params)
        response.raise_for_status()
        data = response.json()

    if data.get("status") != "OK":
        status_code = data.get("status_code")
        raise RuntimeError(f"SMS.ru error: status={data.get('status')}, code={status_code}")

    sms_data = data.get("sms", {}).get(clean_phone, {})
    if sms_data.get("status") != "OK":
        raise RuntimeError(f"SMS.ru failed for {clean_phone}: {sms_data}")

    return {"sms_id": sms_data.get("sms_id"), "status": "sent"}
