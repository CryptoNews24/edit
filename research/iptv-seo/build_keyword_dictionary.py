#!/usr/bin/env python3
"""Expand the IPTV keyword universe. Does not invent volumes.

.ie domains are ignored (IEDR documents required).
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "keyword_dictionary.csv"
SKIP_TLDS = {".ie"}

SERVICES = [
    "iptv",
    "best iptv",
    "iptv provider",
    "iptv subscription",
    "iptv service",
    "iptv services",
    "iptv channels",
    "iptv streaming",
    "iptv player",
    "iptv app",
    "iptv box",
    "iptv trial",
    "iptv free trial",
    "iptv premium",
    "iptv deals",
    "iptv plans",
    "iptv packages",
    "iptv online",
    "iptv streaming service",
    "cheap iptv",
    "iptv review",
    "iptv reviews",
    "iptv comparison",
    "iptv vs cable",
    "legal iptv",
    "iptv 4k",
    "iptv vod",
    "iptv playlist",
]

DEVICES = [
    "iptv for smart tv",
    "iptv for firestick",
    "iptv for fire stick",
    "iptv for android",
    "iptv for samsung",
    "iptv for lg",
    "iptv for roku",
    "iptv for apple tv",
    "iptv firestick",
    "iptv smart tv",
    "iptv android box",
    "iptv nvidia shield",
    "iptv chromecast",
    "iptv mag box",
    "iptv formuler",
]

APPS = [
    "tivimate",
    "tivimate iptv",
    "tivimate premium",
    "tivimate subscription",
    "tivimate playlist",
    "iptv smarters",
    "smarters iptv",
    "iptv smarters pro",
    "smarters pro iptv",
    "iptv smarters subscription",
    "gse smart iptv",
    "smart iptv app",
    "perfect player iptv",
    "xceltv",
    "ott navigator",
    "iptv extreme",
    "set iptv",
    "net iptv",
    "ibo player",
    "duplexplay",
    "iptv player apk",
]

MARKETS = [
    ("Canada", "en", "ca", ["canada", "canadian"]),
    ("Canada", "fr", "ca", ["quebec", "canadien"]),
    ("United States", "en", "us", ["usa", "us", "america"]),
    ("United Kingdom", "en", "uk", ["uk", "britain", "british"]),
    ("France", "fr", "fr", ["france", "francais"]),
    ("Belgium", "fr", "be", ["belgique", "belge"]),
    ("Belgium", "nl", "be", ["belgie", "vlaanderen"]),
    ("Switzerland", "fr", "ch", ["suisse"]),
    ("Switzerland", "de", "ch", ["schweiz"]),
    ("Germany", "de", "de", ["deutschland", "german"]),
    ("Netherlands", "nl", "nl", ["nederland", "dutch"]),
    ("Australia", "en", "au", ["australia", "australian", "aussie"]),
    ("New Zealand", "en", "nz", ["new zealand", "nz"]),
    ("Spain", "es", "es", ["espana", "españa", "spain"]),
    ("Italy", "it", "it", ["italia", "italy"]),
    ("Portugal", "pt", "pt", ["portugal", "portugues"]),
    ("Austria", "de", "at", ["osterreich", "österreich", "austria"]),
    ("Sweden", "sv", "se", ["sverige", "sweden"]),
    ("Norway", "no", "no", ["norge", "norway"]),
    ("Denmark", "da", "dk", ["danmark", "denmark"]),
    ("Finland", "fi", "fi", ["suomi", "finland"]),
    ("Ireland", "en", "ie", ["ireland", "irish"]),  # keywords only, no .ie domains
]

CITIES = {
    "Canada": ["toronto", "montreal", "vancouver", "calgary", "ottawa", "edmonton", "winnipeg", "quebec city"],
    "France": ["paris", "lyon", "marseille", "toulouse", "lille", "bordeaux"],
    "United States": ["new york", "los angeles", "chicago", "houston", "miami"],
    "United Kingdom": ["london", "manchester", "birmingham", "glasgow"],
    "Germany": ["berlin", "munich", "hamburg", "frankfurt", "cologne"],
    "Netherlands": ["amsterdam", "rotterdam", "den haag", "utrecht"],
    "Australia": ["sydney", "melbourne", "brisbane", "perth"],
    "Belgium": ["bruxelles", "brussels", "anvers", "antwerp", "liege", "gand"],
    "Switzerland": ["zurich", "geneve", "geneva", "lausanne", "bern"],
}

LOCAL = {
    "France": [
        "abonnement iptv",
        "meilleur iptv",
        "meilleur abonnement iptv",
        "iptv pas cher",
        "test iptv",
        "essai iptv",
        "iptv box",
        "code iptv",
        "liste iptv",
        "chaine iptv",
        "player iptv",
        "avis iptv",
        "comparateur iptv",
        "abonnement iptv avis",
        "iptv firestick france",
        "iptv smart tv france",
    ],
    "Belgium": [
        "abonnement iptv belgique",
        "meilleur iptv belgique",
        "iptv pas cher belgique",
        "beste iptv belgie",
        "iptv abonnement belgie",
    ],
    "Switzerland": [
        "abonnement iptv suisse",
        "meilleur iptv suisse",
        "iptv abo schweiz",
        "bester iptv schweiz",
    ],
    "Germany": [
        "iptv anbieter",
        "iptv abo",
        "bester iptv",
        "iptv test",
        "iptv vergleich",
        "gunstiger iptv",
        "iptv legal deutschland",
    ],
    "Netherlands": [
        "iptv abonnement",
        "beste iptv",
        "iptv aanbieder",
        "iptv vergelijken",
        "goedkope iptv",
        "iptv proberen",
    ],
    "Spain": [
        "mejor iptv",
        "iptv barato",
        "suscripcion iptv",
        "iptv legal espana",
    ],
    "Italy": [
        "miglior iptv",
        "abbonamento iptv",
        "iptv economica",
        "iptv legale italia",
    ],
    "Portugal": ["melhor iptv", "subscricao iptv", "iptv barato portugal"],
    "Canada": [
        "forfait iptv",
        "essai iptv",
        "meilleur iptv canada",
        "abonnement iptv canada",
        "iptv quebec",
    ],
}

SEEDS_ALREADY = {
    "iptv canada",
    "best iptv canada",
    "iptv ireland",
    "best iptv ireland",
    "abonnement iptv",
}


def domain_hint(country: str, db: str, keyword: str) -> tuple[str, str]:
    if db == "ie" or country == "Ireland":
        return "SKIP_IE_DOCUMENTS", "n/a"
    slug = (
        keyword.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ä", "a")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ñ", "n")
        .replace("ß", "ss")
    )
    slug = "".join(ch if ch.isalnum() else "" for ch in slug)
    if len(slug) < 6 or len(slug) > 24:
        return "cluster-on-country-site", db
    tld = {
        "ca": ".ca",
        "fr": ".fr",
        "be": ".be",
        "ch": ".ch",
        "de": ".de",
        "nl": ".nl",
        "au": ".com.au",
        "nz": ".co.nz",
        "es": ".es",
        "it": ".it",
        "pt": ".pt",
        "at": ".at",
        "se": ".se",
        "no": ".no",
        "dk": ".dk",
        "fi": ".fi",
        "us": ".co",
        "uk": ".co",  # skip .uk when name contains iptv
    }.get(db, ".co")
    if db == "uk" and "iptv" in slug:
        return "brandable-no-iptv-in-uk-tld", ".co"
    return f"{slug}{tld}", tld


def add(rows, seen, country, lang, kw, category, cluster):
    key = (country.lower(), kw.lower())
    if key in seen:
        return
    seen.add(key)
    db = next((m[2] for m in MARKETS if m[0] == country and m[1] == lang), "")
    if not db:
        db = next((m[2] for m in MARKETS if m[0] == country), "")
    hint, tld = domain_hint(country, db, kw)
    if hint in {
        "iptvcanada.ca",
        "iptv-canada.ca",
        "bestiptv.ca",
        "bestiptvcanada.ca",
        "iptvsubscription.ca",
        "abonnementiptv.fr",
        "iptvfrance.fr",
        "meilleuriptv.fr",
    }:
        hint = f"TAKEN:{hint}"
    status = "volume_verified" if kw.lower() in SEEDS_ALREADY else "queued"
    rows.append(
        {
            "Date added": date.today().isoformat(),
            "Country": country,
            "Language": lang,
            "Keyword": kw,
            "Category": category,
            "Cluster": cluster,
            "SEMrush DB": db,
            "Status": status,
            "Domain policy": "ignore_.ie_documents" if country == "Ireland" else "ok",
            "Domain hint": hint,
            "TLD hint": tld,
        }
    )


def main() -> None:
    rows = []
    seen = set()
    for country, lang, db, aliases in MARKETS:
        for svc in SERVICES[:18]:
            add(rows, seen, country, lang, svc, "service", f"{db}_core")
            for alias in aliases:
                add(rows, seen, country, lang, f"{svc} {alias}", "service+geo", f"{db}_geo")
        for device in DEVICES:
            add(rows, seen, country, lang, device, "device", f"{db}_device")
            add(rows, seen, country, lang, f"{device} {aliases[0]}", "device+geo", f"{db}_device")
        for app in APPS:
            add(rows, seen, country, lang, app, "app_seo_only", f"{db}_app")
            add(rows, seen, country, lang, f"{app} {aliases[0]}", "app+geo", f"{db}_app")
        for city in CITIES.get(country, []):
            add(rows, seen, country, lang, f"iptv {city}", "service+city", f"{db}_city")
            add(rows, seen, country, lang, f"best iptv {city}", "best+city", f"{db}_city")
            add(rows, seen, country, lang, f"iptv subscription {city}", "subscription+city", f"{db}_city")
        for loc in LOCAL.get(country, []):
            add(rows, seen, country, lang, loc, "local_language", f"{db}_local")

    extra = [
        ("France", "fr", "iptv firestick france", "device+geo", "fr_device"),
        ("France", "fr", "iptv samsung france", "device+geo", "fr_device"),
        ("Canada", "en", "iptv canada firestick", "device+geo", "ca_device"),
        ("Canada", "en", "iptv canada legal", "legal", "ca_core"),
        ("United States", "en", "best iptv service", "service+best", "us_core"),
        ("United States", "en", "iptv subscription", "subscription", "us_core"),
        ("Germany", "de", "iptv firestick deutschland", "device+geo", "de_device"),
        ("Netherlands", "nl", "iptv firestick nederland", "device+geo", "nl_device"),
        ("Australia", "en", "iptv australia firestick", "device+geo", "au_device"),
        ("Spain", "es", "iptv firestick espana", "device+geo", "es_device"),
        ("Italy", "it", "iptv firestick italia", "device+geo", "it_device"),
    ]
    for item in extra:
        add(rows, seen, *item)

    fields = list(rows[0].keys())
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"WROTE {OUT} rows={len(rows)} unique={len(seen)}")


if __name__ == "__main__":
    main()
