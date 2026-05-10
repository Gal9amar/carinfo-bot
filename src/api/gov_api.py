"""
data.gov.il – Vehicle data client.
Resources:
  - Main registry (registration, basic specs)
  - Vehicle history (km, engine number, structural changes, originality)
  - Ownership history (all past owners with date + type)
  - WLTP specs (safety features, emissions, airbags, ADAS)
  - Recall notices
"""

import asyncio
import httpx
from typing import Optional

BASE_URL = "https://data.gov.il/api/3/action/datastore_search"

RES_MAIN      = "053cea08-09bc-40ec-8f7a-156f0677aff3"  # רישוי + מפרט בסיסי
RES_HISTORY   = "56063a99-8a3e-4ff4-912e-5966c0279bad"  # ק"מ, מנוע, שינויים
RES_OWNERSHIP = "bb2355dc-9ec7-4f06-9c3f-3344672171da"  # היסטוריית בעלויות
RES_WLTP      = "142afde2-6228-49f9-8a29-9b6c3a0cbe40"  # WLTP: בטיחות, פליטות, ציוד
RES_RECALL    = "2c33523f-87aa-44ec-a736-edbb0a82975e"  # ריקולים לפי דגם


async def _search_q(client: httpx.AsyncClient, resource_id: str, q: str, limit: int = 1) -> list:
    params = {"resource_id": resource_id, "q": q, "limit": limit}
    try:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("records", [])
    except Exception:
        return []


async def _search_filter(client: httpx.AsyncClient, resource_id: str, filters: dict, limit: int = 1) -> list:
    import json
    params = {"resource_id": resource_id, "filters": json.dumps(filters), "limit": limit}
    try:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("records", [])
    except Exception:
        return []


async def fetch_vehicle_data(plate: str) -> Optional[dict]:
    clean = plate.replace("-", "").strip()

    async with httpx.AsyncClient(timeout=15) as client:
        main_records, history_records = await asyncio.gather(
            _search_q(client, RES_MAIN,    clean),
            _search_q(client, RES_HISTORY, clean),
        )

    if not main_records:
        return None

    record = main_records[0]
    raw_plate = str(record.get("mispar_rechev", "")).replace("-", "").strip()
    if raw_plate != clean:
        return None

    if history_records:
        h = history_records[0]
        record["mispar_manoa"]          = h.get("mispar_manoa")
        record["kilometer_test_aharon"] = h.get("kilometer_test_aharon")
        record["shinui_mivne_ind"]      = h.get("shinui_mivne_ind")
        record["gapam_ind"]             = h.get("gapam_ind")
        record["shnui_zeva_ind"]        = h.get("shnui_zeva_ind")
        record["shinui_zmig_ind"]       = h.get("shinui_zmig_ind")
        record["rishum_rishon_dt"]      = h.get("rishum_rishon_dt") or record.get("rishum_rishon_dt")
        record["mkoriut_nm"]            = h.get("mkoriut_nm")

    degem_cd   = record.get("degem_cd") or record.get("sug_degem")
    tozeret_cd = record.get("tozeret_cd")
    mispar     = int(clean)

    async with httpx.AsyncClient(timeout=12) as client:
        tasks = [
            _search_filter(client, RES_OWNERSHIP, {"mispar_rechev": mispar}, limit=50),
            _search_filter(client, RES_WLTP,      {"degem_cd": degem_cd, "tozeret_cd": tozeret_cd}, limit=1) if degem_cd and tozeret_cd else asyncio.coroutine(lambda: [])(),
            _search_filter(client, RES_RECALL,    {"DEGEM": record.get("degem_nm", "")}, limit=5),
        ]
        ownership_records, wltp_records, recall_records = await asyncio.gather(*tasks)

    # Ownership history – sort by date ascending
    if ownership_records:
        ownership_records.sort(key=lambda r: str(r.get("baalut_dt", "")))
        record["_ownership"] = ownership_records

    if wltp_records:
        record["_wltp"] = wltp_records[0]

    if recall_records:
        record["_recalls"] = recall_records

    return record
