#!/usr/bin/env python3
"""Rebuild canva CSV + taken CSV + traffic maps from availability_recheck.csv."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from filters import EXPLICIT_DOMAIN_KEYWORD_MAP, domain_meets_volume, skip_domain, skip_keyword

ROOT = Path(__file__).resolve().parent
CANVA = ROOT / "canva"

COUNTRY = {
    ".fr": "France",
    ".ca": "Canada",
    ".ch": "Switzerland",
    ".nl": "Netherlands",
    ".de": "Germany",
    ".be": "Belgium",
    ".com.au": "Australia",
    ".nz": "New Zealand",
    ".net": "Global",
    ".com": "Global",
    ".dk": "Denmark",
    ".fi": "Finland",
    ".at": "Austria",
    ".es": "Spain",
    ".it": "Italy",
    ".pt": "Portugal",
    ".org": "Global",
    ".us": "United States",
    ".co.uk": "United Kingdom",
    ".uk": "United Kingdom",
    ".no": "Norway",
    ".se": "Sweden",
    ".pl": "Poland",
    ".cz": "Czechia",
    ".eu": "EU",
}


def country(d: str) -> str:
    for s, c in sorted(COUNTRY.items(), key=lambda x: -len(x[0])):
        if d.endswith(s):
            return c
    return "Other"


def skip(d: str) -> bool:
    return skip_domain(d)


def competition(ctry: str) -> str:
    if ctry == "France":
        return "Low"
    if ctry == "Canada":
        return "Medium"
    if ctry in {"Netherlands", "Germany"}:
        return "Medium–High"
    return "Medium"


def main() -> None:
    recheck = {}
    with (ROOT / "availability_recheck.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            recheck[r["domain"]] = r

    avail_rows = []
    taken_new = []
    for d, r in sorted(recheck.items()):
        if skip(d):
            continue
        v = r["verdict"]
        ctry = country(d)
        row = {
            "Domain": d,
            "Country": ctry,
            "Organic traffic": "N/A",
            "Competitive rate": competition(ctry),
            "Availability": "AVAILABLE (rechecked)" if v == "AVAILABLE" else v,
        }
        if v == "AVAILABLE":
            avail_rows.append(row)
        elif v == "TAKEN":
            taken_new.append(d)

    taken_path = ROOT / "taken_not_available.csv"
    existing = {}
    with taken_path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            existing[r["Domain"]] = r
    for d in taken_new:
        existing.setdefault(
            d,
            {
                "Domain": d,
                "Country": country(d),
                "Availability": "TAKEN",
                "Website": "DNS yes" if recheck[d]["dns"] == "yes" else "No DNS / offline-looking",
                "Expiry": "",
                "Notes": "Not available. Do not list as a buy.",
            },
        )
    with taken_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Domain", "Country", "Availability", "Website", "Expiry", "Notes"])
        w.writeheader()
        for k in sorted(existing):
            w.writerow(existing[k])

    traffic = json.loads((CANVA / "traffic.json").read_text(encoding="utf-8"))
    # Rebuild from scratch. Do not keep TLD-wide stamps (every .fr → 18.1K).
    kwmap = {}
    for d, kw in EXPLICIT_DOMAIN_KEYWORD_MAP.items():
        row = recheck.get(d)
        if not row or row.get("verdict") != "AVAILABLE":
            continue
        if skip_domain(d):
            continue
        kwmap[d] = kw
    kws = traffic.get("keywords") or {}
    traffic["keywords"] = {n: k for n, k in kws.items() if not skip_keyword(n, {"keywords": kws})}
    kwmap = {d: kw for d, kw in kwmap.items() if not skip_keyword(kw, {"keywords": kws})}
    traffic["domain_keyword_map"] = kwmap
    traffic["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    traffic["semrush_refresh"] = {
        "attempted": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "partial",
        "detail": "Stopped stamping FR abonnement iptv 18.1K onto leftover .fr hunt names. Volume only on EXPLICIT_DOMAIN_KEYWORD_MAP. Q-rows in RANKED_KEYWORDS.md are N/A (not Semrush). Hunt stopped. No invented volumes.",
        "min_volume": 500,
        "exclude_kd": "Difficult",
        "exclude_keyword_pairs": True,
    }
    (CANVA / "traffic.json").write_text(json.dumps(traffic, indent=2) + "\n", encoding="utf-8")

    canva_rows = [row for row in avail_rows if domain_meets_volume(traffic, row["Domain"])]
    with (CANVA / "iptv-domains-canva-import.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["Domain", "Country", "Organic traffic", "Competitive rate", "Availability"]
        )
        w.writeheader()
        w.writerows(canva_rows)
    print(f"canva={len(canva_rows)} available_unfiltered={len(avail_rows)} taken={len(existing)}")

    from generate_ranked_keywords import main as write_ranked
    from generate_strong_keywords import main as write_strong

    write_ranked()
    write_strong()


if __name__ == "__main__":
    main()
