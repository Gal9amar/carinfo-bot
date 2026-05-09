"""
Israel Police – stolen vehicle check.
Uses the gov.il public service endpoint.
"""

import httpx
from typing import Optional

STOLEN_URL = "https://data.gov.il/api/3/action/datastore_search"
STOLEN_RESOURCE_ID = "bf9df4e2-d90d-4b07-8e4f-c3b7d90c3ef0"


async def check_stolen(plate: str) -> Optional[bool]:
    """
    Returns:
        True  – vehicle found in stolen registry
        False – vehicle NOT in stolen registry
        None  – check failed / service unavailable
    """
    params = {
        "resource_id": STOLEN_RESOURCE_ID,
        "q": plate.replace("-", "").strip(),
        "limit": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(STOLEN_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
        records = data.get("result", {}).get("records", [])
        return len(records) > 0
    except Exception:
        return None
