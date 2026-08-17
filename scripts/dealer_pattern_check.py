"""
Read-only analysis: find users whose search behavior looks like a
car dealer (many distinct plates, especially in short bursts) rather
than a private owner checking their own car.

Usage:
    TURSO_DATABASE_URL=... TURSO_AUTH_TOKEN=... python3 scripts/dealer_pattern_check.py

Only reads from search_history / users — makes no writes.
"""
import asyncio
import os
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import execute  # noqa: E402

# A user is "dealer-like" if, in any rolling 1-hour window, they searched
# at least this many DISTINCT plates.
BURST_WINDOW_MINUTES = 60
BURST_DISTINCT_PLATES = 5

# Overall: total distinct plates ever searched, as a softer signal.
TOTAL_DISTINCT_THRESHOLD = 15


async def main():
    r = await execute(
        "SELECT user_id, plate, searched_at FROM search_history ORDER BY user_id, searched_at",
        [],
    )

    by_user = defaultdict(list)
    for row in r.rows:
        uid, plate, ts = row[0], row[1], row[2]
        by_user[uid].append((_parse(ts), plate))

    burst_flagged = {}
    for uid, events in by_user.items():
        events.sort()
        max_distinct_in_window = 0
        for i, (t0, _) in enumerate(events):
            window_plates = set()
            for t1, plate in events[i:]:
                if (t1 - t0).total_seconds() > BURST_WINDOW_MINUTES * 60:
                    break
                window_plates.add(plate)
            max_distinct_in_window = max(max_distinct_in_window, len(window_plates))
        if max_distinct_in_window >= BURST_DISTINCT_PLATES:
            burst_flagged[uid] = max_distinct_in_window

    total_distinct = {
        uid: len({p for _, p in events}) for uid, events in by_user.items()
    }
    total_flagged = {
        uid: n for uid, n in total_distinct.items() if n >= TOTAL_DISTINCT_THRESHOLD
    }

    print(f"Users total: {len(by_user)}")
    print(f"Burst pattern (>= {BURST_DISTINCT_PLATES} distinct plates within "
          f"{BURST_WINDOW_MINUTES}min): {len(burst_flagged)}")
    print(f"High lifetime distinct plates (>= {TOTAL_DISTINCT_THRESHOLD}): {len(total_flagged)}")
    print()

    combined = sorted(
        set(burst_flagged) | set(total_flagged),
        key=lambda u: total_distinct.get(u, 0),
        reverse=True,
    )[:30]

    if not combined:
        print("No users matched either signal.")
        return

    print(f"{'user_id':>12}  {'total_distinct':>14}  {'max_burst':>10}  total_searches")
    for uid in combined:
        total_searches = len(by_user[uid])
        print(f"{uid:>12}  {total_distinct.get(uid, 0):>14}  "
              f"{burst_flagged.get(uid, 0):>10}  {total_searches}")


def _parse(ts: str) -> datetime:
    ts = ts.replace("Z", "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized timestamp format: {ts!r}")


if __name__ == "__main__":
    asyncio.run(main())
