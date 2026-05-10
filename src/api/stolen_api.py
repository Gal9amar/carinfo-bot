"""
Israel Police – stolen vehicle check.
NOTE: The police stolen vehicle database is not publicly accessible via API.
Users should check manually at: https://www.police.gov.il/stolencars.aspx
"""

from typing import Optional


async def check_stolen(plate: str) -> Optional[bool]:
    """
    Returns None – service not publicly available.
    The police stolen vehicle DB has no open API.
    """
    return None


STOLEN_CHECK_URL = "https://www.police.gov.il/stolencars.aspx"
