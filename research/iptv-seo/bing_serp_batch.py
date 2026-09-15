#!/usr/bin/env python3
"""Bing SERP follow-up (DuckDuckGo html endpoint now returns an empty shell)."""

from __future__ import annotations

import csv
import html as htmlmod
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

QUERIES = [
    ("iptv quebec", "Canada"),
    ("forfait iptv", "France/Canada"),
    ("iptv toronto", "Canada"),
    ("iptv montreal", "Canada"),
    ("iptv osterreich", "Austria"),
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
    ("iptv provider canada", "Canada"),
    ("iptv trial canada", "Canada"),
    ("iptv vancouver", "Canada"),
    ("fournisseur iptv", "France"),
]


def bing(q: str) -> tuple[str, str]:
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": q})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=22) as resp:
        page = resp.read().decode("utf-8", "replace")
    cites = re.findall(r"<cite[^>]*>(.*?)</cite>", page, flags=re.I | re.S)
    hosts = []
    for c in cites:
        t = htmlmod.unescape(re.sub("<[^>]+>", "", c))
        t = re.sub(r"\s+", " ", t).strip()
        t = re.sub(r"^https?://", "", t)
        host = t.split()[0].split("/")[0].split("›")[0].strip(" .").lower()
        host = host.removeprefix("www.")
        if host and host not in hosts and "bing.com" not in host:
            hosts.append(host)
    n = len(hosts)
    if n == 0:
        strength = "empty/blocked"
    elif n <= 4:
        strength = "weak"
    elif any("guru99" in h or "softwaretestinghelp" in h for h in hosts[:3]):
        strength = "moderate-hard"
    else:
        strength = "moderate"
    return strength, ", ".join(hosts[:8])


def main() -> None:
    path = ROOT / "keyword_inspections.csv"
    rows = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("SERP") == "empty/blocked":
                continue
            rows.append(r)
    seen = {r["Keyword"].lower() for r in rows}
    for kw, market in QUERIES:
        if kw.lower() in seen:
            continue
        try:
            strength, hosts = bing(kw)
        except Exception as e:
            print("ERR", kw, e)
            time.sleep(2)
            continue
        rows.append(
            {
                "Date": TODAY,
                "Keyword": kw,
                "Market": market,
                "SERP": strength,
                "Top domains": hosts,
                "Related searches": "",
                "Volume": "N/A",
                "Source": "Bing",
            }
        )
        seen.add(kw.lower())
        print(f"{kw:32} {strength:16} {hosts[:90]}")
        time.sleep(1.4)
    with path.open("w", encoding="utf-8", newline="") as f:
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
        w.writerows(rows)
    print("inspections", len(rows))


if __name__ == "__main__":
    main()
