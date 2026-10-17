"""Read an Israeli licence-plate number from a photo with Claude vision.

Opt-in: needs ANTHROPIC_API_KEY and the admin setting ``photo_plate_enabled``.
Only digits are ever extracted from the model's reply, so text inside the photo
cannot steer the bot (the result still goes through the normal confirm + lookup).
"""

import base64
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-5-5"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
PER_USER_LIMIT = 3            # photos per user per hour
GLOBAL_DAILY_LIMIT = 300      # hard cost cap across all users (per UTC day)

_PLATE_RE = re.compile(r"^\d{5,8}$")
_client = None

_PROMPT = (
    "This photo may contain an Israeli vehicle licence plate. Israeli plates are 5-8 digits "
    "(usually 7 or 8), often shown as 12-345-67 or 123-45-678 on a yellow background. "
    "Reply with JSON only, no other text: {\"plate\": \"<digits only>\"} for the plate that is "
    "most prominent in the photo, or {\"plate\": null} if you cannot read one with confidence."
)


def key_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


async def allow(user_id: int) -> bool:
    """Per-user hourly + global daily cap, persisted in the DB so restarts and extra
    instances share the same counters. Records the attempt when allowed."""
    from src.db import execute
    await execute("DELETE FROM photo_ocr_log WHERE at < datetime('now', '-2 days')")
    r = await execute("SELECT COUNT(*) FROM photo_ocr_log WHERE at >= date('now')")
    if int(r.rows[0][0]) >= GLOBAL_DAILY_LIMIT:
        return False
    r = await execute(
        "SELECT COUNT(*) FROM photo_ocr_log WHERE user_id=? AND at >= datetime('now', '-1 hour')", [user_id]
    )
    if int(r.rows[0][0]) >= PER_USER_LIMIT:
        return False
    await execute("INSERT INTO photo_ocr_log (user_id) VALUES (?)", [user_id])
    return True


def parse_plate(reply_text: str) -> str | None:
    """Extract a plate from the model reply. Digits only; None if not plausible."""
    text = (reply_text or "").strip()
    candidate = None
    try:
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start:end + 1])
        candidate = data.get("plate")
    except Exception:
        candidate = None
    if not candidate:
        return None
    digits = re.sub(r"\D", "", str(candidate))
    return digits if _PLATE_RE.match(digits) else None


async def read_plate(image_bytes: bytes, media_type: str = "image/jpeg") -> str | None:
    if len(image_bytes) > MAX_IMAGE_BYTES or not key_configured():
        return None
    import anthropic
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(timeout=30.0, max_retries=1)
    client = _client
    try:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=200,
            output_config={"effort": "low"},
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": media_type,
                        "data": base64.standard_b64encode(image_bytes).decode("utf-8"),
                    }},
                    {"type": "text", "text": _PROMPT},
                ],
            }],
        )
    except anthropic.APIError as exc:
        logger.warning("plate OCR failed: %s status=%s", type(exc).__name__, getattr(exc, "status_code", None))
        return None
    text = "".join(b.text for b in response.content if b.type == "text")
    return parse_plate(text)
