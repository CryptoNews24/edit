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

# Player / box names are SEO seeds only. Do not turn brand names into EMD domains.
APPS = [
    "tivimate",
    "tivimate iptv",
    "tivimate premium",
    "tivimate subscription",
    "tivimate playlist",
    "tivimate firestick",
    "tivimate android",
    "tivimate box",
    "iptv smarters",
    "smarters iptv",
    "iptv smarters pro",
    "smarters pro iptv",
    "iptv smarters subscription",
    "smarters pro firestick",
    "gse smart iptv",
    "smart iptv app",
    "smart iptv subscription",
    "perfect player iptv",
    "xceltv",
    "xciptv",
    "xciptv player",
    "ott navigator",
    "ott navigator iptv",
    "iptv extreme",
    "iptv extreme pro",
    "set iptv",
    "net iptv",
    "ibo player",
    "ibo player iptv",
    "duplexplay",
    "duplex play iptv",
    "iptv player apk",
    "televizo",
    "televizo iptv",
    "lazy iptv",
    "ss iptv",
    "flix iptv",
    "sparkle tv iptv",
    "iptv pro",
    "myiptv player",
    "xeplayer iptv",
    "kodi iptv",
    "vlc iptv",
    "downloader iptv",
    "family player iptv",
    "bob player iptv",
    "9xtream",
    "xtream codes iptv",
    "xtream ui iptv",
    "m3u iptv",
    "mag 254 iptv",
    "mag 256 iptv",
    "formuler iptv",
    "formuler z11",
    "buzztv iptv",
    "dreamlink iptv",
    "zgemma iptv",
    "enigma2 iptv",
    "nvidia shield iptv",
    "firestick iptv",
    "fire tv iptv",
    "apple tv iptv",
    "roku iptv",
    "chromecast iptv",
    "android box iptv",
    "iptv box",
    "iptv server",
    "iptv subscription",
    "iptv reseller",
    "iptv panel",
    "iptv portal",
    "iptv playlist",
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
        "iptv android france",
        "iptv box android",
        "code xtream",
        "m3u iptv france",
        "iptv 4k france",
        "iptv mag france",
        "meilleur iptv box",
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
        "iptv firestick",
        "iptv mag",
        "iptv box kaufen",
        "bester iptv anbieter",
    ],
    "Netherlands": [
        "iptv abonnement",
        "beste iptv",
        "iptv aanbieder",
        "iptv vergelijken",
        "goedkope iptv",
        "iptv proberen",
        "iptv firestick nederland",
        "iptv box nederland",
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
        "iptv firestick canada",
        "best iptv firestick",
        "iptv android canada",
    ],
    "United States": [
        "best iptv service",
        "best iptv subscription",
        "iptv for firestick",
        "iptv reseller",
        "iptv server",
        "iptv panel",
        "iptv m3u playlist",
        "xtream codes",
        "android box iptv",
    ],
    "Sweden": ["basta iptv", "billig iptv sverige", "iptv abonnemang"],
    "Norway": ["beste iptv norge", "billig iptv", "iptv abonnement norge"],
    "Denmark": ["bedste iptv", "billig iptv danmark", "iptv abonnement"],
    "Finland": ["paras iptv", "halpa iptv", "iptv suomi"],
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
        hint, tld = "", ""
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
        ("France", "fr", "iptv box android", "device", "fr_device"),
        ("France", "fr", "code xtream", "server", "fr_server"),
        ("France", "fr", "m3u iptv", "playlist", "fr_playlist"),
        ("United States", "en", "iptv reseller", "b2b", "us_b2b"),
        ("United States", "en", "iptv server", "b2b", "us_b2b"),
        ("United States", "en", "iptv panel", "b2b", "us_b2b"),
        ("United States", "en", "xtream codes", "server", "us_server"),
        ("United States", "en", "iptv m3u", "playlist", "us_playlist"),
        ("Germany", "de", "iptv anbieter vergleich", "local_language", "de_local"),
        ("Germany", "de", "iptv box kaufen", "device", "de_device"),
        ("Netherlands", "nl", "iptv abonnement", "local_language", "nl_local"),
        ("Canada", "fr", "forfait iptv quebec", "local_language", "ca_fr"),
        ("Spain", "es", "mejor iptv", "local_language", "es_local"),
        ("Italy", "it", "abbonamento iptv", "local_language", "it_local"),
        ("Norway", "no", "beste iptv norge", "local_language", "no_local"),
        ("Sweden", "sv", "basta iptv", "local_language", "se_local"),
        ("Denmark", "da", "bedste iptv", "local_language", "dk_local"),
        ("Finland", "fi", "paras iptv", "local_language", "fi_local"),
        ("Switzerland", "fr", "abonnement iptv suisse", "local_language", "ch_local"),
        ("Switzerland", "de", "iptv abo schweiz", "local_language", "ch_local"),
        ("France", "fr", "iptv sport", "content", "fr_content"),
        ("France", "fr", "replay iptv", "content", "fr_content"),
        ("France", "fr", "iptv epg", "guide", "fr_guide"),
        ("United States", "en", "iptv sports", "content", "us_content"),
        ("United States", "en", "iptv epg", "guide", "us_guide"),
        ("Germany", "de", "iptv sport", "content", "de_content"),
        ("Netherlands", "nl", "iptv sport", "content", "nl_content"),
        ("Canada", "en", "iptv sports canada", "content", "ca_content"),
        ("France", "fr", "iptv enfants", "content", "fr_content"),
        ("United States", "en", "iptv kids", "content", "us_content"),
        ("United States", "en", "iptv news", "content", "us_content"),
        ("United States", "en", "how to install iptv", "howto", "us_howto"),
        ("France", "fr", "installer iptv", "howto", "fr_howto"),
        ("Germany", "de", "iptv einrichten", "howto", "de_howto"),
        ("France", "fr", "bouquet iptv", "content", "fr_content"),
        ("United States", "en", "iptv vpn", "howto", "us_howto"),
        ("United States", "en", "xtream line", "reseller", "us_b2b"),
        ("Canada", "en", "iptv mac address", "device", "ca_device"),
        ("France", "fr", "iptv arabe", "geo_lang", "fr_maghreb"),
        ("France", "fr", "iptv maroc", "geo_lang", "fr_maghreb"),
        ("France", "fr", "iptv tunisie", "geo_lang", "fr_maghreb"),
        ("France", "fr", "iptv algerie", "geo_lang", "fr_maghreb"),
        ("United States", "en", "iptv latino", "geo_lang", "us_latam"),
        ("Canada", "en", "iptv latino canada", "geo_lang", "ca_latam"),
        ("United States", "en", "pinoy iptv", "geo_lang", "us_ph"),
        ("United States", "en", "desi iptv", "geo_lang", "us_in"),
        ("France", "fr", "iptv grec", "geo_lang", "fr_gr"),
        ("Canada", "en", "hindi iptv", "geo_lang", "ca_in"),
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
