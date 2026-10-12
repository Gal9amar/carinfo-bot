---
name: add-api-endpoint
description: Checklist and code templates for adding or changing a REST endpoint in carinfo-bot - FastAPI route in api.py, Pydantic body, Telegram initData auth (user vs admin), error codes, the matching webapp/src/api.js client function, and backward-compatible JSON. Use whenever a new endpoint or response field is needed.
---

# Add / change an endpoint

Read neighbours first: `grep -n "@api\." api.py | grep <area>`; copy the closest route's style.

## 1. Decide
| Question | Rule |
|---|---|
| Who may call it? | public (rare) / `Depends(_get_user)` / `Depends(_require_admin)`. Admin prefix is `/api/admin/...`. |
| Does it touch another user's data? | Filter by `user["id"]` in SQL (no IDOR). |
| Does it move money/quota? | Server derives price/searches from DB rows; idempotent; status check before mutate; notify through `src/notifier.py`. |
| Business logic? | Put it in `src/<module>.py` (ask `backend-agent`), keep the route thin. |

## 2. Template (api.py)
```python
class WidgetBody(BaseModel):
    name: str
    qty: int = 1

@api.post("/api/widgets")
async def create_widget(body: WidgetBody, user: dict = Depends(_get_user)):
    from src.widgets import add_widget            # lazy import - project convention
    name = body.name.strip()
    if not name or len(name) > 100 or not (1 <= body.qty <= 100):
        raise HTTPException(status_code=400, detail="נתונים לא תקינים")
    wid = await add_widget(user["id"], name, body.qty)
    return {"id": wid, "name": name, "qty": body.qty}

@api.get("/api/admin/widgets")
async def admin_list_widgets(_: dict = Depends(_require_admin)):
    ...
```
- Path params with ids: `@api.delete("/api/widgets/{wid}")` -> verify ownership, `404` if not found/not yours (don't reveal existence).
- Place new routes ABOVE the SPA catch-all `/{full_path:path}` at the end of `api.py` (it swallows anything defined after it).
- Row -> JSON through a `_widget_json(row)` helper; **append-only** fields.
- Errors: `HTTPException(400/403/404/409)`; don't leak exceptions/SQL; log with `logger`/print as neighbours do.

## 3. Frontend client (webapp/src/api.js)
```js
export async function createWidget(name, qty = 1) {
  const r = await fetch(`${BASE}/api/widgets`, {
    method: 'POST', headers: headers(), body: JSON.stringify({ name, qty }),
  })
  if (!r.ok) throw new Error('Failed to create widget')
  return r.json()
}
```
`headers()` already adds `Content-Type` and `X-Init-Data`. Public endpoints may omit headers. Return shapes must be documented in your hand-off to `design-agent`.

## 4. Docs
Update the endpoint table in `CLAUDE.md` (it is stale - add what you touch).

## 5. Verify (hand to qa-agent / run `qa-verify-change`)
anon 401 - non-admin 403 on admin routes - bad input 400/422 - other user's id 404 - happy path - `npm run build`.
