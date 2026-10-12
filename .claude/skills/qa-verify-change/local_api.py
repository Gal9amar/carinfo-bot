"""Boot the FastAPI app against a throwaway local libsql file and a fake bot token.

Usage:  python .claude/skills/qa-verify-change/local_api.py [port]   (default 8099)
Needs:  pip install -r requirements.txt   (use a venv, e.g. /tmp/venv)
Then hit it with:  python .claude/skills/qa-verify-change/sign_init_data.py <user_id>
No network / Telegram / Turso needed. Data lives in a temp file, never in prod.
"""
import asyncio, os, sys, tempfile

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("ADMIN_TELEGRAM_ID", "1")
os.environ["TURSO_DATABASE_URL"] = "file:" + os.path.join(tempfile.mkdtemp(), "qa.db")
os.environ.setdefault("TURSO_AUTH_TOKEN", "x")
sys.path.insert(0, os.getcwd())

from src.db import init_db            # noqa: E402
from src.users import load_welcome_settings  # noqa: E402
asyncio.run(init_db())
asyncio.run(load_welcome_settings())

import uvicorn                         # noqa: E402
from api import api                    # noqa: E402
uvicorn.run(api, host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8099, log_level="warning")
