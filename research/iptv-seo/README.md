# IPTV SEO + domain opportunity research

Volumes are real only when taken from SEMrush. Nothing is purchased from this folder.

**The list:** `LIST.txt` (same file copied to `AVAILABLE_LIST.txt`). Plain text only — no designed HTML board.

Rebuild: `python3 rebuild_lists.py && python3 generate_text_list.py`

## Status (2026-09-14)

| Source | Status |
| --- | --- |
| Noxtools / SEMrush | Member pages 403 / Semrush 429 from this IP |
| Google Search / Trends | CAPTCHA on this cloud IP |
| Registrars (GoDaddy / Namecheap / Dynadot) | CAPTCHA |
| Registry RDAP + DNS | Used for availability |
| Bing SERP | Partial (later queries went generic and were dropped) |

## Files

| File | Purpose |
| --- | --- |
| `LIST.txt` | **Read this** — picks, volumes, available, confirm, taken, drop-watch |
| `AVAILABLE_LIST.txt` | Identical copy of `LIST.txt` |
| `availability_recheck.csv` | Last RDAP + DNS verdict per domain |
| `taken_not_available.csv` | Taken names — do not buy |
| `almost_expired_offline.csv` | Taken + site down + expiry ≤ 90 days |
| `canva/traffic.json` | Verified Semrush keyword metrics only |
| `keywords.csv` | Keyword opportunities |
| `keyword_dictionary.csv` | Generated term dictionary |
| `generate_text_list.py` | Rebuilds `LIST.txt` |
| `TOP_OPPORTUNITIES.md` | Narrative ranking |

## Pipeline

1. Keyword + domain candidates.
2. RDAP + DNS. Available tab/list only if not taken.
3. Taken perfect names: live-site + expiry probe → `almost_expired_offline.csv` if dead and ≤ 90 days.
4. Verified volumes into `canva/traffic.json` (never invent).
5. Rebuild `LIST.txt`.
6. Do not purchase.

## Rules

- Never fabricate Semrush numbers
- Never present a taken name as available (`iptvcanada.ca` is taken)
- Ignore `.ie` domains
- Skip `.uk` names that contain `iptv`
- TiviMate / IPTV Smarters = SEO topics, not brand EMDs
