"""Print a valid Telegram WebApp initData string for local testing.

Usage:  python sign_init_data.py <user_id> [bot_token]
Use with:  curl -H "X-Init-Data: $(python sign_init_data.py 1)" localhost:8099/api/user
Admin = the user_id equal to ADMIN_TELEGRAM_ID (local_api.py sets it to 1).
"""
import hashlib, hmac, json, sys, time
from urllib.parse import urlencode

uid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
token = sys.argv[2] if len(sys.argv) > 2 else "123456:TESTTOKEN"
fields = {
    "user": json.dumps({"id": uid, "first_name": "QA", "username": f"qa{uid}"}, separators=(",", ":")),
    "auth_date": str(int(time.time())),
}
check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
print(urlencode(fields))
