#!/usr/bin/env python3
"""Keyword-only ranking from Semrush Overview. No leftover domains. No FR. No hyphens."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from filters import skip_keyword

ROOT = Path(__file__).resolve().parent
TRAFFIC = ROOT / "canva" / "traffic.json"
OUT = ROOT / "STRONG_KEYWORDS.md"

# Hunt markets only. No France, no Ireland.
KEEP_DB = frozenset({"us", "ca"})
HYPHEN = re.compile(r"-")

DB_LABEL = {
    "us": "United States",
    "ca": "Canada",
}


def main() -> None:
    traffic = json.loads(TRAFFIC.read_text(encoding="utf-8"))
    rows = []
    for name, k in (traffic.get("keywords") or {}).items():
        if skip_keyword(name, traffic):
            continue
        if HYPHEN.search(name):
            continue
        try:
            vol = int(k["volume"])
        except (KeyError, TypeError, ValueError):
            continue
        db = (k.get("db") or "").lower()
        if db not in KEEP_DB:
            continue
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
    usable = [r for r in rows if r["vol"] >= 500 and "difficult" not in r["kd_label"].lower()]
    heads = [r for r in rows if "difficult" in r["kd_label"].lower()]
    weak = [r for r in rows if r["vol"] < 500]

    lines = [
        "# Strong keywords (Semrush only)",
        "",
        f"Updated {now}. Space-separated queries only. **No France / `.fr`. No hyphen keywords. No leftover domains.** Hunt stopped. No invented volumes.",
        "",
        "## Strongest → weakest",
        "",
        "| Rank | Keyword | Market | Vol / mo | KD | CPC | Intent |",
        "| ---: | --- | --- | ---: | ---: | --- | --- |",
    ]
    for i, r in enumerate(rows, start=1):
        lines.append(
            f"| {i} | `{r['keyword']}` | {r['market']} | {r['vol_d']} | {r['kd']} {r['kd_label']} | {r['cpc']} | {r['intent']} |"
        )

    def bullets(items: list) -> list[str]:
        if not items:
            return ["- —"]
        return [f"- `{r['keyword']}` — {r['vol_d']}/mo · KD {r['kd']} {r['kd_label']} · {r['market']}" for r in items]

    lines += [
        "",
        "## Use first (volume ≥ 500, KD not Difficult)",
        "",
        *bullets(usable),
        "",
        "## High volume, Difficult KD",
        "",
        *bullets(heads),
        "",
        "## Weak (under 500/mo)",
        "",
        *bullets(weak),
        "",
        "This is the full Semrush set for US/CA after dropping FR and hyphen queries. Hunt is stopped.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE {OUT} keywords={len(rows)}")


if __name__ == "__main__":
    main()
