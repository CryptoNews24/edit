# IPTV SEO + domain opportunity research

Volumes are real only when taken from SEMrush. Nothing is purchased from this folder.

**Suggested keywords (queued, no invented volume):** `SUGGESTED_KEYWORDS.md`  
**Domain list:** `LIST.txt` (same filters; no 3+ word labels; no taken dumps)

Rebuild: `python3 rebuild_lists.py && python3 generate_text_list.py`

## Status (2026-09-14)

| Source | Status |
| --- | --- |
| Noxtools / SEMrush | Works in your browser. This VM: **not HTTP 429**. `noxtools.com` Cloudflare 403; Semrush.in HTTP 200 “Session expired”. |
| Google Search / Trends | CAPTCHA on this cloud IP |
| Registrars (GoDaddy / Namecheap / Dynadot) | CAPTCHA |
| Registry RDAP + DNS | Used for availability — `KEYWORDS.md` lists AVAILABLE leftovers per TLD |
| Bing SERP | Partial (later queries went generic and were dropped) |

## Files

| File | Purpose |
| --- | --- |
| `KEYWORDS.md` | **Keyword tables** — verified Semrush, tracked keywords, SERP, domain picks |
| `LIST.txt` | Domain dump — AVAILABLE + almost-expired only |
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
- Two-word domain names only (e.g. `avis-iptv.fr`, `compareiptv.us`). Do not hunt 3+ word labels
- Exclude Semrush `keyword - keyword` pair rows (Related / also-rank labels, not queries)
- TiviMate / IPTV Smarters = SEO topics, not brand EMDs
