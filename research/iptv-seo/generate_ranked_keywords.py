#!/usr/bin/env python3
"""One ranked keyword table. Real queries only (no Semrush 'a - b' pair rows). No invented volumes."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from filters import MIN_VOLUME, kd_is_excluded, skip_domain, skip_keyword

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "RANKED_KEYWORDS.md"
TRAFFIC = ROOT / "canva" / "traffic.json"
RECHECK = ROOT / "availability_recheck.csv"

# Markets the user asked to hunt: CA / US / UK / Scandinavia — not .fr leftovers.
FOCUS_DB = {"ca", "us", "uk", "se", "no", "dk", "fi"}
FOCUS_ENDS = (".ca", ".us", ".dk", ".no", ".se", ".fi", ".co.uk", ".uk")
FOCUS_LABEL = {
    "ca": "Canada",
    "us": "United States",
    "uk": "United Kingdom",
    "se": "Sweden",
    "no": "Norway",
    "dk": "Denmark",
    "fi": "Finland",
}

# Participant queries (spaces, not hyphen-pairs). Queued until Semrush Overview exists.
QUEUED = (
    ("tivimate playlist", "us", "TiviMate playlist commercial"),
    ("tivimate setup", "us", "TiviMate install commercial"),
    ("smarters pro", "us", "IPTV Smarters Pro app"),
    ("ibo player", "us", "IBO Player app"),
    ("ibo pro", "us", "IBO Pro app"),
    ("ott navigator", "us", "OTT Navigator app"),
    ("ott play", "us", "OTTplay app"),
    ("gse smart iptv", "us", "GSE Smart IPTV app"),
    ("xtream codes", "us", "Panel / playlist commercial"),
    ("xciptv", "us", "XCIPTV app"),
    ("televizo", "us", "Televizo app"),
    ("ss iptv", "us", "SS IPTV app"),
    ("smart iptv", "us", "Smart IPTV app"),
    ("kodi iptv", "us", "Kodi + IPTV setup"),
    ("perfect player", "us", "Perfect Player app"),
    ("lazy iptv", "us", "Lazy IPTV app"),
    ("iptv extreme", "us", "IPTV Extreme app"),
    ("duplex iptv", "us", "Duplex IPTV app"),
    ("purple player", "us", "Purple Player app"),
    ("flix iptv", "us", "Flix IPTV app"),
    ("magis tv", "us", "Magis TV app"),
    ("google tv iptv", "us", "Google TV box commercial"),
    ("onn box", "us", "Walmart Onn box"),
    ("xiaomi iptv", "us", "Cheap Android box"),
    ("roku iptv", "us", "Roku + IPTV setup"),
    ("vlc iptv", "us", "VLC + playlist setup"),
    ("apple tv iptv", "us", "Apple TV + IPTV"),
    ("fire cube iptv", "us", "Fire TV Cube + IPTV"),
    ("british iptv", "uk", "UK geo commercial — not .irish"),
    ("beste iptv", "no", "Norwegian best IPTV"),
    ("bedste iptv", "dk", "Danish best IPTV"),
    ("basta iptv", "se", "Swedish best IPTV"),
    ("paras iptv", "fi", "Finnish best IPTV"),
    ("tivimate canada", "ca", "TiviMate + CA geo"),
    ("tivimate firestick", "us", "App + Fire Stick"),
    ("formuler iptv", "us", "Formuler box"),
    ("sparkle iptv", "us", "Sparkle TV app"),
    ("set iptv", "us", "SetIPTV app"),
)

# Map queued keyword -> domain needles (two-word focus TLDs).
NEEDLES = {
    "tivimate playlist": ("tivimate-playlist", "playlist-tivimate"),
    "tivimate setup": ("tivimate-setup",),
    "smarters pro": ("smarters-pro", "smarters-box", "smarters-player", "smarters-guide"),
    "ibo player": ("ibo-player", "ibo-box"),
    "ibo pro": ("ibo-pro", "ibopro-player"),
    "ott navigator": ("ott-navigator", "navigator-box"),
    "ott play": ("ott-play", "ottplay-box"),
    "gse smart iptv": ("gse-smart", "gse-player", "gse-box"),
    "xtream codes": ("xtream-guide", "xtream-tivimate", "tivimate-xtream"),
    "xciptv": ("xciptv-box", "xciptv-player", "xciptv-guide"),
    "televizo": ("televizo-box", "televizo-player"),
    "ss iptv": ("ssiptv-box", "ssiptv-player"),
    "smart iptv": ("smartiptv-box",),
    "kodi iptv": ("kodi-guide", "kodi-player", "kodi-box", "tivimate-kodi"),
    "perfect player": ("perfect-player",),
    "lazy iptv": ("lazy-player", "lazyiptv-box"),
    "iptv extreme": ("extreme-player",),
    "duplex iptv": ("duplex-player", "duplex-box"),
    "purple player": ("purple-player", "purple-tv"),
    "flix iptv": ("flix-player", "flixiptv-box"),
    "magis tv": ("magis-tv", "magis-box"),
    "google tv iptv": ("googletv-box", "googletv-tivimate"),
    "onn box": ("onn-box", "onn-player"),
    "xiaomi iptv": ("xiaomi-box", "xiaomi-iptv"),
    "roku iptv": ("roku-guide",),
    "vlc iptv": ("vlc-player",),
    "apple tv iptv": ("appletv-box", "appletv-tivimate"),
    "fire cube iptv": ("firecube-box",),
    "british iptv": ("british-box", "british-guide", "british-iptv"),
    "beste iptv": ("beste-tivimate", "beste-box"),
    "bedste iptv": ("bedste-tivimate", "bedste-box"),
    "basta iptv": ("basta-tivimate", "basta-box"),
    "paras iptv": ("paras-tivimate", "paras-box"),
    "tivimate canada": ("tivimate-canada", "canada-tivimate", "tivimate-box"),
    "tivimate firestick": ("tivimate-firestick", "firestick-guide"),
    "formuler iptv": ("formuler-box", "formuler-guide"),
    "sparkle iptv": ("sparkle-player", "sparkle-box", "sparkle-tv"),
    "set iptv": ("setiptv-box",),
    "best iptv": ("compareiptv", "avis-iptv"),
    "iptv usa": ("usa-tivimate", "tivimate-usa"),
    "best iptv canada": ("compareiptv", "iptvguide"),
    "iptv uk": ("british-box", "british-guide"),
    "iptv firestick": ("firestick-guide", "tivimate-firestick"),
    "iptv subscription": ("tivimate-premium",),
}


def focus_tld(domain: str) -> bool:
    return any(domain.endswith(e) for e in FOCUS_ENDS)


MARKET_ENDS = {
    "ca": (".ca",),
    "us": (".us",),
    "uk": (".co.uk", ".uk"),
    "se": (".se",),
    "no": (".no",),
    "dk": (".dk",),
    "fi": (".fi",),
}


def available_focus(recheck: dict) -> list[str]:
    out = []
    for d, r in recheck.items():
        if r.get("verdict") != "AVAILABLE":
            continue
        if d.endswith(".se"):
            continue
        if skip_domain(d) or not focus_tld(d):
            continue
        out.append(d)
    return out


def pick_leftover(needles: tuple[str, ...], pool: list[str], db: str = "") -> str:
    hits = []
    prefer = MARKET_ENDS.get(db, ())
    for d in pool:
        needle_i = next((i for i, n in enumerate(needles) if n in d), None)
        if needle_i is None:
            continue
        pri = 0
        if prefer and d.endswith(prefer):
            pri = 10
        elif d.endswith(".ca"):
            pri = 3
        elif d.endswith(".us"):
            pri = 2
        elif d.endswith(".co.uk") or d.endswith(".uk"):
            pri = 2
        elif d.endswith((".dk", ".no", ".fi")):
            pri = 1
        hits.append((-pri, needle_i, d))
    hits.sort()
    if not hits:
        return "—"
    _pri, _needle_i, domain = hits[0]
    return domain


def score_row(k: dict) -> float:
    vol = int(k["volume"])
    kd = int(k.get("kd") or 0)
    return vol * (100 - kd) / 100.0


def main() -> None:
    traffic = json.loads(TRAFFIC.read_text(encoding="utf-8"))
    recheck = {}
    with RECHECK.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            recheck[r["domain"]] = r

    pool = available_focus(recheck)

    verified = []
    for name, k in (traffic.get("keywords") or {}).items():
        if skip_keyword(name):
            continue
        if kd_is_excluded(k):
            continue
        try:
            vol = int(k["volume"])
        except (KeyError, TypeError, ValueError):
            continue
        if vol < MIN_VOLUME:
            continue
        db = (k.get("db") or "").lower()
        if db == "ie":
            continue
        if db not in FOCUS_DB and name not in {"iptv uk"}:
            continue
        leftover = pick_leftover(NEEDLES.get(name, (name.replace(" ", "-"),)), pool, db)
        verified.append(
            {
                "keyword": name,
                "market": FOCUS_LABEL.get(db, db),
                "vol": k.get("volume_display") or str(vol),
                "kd": f"{k.get('kd')} {k.get('kd_label') or ''}".strip(),
                "score": score_row(k),
                "why": k.get("intent") or "Commercial",
                "domain": leftover,
                "band": "verified",
            }
        )
    verified.sort(key=lambda r: -r["score"])

    queued = []
    seen = {r["keyword"] for r in verified}
    for name, db, why in QUEUED:
        if skip_keyword(name) or name in seen:
            continue
        leftover = pick_leftover(NEEDLES.get(name, (name.replace(" ", "-"),)), pool, db)
        queued.append(
            {
                "keyword": name,
                "market": FOCUS_LABEL.get(db, db),
                "vol": "N/A",
                "kd": "N/A",
                "score": -1,
                "why": why,
                "domain": leftover,
                "band": "queued",
            }
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Ranked keywords (one table)",
        "",
        f"Updated {now}. **Only this file** is the keyword ranking. Real search queries (spaces). **No Semrush `keyword - keyword` pair rows.** No invented volumes. Difficult KD and volume < {MIN_VOLUME} are out. Focus leftovers: `.ca` `.us` `.co.uk`/`.uk` (no `iptv` in UK labels) `.dk` `.no` `.fi` — not `.fr`. `.se` UNKNOWN is not listed as a buy.",
        "",
        "| Rank | Keyword | Market | Vol / mo | KD | Score | Why it is strong | AVAILABLE leftover (focus TLD) |",
        "| ---: | --- | --- | ---: | --- | ---: | --- | --- |",
    ]
    rank = 1
    for r in verified:
        sc = f"{r['score']:.0f}"
        lines.append(
            f"| {rank} | `{r['keyword']}` | {r['market']} | {r['vol']} | {r['kd']} | {sc} | {r['why']} | `{r['domain']}` |"
        )
        rank += 1
    qn = 1
    for r in queued:
        lines.append(
            f"| Q{qn} | `{r['keyword']}` | {r['market']} | N/A | N/A | — | {r['why']} (Semrush pending) | `{r['domain']}` |"
        )
        qn += 1
    lines += [
        "",
        "Score = volume × (100 − KD) / 100 on verified rows only. Q-rows are participant app/platform queries with no Overview yet.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE {OUT} verified={len(verified)} queued={len(queued)}")


if __name__ == "__main__":
    main()
