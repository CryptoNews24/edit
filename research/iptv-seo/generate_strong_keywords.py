#!/usr/bin/env python3
"""Keyword-only ranking from Semrush Overview. No leftover domains."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from filters import skip_keyword

ROOT = Path(__file__).resolve().parent
TRAFFIC = ROOT / "canva" / "traffic.json"
OUT = ROOT / "STRONG_KEYWORDS.md"

DB_LABEL = {
    "us": "United States",
    "ca": "Canada",
    "uk": "United Kingdom",
    "fr": "France",
    "ie": "Ireland",
}


def main() -> None:
    traffic = json.loads(TRAFFIC.read_text(encoding="utf-8"))
    rows = []
    for name, k in (traffic.get("keywords") or {}).items():
        if skip_keyword(name, traffic):
            continue
        try:
            vol = int(k["volume"])
        except (KeyError, TypeError, ValueError):
            continue
        db = (k.get("db") or "").lower()
        kd = int(k.get("kd") or 0)
        rows.append(
            {
                "keyword": name,
                "db": db,
                "market": DB_LABEL.get(db, db.upper()),
                "vol": vol,
                "vol_d": k.get("volume_display") or str(vol),
                "kd": kd,
                "kd_label": k.get("kd_label") or "",
                "cpc": k.get("cpc") or "N/A",
                "intent": k.get("intent") or "",
            }
        )
    rows.sort(key=lambda r: (-r["vol"], r["keyword"]))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Strong keywords (Semrush only)",
        "",
        f"Updated {now}. **This file is the keyword list.** Queries only. No leftover domains. No invented volumes. Source: Noxtools / stored Semrush Keyword Overview in `canva/traffic.json`.",
        "",
        "A leftover domain is not a keyword. `RANKED_KEYWORDS.md` Q-rows are leftover hunt names and are **not** ranked by traffic.",
        "",
        "## All verified queries (strongest volume → weakest)",
        "",
        "| Rank | Keyword | Semrush DB | Vol / mo | KD | CPC | Intent |",
        "| ---: | --- | --- | ---: | ---: | --- | --- |",
    ]
    for i, r in enumerate(rows, start=1):
        lines.append(
            f"| {i} | `{r['keyword']}` | {r['market']} (`{r['db']}`) | {r['vol_d']} | {r['kd']} {r['kd_label']} | {r['cpc']} | {r['intent']} |"
        )

    focus = [r for r in rows if r["db"] in {"us", "ca"}]
    fr = [r for r in rows if r["db"] == "fr"]
    usable = [r for r in focus if r["vol"] >= 500 and "difficult" not in r["kd_label"].lower()]
    heads = [r for r in focus if "difficult" in r["kd_label"].lower()]
    weak = [r for r in focus if r["vol"] < 500]

    def bullets(items: list) -> list[str]:
        return [f"- `{r['keyword']}` — {r['vol_d']}/mo · KD {r['kd']} {r['kd_label']} · {r['market']}" for r in items]

    lines += [
        "",
        "## Use these first (US / CA, volume ≥ 500, KD not Difficult)",
        "",
        *bullets(usable),
        "",
        "## High volume, hard to rank (still real keywords)",
        "",
        *bullets(heads),
        "",
        "## Weak verified (under 500/mo)",
        "",
        *bullets(weak),
        "",
        "## France DB only (real queries — not leftover `.fr` names)",
        "",
        *bullets(fr),
        "",
        "Ireland `iptv ireland` 1.9K is in the full table (SEO copy only; no `.ie` domain).",
        "",
        "Nothing else in this repo has Semrush volume. App/chipset leftover names were never Overview-checked.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE {OUT} keywords={len(rows)}")


if __name__ == "__main__":
    main()
