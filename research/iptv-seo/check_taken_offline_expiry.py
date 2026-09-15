#!/usr/bin/env python3
"""Pipeline step: perfect taken domains whose sites are down and nearly expire.

Does not purchase anything. Uses public RDAP + HTTP probes only.
"""

from __future__ import annotations

import csv
import json
import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALMOST_EXPIRED_DAYS = 90
WATCH_DAYS = 180
TODAY = datetime.now(timezone.utc)

RDAP = {
    "ca": "https://rdap.ca.fury.ca/rdap/domain/{d}",
    "fr": "https://rdap.nic.fr/domain/{d}",
    "nl": "https://rdap.sidn.nl/domain/{d}",
    "de": "https://rdap.denic.de/domain/{d}",
    "ch": "https://rdap.nic.ch/domain/{d}",
    "net": "https://rdap.verisign.com/net/v1/domain/{d}",
    "com": "https://rdap.verisign.com/com/v1/domain/{d}",
    "no": "https://rdap.norid.no/domain/{d}",
}

PARK_HINTS = (
    "domain is for sale",
    "buy this domain",
    "this domain may be for sale",
    "parked",
    "sedo",
    "hugedomains",
    "afternic",
    "dan.com",
    "godaddy.com/domainsearch",
    "parkingcrew",
    "related searches",
    "this webpage is parked",
    "coming soon",
    "default web page",
    "apache2 default",
    "nginx default",
    "iis windows server",
    "account suspended",
    "website expired",
)

# High-value exact / close-match names already known taken.
PERFECT_TAKEN = [
    "iptvcanada.ca",
    "iptv-canada.ca",
    "bestiptv.ca",
    "bestiptvcanada.ca",
    "iptvsubscription.ca",
    "iptvservice.ca",
    "iptvprovider.ca",
    "streamcanada.ca",
    "mapleiptv.ca",
    "iptvreviews.ca",
    "iptvtrial.ca",
    "streamnorth.ca",
    "watchiptv.ca",
    "livetvcanada.ca",
    "iptvcanada.net",
    "iptvireland.net",
    "irishiptv.net",
    "bestiptvireland.net",
    "iptvfrance.fr",
    "abonnementiptv.fr",
    "meilleuriptv.fr",
    "iptv.fr",
    "abo-iptv.fr",
    "iptvguide.fr",
    "meilleur-iptv.fr",
    "iptvplayer.fr",
    "testiptv.fr",
    "iptvessai.fr",
    "iptvnederland.nl",
    "iptv.nl",
    "iptvabonnement.nl",
    "besteiptv.nl",
    "iptvgids.nl",
    "iptvvergelijken.nl",
    "iptvdeutschland.de",
    "iptv.de",
    "iptvanbieter.de",
    "iptvabo.de",
    "iptvvergleich.de",
    "iptv.ch",
    "iptvsuisse.ch",
    "iptvschweiz.ch",
    "meilleuriptv.ch",
    "iptvaustralia.com.au",
    "iptv.com.au",
    "bestiptv.com.au",
    "iptvaustralia.net",
    "iptvfrance.net",
    "abonnementiptv.net",
    "iptvbelgique.net",
    "iptvsuisse.net",
    "iptvguide.net",
    "iptvdeals.net",
    "bestiptv.net",
    "iptvusa.net",
    "iptvsubscription.net",
    "iptvprovider.net",
    "iptvservice.net",
    "iptvireland.ie",
    "irishiptv.ie",
]


def tld_of(domain: str) -> str:
    parts = domain.lower().split(".")
    if domain.endswith(".com.au"):
        return "com.au"
    return parts[-1]


def rdap_url(domain: str) -> str | None:
    if domain.endswith(".com.au"):
        return f"https://rdap.org/domain/{domain}"
    tmpl = RDAP.get(tld_of(domain))
    return tmpl.format(d=domain) if tmpl else f"https://rdap.org/domain/{domain}"


def http_json(url: str, timeout: int = 18):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "IPTV-SEO-expiry-watch/1.0"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.getcode(), json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return None, None


def parse_expiry(payload: dict | None) -> str:
    if not payload:
        return ""
    dates = []
    for ev in payload.get("events") or []:
        action = (ev.get("eventAction") or "").lower()
        if action in {"expiration", "expiry", "expire"}:
            dates.append(ev.get("eventDate") or "")
    for key in ("expires", "expiry"):
        if payload.get(key):
            dates.append(str(payload[key]))
    dates = [x for x in dates if x]
    if not dates:
        return ""
    return sorted(dates)[-1]


def days_until(iso: str) -> str:
    if not iso:
        return ""
    try:
        raw = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return str((dt - TODAY).days)
    except Exception:
        return ""


def dns_ok(host: str) -> bool:
    try:
        socket.getaddrinfo(host, 443)
        return True
    except Exception:
        return False


def probe_site(domain: str) -> tuple[str, str, str]:
    """Return site_status, http_code, note."""
    if not dns_ok(domain):
        return "offline_no_dns", "", "no A/AAAA"
    ctx = ssl.create_default_context()
    last_code = ""
    body = ""
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}/"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; IPTV-SEO-site-check/1.0)"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
                last_code = str(resp.getcode())
                body = resp.read(8000).decode("utf-8", "replace").lower()
                break
        except urllib.error.HTTPError as e:
            last_code = str(e.code)
            try:
                body = e.read(4000).decode("utf-8", "replace").lower()
            except Exception:
                body = ""
            if e.code >= 500:
                return "offline_http_error", last_code, f"HTTP {e.code}"
            break
        except Exception as e:
            last_code = type(e).__name__
            continue
    if not body and last_code in {"", "URLError", "timeout", "TimeoutError", "OSError"}:
        return "offline", last_code, "connection failed"
    if any(h in body for h in PARK_HINTS):
        return "parked_or_placeholder", last_code, "parking/placeholder page"
    if last_code.startswith("2") or last_code.startswith("3"):
        return "online", last_code, "responds"
    if last_code in {"403", "401", "429"}:
        return "online_restricted", last_code, "host responds but blocked"
    if last_code.startswith("4"):
        return "broken_site", last_code, f"HTTP {last_code}"
    return "offline", last_code, "no usable response"


def country_for(domain: str) -> str:
    tld = tld_of(domain)
    return {
        "ca": "Canada",
        "ie": "Ireland",
        "fr": "France",
        "nl": "Netherlands",
        "de": "Germany",
        "ch": "Switzerland",
        "be": "Belgium",
        "com.au": "Australia",
        "net": "Global / .net",
        "com": "Global / .com",
        "no": "Norway",
    }.get(tld, tld)


def website_not_working(status: str) -> bool:
    return status in {
        "offline_no_dns",
        "offline",
        "offline_http_error",
        "parked_or_placeholder",
        "broken_site",
    }


def main() -> None:
    rows = []
    for i, domain in enumerate(PERFECT_TAKEN):
        url = rdap_url(domain)
        code, payload = http_json(url) if url else (None, None)
        expiry = parse_expiry(payload)
        days = days_until(expiry)
        site, http_code, note = probe_site(domain)
        almost = ""
        if days != "":
            d = int(days)
            if d <= ALMOST_EXPIRED_DAYS:
                almost = "yes"
            elif d <= WATCH_DAYS:
                almost = "approaching"
            else:
                almost = "no"
        elif website_not_working(site):
            almost = "expiry_unknown"
        # Primary table: site down AND expiry within 90 days (includes already-expired / redemption).
        watchlist = website_not_working(site) and almost == "yes"
        # Secondary: site down but expiry later or unpublished (NL/DE RDAP often hides dates).
        secondary = website_not_working(site) and almost in {"approaching", "expiry_unknown"}
        rows.append(
            {
                "Date checked": TODAY.date().isoformat(),
                "Domain": domain,
                "Country": country_for(domain),
                "Perfect / taken": "yes",
                "Website status": site,
                "HTTP": http_code,
                "Expiry date": expiry[:10] if expiry else "N/A",
                "Days to expiry": days if days != "" else "N/A",
                "Almost expired (<=90d)": almost,
                "On offline+expiry watchlist": "yes" if watchlist else "no",
                "On secondary offline watch": "yes" if secondary else "no",
                "RDAP HTTP": "" if code is None else str(code),
                "Notes": note,
            }
        )
        print(f"{site:24} exp={expiry[:10] if expiry else 'N/A':12} days={days or 'N/A':5} {domain}")
        time.sleep(0.55)

    fields = list(rows[0].keys())
    all_path = ROOT / "taken_perfect_site_expiry.csv"
    watch_path = ROOT / "almost_expired_offline.csv"
    secondary_path = ROOT / "taken_offline_watch.csv"
    with all_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    watch_rows = [r for r in rows if r["On offline+expiry watchlist"] == "yes"]
    secondary_rows = [r for r in rows if r["On secondary offline watch"] == "yes"]
    with watch_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(watch_rows)
    with secondary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(secondary_rows)

    state_path = ROOT / "iptv_seo_research_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    state["timestamp"] = TODAY.isoformat()
    state["pipeline_steps"] = state.get("pipeline_steps") or []
    if "taken_offline_almost_expired" not in state["pipeline_steps"]:
        state["pipeline_steps"].append("taken_offline_almost_expired")
    state["almost_expired_offline"] = {
        "table": "almost_expired_offline.csv",
        "secondary_table": "taken_offline_watch.csv",
        "full_probe_table": "taken_perfect_site_expiry.csv",
        "almost_expired_days": ALMOST_EXPIRED_DAYS,
        "watch_days": WATCH_DAYS,
        "count": len(watch_rows),
        "domains": [r["Domain"] for r in watch_rows],
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    print(f"WROTE {all_path.name} ({len(rows)})")
    print(f"WROTE {watch_path.name} ({len(watch_rows)})")
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "generate_text_list", ROOT / "generate_text_list.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
    except Exception as exc:
        print("canva rebuild skipped:", exc)


if __name__ == "__main__":
    main()
