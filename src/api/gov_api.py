"""
data.gov.il – Vehicle registration API client.
Endpoint: https://data.gov.il/api/3/action/datastore_search
Resource:  053cea08-09bc-40ec-8f7a-156f0677aff3  (private & commercial vehicles)
"""

import httpx
from typing import Optional

RESOURCE_ID = "053cea08-09bc-40ec-8f7a-156f0677aff3"
BASE_URL = "https://data.gov.il/api/3/action/datastore_search"

FIELD_LABELS = {
    "mispar_rechev": "מספר רכב",
    "tozeret_nm": "יצרן",
    "kinuy_mishari": "כינוי מסחרי",
    "shnat_yitzur": "שנת ייצור",
    "degem_nm": "דגם",
    "tzeva_rechev": "צבע",
    "sug_delek_nm": "סוג דלק",
    "mivchan_acharon_dt": "תאריך טסט אחרון",
    "tokef_dt": "תוקף טסט",
    "baalut": "בעלות",
    "misgeret": "מסגרת (שלדה)",
    "horaat_rishum": "הוראת רישום",
    "moed_aliya_lakvish": "מועד עלייה לכביש",
    "kvuzat_zihum": "קבוצת זיהום",
    "sug_rechev_nm": "סוג רכב",
    "mishkal_kolel": "משקל כולל (ק\"ג)",
    "nefach_manoa": "נפח מנוע (סמ\"ק)",
    "koah_sus": "כוח סוס",
    "mispar_moshavim": "מספר מושבים",
    "mispar_dlatot": "מספר דלתות",
    "zmig_kidmi": "צמיג קדמי",
    "zmig_achori": "צמיג אחורי",
    "rishum_rishon_dt": "תאריך רישום ראשון",
}


async def fetch_vehicle_data(plate: str) -> Optional[dict]:
    """Return raw record dict from data.gov.il or None on failure."""
    params = {
        "resource_id": RESOURCE_ID,
        "q": plate.strip(),
        "limit": 1,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    records = data.get("result", {}).get("records", [])
    if not records:
        return None

    record = records[0]
    # Verify the plate actually matches (the `q` param does full-text search)
    raw_plate = str(record.get("mispar_rechev", "")).replace("-", "").strip()
    clean_input = plate.replace("-", "").strip()
    if raw_plate != clean_input:
        return None

    return record
