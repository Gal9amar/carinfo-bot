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
import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# GOV_API_BASE lets a proxy in Israel stand in for data.gov.il when the host blocks
# datacenter IPs (it answers 403 to Render). Must accept the same query string.
BASE_URL = os.environ.get("GOV_API_BASE") or "https://data.gov.il/api/3/action/datastore_search"

# Look like a normal browser: data.gov.il's WAF rejects the default python-httpx agent.
GOV_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://data.gov.il/",
}

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
RES_EMISSION_FILTER = "7cb2bd95-bf2e-49b6-aea1-fcb5ff6f0473"  # מסנני חלקיקים להפחתת פליטות
RES_SCRAPPED_2010  = "4e6b9724-4c1e-43f0-909a-154d4cc4e046"  # ביטול סופי 2010-2016
RES_SCRAPPED_2000  = "ec8cbc34-72e1-4b69-9c48-22821ba0bd6c"  # ביטול סופי 2000-2009
RES_ANCHOR_POINTS  = "786b33b5-75c4-42a3-a241-b1af3c9ca487"  # חובת נקודות עיגון למטענים
RES_SAFETY_DISCOUNT = "83bfb278-7be1-4dab-ae2d-40125a923da1"  # זכאות להנחה – מערכות בטיחות
RES_HEAVY_TRUCK    = "cd3acc5c-03c3-4c89-9c54-d40f93c0d790"  # מעל 3.5 טון / ללא קוד דגם
RES_MOTORCYCLE     = "bf9df4e2-d90d-4c0a-a400-19e15af8e95f"  # דו גלגליים
RES_PUBLIC         = "cf29862d-ca25-4691-84f6-1be60dcb4a1e"  # רכב ציבורי פעיל

# סדר חיפוש כשהרכב לא נמצא במרשם הראשי: (resource, תווית סוג)
_FALLBACK_REGISTRIES = (
    (RES_MOTORCYCLE,  "אופנוע / דו גלגלי"),
    (RES_PUBLIC,      "רכב ציבורי"),
    (RES_HEAVY_TRUCK, "רכב כבד (מעל 3.5 טון) / ללא קוד דגם"),
)

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


class GovUnavailable(Exception):
    """data.gov.il could not be reached (as opposed to 'no such vehicle')."""


async def _search_filter(
    client: httpx.AsyncClient, resource_id: str, filters: dict, limit: int = 1,
    strict: bool = False,
) -> list:
    params = {"resource_id": resource_id, "filters": json.dumps(filters, ensure_ascii=False), "limit": limit}
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = await client.get(BASE_URL, params=params)
            resp.raise_for_status()
            return resp.json().get("result", {}).get("records", [])
        except Exception as exc:
            last_exc = exc
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (400, 403, 404):
                break
            if attempt < 2:
                await asyncio.sleep(0.4 * (attempt + 1))
    logger.warning("gov_api _search_filter failed resource=%s filters=%s: %s", resource_id, filters, last_exc)
    if strict:
        raise GovUnavailable(str(last_exc))
    return []



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


async def _fetch_fallback_vehicle(mispar: int) -> Optional[dict]:
    """Plate not in main registry: try motorcycles, heavy trucks, public vehicles."""
    async with httpx.AsyncClient(timeout=15, headers=GOV_HEADERS) as client:
        results = await asyncio.gather(*[
            _search_filter(client, res, {"mispar_rechev": mispar}, limit=1)
            for res, _ in _FALLBACK_REGISTRIES
        ])
    for (_, label), recs in zip(_FALLBACK_REGISTRIES, results):
        if recs:
            record = recs[0]
            record["_vehicle_class"] = label
            return record

    # Final cancellation registries (vehicle left the road)
    padded = f"{mispar:08d}"
    async with httpx.AsyncClient(timeout=15, headers=GOV_HEADERS) as client:
        scrapped = await asyncio.gather(
            _search_filter(client, RES_SCRAPPED, {"mispar_rechev": mispar}, limit=1),
            _search_filter(client, RES_SCRAPPED_2010, {"mispar_rechev": padded}, limit=1),
            _search_filter(client, RES_SCRAPPED_2000, {"mispar_rechev": padded}, limit=1),
        )
    for recs in scrapped:
        if recs:
            record = recs[0]
            record["_scrapped_dt"] = record.get("bitul_dt", "")
            return record
    return None


async def fetch_vehicle_data(plate: str) -> Optional[dict]:
    """Registry lookup. Latency matters (the user waits on it), so everything that only needs the plate
    number starts immediately and together with the main record, over ONE shared connection pool; the
    few lookups that need the main record (WLTP, importer price, same-model count, model recalls) then
    run in parallel with each other instead of one after another."""
    clean = plate.replace("-", "").strip()
    mispar = int(clean)

    limits = httpx.Limits(max_connections=20, max_keepalive_connections=20)
    async with httpx.AsyncClient(timeout=15, headers=GOV_HEADERS, limits=limits) as client:
        # Plate-only lookups: independent of the main record, so they start right away.
        side = asyncio.ensure_future(asyncio.gather(
            _search_filter(client, RES_OWNERSHIP, {"mispar_rechev": mispar}, limit=50),
            _search_filter(client, RES_RECALL_CAR, {"MISPAR_RECHEV": mispar}, limit=10),
            _search_filter(client, RES_TAG_NACHE, {"MISPAR RECHEV": mispar}, limit=1),
            _search_filter(client, RES_INACTIVE, {"mispar_rechev": mispar}, limit=1),
            _search_filter(client, RES_INACTIVE_NODEG, {"mispar_rechev": mispar}, limit=1),
            _search_filter(client, RES_PERSONAL_IMPORT, {"mispar_rechev": mispar}, limit=1),
            _search_filter(client, RES_SCRAPPED, {"mispar_rechev": mispar}, limit=1),
            _search_filter(client, RES_EMISSION_FILTER, {"mispar_rechev": mispar}, limit=1),
            _search_filter(client, RES_SCRAPPED_2010, {"mispar_rechev": f"{mispar:08d}"}, limit=1),
            _search_filter(client, RES_SCRAPPED_2000, {"mispar_rechev": f"{mispar:08d}"}, limit=1),
            _search_filter(client, RES_ANCHOR_POINTS, {"mispar_rechev": mispar}, limit=1),
            _search_filter(client, RES_SAFETY_DISCOUNT, {"mispar_rechev": mispar}, limit=1),
        ))
        try:
            main_records, history_records, ext_records = await asyncio.gather(
                _search_filter(client, RES_MAIN, {"mispar_rechev": mispar}, limit=1, strict=True),
                _search_filter(client, RES_HISTORY, {"mispar_rechev": mispar}, limit=1),
                _search_filter(client, RES_MAIN_EXT, {"mispar_rechev": mispar}, limit=1),
            )
        except BaseException:
            side.cancel()
            raise

        record = main_records[0] if main_records else None
        raw_plate = str(record.get("mispar_rechev", "")).replace("-", "").strip() if record else ""
        if not record or raw_plate != clean:
            side.cancel()
            try:
                await side
            except BaseException:
                pass
            return await _fetch_fallback_vehicle(mispar) if not record else None

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

        async def _same_model_count():
            _degem, _tozeret = str(degem_cd or "").strip(), str(tozeret_cd or "").strip()
            if not (_degem and _tozeret):
                return None
            try:
                _filters = {"tozeret_cd": int(float(_tozeret)), "degem_cd": int(float(_degem))}
                if record.get("shnat_yitzur"):
                    _filters["shnat_yitzur"] = record["shnat_yitzur"]
                _r = await client.get(BASE_URL, params={
                    "resource_id": RES_MAIN, "filters": json.dumps(_filters), "limit": 1,
                })
                return _r.json().get("result", {}).get("total")
            except Exception as exc:
                logger.warning("same_model_count failed plate=%s: %s", clean, exc)
                return None

        importer_task = (
            _search_filter(client, RES_IMPORTER, {
                "tozeret_cd": tozeret_cd,
                "degem_cd": degem_cd,
                "shnat_yitzur": record.get("shnat_yitzur"),
            }, limit=1)
            if degem_cd and tozeret_cd else _empty()
        )

        # Needs the main record; model recalls are only used when the plate has no recall of its own
        # (started speculatively — one cheap request — so they don't add a serial round-trip).
        (wltp_records, importer_records, same_model_total, model_recalls), (
            ownership_records, recall_car_records,
            tag_nache_records, inactive_records, inactive_nodeg_records,
            import_records, scrapped_records, filter_records,
            scrapped_2010, scrapped_2000, anchor_records, safety_discount_records,
        ) = await asyncio.gather(
            asyncio.gather(_wltp_with_fallback(), importer_task, _same_model_count(),
                           _fetch_model_recalls(client, record)),
            side,
        )

    if ownership_records:
        ownership_records.sort(key=lambda r: str(r.get("baalut_dt", "")))
        record["_ownership"] = ownership_records

    if wltp_records:
        record["_wltp"] = wltp_records[0]

    if recall_car_records:
        record["_recalls"] = recall_car_records
        record["_recalls_by_plate"] = True
    elif model_recalls:
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

    if filter_records:
        record["_emission_filter"] = filter_records[0]

    scrapped_any = scrapped_records or scrapped_2010 or scrapped_2000
    if scrapped_any:
        record["_scrapped_dt"] = scrapped_any[0].get("bitul_dt", "")

    record["_anchor_points_required"] = bool(anchor_records)
    record["_safety_discount_eligible"] = bool(safety_discount_records)

    if same_model_total is not None:
        record["_same_model_count"] = same_model_total
    return record
