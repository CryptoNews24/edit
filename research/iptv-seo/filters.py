#!/usr/bin/env python3
"""Shared list filters for the IPTV hunt."""

from __future__ import annotations

MIN_VOLUME = 500

# Country-code hunt order: CA, US, then Europe. `.ie` is never listed.
COUNTRY_TLD_LABELS = [
    ("ca", "Canada"),
    ("us", "United States"),
    ("fr", "France"),
    ("de", "Germany"),
    ("nl", "Netherlands"),
    ("ch", "Switzerland"),
    ("be", "Belgium"),
    ("at", "Austria"),
    ("es", "Spain"),
    ("it", "Italy"),
    ("pt", "Portugal"),
    ("se", "Sweden"),
    ("no", "Norway"),
    ("dk", "Denmark"),
    ("fi", "Finland"),
    ("pl", "Poland"),
    ("cz", "Czechia"),
    ("eu", "EU (.eu)"),
    ("co.uk", "United Kingdom"),
]


# Longest-first tokens so compareiptv → compare + iptv, not leftover junk.
_WORD_TOKENS = tuple(
    sorted(
        {
            "abonnement",
            "comparateur",
            "comparatif",
            "classement",
            "anbietervergleich",
            "aanbieders",
            "vergelijken",
            "vergelijker",
            "vergleicher",
            "vergleich",
            "streaming",
            "firestick",
            "androidtv",
            "android",
            "appletv",
            "smarters",
            "tivimate",
            "formuler",
            "canadian",
            "canada",
            "quebec",
            "ontario",
            "france",
            "deutsch",
            "nederland",
            "belgique",
            "belgie",
            "schweiz",
            "suisse",
            "meilleur",
            "pascher",
            "compare",
            "comparer",
            "stream",
            "watch",
            "guide",
            "avis",
            "essai",
            "test",
            "trial",
            "forfait",
            "abo",
            "liste",
            "legal",
            "reddit",
            "player",
            "picks",
            "plans",
            "rank",
            "rating",
            "review",
            "reviews",
            "deals",
            "cheap",
            "best",
            "beste",
            "bedste",
            "paras",
            "basta",
            "sammenlign",
            "vertaa",
            "jamfor",
            "iptv",
            "live",
            "box",
            "ott",
            "tv",
            "4k",
            "usa",
            "uk",
            "nl",
            "de",
            "fr",
            "ch",
            "be",
            "no",
            "dk",
            "fi",
            "nord",
            "maple",
            "roku",
            "samsung",
            "cordcut",
            "cordcutter",
            "cutthecord",
            "smarttv",
            "smarter",
            "xtream",
            "m3u",
            "mag",
            "stick",
            "apps",
            "app",
            "gids",
            "opas",
            "pruvodce",
            "przewodnik",
            "guia",
            "guida",
            "confronta",
            "comparar",
            "mejor",
            "migliore",
            "melhor",
            "najlepszy",
            "nejlepsi",
            "porownaj",
            "srovnani",
            "ratgeber",
            "anbieter",
            "goedkoop",
            "goedkope",
            "guenstig",
            "guenstige",
            "houston",
            "dallas",
            "miami",
            "atlanta",
            "seattle",
            "denver",
            "boston",
            "detroit",
            "philadelphia",
            "lasvegas",
            "portland",
            "nashville",
            "austin",
            "charlotte",
            "toronto",
            "montreal",
            "vancouver",
            "calgary",
            "ottawa",
            "edmonton",
            "winnipeg",
            "halifax",
            "hamilton",
            "kelowna",
            "regina",
            "saskatoon",
            "victoria",
            "mississauga",
            "brampton",
            "laval",
            "gatineau",
            "windsor",
            "london",
            "alberta",
            "manitoba",
            "atlantic",
            "sask",
            "bc",
            "kw",
            "berlin",
            "hamburg",
            "muenchen",
            "frankfurt",
            "stuttgart",
            "koeln",
            "duesseldorf",
            "amsterdam",
            "rotterdam",
            "utrecht",
            "eindhoven",
            "denhaag",
            "zurich",
            "geneve",
            "lausanne",
            "bern",
            "basel",
            "oslo",
            "bergen",
            "kobenhavn",
            "aarhus",
            "helsinki",
            "tampere",
            "paris",
            "lyon",
            "marseille",
            "toulouse",
            "lille",
            "nantes",
            "bordeaux",
            "nice",
            "reims",
            "dijon",
            "angers",
            "madrid",
            "barcelona",
            "roma",
            "milano",
            "lisboa",
            "wien",
            "praha",
            "warszawa",
            "chooser",
            "checker",
            "compareott",
            "paytv",
            "playlist",
            "smart",
            "tivi",
            "mate",
        },
        key=len,
        reverse=True,
    )
)


def domain_label(domain: str) -> str:
    d = domain.lower().strip()
    if d.endswith(".co.uk"):
        return d[: -len(".co.uk")]
    if d.endswith(".com.au"):
        return d[: -len(".com.au")]
    if "." in d:
        return d.rsplit(".", 1)[0]
    return d


def _tokenize_piece(piece: str) -> list[str]:
    s = piece.lower()
    out: list[str] = []
    i = 0
    while i < len(s):
        hit = None
        for tok in _WORD_TOKENS:
            if s.startswith(tok, i):
                hit = tok
                break
        if hit:
            out.append(hit)
            i += len(hit)
            continue
        out.append(s[i:])
        break
    return out


def domain_word_count(domain: str) -> int:
    """Hyphen parts plus smashed words inside each part (compareiptv = 2)."""
    label = domain_label(domain)
    if not label:
        return 0
    total = 0
    for part in label.replace("_", "-").split("-"):
        if not part:
            continue
        total += len(_tokenize_piece(part))
    return total


def is_two_word_domain(domain: str) -> bool:
    return domain_word_count(domain) == 2


def skip_domain(domain: str) -> bool:
    if domain.endswith(".ie"):
        return True
    if "iptv" in domain and (domain.endswith(".uk") or domain.endswith(".co.uk")):
        return True
    if not is_two_word_domain(domain):
        return True
    return False


def tld_key(domain: str) -> str:
    if domain.endswith(".co.uk"):
        return "co.uk"
    if domain.endswith(".com.au"):
        return "com.au"
    return domain.rsplit(".", 1)[-1]


def verdict_bucket(verdict: str) -> str:
    v = (verdict or "").strip()
    if v == "AVAILABLE":
        return "AVAILABLE"
    if v == "TAKEN":
        return "TAKEN"
    if v == "UNKNOWN":
        return "UNKNOWN"
    return "CONFIRM"


def country_tld_groups(recheck: dict[str, dict]) -> dict[str, dict[str, list[str]]]:
    """AVAILABLE / TAKEN / CONFIRM / UNKNOWN names per country TLD."""
    out: dict[str, dict[str, list[str]]] = {}
    for tld, _label in COUNTRY_TLD_LABELS:
        out[tld] = {"AVAILABLE": [], "TAKEN": [], "CONFIRM": [], "UNKNOWN": []}
    for domain, row in recheck.items():
        if skip_domain(domain):
            continue
        tld = tld_key(domain)
        if tld not in out:
            continue
        out[tld][verdict_bucket(row.get("verdict") or "")].append(domain)
    for tld in out:
        for k in out[tld]:
            out[tld][k].sort()
    return out


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
    "compareiptv.fr",
    "compareiptv.us",
    "avis-iptv.us",
    "firestick-guide.us",
)


def rank_available_domains(traffic: dict, recheck: dict, limit: int = 10, per_keyword: int = 3) -> list[dict]:
    """AVAILABLE names, volume >= 500, sorted by high traffic and low KD."""
    scored = []
    kws = traffic.get("keywords") or {}
    for domain, row in recheck.items():
        if row.get("verdict") != "AVAILABLE":
            continue
        if skip_domain(domain):
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
