#!/usr/bin/env python3
"""Write the hunt as plain text. No designed HTML."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from filters import (
    COUNTRY_TLD_LABELS,
    MIN_VOLUME,
    country_tld_groups,
    domain_meets_volume,
    keyword_volume,
    mapped_keyword,
    meets_opportunity,
    rank_available_domains,
    skip_domain,
)

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
    ".us": "United States",
    ".uk": "United Kingdom",
    ".no": "Norway",
    ".pl": "Poland",
    ".cz": "Czechia",
    ".eu": "EU",
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
]


def country_of(domain: str) -> str:
    for suffix, name in sorted(COUNTRY.items(), key=lambda x: -len(x[0])):
        if domain.endswith(suffix):
            return name
    return "Other"


def kw_line(domain: str, traffic: dict) -> str:
    name = mapped_keyword(traffic, domain)
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
            if skip_domain(r["domain"]):
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
    kws = {n: k for n, k in (traffic.get("keywords") or {}).items() if meets_opportunity(traffic, n)}

    lines = [
        "IPTV SEO domain hunt — AVAILABLE names only",
        f"Updated {now}",
        "",
        f"Filters: AVAILABLE only. Two-word names only (no 3+ word labels). Semrush volume >= {MIN_VOLUME}/mo (verified). **Difficult KD excluded.** **keyword - keyword pairs excluded.**",
        "Taken names are omitted except the almost-expired table (site down + expiry soon + mapped volume >= 500).",
        "Confirm-at-registrar and unverified (N/A) names are not buyable.",
        "Do not purchase from this file. Recheck at a registrar cart before buying.",
        "Ignore .ie domains. Skip .uk names that contain iptv.",
        "",
        "======== TOP 10 (high Semrush traffic × low KD) ========",
        "",
        "Score = monthly volume × (100 − KD) / 100. AVAILABLE only. Max 3 names per keyword.",
        "",
    ]
    for i, row in enumerate(rank_available_domains(traffic, recheck, 10), start=1):
        lines.append(
            f"  {i}. {row['domain']}"
        )
        lines.append(
            f"     {row['keyword']}  {row['volume_display']}/mo  KD {row['kd']} {row['kd_label']}  score {row['score']}"
        )
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
        f"Dropped below {MIN_VOLUME}: iptv subscription canada (390), best iptv ireland (140), cheap iptv US (390).",
        "Semrush: Chrome CDP pulled live US free-tool JSON (5 lookups/IP/day, quota used). Noxtools curl=Cloudflare; Chrome Sign In only. NordLayer Linux cannot run on this VM.",
        "",
    ]
    lines += block(
        "======== AVAILABLE (RDAP 404 + no DNS, Semrush >= 500) ========",
        available,
        traffic,
    )
    us_avail = [
        d for d, r in recheck.items()
        if d.endswith(".us") and r["verdict"] == "AVAILABLE"
    ]
    uk_avail = [
        d for d, r in recheck.items()
        if (d.endswith(".co.uk") or d.endswith(".uk"))
        and "iptv" not in d
        and r["verdict"] == "AVAILABLE"
    ]
    extra_us = {d: "native nic.us RDAP 404 + no DNS. Semrush US volume N/A — not in Top 10 yet." for d in us_avail}
    extra_uk = {d: "Nominet RDAP 404 + no DNS. No iptv in the name. Semrush UK volume N/A — not in Top 10 yet." for d in uk_avail}
    lines += block(
        "======== ALMOST EXPIRED (only taken table: site down + expiry soon + Semrush >= 500) — not for sale ========",
        drop,
        traffic,
        extra=drop_extra,
    )
    lines += block(
        "======== AVAILABLE .us (nic.us RDAP 404 + no DNS; Semrush US still N/A) ========",
        us_avail,
        traffic,
        extra=extra_us,
    )
    lines += block(
        "======== AVAILABLE .uk/.co.uk with NO iptv in the name (Nominet) ========",
        uk_avail,
        traffic,
        extra=extra_uk,
    )
    groups = country_tld_groups(recheck)
    lines += [
        "======== COUNTRY TLDs (.ca .us Europe) — AVAILABLE leftovers ========",
        "",
        "AVAILABLE = native RDAP 404 + no DNS. Two-word names only. Confirm/UNKNOWN are NOT free. .ie ignored. .uk with iptv skipped.",
        "Taken names omitted. US/UK/most EU volumes still N/A from this IP — not in Top 10 until Semrush >= 500.",
        "",
    ]
    for tld, label in COUNTRY_TLD_LABELS:
        g = groups[tld]
        if not g["AVAILABLE"] and not g["CONFIRM"] and not g["UNKNOWN"]:
            continue
        lines.append(
            f".{tld}  {label}  AVAILABLE={len(g['AVAILABLE'])}  "
            f"confirm={len(g['CONFIRM'])}  unknown={len(g['UNKNOWN'])}"
        )
    lines.append("")
    for tld, label in COUNTRY_TLD_LABELS:
        g = groups[tld]
        if not any(g.values()):
            continue
        lines.append(f"-------- .{tld} {label} AVAILABLE --------")
        if g["AVAILABLE"]:
            for d in g["AVAILABLE"]:
                lines.append(f"  {d}")
        else:
            lines.append("  (none marked AVAILABLE)")
        if g["CONFIRM"]:
            lines.append("  CONFIRM AT REGISTRAR: " + ", ".join(g["CONFIRM"]))
        if g["UNKNOWN"]:
            lines.append("  UNKNOWN: " + ", ".join(g["UNKNOWN"]))
        lines.append("")
    lines += [
        "======== NOTES ========",
        "",
        "Noxtools works in a normal browser. Curl hits Cloudflare. Chrome reached Sign In; Semrush Servers 1-6 need login.",
        "Semrush free Keyword Volume Checker: 5 live lookups per IP per day. US terms pulled; further DBs quota-blocked.",
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
