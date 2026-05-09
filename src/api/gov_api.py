"""
data.gov.il – Vehicle data client.
Fetches from multiple resources in parallel:
  - Main registry (registration, basic specs)
  - Vehicle history (km, engine number, structural changes, originality)
  - WLTP specs (safety features, emissions, airbags, ADAS, tires)
  - Recall notices
"""

import asyncio
import httpx
from typing import Optional

BASE_URL = "https://data.gov.il/api/3/action/datastore_search"

# Resource IDs
RES_MAIN     = "053cea08-09bc-40ec-8f7a-156f0677aff3"  # רישוי + מפרט בסיסי
RES_HISTORY  = "56063a99-8a3e-4ff4-912e-5966c0279bad"  # היסטוריה: ק"מ, מנוע, שינויים
RES_WLTP     = "142afde2-6228-49f9-8a29-9b6c3a0cbe40"  # WLTP: בטיחות, פליטות, ציוד
RES_RECALL   = "2c33523f-87aa-44ec-a736-edbb0a82975e"  # ריקולים לפי דגם


async def _search(client: httpx.AsyncClient, resource_id: str, filters: dict, limit: int = 1) -> list:
    params = {"resource_id": resource_id, "filters": str(filters).replace("'", '"'), "limit": limit}
    try:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("records", [])
    except Exception:
        return []


async def _search_q(client: httpx.AsyncClient, resource_id: str, q: str, limit: int = 1) -> list:
    params = {"resource_id": resource_id, "q": q, "limit": limit}
    try:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("records", [])
    except Exception:
        return []


async def fetch_vehicle_data(plate: str) -> Optional[dict]:
    """
    Fetches and merges vehicle data from all available gov.il resources.
    Returns a unified dict or None if plate not found.
    """
    clean = plate.replace("-", "").strip()

    async with httpx.AsyncClient(timeout=15) as client:
        # Main + history searched by plate number
        main_task    = _search_q(client, RES_MAIN,    clean)
        history_task = _search_q(client, RES_HISTORY, clean)

        main_records, history_records = await asyncio.gather(main_task, history_task)

    if not main_records:
        return None

    record = main_records[0]

    # Verify plate match
    raw_plate = str(record.get("mispar_rechev", "")).replace("-", "").strip()
    if raw_plate != clean:
        return None

    # Merge history fields
    if history_records:
        h = history_records[0]
        record["mispar_manoa"]        = h.get("mispar_manoa")
        record["kilometer_test_aharon"] = h.get("kilometer_test_aharon")
        record["shinui_mivne_ind"]    = h.get("shinui_mivne_ind")
        record["gapam_ind"]           = h.get("gapam_ind")
        record["shnui_zeva_ind"]      = h.get("shnui_zeva_ind")
        record["shinui_zmig_ind"]     = h.get("shinui_zmig_ind")
        record["rishum_rishon_dt"]    = h.get("rishum_rishon_dt") or record.get("rishum_rishon_dt")
        record["mkoriut_nm"]          = h.get("mkoriut_nm")

    # Fetch WLTP data by degem_cd (model code) — async separately to avoid slowing main lookup
    degem_cd = record.get("degem_cd") or record.get("sug_degem")
    tozeret_cd = record.get("tozeret_cd")
    shnat = record.get("shnat_yitzur")

    if degem_cd and tozeret_cd:
        async with httpx.AsyncClient(timeout=10) as client:
            wltp_task   = _search(client, RES_WLTP,   {"degem_cd": degem_cd, "tozeret_cd": tozeret_cd}, limit=1)
            recall_task = _search(client, RES_RECALL,  {"DEGEM": record.get("degem_nm", "")}, limit=5)
            wltp_records, recall_records = await asyncio.gather(wltp_task, recall_task)

        if wltp_records:
            w = wltp_records[0]
            record["_wltp"] = w

        if recall_records:
            record["_recalls"] = recall_records

    return record
