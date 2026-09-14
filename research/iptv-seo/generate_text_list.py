#!/usr/bin/env python3
"""Write the hunt as plain text. No designed HTML."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from filters import MIN_VOLUME, domain_meets_volume, keyword_volume, mapped_keyword, meets_volume

ROOT = Path(__file__).resolve().parent
CANVA = ROOT / "canva"
OUT = ROOT / "LIST.txt"
OUT_ALIAS = ROOT / "AVAILABLE_LIST.txt"

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
    ".se": "Sweden",
}

PICKS = [
    "compareriptv.fr",
    "avis-iptv.fr",
    "comparateur-iptv.fr",
    "pascheriptv.fr",
    "essaiiptv.fr",
    "guideiptv.fr",
    "compareiptv.ca",
    "iptvguide.ca",
    "iptvcompare.ca",
    "compareriptv.ca",
    "avis-iptv.ca",
    "guideiptv.ca",
    "guide-abonnement-iptv.fr",
    "avis-abonnement-iptv.fr",
]


def country_of(domain: str) -> str:
    for suffix, name in sorted(COUNTRY.items(), key=lambda x: -len(x[0])):
        if domain.endswith(suffix):
            return name
    return "Other"


def kw_line(domain: str, traffic: dict) -> str:
    name = (traffic.get("domain_keyword_map") or {}).get(domain)
    kws = traffic.get("keywords") or {}
    if not name or name not in kws:
        return "volume N/A (not verified in Semrush yet)"
    k = kws[name]
    cpc = k.get("cpc")
    cpc_s = "N/A" if cpc in (None, "", "N/A") else f"${cpc}"
    return (
        f"{name} — {k.get('volume_display')}/mo "
        f"KD {k.get('kd')} {k.get('kd_label')} CPC {cpc_s} [{k.get('db','').upper()}]"
    )


def load_recheck() -> dict[str, dict]:
    rows = {}
    with (ROOT / "availability_recheck.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["domain"].endswith(".ie") or ".uk" in r["domain"]:
                continue
            rows[r["domain"]] = r
    return rows


def grouped(domains: list[str]) -> dict[str, list[str]]:
    by: dict[str, list[str]] = {}
    for d in sorted(domains):
        by.setdefault(country_of(d), []).append(d)
    return by


def block(title: str, domains: list[str], traffic: dict, extra: dict[str, str] | None = None) -> list[str]:
    lines = [title, ""]
    extra = extra or {}
    for country, names in grouped(domains).items():
        lines.append(country)
        for d in names:
            tail = extra.get(d, kw_line(d, traffic))
            lines.append(f"  {d}")
            lines.append(f"    {tail}")
        lines.append("")
    return lines


def main() -> None:
    traffic = json.loads((CANVA / "traffic.json").read_text(encoding="utf-8"))
    recheck = load_recheck()
    available = [
        d
        for d, r in recheck.items()
        if r["verdict"] == "AVAILABLE" and domain_meets_volume(traffic, d)
    ]

    drop = []
    drop_extra: dict[str, str] = {}
    with (ROOT / "almost_expired_offline.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = r["Domain"]
            if not domain_meets_volume(traffic, d):
                continue
            drop.append(d)
            days = r.get("Days to expiry", "")
            try:
                n = int(days)
                left = f"expired {abs(n)}d" if n < 0 else f"{n} days left"
            except ValueError:
                left = days
            vol = keyword_volume(traffic, mapped_keyword(traffic, d))
            drop_extra[d] = (
                f"TAKEN + offline/parked — expiry {r.get('Expiry date')} ({left}). "
                f"Site not working. Mapped Semrush keyword {mapped_keyword(traffic, d)} = {vol}/mo. Not for sale today."
            )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    kws = {n: k for n, k in (traffic.get("keywords") or {}).items() if meets_volume(traffic, n)}

    lines = [
        "IPTV SEO domain hunt — AVAILABLE names (plus high-volume drop-watch)",
        f"Updated {now}",
        "",
        f"Filters: AVAILABLE only. Semrush volume >= {MIN_VOLUME}/mo (verified). Taken names excluded",
        "except almost-expired + website down + mapped keyword volume >= 500.",
        "Confirm-at-registrar and unverified (N/A) names are excluded until Semrush confirms >= 500.",
        "Do not purchase from this file. Recheck at a registrar cart before buying.",
        "iptvcanada.ca is TAKEN (drop-watch only). Ignore .ie domains. Skip iptv*.uk.",
        "",
        "======== PICKS (AVAILABLE, volume >= 500) ========",
        "",
    ]
    for d in PICKS:
        status = (recheck.get(d) or {}).get("verdict", "not in last RDAP batch")
        if status != "AVAILABLE" or not domain_meets_volume(traffic, d):
            continue
        lines.append(f"  {d}")
        lines.append(f"    {country_of(d)} — {kw_line(d, traffic)}")
    lines += ["", "======== VERIFIED SEMRUSH (>= 500/mo) ========", ""]
    for name, k in sorted(kws.items(), key=lambda kv: -int(kv[1].get("volume") or 0)):
        cpc = k.get("cpc")
        cpc_s = "N/A" if cpc in (None, "", "N/A") else f"${cpc}"
        lines.append(
            f"  {name}  [{k.get('db','').upper()}]  {k.get('volume_display')}/mo  "
            f"KD {k.get('kd')} {k.get('kd_label')}  CPC {cpc_s}  {k.get('intent')}"
        )
    lines += [
        "",
        "Ireland keywords are SEO-only. Do not register .ie.",
        f"Dropped below {MIN_VOLUME}: iptv subscription canada (390), best iptv ireland (140).",
        "Semrush refresh from this IP: Noxtools Cloudflare blocked; public Semrush page has no live numbers. Last verified figures kept.",
        "",
    ]
    lines += block(
        "======== AVAILABLE (RDAP 404 + no DNS, Semrush >= 500) ========",
        available,
        traffic,
    )
    lines += block(
        "======== DROP-WATCH (taken + site down + expiry <=90d + Semrush >= 500) — not for sale ========",
        drop,
        traffic,
        extra=drop_extra,
    )
    lines += [
        "======== NOTES ========",
        "",
        "Noxtools works in a normal browser. This cloud IP hits Cloudflare on noxtools.com, so volumes",
        "cannot be refreshed from here. They will be updated as soon as Semrush is reachable.",
        "Rebuild: python3 research/iptv-seo/rebuild_lists.py && python3 research/iptv-seo/generate_text_list.py",
        "",
    ]
    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    OUT_ALIAS.write_text(text, encoding="utf-8")
    print(f"WROTE {OUT} available={len(available)} dropwatch={len(drop)} keywords={len(kws)}")
    from generate_keywords_md import main as write_keywords_md

    write_keywords_md()


if __name__ == "__main__":
    main()
