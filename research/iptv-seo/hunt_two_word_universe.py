#!/usr/bin/env python3
"""RDAP-check two-word app/box/server/subscription domains. No invented volumes."""

from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from continue_research_batch import RDAP, has_dns, http_status, rdap_url, tld_of, verdict
from filters import is_two_word_domain, skip_domain

ROOT = Path(__file__).resolve().parent
RECHECK = ROOT / "availability_recheck.csv"

# Trusted country TLDs for this hunt. No .ie. No .uk names containing iptv.
TLDS = (".ca", ".us", ".fr", ".de", ".nl", ".ch", ".dk", ".no", ".se", ".fi")

# Generic two-word stems only. Brand app names stay SEO keywords, not EMDs.
STEMS = (
    "iptvbox",
    "iptv-box",
    "box-iptv",
    "iptvplayer",
    "iptv-player",
    "player-iptv",
    "iptvapp",
    "iptv-app",
    "app-iptv",
    "iptvserver",
    "iptv-server",
    "server-iptv",
    "iptvpanel",
    "iptv-panel",
    "panel-iptv",
    "iptvportal",
    "iptv-portal",
    "iptvreseller",
    "iptv-reseller",
    "reseller-iptv",
    "iptvplaylist",
    "iptv-playlist",
    "playlist-iptv",
    "iptvtrial",
    "iptv-trial",
    "trial-iptv",
    "iptvsetup",
    "iptv-setup",
    "setup-iptv",
    "iptvcodes",
    "iptv-codes",
    "xtream-iptv",
    "iptv-xtream",
    "m3u-iptv",
    "iptv-m3u",
    "mag-iptv",
    "iptv-mag",
    "magbox",
    "formuler-iptv",
    "formuler-box",
    "android-box",
    "android-iptv",
    "smart-box",
    "firestick-iptv",
    "firestick-box",
    "firetv-iptv",
    "roku-iptv",
    "appletv-iptv",
    "chromecast-iptv",
    "box-guide",
    "player-guide",
    "server-guide",
    "box-avis",
    "player-avis",
    "box-compare",
    "compare-box",
    "guide-box",
    "guide-player",
    "essai-box",
    "test-box",
    "vod-iptv",
    "iptv-vod",
    "premium-iptv",
    "iptv-premium",
    "stick-iptv",
    "iptv-stick",
    "shield-iptv",
    "nvidia-iptv",
)


def candidates() -> list[str]:
    out = []
    seen = set()
    for stem in STEMS:
        for tld in TLDS:
            d = f"{stem}{tld}"
            if skip_domain(d):
                continue
            if not is_two_word_domain(d):
                continue
            if d not in seen:
                seen.add(d)
                out.append(d)
    return out


def main() -> None:
    existing: dict[str, dict] = {}
    if RECHECK.exists():
        with RECHECK.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                existing[r["domain"]] = r

    todo = [d for d in candidates() if d not in existing]
    print(f"universe={len(candidates())} already={len(existing)} todo={len(todo)}")

    new_avail = []
    done = 0

    def check(domain: str) -> tuple[str, dict]:
        code, dns, v = verdict(domain)
        return domain, {
            "domain": domain,
            "rdap": "" if code is None else str(code),
            "dns": "yes" if dns else "no",
            "verdict": v,
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(check, d) for d in todo]
        for fut in as_completed(futs):
            domain, row = fut.result()
            existing[domain] = row
            done += 1
            if row["verdict"] == "AVAILABLE":
                new_avail.append(domain)
            print(f"{done:3}/{len(todo)} {domain:32} rdap={row['rdap']:4} dns={row['dns']:3} {row['verdict']}")

    with RECHECK.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["domain", "rdap", "dns", "verdict"])
        w.writeheader()
        for d in sorted(existing):
            w.writerow(existing[d])

    print("NEW_AVAILABLE", len(new_avail))
    for d in new_avail:
        print(" ", d)


if __name__ == "__main__":
    # Keep unused imports honest for static checkers.
    _ = (RDAP, has_dns, http_status, rdap_url, tld_of)
    main()
