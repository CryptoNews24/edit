# CryptoSentinel drop-in (from live desk)

Copied from the hosted desk at aqua-goldfish-684764.hostingersite.com, then patched.

## What this folder is
The Hostinger **backend** (FastAPI `/api`) is not in GitHub. These are the **static files** the desk already serves, plus:

1. **Pumps** — Binance USDT-M **futures top gainers** only. Slider locked at **500%**. One Telegram when a name hits +500%. Spot ignored.
2. **ONG bot** — paper hedge inside **Auto Trades** (separated section) + Settings tab **ONG bot**. **$500**, take **+$15 or +$20**, flatten, re-enter, **3-day** clock, **Total P&L WIN/LOSS**. Optional unattended runner: `python3 ong_paper_bot.py` (default TP $15).

## Copy onto Hostinger
File Manager → `public_html`:

- `index.html` → replace
- `js/app.js` → replace
- `css/app.css` → replace
- optional: `pump_futures_worker.py` on the VPS for 24/7 Telegram if the browser tab is closed
- optional: `python3 ong_paper_bot.py --fresh` for a 3-day unattended paper test (`ONG_TP=15` or `20`)

Hard refresh. Settings → Pump Alerts ON, min **500**, Telegram ON.

If the desk API masks the bot token as `••••••••`, paste the token once more so the browser can send Telegram, or run the worker with `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`.
