#!/usr/bin/env python3
"""Write the hunt as plain text. No designed HTML."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

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
    "forfaitiptv.ca",
    "essaiiptv.ca",
    "essai-iptv.ca",
    "guide-abonnement-iptv.fr",
    "avis-abonnement-iptv.fr",
    "iptvvergelijker.nl",
    "iptvvergleicher.de",
    "iptvguide.ch",
    "iptvcompare.com",
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
    available = [d for d, r in recheck.items() if r["verdict"] == "AVAILABLE"]
    confirm = [d for d, r in recheck.items() if r["verdict"].startswith("Confirm")]

    taken_extra: dict[str, str] = {}
    taken = []
    with (ROOT / "taken_not_available.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = r["Domain"]
            taken.append(d)
            bits = [r.get("Availability") or "TAKEN"]
            if r.get("Website"):
                bits.append(r["Website"])
            if r.get("Expiry"):
                bits.append(f"expiry {r['Expiry']}")
            if r.get("Notes"):
                bits.append(r["Notes"])
            taken_extra[d] = " — ".join(bits)

    drop = []
    drop_extra: dict[str, str] = {}
    with (ROOT / "almost_expired_offline.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = r["Domain"]
            drop.append(d)
            days = r.get("Days to expiry", "")
            try:
                n = int(days)
                left = f"expired {abs(n)}d" if n < 0 else f"{n} days left"
            except ValueError:
                left = days
            drop_extra[d] = (
                f"TAKEN — {r.get('Website status')} — expiry {r.get('Expiry date')} ({left}). Not for sale."
            )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    kws = traffic.get("keywords") or {}

    lines = [
        "IPTV SEO domain hunt — plain text list",
        f"Updated {now}",
        "",
        "Do not purchase from this file. Recheck at a registrar cart before buying.",
        "iptvcanada.ca is TAKEN. Ignore .ie domains. Skip .uk names that contain iptv.",
        "TiviMate / IPTV Smarters = SEO topics only, not brand domains.",
        "Keyword volume is not website sessions. Unregistered names have 0 site traffic.",
        "Volumes below are only Semrush numbers we actually saw. Everything else is N/A.",
        "",
        "======== PICKS (AVAILABLE, strongest fit) ========",
        "",
    ]
    for d in PICKS:
        status = (recheck.get(d) or {}).get("verdict", "not in last RDAP batch")
        if status != "AVAILABLE":
            lines.append(f"  {d}  SKIP — {status}")
            continue
        lines.append(f"  {d}")
        lines.append(f"    {country_of(d)} — {kw_line(d, traffic)}")
    lines += ["", "======== VERIFIED KEYWORD VOLUME ========", ""]
    for name, k in kws.items():
        cpc = k.get("cpc")
        cpc_s = "N/A" if cpc in (None, "", "N/A") else f"${cpc}"
        lines.append(
            f"  {name}  [{k.get('db','').upper()}]  {k.get('volume_display')}/mo  "
            f"KD {k.get('kd')} {k.get('kd_label')}  CPC {cpc_s}  {k.get('intent')}"
        )
    lines += [
        "",
        "Ireland keywords are SEO-only. Do not register .ie.",
        "",
    ]
    lines += block(
        "======== AVAILABLE (RDAP 404 + no DNS) ========",
        available,
        traffic,
    )
    lines += block(
        "======== CONFIRM AT REGISTRAR (flaky TLD RDAP: .be .com.au .nz .at .es .it .pt .org) ========",
        confirm,
        traffic,
        extra={d: "rdap.org 404 + no DNS — confirm in registrar cart before treating as free" for d in confirm},
    )
    lines += block("======== TAKEN — DO NOT BUY ========", taken, traffic, extra=taken_extra)
    lines += block(
        "======== TAKEN + OFFLINE / DROP-WATCH (<=90 days) — still NOT available ========",
        drop,
        traffic,
        extra=drop_extra,
    )
    lines += [
        "======== NOTES ========",
        "",
        "Noxtools itself is up. This cloud IP (datacenter) hits Cloudflare 'Just a moment...' on noxtools.com,",
        "so Semrush via Noxtools cannot be opened from this agent even though your home browser still works.",
        "Until Cloudflare lets this IP through, volumes stay at the last verified Semrush numbers only.",
        "Rebuild: python3 research/iptv-seo/rebuild_lists.py && python3 research/iptv-seo/generate_text_list.py",
        "",
    ]
    text = "\n".join(lines)
    OUT.write_text(text, encoding="utf-8")
    OUT_ALIAS.write_text(text, encoding="utf-8")
    print(f"WROTE {OUT} and {OUT_ALIAS} available={len(available)} confirm={len(confirm)} taken={len(taken)}")


if __name__ == "__main__":
    main()
