#!/usr/bin/env python3
"""Live-recheck every volume-mapped AVAILABLE name. Flip TAKEN if RDAP/DNS says so."""

from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from continue_research_batch import verdict
from filters import domain_meets_volume, skip_domain

ROOT = Path(__file__).resolve().parent
RECHECK = ROOT / "availability_recheck.csv"
TRAFFIC = ROOT / "canva" / "traffic.json"

# Always re-probe these even if mapping/volume changes.
MUST = (
    "compareriptv.fr",
    "avis-iptv.fr",
    "comparateur-iptv.fr",
    "box-avis.fr",
    "essaiiptv.fr",
    "essai-iptv.fr",
    "guideiptv.fr",
    "pascheriptv.fr",
    "compareiptv.ca",
    "iptvguide.ca",
    "compareriptv.ca",
    "compareiptv.us",
    "avis-iptv.us",
    "cordcutusa.us",
    "firestick-iptv.us",
    "abonnementiptv.fr",
)


def main() -> None:
    traffic = json.loads(TRAFFIC.read_text(encoding="utf-8"))
    existing: dict[str, dict] = {}
    with RECHECK.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            existing[r["domain"]] = r

    todo = set(MUST)
    for d, r in existing.items():
        if skip_domain(d):
            continue
        if r.get("verdict") == "AVAILABLE" and domain_meets_volume(traffic, d):
            todo.add(d)
    todo = sorted(todo)
    print(f"recheck {len(todo)} names")

    flipped = []

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
        done = 0
        for fut in as_completed(futs):
            domain, row = fut.result()
            old = existing.get(domain, {}).get("verdict")
            existing[domain] = row
            done += 1
            mark = ""
            if old == "AVAILABLE" and row["verdict"] != "AVAILABLE":
                flipped.append(domain)
                mark = "  FLIPPED"
            print(
                f"{done:3}/{len(todo)} {domain:32} rdap={row['rdap']:4} "
                f"dns={row['dns']:3} {row['verdict']}{mark}"
            )

    with RECHECK.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["domain", "rdap", "dns", "verdict"])
        w.writeheader()
        for d in sorted(existing):
            w.writerow(existing[d])

    print("FLIPPED_OFF_AVAILABLE", len(flipped))
    for d in flipped:
        print(" ", d)


if __name__ == "__main__":
    main()
