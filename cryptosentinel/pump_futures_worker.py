#!/usr/bin/env python3
"""USDT-M futures pump catcher for CryptoSentinel.

Scans Binance perpetual USDT pairs. Alerts Telegram when last price is
+500% (configurable) above the 24h low. No orders. Spot is ignored.

Run next to the desk (VPS / Hostinger cron) so alerts fire even if the
browser tab is closed:

  export TELEGRAM_BOT_TOKEN='...'
  export TELEGRAM_CHAT_ID='...'
  python3 pump_futures_worker.py

Optional:
  PUMP_THRESHOLD_PCT=500
  PUMP_MIN_VOLUME_M=0
  PUMP_POLL_SEC=60
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

THRESHOLD = float(os.environ.get("PUMP_THRESHOLD_PCT", "500"))
MIN_VOL_M = float(os.environ.get("PUMP_MIN_VOLUME_M", "0"))
POLL = int(os.environ.get("PUMP_POLL_SEC", "60"))
COOLDOWN = int(os.environ.get("PUMP_COOLDOWN_SEC", str(6 * 3600)))
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


def scan(state: dict) -> dict:
    now = time.time()
    min_vol = MIN_VOL_M * 1_000_000
    hits = []
    for t in tickers():
        sym = t.get("symbol") or ""
        if not sym.endswith("USDT") or "_" in sym:
            continue
        try:
            last = float(t["lastPrice"])
            low = float(t["lowPrice"])
            vol = float(t.get("quoteVolume") or 0)
            ch = float(t.get("priceChangePercent") or 0)
        except (TypeError, ValueError, KeyError):
            continue
        if low <= 0 or last <= 0:
            continue
        from_low = (last / low - 1) * 100
        if from_low < THRESHOLD:
            continue
        if min_vol and vol < min_vol:
            continue
        prev = float(state.get(sym) or 0)
        if now - prev < COOLDOWN:
            continue
        hits.append((from_low, ch, sym, last, low, vol))
        state[sym] = now
    hits.sort(reverse=True)
    for from_low, ch, sym, last, low, vol in hits:
        msg = (
            f"FUTURES PUMP {sym}\n"
            f"+{from_low:.0f}% from 24h low (min {THRESHOLD:.0f}%)\n"
            f"Last {last}  Low {low}\n"
            f"24h {ch:.1f}%  Vol ${vol/1e6:.1f}M\n"
            f"https://www.binance.com/en/futures/{sym}"
        )
        print(msg.replace("\n", " | "))
        telegram(msg)
    if hits:
        save_state(state)
    return state


def main() -> None:
    if not TOKEN or not CHAT:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (same as CryptoSentinel Settings).")
    print(f"Watching USDT-M futures · min +{THRESHOLD:.0f}% from 24h low · poll {POLL}s")
    state = load_state()
    while True:
        try:
            state = scan(state)
        except Exception as e:
            print("scan_error", type(e).__name__, e)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
