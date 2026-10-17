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
import time
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-5-5"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
PER_USER_LIMIT = 5            # photos per user per window
PER_USER_WINDOW = 3600        # seconds
GLOBAL_DAILY_LIMIT = 300      # hard cost cap across all users

_PLATE_RE = re.compile(r"^\d{5,8}$")
_user_hits: dict[int, deque] = defaultdict(deque)
_day = {"date": "", "count": 0}

_PROMPT = (
    "This photo may contain an Israeli vehicle licence plate. Israeli plates are 5-8 digits "
    "(usually 7 or 8), often shown as 12-345-67 or 123-45-678 on a yellow background. "
    "Reply with JSON only, no other text: {\"plate\": \"<digits only>\"} for the plate that is "
    "most prominent in the photo, or {\"plate\": null} if you cannot read one with confidence."
)


def key_configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def allow(user_id: int) -> bool:
    """Per-user + global daily rate limit. Records the hit when allowed."""
    now = time.time()
    today = time.strftime("%Y-%m-%d")
    if _day["date"] != today:
        _day.update(date=today, count=0)
    if _day["count"] >= GLOBAL_DAILY_LIMIT:
        return False
    hits = _user_hits[user_id]
    while hits and now - hits[0] > PER_USER_WINDOW:
        hits.popleft()
    if len(hits) >= PER_USER_LIMIT:
        return False
    hits.append(now)
    _day["count"] += 1
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
    client = anthropic.AsyncAnthropic(timeout=30.0, max_retries=1)
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
        logger.warning("plate OCR failed: %s", type(exc).__name__)
        return None
    text = "".join(b.text for b in response.content if b.type == "text")
    return parse_plate(text)
