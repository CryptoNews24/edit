#!/usr/bin/env python3
"""Shared list filters for the IPTV hunt."""

from __future__ import annotations

MIN_VOLUME = 500


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
