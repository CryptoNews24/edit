#!/usr/bin/env python3
"""Shared list filters for the IPTV hunt."""

from __future__ import annotations

MIN_VOLUME = 500


def opportunity_score(volume: int, kd: int) -> float:
    """Higher is better: more searches, lower keyword difficulty."""
    kd = max(0, min(100, int(kd)))
    return round(volume * (100 - kd) / 100.0, 1)


def keyword_volume(traffic: dict, name: str | None) -> int | None:
    if not name:
        return None
    k = (traffic.get("keywords") or {}).get(name)
    if not k:
        return None
    try:
        return int(k["volume"])
    except (KeyError, TypeError, ValueError):
        return None


def meets_volume(traffic: dict, name: str | None) -> bool:
    vol = keyword_volume(traffic, name)
    return vol is not None and vol >= MIN_VOLUME


def mapped_keyword(traffic: dict, domain: str) -> str | None:
    return (traffic.get("domain_keyword_map") or {}).get(domain)


def domain_meets_volume(traffic: dict, domain: str) -> bool:
    return meets_volume(traffic, mapped_keyword(traffic, domain))


PREFERRED_DOMAINS = (
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
    "compareiptv.fr",
    "pas-cher-iptv.fr",
)


def rank_available_domains(traffic: dict, recheck: dict, limit: int = 10, per_keyword: int = 3) -> list[dict]:
    """AVAILABLE names, volume >= 500, sorted by high traffic and low KD."""
    scored = []
    kws = traffic.get("keywords") or {}
    for domain, row in recheck.items():
        if row.get("verdict") != "AVAILABLE":
            continue
        if domain.endswith(".ie"):
            continue
        if "iptv" in domain and (domain.endswith(".uk") or ".co.uk" in domain):
            continue
        kw = mapped_keyword(traffic, domain)
        if not meets_volume(traffic, kw):
            continue
        k = kws[kw]
        vol = int(k["volume"])
        kd = int(k["kd"])
        scored.append(
            {
                "domain": domain,
                "keyword": kw,
                "volume": vol,
                "volume_display": k.get("volume_display"),
                "kd": kd,
                "kd_label": k.get("kd_label"),
                "cpc": k.get("cpc"),
                "db": k.get("db"),
                "score": opportunity_score(vol, kd),
                "preferred": domain in PREFERRED_DOMAINS,
            }
        )
    scored.sort(key=lambda r: (-r["score"], 0 if r["preferred"] else 1, len(r["domain"]), r["domain"]))
    out: list[dict] = []
    seen_kw: set[str] = set()
    for row in scored:
        if row["keyword"] in seen_kw:
            continue
        if row["db"] == "ie":
            continue
        seen_kw.add(row["keyword"])
        out.append(row)
        if len(out) >= limit:
            return out
    counts = {row["keyword"]: 1 for row in out}
    taken = {row["domain"] for row in out}
    for row in scored:
        if row["domain"] in taken:
            continue
        n = counts.get(row["keyword"], 0)
        if n >= per_keyword:
            continue
        counts[row["keyword"]] = n + 1
        out.append(row)
        taken.add(row["domain"])
        if len(out) >= limit:
            break
    return out
