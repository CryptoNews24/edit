#!/usr/bin/env python3
"""ONG paper hedge bot — $500, 3-day test.

Short ONG/USDT spot + long ONGUSDT perp, same qty.
Take +$15 or +$20 (ONG_TP), flatten, re-enter. Cut loser at -$TP.
Prints total P&L WIN/LOSS. Paper only — no API keys, no orders.

  python3 ong_paper_bot.py              # run 3 days (poll every 4s)
  python3 ong_paper_bot.py --once       # one tick (for tests / cron)
  ONG_TP=20 python3 ong_paper_bot.py
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

START_CASH = 500.0
TEST_SEC = 3 * 24 * 60 * 60
SPOT_FEE = 0.001
PERP_FEE = 0.0005
MIN_GAP = 0.004
POLL = int(os.environ.get("ONG_POLL_SEC", "4"))
TP = float(os.environ.get("ONG_TP", "15"))
STATE = Path(
    os.environ.get(
        "ONG_STATE_FILE",
        str(Path(__file__).with_name("ong_paper_state.json")),
    )
)
SPOT_URL = "https://data-api.binance.vision/api/v3/ticker/bookTicker?symbol=ONGUSDT"
PERP_URLS = (
    "https://www.binance.com/fapi/v1/ticker/bookTicker?symbol=ONGUSDT",
    "https://fapi.binance.com/fapi/v1/ticker/bookTicker?symbol=ONGUSDT",
)


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "CryptoSentinelOngBot/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def fmt_pnl(n: float) -> str:
    if n > 0:
        return f"+${n:.2f}"
    if n < 0:
        return f"-${abs(n):.2f}"
    return "$0.00"


def wl(n: float) -> str:
    if n > 0:
        return "WIN"
    if n < 0:
        return "LOSS"
    return "FLAT"


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return empty_state()


def empty_state() -> dict:
    t = time.time()
    return {
        "running": True,
        "startAt": t,
        "endAt": t + TEST_SEC,
        "tp": TP,
        "totalPnl": 0.0,
        "wins": 0,
        "losses": 0,
        "pos": None,
        "log": [],
    }


def save_state(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))


def prices() -> dict:
    s = get_json(SPOT_URL)
    last = None
    p = None
    for url in PERP_URLS:
        try:
            p = get_json(url)
            break
        except Exception as e:
            last = e
    if p is None:
        raise last
    spot = (float(s["bidPrice"]) + float(s["askPrice"])) / 2
    perp = (float(p["bidPrice"]) + float(p["askPrice"])) / 2
    if not spot or not perp:
        raise RuntimeError("bad px")
    mid = (spot + perp) / 2
    return {"spot": spot, "perp": perp, "gap": (spot - perp) / mid}


def clip_pnl(pos: dict, spot: float, perp: float) -> float:
    q = pos["qty"]
    spot_pnl = (pos["spot"] - spot) * q
    perp_pnl = (perp - pos["perp"]) * q
    open_n = q * ((pos["spot"] + pos["perp"]) / 2)
    close_n = q * ((spot + perp) / 2)
    fees = open_n * (SPOT_FEE + PERP_FEE) + close_n * (SPOT_FEE + PERP_FEE)
    return spot_pnl + perp_pnl - fees


def push_log(st: dict, event: str, spot, perp, clip, total) -> None:
    st["log"].insert(
        0,
        {
            "t": now_iso(),
            "event": event,
            "spot": spot,
            "perp": perp,
            "clip": clip,
            "total": total,
        },
    )
    st["log"] = st["log"][:80]


def enter(st: dict, px: dict) -> None:
    equity = START_CASH + st["totalPnl"]
    notional = max(80.0, min(equity * 0.8, 400.0))
    mid = (px["spot"] + px["perp"]) / 2
    qty = notional / mid
    st["pos"] = {
        "spot": px["spot"],
        "perp": px["perp"],
        "qty": qty,
        "notional": notional,
        "t": time.time(),
    }
    push_log(st, "ENTER short spot / long perp", px["spot"], px["perp"], None, st["totalPnl"])
    print(
        f"{now_iso()}  ENTER  qty={qty:.1f}  spot={px['spot']:.5f}  perp={px['perp']:.5f}  "
        f"gap={px['gap']*100:.2f}%  notional=${notional:.0f}  total={fmt_pnl(st['totalPnl'])}"
    )


def flatten(st: dict, px: dict, reason: str) -> float:
    pnl = clip_pnl(st["pos"], px["spot"], px["perp"])
    st["totalPnl"] += pnl
    if pnl >= 0:
        st["wins"] += 1
    else:
        st["losses"] += 1
    push_log(st, f"{reason} {fmt_pnl(pnl)}", px["spot"], px["perp"], pnl, st["totalPnl"])
    st["pos"] = None
    print(
        f"{now_iso()}  {reason}  clip={fmt_pnl(pnl)}  TOTAL {fmt_pnl(st['totalPnl'])} {wl(st['totalPnl'])}  "
        f"equity=${START_CASH + st['totalPnl']:.2f}  W/L {st['wins']}/{st['losses']}"
    )
    return pnl


def summary(st: dict, extra: str = "") -> str:
    eq = START_CASH + st["totalPnl"]
    left = max(0, st["endAt"] - time.time())
    d, rem = divmod(int(left), 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    return (
        f"{extra}Total P&L {fmt_pnl(st['totalPnl'])} {wl(st['totalPnl'])}  "
        f"equity ${eq:.2f}  wins/losses {st['wins']}/{st['losses']}  "
        f"time left {d}d {h:02d}:{m:02d}"
    )


def tick(st: dict) -> dict:
    if not st.get("running"):
        return st
    if time.time() >= st["endAt"]:
        try:
            px = prices()
            if st["pos"]:
                flatten(st, px, "3D END flatten")
        except Exception:
            st["pos"] = None
        st["running"] = False
        print(summary(st, "3-day test over.  "))
        save_state(st)
        return st

    px = prices()
    if st["pos"] is None:
        if px["gap"] >= MIN_GAP:
            enter(st, px)
        else:
            print(
                f"{now_iso()}  FLAT  gap={px['gap']*100:.2f}%  waiting ≥0.4%  "
                + summary(st)
            )
        save_state(st)
        return st

    pnl = clip_pnl(st["pos"], px["spot"], px["perp"])
    print(
        f"{now_iso()}  IN CLIP  {fmt_pnl(pnl)} / TP {fmt_pnl(st['tp'])}  "
        f"spot={px['spot']:.5f} perp={px['perp']:.5f} gap={px['gap']*100:.2f}%  "
        + summary(st)
    )
    if pnl >= st["tp"]:
        flatten(st, px, "TP HIT")
        if px["gap"] >= MIN_GAP:
            enter(st, px)
    elif pnl <= -st["tp"]:
        flatten(st, px, "CUT LOSS")
        if START_CASH + st["totalPnl"] < 80:
            st["running"] = False
            print(summary(st, "Stopped — equity too low.  "))
            save_state(st)
            return st
        if px["gap"] >= MIN_GAP:
            enter(st, px)
    save_state(st)
    return st


def self_test() -> None:
    pos = {"spot": 0.180, "perp": 0.160, "qty": 2000.0}
    # basis shrinks 0.02 → 0: both legs win
    pnl = clip_pnl(pos, 0.170, 0.170)
    assert pnl > 38, pnl
    # basis widens 0.02 → 0.04: both legs lose
    pnl2 = clip_pnl(pos, 0.190, 0.150)
    assert pnl2 < -38, pnl2
    print("self-test ok", f"converge={pnl:.2f}", f"diverge={pnl2:.2f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="start a new 3-day $500 test")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    if args.fresh or not STATE.exists():
        st = empty_state()
        st["tp"] = TP
        push_log(st, f"START 3d · ${START_CASH:.0f} · TP ${st['tp']:.0f}", None, None, None, 0)
        save_state(st)
        print(summary(st, "Started.  "))
    else:
        st = load_state()
        print(summary(st, "Resumed.  "))
    if args.once:
        tick(st)
        return
    while st.get("running"):
        try:
            tick(st)
        except Exception as e:
            print(f"{now_iso()}  price fetch failed: {e}")
        if not st.get("running"):
            break
        time.sleep(POLL)


if __name__ == "__main__":
    main()
