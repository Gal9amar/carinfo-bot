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
RES_TAG_NACHE  = "c8b9f9c8-4612-4068-934f-d4acd2e3c06e"  # תגי נכה לפי מספר רכב
RES_RENTAL     = "f6efe89a-fb3d-43a4-bb61-9bf12a9b9099"  # רכבים שנרשמו כ"רכב שכור"
RES_IMPORTER   = "39f455bf-6db0-4926-859d-017f34eacbcb"  # מחירון יבואן לפי דגם+שנה
RES_RECALL_CAR = "36bf1404-0be4-49d2-82dc-2f1ead4a8b93"  # ריקולים לפי מספר רכב ספציפי
RES_SCRAPPED   = "851ecab1-0622-4dbe-a6c7-f950cf82abf9"  # רכבים מבוטלים/גרוטאה


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
        async def _empty():
            return []

        async def _wltp_with_fallback():
            if not degem_cd or not tozeret_cd:
                return []
            shnat = record.get("shnat_yitzur")
            # Try exact year match first
            if shnat:
                res = await _search_filter(client, RES_WLTP,
                    {"degem_cd": degem_cd, "tozeret_cd": tozeret_cd, "shnat_yitzur": shnat}, limit=1)
                if res:
                    return res
            # Fallback: any year for this model
            return await _search_filter(client, RES_WLTP,
                {"degem_cd": degem_cd, "tozeret_cd": tozeret_cd}, limit=1)
        wltp_task = _wltp_with_fallback()
        importer_task = (
            _search_filter(client, RES_IMPORTER, {
                "tozeret_cd": tozeret_cd,
                "degem_cd":   degem_cd,
                "shnat_yitzur": record.get("shnat_yitzur"),
            }, limit=1)
            if degem_cd and tozeret_cd else _empty()
        )
        tasks = [
            _search_filter(client, RES_OWNERSHIP,  {"mispar_rechev": mispar}, limit=50),
            wltp_task,
            _search_filter(client, RES_RECALL_CAR, {"MISPAR_RECHEV": mispar}, limit=10),
            _search_filter(client, RES_TAG_NACHE,  {"MISPAR RECHEV": mispar}, limit=1),
            _search_filter(client, RES_RENTAL,     {"mispar_rechev": mispar}, limit=1),
            importer_task,
            _search_filter(client, RES_SCRAPPED,   {"mispar_rechev": mispar}, limit=1),
        ]
        (ownership_records, wltp_records, recall_records,
         tag_nache_records, rental_records, importer_records,
         scrapped_records) = await asyncio.gather(*tasks)

    # Ownership history – sort by date ascending
    if ownership_records:
        ownership_records.sort(key=lambda r: str(r.get("baalut_dt", "")))
        record["_ownership"] = ownership_records

    if wltp_records:
        record["_wltp"] = wltp_records[0]

    # Recalls: per-car lookup (specific plate) – more accurate than by model
    if recall_records:
        record["_recalls"] = recall_records
        record["_recalls_by_plate"] = True  # flag for formatter

    if tag_nache_records:
        t = tag_nache_records[0]
        record["_tag_nache"] = {
            "sug_tav": t.get("SUG TAV"),
            "hafakat": t.get("TAARICH HAFAKAT TAG"),
        }

    record["_was_rental"] = bool(rental_records)

    if importer_records:
        record["_importer_price"] = importer_records[0].get("mehir")

    if scrapped_records:
        record["_scrapped_dt"] = scrapped_records[0].get("bitul_dt", "")

    return record
