#!/usr/bin/env python3
"""Rebuild the standalone Canva board (open in a new browser tab).

Run after every research batch so the board stays current.
"""

from __future__ import annotations

import csv
import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANVA = ROOT / "canva"
OUT = CANVA / "board.html"
TEXT = ROOT / "AVAILABLE_LIST.txt"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def traffic_cell(domain: str, traffic: dict) -> tuple[str, str]:
    kw_name = (traffic.get("domain_keyword_map") or {}).get(domain)
    kws = traffic.get("keywords") or {}
    if kw_name and kw_name in kws:
        k = kws[kw_name]
        label = f"{k['volume_display']}/mo keyword"
        detail = f"{kw_name} · {k['db'].upper()} · KD {k['kd']}% {k['kd_label']} · SEMrush free tool"
        return label, detail
    return "N/A", "Not checked yet (SEMrush daily cap or not in last batch)"


def rows_from_available(traffic: dict) -> list[dict]:
    path = CANVA / "iptv-domains-canva-import.csv"
    out = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Domain"].endswith(".ie"):
                continue
            label, detail = traffic_cell(r["Domain"], traffic)
            out.append(
                {
                    "domain": r["Domain"],
                    "country": r["Country"],
                    "organic": label,
                    "organic_note": detail,
                    "competition": r["Competitive rate"],
                    "availability": r["Availability"],
                }
            )
    return out


def rows_from_expired(traffic: dict) -> list[dict]:
    path = ROOT / "almost_expired_offline.csv"
    out = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            label, detail = traffic_cell(r["Domain"], traffic)
            days = r.get("Days to expiry", "")
            try:
                d = int(days)
                left = f"Expired {abs(d)}d" if d < 0 else f"{d} days"
            except Exception:
                left = days
            out.append(
                {
                    "domain": r["Domain"],
                    "country": r["Country"],
                    "organic": label,
                    "organic_note": f"Site traffic 0 (offline/parked). {detail}",
                    "website": r["Website status"],
                    "expiry": r["Expiry date"],
                    "left": left,
                    "availability": "Taken — watch drop",
                }
            )
    return out


def tr_available(r: dict) -> str:
    return f"""<tr>
      <td class="domain">{esc(r['domain'])}</td>
      <td>{esc(r['country'])}</td>
      <td><div class="vol">{esc(r['organic'])}</div><div class="sub">{esc(r['organic_note'])}</div></td>
      <td>{esc(r['competition'])}</td>
      <td><span class="pill">{esc(r['availability'])}</span></td>
    </tr>"""


def rows_from_taken() -> list[dict]:
    path = ROOT / "taken_not_available.csv"
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(r)
    return out


def tr_taken(r: dict) -> str:
    return f"""<tr>
      <td class="domain">{esc(r.get('Domain'))}</td>
      <td>{esc(r.get('Country'))}</td>
      <td><span class="pill taken">{esc(r.get('Availability'))}</span></td>
      <td>{esc(r.get('Website'))}</td>
      <td>{esc(r.get('Expiry'))}</td>
      <td class="sub">{esc(r.get('Notes'))}</td>
    </tr>"""


def tr_expired(r: dict) -> str:
    return f"""<tr>
      <td class="domain">{esc(r['domain'])}</td>
      <td>{esc(r['country'])}</td>
      <td><div class="vol">{esc(r['organic'])}</div><div class="sub">{esc(r['organic_note'])}</div></td>
      <td>{esc(r['website'])}</td>
      <td>{esc(r['expiry'])}</td>
      <td><span class="pill warn">{esc(r['left'])}</span></td>
    </tr>"""


def main() -> None:
    traffic = load_json(CANVA / "traffic.json")
    avail = rows_from_available(traffic)
    taken = rows_from_taken()
    expired = rows_from_expired(traffic)
    kws = traffic.get("keywords") or {}
    kw_rows = []
    for name, k in kws.items():
        kw_rows.append(
            f"""<tr>
      <td class="domain">{esc(name)}</td>
      <td>{esc(k.get('db','')).upper()}</td>
      <td><div class="vol">{esc(k.get('volume_display'))}/mo</div></td>
      <td>{esc(k.get('kd'))}% {esc(k.get('kd_label'))}</td>
      <td>{esc(k.get('cpc'))}</td>
      <td>{esc(k.get('intent'))}</td>
    </tr>"""
        )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>IPTV SEO Canva · live board</title>
  <style>
    :root {{
      --bg: #0b1220;
      --card: #121b2e;
      --line: rgba(148,163,184,.16);
      --text: #eef3ff;
      --muted: #93a4c4;
      --sky: #7dd3fc;
      --ok: #6ee7b7;
      --warn: #fbbf24;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Manrope, Segoe UI, sans-serif;
      background: radial-gradient(1000px 500px at 0% 0%, rgba(56,189,248,.14), transparent 50%),
                  #0b1220;
      color: var(--text);
    }}
    header {{
      padding: 28px 40px 12px;
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-end;
    }}
    h1 {{ margin: 6px 0 0; font-size: 32px; letter-spacing: -.03em; }}
    .eyebrow {{ color: var(--sky); letter-spacing: .16em; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .meta {{ color: var(--muted); font-size: 14px; text-align: right; line-height: 1.45; }}
    nav {{
      display: flex;
      gap: 8px;
      padding: 8px 40px 0;
    }}
    nav button {{
      background: transparent;
      color: var(--muted);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 8px 16px;
      font-weight: 700;
      cursor: pointer;
    }}
    nav button.active {{ color: #0b1220; background: var(--sky); border-color: var(--sky); }}
    section {{ display: none; padding: 20px 40px 48px; }}
    section.active {{ display: block; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      overflow: hidden;
    }}
    th {{
      text-align: left;
      font-size: 12px;
      letter-spacing: .1em;
      text-transform: uppercase;
      color: var(--muted);
      padding: 14px 16px;
      background: #0c1424;
    }}
    td {{
      padding: 12px 16px;
      border-top: 1px solid var(--line);
      vertical-align: top;
    }}
    .domain {{ font-weight: 800; }}
    .vol {{ font-weight: 800; color: var(--ok); }}
    .sub {{ color: var(--muted); font-size: 12px; margin-top: 4px; max-width: 420px; }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(16,185,129,.16);
      color: var(--ok);
      font-size: 13px;
      font-weight: 700;
    }}
    .pill.warn {{ background: rgba(245,158,11,.16); color: var(--warn); }}
    .pill.taken {{ background: rgba(248,113,113,.18); color: #fecaca; }}
    footer {{ padding: 0 40px 32px; color: var(--muted); font-size: 13px; }}
  </style>
</head>
<body>
  <header>
    <div>
      <div class="eyebrow">IPTV SEO · Canva board · open this file in its own tab</div>
      <h1>Domains, country, organic traffic, competition, availability</h1>
    </div>
    <div class="meta">
      Last rebuilt {esc(now)}<br />
      Regenerated automatically after each research batch<br />
      Keyword dictionary: 2857 terms · .ie domains ignored
    </div>
  </header>
  <nav>
    <button class="active" data-tab="available">AVAILABLE only (rechecked)</button>
    <button data-tab="taken">TAKEN — not for sale</button>
    <button data-tab="expired">TAKEN + offline / almost expired</button>
    <button data-tab="keywords">Verified keyword traffic</button>
  </nav>
  <section id="available" class="active">
    <p class="sub" style="margin:0 0 12px">AVAILABLE tab only. Rechecked today with registry RDAP. <b>iptvcanada.ca is TAKEN</b> and is not listed here.</p>
    <table>
      <thead>
        <tr>
          <th>Domain</th><th>Country</th><th>Organic traffic</th><th>Competitive rate</th><th>Availability</th>
        </tr>
      </thead>
      <tbody>
        {''.join(tr_available(r) for r in avail)}
      </tbody>
    </table>
  </section>
  <section id="taken">
    <table>
      <thead>
        <tr>
          <th>Domain</th><th>Country</th><th>Availability</th><th>Website</th><th>Expiry</th><th>Notes</th>
        </tr>
      </thead>
      <tbody>
        {''.join(tr_taken(r) for r in taken)}
      </tbody>
    </table>
  </section>
  <section id="expired">
    <table>
      <thead>
        <tr>
          <th>Domain</th><th>Country</th><th>Organic traffic</th><th>Website</th><th>Expiry</th><th>Time left</th>
        </tr>
      </thead>
      <tbody>
        {''.join(tr_expired(r) for r in expired)}
      </tbody>
    </table>
  </section>
  <section id="keywords">
    <table>
      <thead>
        <tr>
          <th>Keyword</th><th>DB</th><th>Monthly volume</th><th>KD</th><th>CPC</th><th>Intent</th>
        </tr>
      </thead>
      <tbody>
        {''.join(kw_rows)}
      </tbody>
    </table>
  </section>
  <footer>
    Site traffic on unregistered or dead domains is 0. Organic column shows the mapped SEMrush keyword volume when we have it; otherwise N/A (not invented).
    Free-tool daily cap blocked more country lookups. Do not purchase from this board. TiviMate/Smarters domains are excluded.
  </footer>
  <script>
    document.querySelectorAll("nav button").forEach((btn) => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll("nav button").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll("section").forEach((s) => s.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById(btn.dataset.tab).classList.add("active");
      }});
    }});
  </script>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"WROTE {OUT} available={len(avail)} taken={len(taken)} expired={len(expired)} keywords={len(kws)}")
    write_text_list(traffic, avail, taken, expired, kws, now)


def write_text_list(traffic: dict, avail: list[dict], taken: list[dict], expired: list[dict], kws: dict, now: str) -> None:
    lines = [
        f"IPTV SEO domain hunt — text list — {now}",
        "Do not purchase from this file. Recheck at a registrar before buying.",
        ".ie domains ignored. .uk names containing iptv skipped. TiviMate/Smarters = SEO only.",
        "iptvcanada.ca is TAKEN (not available). Organic numbers are keyword volume, not site sessions.",
        "",
        "=== VERIFIED KEYWORD VOLUME (Noxtools Semrush S6 / earlier verified) ===",
    ]
    for name, k in kws.items():
        lines.append(
            f"- {name} [{k.get('db','').upper()}] {k.get('volume_display')}/mo · KD {k.get('kd')} {k.get('kd_label')} · CPC ${k.get('cpc')} · {k.get('intent')}"
        )
    lines += ["", "=== AVAILABLE (registry RDAP 404 + no DNS) — register these, not the taken EMDs ==="]
    by_c: dict[str, list[dict]] = {}
    for r in avail:
        by_c.setdefault(r["country"], []).append(r)
    for country in sorted(by_c):
        lines.append(f"\n{country}")
        for r in by_c[country]:
            lines.append(
                f"  {r['domain']}  |  {r['organic']}  |  competition {r['competition']}  |  {r['availability']}"
            )
    lines += ["", "=== TAKEN — DO NOT BUY ==="]
    for r in taken:
        lines.append(
            f"  {r.get('Domain')}  |  {r.get('Country')}  |  {r.get('Website')}  |  expiry {r.get('Expiry') or 'n/a'}  |  {r.get('Notes')}"
        )
    lines += ["", "=== TAKEN + OFFLINE / DROP-WATCH (<=90d) — still NOT available ==="]
    for r in expired:
        lines.append(
            f"  {r['domain']}  |  {r['country']}  |  {r['website']}  |  {r['expiry']}  |  {r['left']}"
        )
    note = traffic.get("note") or ""
    lines += ["", "=== NOTES ===", note, "Noxtools Servers 1-6 often HTTP 429 from this IP; retry Server 6. Never invent volumes."]
    TEXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE {TEXT}")


if __name__ == "__main__":
    main()
