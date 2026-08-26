# CryptoSentinel drop-in (from live desk)

Copied from the hosted desk at aqua-goldfish-684764.hostingersite.com, then patched.

## What this folder is
The Hostinger **backend** (FastAPI `/api`) is not in GitHub. These are the **static files** the desk already serves, plus:

1. **Pumps** — USDT-M futures only, Telegram at **+500% from 24h low** (spot ignored).
2. **ONG paper** — live Binance spot vs perp, no real orders (`/ong.html` and the **ONG paper** nav tab).

## Copy onto Hostinger
File Manager → `public_html`:

- `index.html` → replace
- `js/app.js` → replace
- `css/app.css` → replace
- `ong.html` → new file
- optional: `pump_futures_worker.py` on the VPS for 24/7 Telegram if the browser tab is closed

Hard refresh. Settings → Pump Alerts ON, min **500**, Telegram ON.

If the desk API masks the bot token as `••••••••`, paste the token once more so the browser can send Telegram, or run the worker with `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`.
