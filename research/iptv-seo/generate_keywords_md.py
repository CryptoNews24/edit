#!/usr/bin/env python3
"""Write KEYWORDS.md — markdown tables for keyword research."""

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
    mapped_keyword,
    meets_volume,
    rank_available_domains,
    skip_domain,
)

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
        f"Updated {now}. **AVAILABLE domains only**, plus drop-watch (taken + site down + almost expired) when mapped Semrush volume is **>= {MIN_VOLUME}/mo**.",
        f"Keywords with Semrush volume **under {MIN_VOLUME}** are excluded. Unverified (N/A) keywords are excluded until Semrush confirms them.",
        "",
        "Semrush refresh attempted this run: **Noxtools Cloudflare-blocked** from this IP; public Semrush HTML has no live metrics. Figures below are the last verified pulls (not invented). They will be replaced as soon as Noxtools/Semrush is reachable.",
        "",
        "Rules: do not buy from this file. `iptvcanada.ca` is **TAKEN**. Ignore `.ie` domains. Skip `.uk` names that contain `iptv`. TiviMate / IPTV Smarters = SEO topics, not brand domains.",
        "",
        "Noxtools still works in a normal browser. This cloud IP is blocked by Cloudflare, so new Semrush rows cannot be filled from here until that clears.",
        "",
        "## Top 10 AVAILABLE (high traffic, low competition)",
        "",
        "Score = Semrush volume × (100 − KD) / 100. Higher is better. Only AVAILABLE names with verified volume ≥ 500. At most 3 domains per keyword so the list is not ten copies of the same French head term.",
        "",
        "| Rank | Domain | Keyword | Volume / mo | KD | Score |",
        "| ---: | --- | --- | ---: | --- | ---: |",
    ]

    for i, row in enumerate(rank_available_domains(traffic, recheck, 10), start=1):
        lines.append(
            f"| {i} | `{cell(row['domain'])}` | {cell(row['keyword'])} | {cell(row['volume_display'])} | {row['kd']} {cell(row['kd_label'])} | {row['score']} |"
        )

    lines += [
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
            "priority": "EXCLUDED (<500)",
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
        if not meets_volume({"keywords": kws}, name):
            continue
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
        "Canada verified cluster ≈ **16.7K**/mo (`iptv canada` + `best iptv canada`). `iptv subscription canada` (390) is excluded (<500).",
        "",
        "## 2. Tracked keywords (Semrush volume >= 500 only)",
        "",
        "Unverified rows and volumes under 500 are omitted. Ireland is SEO-only (no `.ie` domain).",
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
        raw = r.get("Search Volume") or "N/A"
        try:
            vol_n = int(float(raw))
        except ValueError:
            continue
        if vol_n < MIN_VOLUME:
            continue
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
        "## 3. SERP notes (keywords with volume >= 500)",
        "",
        "| Keyword | Market | SERP | Top domains | Related searches |",
        "| --- | --- | --- | --- | --- |",
    ]
    keep_kw = {n.lower() for n in kws if meets_volume({"keywords": kws}, n)}
    for r in inspections:
        if r["Keyword"].lower() not in keep_kw:
            continue
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
        ("guide-abonnement-iptv.fr", "iptv france"),
        ("avis-abonnement-iptv.fr", "abonnement iptv"),
    ]
    lines += [
        "",
        "## 4. Keyword → domain picks",
        "",
        "| Domain | Maps to keyword | Volume / KD | RDAP verdict |",
        "| --- | --- | --- | --- |",
    ]
    for domain, kw_name in picks:
        if not meets_volume(traffic, kw_name):
            continue
        k = kws[kw_name]
        metrics = f"{k['volume_display']}/mo · KD {k['kd']} {k['kd_label']}"
        if domain_verdict(domain, recheck) != "AVAILABLE":
            continue
        lines.append(
            f"| `{cell(domain)}` | {cell(kw_name)} | {cell(metrics)} | AVAILABLE |"
        )

    lines += [
        "",
        "## 5. AVAILABLE domains (mapped Semrush volume >= 500)",
        "",
        "| Domain | Country | Keyword | Volume / mo | KD | Availability |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    country_of = {
        ".fr": "France",
        ".ca": "Canada",
        ".ch": "Switzerland",
        ".nl": "Netherlands",
        ".de": "Germany",
        ".us": "United States",
        ".co.uk": "United Kingdom",
        ".no": "Norway",
        ".dk": "Denmark",
        ".fi": "Finland",
        ".se": "Sweden",
        ".be": "Belgium",
        ".at": "Austria",
        ".es": "Spain",
        ".it": "Italy",
        ".pt": "Portugal",
        ".net": "Global",
        ".com": "Global",
        ".eu": "EU",
    }

    def ctry(d: str) -> str:
        for s, n in sorted(country_of.items(), key=lambda x: -len(x[0])):
            if d.endswith(s):
                return n
        return "Other"

    avail_rows = []
    for d, r in recheck.items():
        if r["verdict"] != "AVAILABLE" or skip_domain(d):
            continue
        if not domain_meets_volume(traffic, d):
            continue
        kw_name = mapped_keyword(traffic, d)
        k = kws[kw_name]
        avail_rows.append((ctry(d), d, kw_name, k))
    for country, d, kw_name, k in sorted(avail_rows, key=lambda x: (-int(x[3]["volume"]), x[0], x[1])):
        lines.append(
            f"| `{cell(d)}` | {cell(country)} | {cell(kw_name)} | {cell(k['volume_display'])} | {k['kd']} {k['kd_label']} | AVAILABLE |"
        )

    lines += [
        "",
        "## 6. Drop-watch only (taken + site down + almost expired + volume >= 500)",
        "",
        "Not for sale today. Shown because the mapped keyword is strong and the site is dead.",
        "",
        "| Domain | Keyword | Volume / mo | Site | Expiry |",
        "| --- | --- | ---: | --- | --- |",
    ]
    with (ROOT / "almost_expired_offline.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = r["Domain"]
            if not domain_meets_volume(traffic, d):
                continue
            kw_name = mapped_keyword(traffic, d)
            k = kws[kw_name]
            lines.append(
                f"| `{cell(d)}` | {cell(kw_name)} | {cell(k['volume_display'])} | {cell(r.get('Website status'))} | {cell(r.get('Expiry date'))} |"
            )

    brand_skip = ("tivimate", "smartersguide", "smarters-")
    us_uk = []
    for d, r in sorted(recheck.items()):
        if not (d.endswith(".us") or d.endswith(".co.uk") or (d.endswith(".uk") and not d.endswith(".co.uk"))):
            continue
        if "iptv" in d and (d.endswith(".uk") or d.endswith(".co.uk")):
            continue
        note = ""
        if "tivimate" in d or "smartersguide" in d or "smarters-" in d:
            note = "SEO topic only — do not register brand EMD"
        us_uk.append((d, r, note))
    avail_uu = [x for x in us_uk if x[1]["verdict"] == "AVAILABLE"]
    taken_uu = [x for x in us_uk if x[1]["verdict"] == "TAKEN"]
    lines += [
        "",
        "## 7. `.us` and `.uk` (no `iptv` in `.uk` names)",
        "",
        "Native RDAP: `rdap.nic.us` and Nominet. **404 + no DNS = AVAILABLE**. Semrush US/UK volume is still **N/A** from this IP, so these are **not** in the Top 10 until a keyword is verified ≥ 500.",
        f"Checked {len(us_uk)} names this hunt: **{len(avail_uu)} AVAILABLE**, **{len(taken_uu)} TAKEN**.",
        "",
        "### AVAILABLE `.us` / `.uk`",
        "",
        "| Domain | TLD | Notes |",
        "| --- | --- | --- |",
    ]
    for d, r, note in avail_uu:
        tld = ".us" if d.endswith(".us") else ".co.uk"
        lines.append(f"| `{cell(d)}` | {tld} | {cell(note or 'native RDAP 404 + no DNS')} |")
    lines += [
        "",
        "### TAKEN `.us` / `.uk` — do not buy",
        "",
        "| Domain | TLD | DNS |",
        "| --- | --- | --- |",
    ]
    for d, r, note in taken_uu:
        tld = ".us" if d.endswith(".us") else ".co.uk"
        lines.append(f"| `{cell(d)}` | {tld} | {cell(r['dns'])} |")

    groups = country_tld_groups(recheck)
    lines += [
        "",
        "## 8. Country TLDs — `.ca`, `.us`, and Europe",
        "",
        "Full RDAP+DNS hunt across country-code names. Native registries: CIRA (`.ca`), nic.us (`.us`), AFNIC, DENIC, SIDN, SWITCH, Norid, Punktum, Traficom, Nominet. **404 + no DNS = AVAILABLE** on those. "
        "`.be` / `.es` / `.it` / `.pt` / `.at` / `.se` / `.pl` / `.cz` / `.eu` are **not** listed as AVAILABLE — confirm at a registrar. **`.ie` ignored.** `.uk` names that contain `iptv` are skipped.",
        "Semrush is still unverified for US/UK/most EU languages from this IP, so these sit **outside** the Top 10 until volume ≥ 500 is confirmed.",
        "",
        "| TLD | Country | AVAILABLE | TAKEN | Confirm | UNKNOWN |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for tld, label in COUNTRY_TLD_LABELS:
        g = groups[tld]
        lines.append(
            f"| .{tld} | {label} | {len(g['AVAILABLE'])} | {len(g['TAKEN'])} | {len(g['CONFIRM'])} | {len(g['UNKNOWN'])} |"
        )
    for tld, label in COUNTRY_TLD_LABELS:
        g = groups[tld]
        if not any(g.values()):
            continue
        lines += ["", f"### .{tld} — {label}", ""]
        if g["AVAILABLE"]:
            lines += [
                f"**AVAILABLE ({len(g['AVAILABLE'])})** — native RDAP 404 + no DNS.",
                "",
                "| Domain |",
                "| --- |",
            ]
            for d in g["AVAILABLE"]:
                note = ""
                if "tivimate" in d or "smartersguide" in d or "smarters-" in d:
                    note = " — SEO topic only, do not register brand EMD"
                lines.append(f"| `{cell(d)}`{note} |")
            lines.append("")
        else:
            lines.append("No names marked AVAILABLE (native RDAP not trusted, or none free).")
            lines.append("")
        if g["TAKEN"]:
            lines.append("**TAKEN — do not buy:** " + ", ".join(f"`{d}`" for d in g["TAKEN"]))
            lines.append("")
        if g["CONFIRM"]:
            lines.append("**Confirm at registrar (not listed as free):** " + ", ".join(f"`{d}`" for d in g["CONFIRM"]))
            lines.append("")
        if g["UNKNOWN"]:
            lines.append("**UNKNOWN (RDAP failed):** " + ", ".join(f"`{d}`" for d in g["UNKNOWN"]))
            lines.append("")

    lines += [
        "",
        "## Rebuild",
        "",
        "`python3 research/iptv-seo/generate_keywords_md.py`",
        "",
        "Also rebuilt from `generate_text_list.py`. Domain dump (same filters): `LIST.txt`.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE {OUT} verified={len(kws)} tracked={len(tracked)} serp={len(inspections)}")


if __name__ == "__main__":
    main()
