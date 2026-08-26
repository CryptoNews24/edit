#!/usr/bin/env python3
"""USDT-M futures top-gainer catcher.

Watches Binance perpetual USDT pairs (not spot). Ranks 24h gainers.
Sends Telegram once when 24h % (or % from 24h low) hits +500%.
Does not re-ping while it stays above 500%. Pings again only after it
drops back under 500% and crosses again. No orders.

  export TELEGRAM_BOT_TOKEN='...'
  export TELEGRAM_CHAT_ID='...'
  python3 pump_futures_worker.py
"""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

THRESHOLD = 500.0
MIN_VOL_M = float(os.environ.get("PUMP_MIN_VOLUME_M", "0"))
POLL = int(os.environ.get("PUMP_POLL_SEC", "60"))
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
STATE = Path(os.environ.get("PUMP_STATE_FILE", str(Path(__file__).with_name("pump_futures_state.json"))))
TICKER_URLS = (
    "https://www.binance.com/fapi/v1/ticker/24hr",
    "https://fapi.binance.com/fapi/v1/ticker/24hr",
)


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "CryptoSentinelPump/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def tickers():
    last = None
    for url in TICKER_URLS:
        try:
            return get_json(url)
        except Exception as e:
            last = e
    raise last


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            return {}
    return {}


def save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st))


def telegram(text: str) -> None:
    if not TOKEN or not CHAT:
        print("NO_TELEGRAM", text.replace("\n", " | "))
        return
    body = urllib.parse.urlencode(
        {"chat_id": CHAT, "text": text, "disable_web_page_preview": "true"}
    ).encode()
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        r.read()


def scan(fired: dict) -> dict:
    min_vol = MIN_VOL_M * 1_000_000
    hot = {}
    for t in tickers():
        sym = t.get("symbol") or ""
        if not sym.endswith("USDT") or "_" in sym:
            continue
        try:
            last = float(t["lastPrice"])
            low = float(t.get("lowPrice") or 0)
            vol = float(t.get("quoteVolume") or 0)
            ch = float(t.get("priceChangePercent") or 0)
        except (TypeError, ValueError, KeyError):
            continue
        if last <= 0:
            continue
        from_low = (last / low - 1) * 100 if low > 0 else ch
        if min_vol and vol < min_vol:
            continue
        if ch < THRESHOLD and from_low < THRESHOLD:
            continue
        hot[sym] = (ch, from_low, last, vol)

    for sym in list(fired):
        if sym not in hot:
            del fired[sym]

    for sym, (ch, from_low, last, vol) in hot.items():
        if fired.get(sym):
            continue
        pct = max(ch, from_low)
        msg = (
            f"FUTURES TOP GAINER {sym}\n"
            f"+{pct:.0f}% (alert at {THRESHOLD:.0f}%)\n"
            f"24h {ch:.1f}%  from low +{from_low:.0f}%\n"
            f"Last {last}  Vol ${vol/1e6:.1f}M\n"
            f"https://www.binance.com/en/futures/{sym}"
        )
        print(msg.replace("\n", " | "))
        telegram(msg)
        fired[sym] = 1
    save_state(fired)
    return fired


def main() -> None:
    if not TOKEN or not CHAT:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (same as CryptoSentinel Settings).")
    print(f"Watching USDT-M futures top gainers · one Telegram at +{THRESHOLD:.0f}% · poll {POLL}s")
    fired = load_state()
    while True:
        try:
            fired = scan(fired)
        except Exception as e:
            print("scan_error", type(e).__name__, e)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
