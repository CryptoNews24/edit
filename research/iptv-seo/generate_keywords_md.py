#!/usr/bin/env python3
"""Write KEYWORDS.md — markdown tables for keyword research."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "KEYWORDS.md"

DB_COUNTRY = {
    "fr": "France",
    "ca": "Canada",
    "ie": "Ireland",
    "be": "Belgium",
    "nl": "Netherlands",
    "de": "Germany",
    "ch": "Switzerland",
    "au": "Australia",
    "us": "United States",
    "uk": "United Kingdom",
    "es": "Spain",
    "it": "Italy",
    "dk": "Denmark",
    "nz": "New Zealand",
}


def cell(v) -> str:
    s = "" if v is None else str(v).strip()
    return s.replace("|", "/").replace("\n", " ")


def cpc_fmt(v) -> str:
    s = cell(v)
    if s in {"", "N/A"}:
        return "N/A"
    if s.startswith("$"):
        return s
    return f"${s}"


def domain_verdict(domain: str, recheck: dict[str, dict]) -> str:
    if not domain or domain.startswith("SKIP") or domain.startswith("N/A") or domain.startswith("cluster"):
        return "—"
    if domain.startswith("TAKEN:"):
        return "TAKEN"
    row = recheck.get(domain)
    if not row:
        return "not rechecked"
    return row["verdict"]


def main() -> None:
    traffic = json.loads((ROOT / "canva" / "traffic.json").read_text(encoding="utf-8"))
    kws = traffic.get("keywords") or {}
    recheck = {}
    with (ROOT / "availability_recheck.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            recheck[r["domain"]] = r

    tracked = []
    with (ROOT / "keywords.csv").open(encoding="utf-8") as f:
        tracked = list(csv.DictReader(f))

    inspections = []
    insp_by_kw: dict[str, dict] = {}
    with (ROOT / "keyword_inspections.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            inspections.append(r)
            insp_by_kw[r["Keyword"].lower()] = r

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# IPTV keyword table",
        "",
        f"Updated {now}. Volumes and KD are **only** numbers seen in Semrush (Noxtools Server 6 or earlier verified pulls). Everything else is **N/A** — not guessed.",
        "",
        "Rules: do not buy from this file. `iptvcanada.ca` is **TAKEN**. Ignore `.ie` domains. Skip `.uk` names that contain `iptv`. TiviMate / IPTV Smarters = SEO topics, not brand domains.",
        "",
        "Noxtools still works in a normal browser. This cloud IP is blocked by Cloudflare, so new Semrush rows cannot be filled from here until that clears.",
        "",
        "## 1. Verified Semrush (sorted by volume)",
        "",
        "| Keyword | Country (DB) | Volume / mo | KD | CPC | Intent | Priority | Best AVAILABLE domain | Taken exact-match |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]

    verified_meta = {
        "abonnement iptv": {
            "priority": "JACKPOT",
            "domain": "compareriptv.fr",
            "taken": "abonnementiptv.fr",
        },
        "iptv canada": {
            "priority": "HIGH",
            "domain": "compareiptv.ca",
            "taken": "iptvcanada.ca (offline, expiry 2026-11-02)",
        },
        "iptv france": {
            "priority": "HIGH",
            "domain": "guideiptv.fr",
            "taken": "iptvfrance.fr",
        },
        "meilleur iptv": {
            "priority": "HIGH",
            "domain": "compareriptv.fr",
            "taken": "meilleuriptv.fr",
        },
        "iptv pas cher": {
            "priority": "HIGH",
            "domain": "pascheriptv.fr",
            "taken": "iptvpascher.fr / iptv-pas-cher.fr",
        },
        "best iptv canada": {
            "priority": "MEDIUM",
            "domain": "iptvguide.ca",
            "taken": "bestiptv.ca",
        },
        "iptv ireland": {
            "priority": "SEO only",
            "domain": "none — ignore .ie",
            "taken": "n/a",
        },
        "essai iptv": {
            "priority": "LONG-TAIL",
            "domain": "essaiiptv.fr",
            "taken": "essaiiptv.fr is AVAILABLE (not taken)",
        },
        "iptv subscription canada": {
            "priority": "LONG-TAIL",
            "domain": "iptvplans.ca / forfaitiptv.ca",
            "taken": "iptvsubscription.ca",
        },
        "best iptv ireland": {
            "priority": "SEO only",
            "domain": "none — ignore .ie",
            "taken": "n/a",
        },
    }

    for name, k in sorted(kws.items(), key=lambda kv: -int(kv[1].get("volume") or 0)):
        meta = verified_meta.get(name, {})
        db = (k.get("db") or "").lower()
        country = DB_COUNTRY.get(db, db.upper())
        domain = meta.get("domain", "—")
        if "ignore" in domain:
            domain_md = "— (SEO only, no `.ie`)"
        else:
            verdict = domain_verdict(domain.split("/")[0].strip(), recheck)
            domain_md = f"`{cell(domain)}` ({cell(verdict)})"
        lines.append(
            "| {kw} | {country} (`{db}`) | {vol} | {kd} {lab} | {cpc} | {intent} | {pri} | {dom} | {taken} |".format(
                kw=cell(name),
                country=country,
                db=db.upper(),
                vol=cell(k.get("volume_display")),
                kd=cell(k.get("kd")),
                lab=cell(k.get("kd_label")),
                cpc=cpc_fmt(k.get("cpc")),
                intent=cell(k.get("intent")),
                pri=cell(meta.get("priority", "—")),
                dom=domain_md,
                taken=cell(meta.get("taken", "—")),
            )
        )

    lines += [
        "",
        "France verified cluster ≈ **33.8K**/mo (`abonnement iptv` + `iptv france` + `meilleur iptv` + `iptv pas cher` + `essai iptv`).",
        "Canada verified cluster ≈ **17.1K**/mo (`iptv canada` + `best iptv canada` + `iptv subscription canada`).",
        "",
        "## 2. Tracked keywords (all rows we scored)",
        "",
        "Unverified volume/KD stay **N/A**. Domain column is the candidate to register, not a live site.",
        "",
        "| Keyword | Country | Lang | Volume | KD | CPC | Intent | SERP | Priority | Domain | Availability | Notes |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    def vol_sort(row: dict) -> tuple:
        v = row.get("Search Volume") or "N/A"
        try:
            return (0, -int(float(v)))
        except ValueError:
            return (1, 0)

    for r in sorted(tracked, key=vol_sort):
        kw = r["Keyword"]
        serp = r.get("SERP Difficulty") or "N/A"
        insp = insp_by_kw.get(kw.lower())
        if insp and (not serp or serp == "N/A"):
            serp = insp.get("SERP") or serp
        domain = r.get("Domain Candidate") or ""
        avail = r.get("Availability") or ""
        if domain.startswith("SKIP") or domain.startswith("N/A"):
            avail = "ignored" if "IE" in domain or domain.startswith("SKIP") else "SEO only"
            domain_md = cell(domain)
        else:
            live = domain_verdict(domain, recheck)
            if live not in {"—", "not rechecked"}:
                avail = live
            domain_md = f"`{cell(domain)}`"
        lines.append(
            "| {kw} | {co} | {lang} | {vol} | {kd} | {cpc} | {intent} | {serp} | {pri} | {dom} | {avail} | {notes} |".format(
                kw=cell(kw),
                co=cell(r.get("Country")),
                lang=cell(r.get("Language")),
                vol=cell(r.get("Search Volume")),
                kd=cell(r.get("KD %")) + ((" " + cell(r.get("KD Category"))) if r.get("KD %") not in {"", "N/A"} else ""),
                cpc=cpc_fmt(r.get("CPC")),
                intent=cell(r.get("Intent")),
                serp=cell(serp),
                pri=cell(r.get("Priority")),
                dom=domain_md,
                avail=cell(avail),
                notes=cell(r.get("Notes")),
            )
        )

    lines += [
        "",
        "## 3. SERP notes (DuckDuckGo / Bing)",
        "",
        "| Keyword | Market | SERP | Top domains | Related searches |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in inspections:
        lines.append(
            "| {kw} | {m} | {s} | {top} | {rel} |".format(
                kw=cell(r.get("Keyword")),
                m=cell(r.get("Market")),
                s=cell(r.get("SERP")),
                top=cell(r.get("Top domains")),
                rel=cell(r.get("Related searches")),
            )
        )

    picks = [
        ("compareriptv.fr", "abonnement iptv"),
        ("avis-iptv.fr", "abonnement iptv"),
        ("comparateur-iptv.fr", "abonnement iptv"),
        ("pascheriptv.fr", "iptv pas cher"),
        ("essaiiptv.fr", "essai iptv"),
        ("guideiptv.fr", "iptv france"),
        ("compareiptv.ca", "iptv canada"),
        ("iptvguide.ca", "iptv canada"),
        ("compareriptv.ca", "iptv canada"),
        ("forfaitiptv.ca", "iptv subscription canada"),
        ("essaiiptv.ca", "iptv subscription canada"),
        ("iptvvergelijker.nl", None),
        ("iptvvergleicher.de", None),
        ("iptvguide.ch", None),
    ]
    lines += [
        "",
        "## 4. Keyword → domain picks",
        "",
        "| Domain | Maps to keyword | Volume / KD | RDAP verdict |",
        "| --- | --- | --- | --- |",
    ]
    for domain, kw_name in picks:
        if kw_name and kw_name in kws:
            k = kws[kw_name]
            metrics = f"{k['volume_display']}/mo · KD {k['kd']} {k['kd_label']}"
            kw_label = kw_name
        else:
            metrics = "N/A"
            kw_label = kw_name or "not verified yet"
        lines.append(
            f"| `{cell(domain)}` | {cell(kw_label)} | {cell(metrics)} | {cell(domain_verdict(domain, recheck))} |"
        )

    lines += [
        "",
        "## Rebuild",
        "",
        "`python3 research/iptv-seo/generate_keywords_md.py`",
        "",
        "Also rebuilt from `generate_text_list.py`. Full available/taken dump: `LIST.txt`.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE {OUT} verified={len(kws)} tracked={len(tracked)} serp={len(inspections)}")


if __name__ == "__main__":
    main()
