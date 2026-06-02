"""
data.gov.il – Vehicle data client.
Resources:
  - Main registry + extension (tires, towing)
  - Vehicle history (km, engine, structural changes)
  - Ownership history
  - WLTP specs
  - Recalls (per plate, fallback per model)
  - Disability tags, scrapped, importer price
  - Personal import, inactive registries
"""

import asyncio
import json
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://data.gov.il/api/3/action/datastore_search"

RES_MAIN           = "053cea08-09bc-40ec-8f7a-156f0677aff3"  # רישוי + מפרט בסיסי
RES_MAIN_EXT       = "0866573c-40cd-4ca8-91d2-9dd2d7a492e5"  # המשך מרשם: גרירה, קודי צמיג
RES_HISTORY        = "56063a99-8a3e-4ff4-912e-5966c0279bad"  # ק"מ, מנוע, שינויים
RES_OWNERSHIP      = "bb2355dc-9ec7-4f06-9c3f-3344672171da"  # היסטוריית בעלויות
RES_WLTP           = "142afde2-6228-49f9-8a29-9b6c3a0cbe40"  # WLTP
RES_RECALL         = "2c33523f-87aa-44ec-a736-edbb0a82975e"  # ריקולים לפי דגם
RES_TAG_NACHE      = "c8b9f9c8-4612-4068-934f-d4acd2e3c06e"  # תגי נכה
RES_INACTIVE       = "f6efe89a-fb3d-43a4-bb61-9bf12a9b9099"  # רכב לא פעיל (עם קוד דגם)
RES_INACTIVE_NODEG = "6f6acd03-f351-4a8f-8ecf-df792f4f573a"  # רכב לא פעיל ללא קוד דגם
RES_PERSONAL_IMPORT = "03adc637-b6fe-402b-9937-7c3d3afc9140"  # יבוא אישי
RES_IMPORTER       = "39f455bf-6db0-4926-859d-017f34eacbcb"  # מחירון יבואן
RES_RECALL_CAR     = "36bf1404-0be4-49d2-82dc-2f1ead4a8b93"  # ריקולים לפי לוחית
RES_SCRAPPED       = "851ecab1-0622-4dbe-a6c7-f950cf82abf9"  # גרוטאה

# שדות מהמשך מרשם הרישוי
_EXT_FIELDS = (
    "grira_nm",
    "kod_omes_tzmig_kidmi",
    "kod_omes_tzmig_ahori",
    "kod_mehirut_tzmig_kidmi",
    "kod_mehirut_tzmig_ahori",
)


async def _search_q(client: httpx.AsyncClient, resource_id: str, q: str, limit: int = 1) -> list:
    params = {"resource_id": resource_id, "q": q, "limit": limit}
    try:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("records", [])
    except Exception as exc:
        logger.warning("gov_api _search_q failed resource=%s q=%s: %s", resource_id, q, exc)
        return []


async def _search_filter(
    client: httpx.AsyncClient, resource_id: str, filters: dict, limit: int = 1,
) -> list:
    params = {"resource_id": resource_id, "filters": json.dumps(filters, ensure_ascii=False), "limit": limit}
    try:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("records", [])
    except Exception as exc:
        logger.warning("gov_api _search_filter failed resource=%s filters=%s: %s", resource_id, filters, exc)
        return []


async def _count_filter(
    client: httpx.AsyncClient, resource_id: str, filters: dict,
) -> Optional[int]:
    # limit=1 is more reliable than limit=0 — some CKAN instances return total=0 for limit=0
    params = {"resource_id": resource_id, "filters": json.dumps(filters, ensure_ascii=False), "limit": 1}
    try:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("total")
    except Exception as exc:
        logger.warning("gov_api _count_filter failed resource=%s filters=%s: %s", resource_id, filters, exc)
        return None


def _merge_ext_fields(record: dict, ext: dict) -> None:
    for key in _EXT_FIELDS:
        val = ext.get(key)
        if val is not None and str(val).strip() not in ("", "None", "nan"):
            record[key] = val


def _year_in_recall_range(recall: dict, year: int) -> bool:
    try:
        begin = int(str(recall.get("BUILD_BEGIN_A", ""))[:4])
        end = int(str(recall.get("BUILD_END_A", ""))[:4])
        return begin <= year <= end
    except Exception:
        return True


async def _fetch_model_recalls(
    client: httpx.AsyncClient, record: dict, limit: int = 15,
) -> list:
    """Fallback recalls by commercial model name + production year."""
    query = (
        str(record.get("kinuy_mishari") or "")
        or str(record.get("degem_nm") or "")
    ).strip()
    if len(query) < 2:
        return []
    raw = await _search_q(client, RES_RECALL, query[:24], limit=limit)
    if not raw:
        return []
    try:
        year = int(record.get("shnat_yitzur"))
    except (TypeError, ValueError):
        return raw[:10]
    matched = [r for r in raw if _year_in_recall_range(r, year)]
    return (matched or raw)[:10]


async def fetch_vehicle_data(plate: str) -> Optional[dict]:
    clean = plate.replace("-", "").strip()

    async with httpx.AsyncClient(timeout=15) as client:
        main_records, history_records, ext_records = await asyncio.gather(
            _search_q(client, RES_MAIN, clean),
            _search_q(client, RES_HISTORY, clean),
            _search_filter(client, RES_MAIN_EXT, {"mispar_rechev": int(clean)}, limit=1),
        )

    if not main_records:
        return None

    record = main_records[0]
    raw_plate = str(record.get("mispar_rechev", "")).replace("-", "").strip()
    if raw_plate != clean:
        return None

    if ext_records:
        _merge_ext_fields(record, ext_records[0])

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
            if shnat:
                res = await _search_filter(
                    client, RES_WLTP,
                    {"degem_cd": degem_cd, "tozeret_cd": tozeret_cd, "shnat_yitzur": shnat},
                    limit=1,
                )
                if res:
                    return res
            return await _search_filter(
                client, RES_WLTP, {"degem_cd": degem_cd, "tozeret_cd": tozeret_cd}, limit=1,
            )

        importer_task = (
            _search_filter(client, RES_IMPORTER, {
                "tozeret_cd": tozeret_cd,
                "degem_cd": degem_cd,
                "shnat_yitzur": record.get("shnat_yitzur"),
            }, limit=1)
            if degem_cd and tozeret_cd else _empty()
        )

        tasks = [
            _search_filter(client, RES_OWNERSHIP, {"mispar_rechev": mispar}, limit=50),
            _wltp_with_fallback(),
            _search_filter(client, RES_RECALL_CAR, {"MISPAR_RECHEV": mispar}, limit=10),
            _search_filter(client, RES_TAG_NACHE, {"MISPAR RECHEV": mispar}, limit=1),
            _search_filter(client, RES_INACTIVE, {"mispar_rechev": mispar}, limit=1),
            _search_filter(client, RES_INACTIVE_NODEG, {"mispar_rechev": mispar}, limit=1),
            _search_filter(client, RES_PERSONAL_IMPORT, {"mispar_rechev": mispar}, limit=1),
            importer_task,
            _search_filter(client, RES_SCRAPPED, {"mispar_rechev": mispar}, limit=1),
        ]
        (
            ownership_records, wltp_records, recall_car_records,
            tag_nache_records, inactive_records, inactive_nodeg_records,
            import_records, importer_records, scrapped_records,
        ) = await asyncio.gather(*tasks)

    # Same-model count — convert codes to int to match CKAN's stored type
    same_model_filters = {}
    try:
        if tozeret_cd is not None:
            same_model_filters["tozeret_cd"] = int(float(str(tozeret_cd)))
        if degem_cd is not None:
            same_model_filters["degem_cd"] = int(float(str(degem_cd)))
        shnat = record.get("shnat_yitzur")
        if shnat is not None:
            same_model_filters["shnat_yitzur"] = int(float(str(shnat)))
    except (ValueError, TypeError):
        pass
    if same_model_filters:
        async with httpx.AsyncClient(timeout=20) as client:
            same_model_count = await _count_filter(client, RES_MAIN, same_model_filters)
    else:
        same_model_count = None

    if ownership_records:
        ownership_records.sort(key=lambda r: str(r.get("baalut_dt", "")))
        record["_ownership"] = ownership_records

    if wltp_records:
        record["_wltp"] = wltp_records[0]

    if recall_car_records:
        record["_recalls"] = recall_car_records
        record["_recalls_by_plate"] = True
    else:
        async with httpx.AsyncClient(timeout=12) as client:
            model_recalls = await _fetch_model_recalls(client, record)
        if model_recalls:
            record["_recalls"] = model_recalls
            record["_recalls_by_plate"] = False

    if tag_nache_records:
        t = tag_nache_records[0]
        record["_tag_nache"] = {
            "sug_tav": t.get("SUG TAV"),
            "hafakat": t.get("TAARICH HAFAKAT TAG"),
        }

    record["_inactive_registry"] = bool(inactive_records)
    record["_inactive_no_degem"] = bool(inactive_nodeg_records)
    # תאימות לאחור (שדה ישן — לא השכרה)
    record["_was_rental"] = record["_inactive_registry"]

    if import_records:
        record["_personal_import"] = import_records[0]

    if importer_records:
        record["_importer_price"] = importer_records[0].get("mehir")

    if scrapped_records:
        record["_scrapped_dt"] = scrapped_records[0].get("bitul_dt", "")

    if same_model_count is not None:
        record["_same_model_count"] = same_model_count

    return record
