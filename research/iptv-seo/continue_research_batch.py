#!/usr/bin/env python3
"""Continue domain RDAP + DuckDuckGo SERP without stopping after one batch."""

from __future__ import annotations

import csv
import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

RDAP = {
    "ca": "https://rdap.ca.fury.ca/rdap/domain/{d}",
    "fr": "https://rdap.nic.fr/domain/{d}",
    "nl": "https://rdap.sidn.nl/domain/{d}",
    "de": "https://rdap.denic.de/domain/{d}",
    "ch": "https://rdap.nic.ch/domain/{d}",
    "net": "https://rdap.verisign.com/net/v1/domain/{d}",
    "com": "https://rdap.verisign.com/com/v1/domain/{d}",
    "at": "https://rdap.nic.at/rdap/domain/{d}",
    "es": "https://rdap.nic.es/rdap/domain/{d}",
    "it": "https://rdap.nic.it/rdap/domain/{d}",
    "se": "https://rdap.iis.se/rdap/domain/{d}",
    "pt": "https://rdap.dns.pt/rdap/domain/{d}",
    "dk": "https://rdap.punktum.dk/rdap/domain/{d}",
    "fi": "https://rdap.fi/rdap/domain/{d}",
    "nz": "https://rdap.nzrs.net.nz/rdap/domain/{d}",
}

UA = "Mozilla/5.0 (compatible; IPTV-SEO-research/1.0; +https://example.invalid)"

CANDIDATES = [
    # France leftovers
    ("avisiptv.fr", "France"),
    ("classementiptv.fr", "France"),
    ("comparatifiptv.fr", "France"),
    ("rankingiptv.fr", "France"),
    ("iptvfiable.fr", "France"),
    ("selectiptv.fr", "France"),
    ("choisiriptv.fr", "France"),
    ("forfaitiptv.fr", "France"),
    ("abo-iptv-avis.fr", "France"),
    ("iptvandroid.fr", "France"),
    ("iptv4k.fr", "France"),
    ("meilleurabo.fr", "France"),
    ("iptvlegal.fr", "France"),
    ("boxandroidiptv.fr", "France"),
    ("playeriptv.fr", "France"),
    # Canada leftovers
    ("iptvrating.ca", "Canada"),
    ("iptvrank.ca", "Canada"),
    ("compare-iptv.ca", "Canada"),
    ("iptvchooser.ca", "Canada"),
    ("quebeciptv.ca", "Canada"),
    ("forfaitiptv.ca", "Canada"),
    ("essaiiptv.ca", "Canada"),
    ("iptvfrancais.ca", "Canada"),
    ("iptvottawa.ca", "Canada"),
    ("iptvcalgary.ca", "Canada"),
    ("iptvwinnipeg.ca", "Canada"),
    ("iptvhalifax.ca", "Canada"),
    ("iptvtoronto.ca", "Canada"),
    ("iptvmontreal.ca", "Canada"),
    ("iptvvancouver.ca", "Canada"),
    ("canadianiptv.ca", "Canada"),
    ("mapleiptvguide.ca", "Canada"),
    ("iptvplans.ca", "Canada"),
    ("watchcompare.ca", "Canada"),
    ("streamrank.ca", "Canada"),
    # NL / DE / CH / AT
    ("iptvgidsvergelijken.nl", "Netherlands"),
    ("beste-iptv.nl", "Netherlands"),
    ("goedkopeiptv.nl", "Netherlands"),
    ("iptvreview.nl", "Netherlands"),
    ("iptvvergelijker.nl", "Netherlands"),
    ("iptvratgeber.de", "Germany"),
    ("iptvtest.de", "Germany"),
    ("iptvguide.de", "Germany"),
    ("iptvvergleicher.de", "Germany"),
    ("anbieteriptv.de", "Germany"),
    ("comparatifiptv.ch", "Switzerland"),
    ("avis-iptv.ch", "Switzerland"),
    ("iptvguide.ch", "Switzerland"),
    ("iptvvergleich.at", "Austria"),
    ("iptvguide.at", "Austria"),
    # BE — mark confirm
    ("iptvgids.be", "Belgium"),
    ("besteiptv.be", "Belgium"),
    ("compareriptv.be", "Belgium"),
    ("abonnementiptv.be", "Belgium"),
    ("iptvbelgie.be", "Belgium"),
    # AU / NZ
    ("compareiptv.com.au", "Australia"),
    ("iptvguide.com.au", "Australia"),
    ("iptvreview.com.au", "Australia"),
    ("bestiptvguide.com.au", "Australia"),
    ("iptvguide.nz", "New Zealand"),
    ("compareiptv.nz", "New Zealand"),
    # ES / IT / PT / Nordics
    ("comparariptv.es", "Spain"),
    ("guiaiptv.es", "Spain"),
    ("mejor-iptv.es", "Spain"),
    ("confrontaiptv.it", "Italy"),
    ("guidaiptv.it", "Italy"),
    ("comparariptv.pt", "Portugal"),
    ("jamforiptv.se", "Sweden"),
    ("sammenligniptv.dk", "Denmark"),
    ("vertaa-iptv.fi", "Finland"),
    # Global .net/.com review names (skip iptv*.uk)
    ("compareiptv.net", "Global"),
    ("iptvpicks.net", "Global"),
    ("streamcompare.net", "Global"),
    ("iptvchooser.net", "Global"),
    ("iptvrating.net", "Global"),
    ("compareiptv.com", "Global"),
    ("iptvcompare.com", "Global"),
    ("avisiptv.com", "Global"),
    ("iptvvergelijker.com", "Global"),
]

SERP_QUERIES = [
    ("iptv quebec", "Canada"),
    ("forfait iptv", "France/Canada"),
    ("iptv toronto", "Canada"),
    ("iptv montreal", "Canada"),
    ("iptv österreich", "Austria"),
    ("iptv espana", "Spain"),
    ("iptv italia", "Italy"),
    ("iptv portugal", "Portugal"),
    ("iptv sverige", "Sweden"),
    ("iptv norge", "Norway"),
    ("iptv danmark", "Denmark"),
    ("iptv suomi", "Finland"),
    ("iptv new zealand", "New Zealand"),
    ("iptv roku", "US/global"),
    ("iptv apple tv", "US/global"),
    ("iptv lg", "Global"),
    ("gse smart iptv", "Global"),
    ("perfect player iptv", "Global"),
    ("iptv vod", "Global"),
    ("iptv 4k", "Global"),
    ("iptv legal france", "France"),
    ("iptv box android", "France"),
    ("meilleur iptv 4k", "France"),
    ("iptv abonnement belgique", "Belgium"),
    ("beste iptv nederland", "Netherlands"),
    ("iptv kostenlos legal", "Germany"),
    ("iptv abonnement suisse", "Switzerland"),
    ("best iptv new zealand", "New Zealand"),
]


def tld_of(domain: str) -> str:
    if domain.endswith(".com.au"):
        return "com.au"
    if domain.endswith(".co.nz"):
        return "co.nz"
    return domain.rsplit(".", 1)[-1]


def rdap_url(domain: str) -> str:
    if domain.endswith(".com.au") or domain.endswith(".be") or domain.endswith(".nz"):
        return f"https://rdap.org/domain/{domain}"
    tmpl = RDAP.get(tld_of(domain))
    return tmpl.format(d=domain) if tmpl else f"https://rdap.org/domain/{domain}"


def http_status(url: str, timeout: int = 16) -> tuple[int | None, dict | None]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                return resp.getcode(), json.loads(raw)
            except json.JSONDecodeError:
                return resp.getcode(), None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None


def has_dns(domain: str) -> bool:
    try:
        socket.getaddrinfo(domain, None)
        return True
    except socket.gaierror:
        return False


def verdict(domain: str) -> tuple[int | None, bool, str]:
    code, _ = http_status(rdap_url(domain))
    dns = has_dns(domain)
    tld = tld_of(domain)
    confirm_tlds = {"be", "com.au", "nz", "es", "it", "pt"}
    if dns:
        v = "TAKEN"
    elif code == 200:
        v = "TAKEN"
    elif code == 404:
        v = "Confirm at registrar" if tld in confirm_tlds else "AVAILABLE"
    else:
        v = "UNKNOWN"
    return code, dns, v


def html_get(url: str, timeout: int = 20) -> str:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def ddg_serp(q: str) -> tuple[str, str, str]:
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": q})
    try:
        page = html_get(url)
    except Exception as e:
        return "error", str(e)[:80], ""
    hrefs = re.findall(r'uddg=([^&"]+)', page)
    hosts = []
    for h in hrefs[:12]:
        try:
            host = urllib.parse.urlparse(urllib.parse.unquote(h)).netloc.lower()
            host = host.removeprefix("www.")
            if host and host not in hosts and "duckduckgo" not in host:
                hosts.append(host)
        except Exception:
            pass
    related = re.findall(r'class="result__a"[^>]*>([^<]+)', page)
    related = [re.sub(r"\s+", " ", x).strip() for x in related][:8]
    n = len(hosts)
    if n == 0:
        strength = "empty/blocked"
    elif any(x.endswith((".guru99.com",)) or "guru99" in x or "softwaretestinghelp" in x for x in hosts[:3]) and n >= 5:
        strength = "moderate-hard"
    elif n <= 4:
        strength = "weak"
    else:
        strength = "moderate"
    return strength, ", ".join(hosts[:6]), "; ".join(related[:6])


def main() -> None:
    recheck_path = ROOT / "availability_recheck.csv"
    existing = {}
    if recheck_path.exists():
        with recheck_path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                existing[r["domain"]] = r

    new_rows = []
    for domain, _country in CANDIDATES:
        code, dns, v = verdict(domain)
        row = {
            "domain": domain,
            "rdap": "" if code is None else str(code),
            "dns": "yes" if dns else "no",
            "verdict": v,
        }
        existing[domain] = row
        new_rows.append(row)
        print(f"{domain:32} rdap={row['rdap']:4} dns={row['dns']:3} {v}")
        time.sleep(0.25)

    with recheck_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["domain", "rdap", "dns", "verdict"])
        w.writeheader()
        for d in sorted(existing):
            w.writerow(existing[d])

    insp_path = ROOT / "keyword_inspections.csv"
    seen = set()
    insp_rows = []
    if insp_path.exists():
        with insp_path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                insp_rows.append(r)
                seen.add(r["Keyword"].lower())

    for kw, market in SERP_QUERIES:
        if kw.lower() in seen:
            continue
        strength, hosts, related = ddg_serp(kw)
        row = {
            "Date": TODAY,
            "Keyword": kw,
            "Market": market,
            "SERP": strength,
            "Top domains": hosts,
            "Related searches": related,
            "Volume": "N/A",
            "Source": "DuckDuckGo",
        }
        insp_rows.append(row)
        seen.add(kw.lower())
        print(f"SERP {kw:28} {strength:16} {hosts[:70]}")
        time.sleep(1.1)

    with insp_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "Date",
                "Keyword",
                "Market",
                "SERP",
                "Top domains",
                "Related searches",
                "Volume",
                "Source",
            ],
        )
        w.writeheader()
        w.writerows(insp_rows)

    out = ROOT / "continue_batch_results.json"
    out.write_text(
        json.dumps(
            {
                "checked": new_rows,
                "inspections_total": len(insp_rows),
                "available": [r["domain"] for r in new_rows if r["verdict"] == "AVAILABLE"],
                "taken": [r["domain"] for r in new_rows if r["verdict"] == "TAKEN"],
                "confirm": [r["domain"] for r in new_rows if r["verdict"].startswith("Confirm")],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"WROTE {out}")


if __name__ == "__main__":
    main()
