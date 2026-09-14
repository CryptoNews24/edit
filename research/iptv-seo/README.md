# IPTV SEO + domain opportunity research

Living research workspace. **Do not treat search volumes or keyword difficulty as real unless they come from a logged-in SEMrush/Noxtools session.**

## Status (2026-09-13)

| Source | Status |
| --- | --- |
| Noxtools / SEMrush | **Blocked — login required.** Browser hit `https://noxtools.com/secure/login`. No credentials were entered. |
| Google Search / Trends | CAPTCHA / unusual-traffic block on this cloud IP |
| GoDaddy / Namecheap / Dynadot | CAPTCHA or access denied |
| DuckDuckGo SERPs | Collected (see `serp_notes.md`) |
| Registry RDAP | Collected (see `domains.csv`) |
| Porkbun UI | Partial (exact-match `.ca` taken) |

**Action to unblock keyword metrics:** log into Noxtools manually in the research browser, then continue from `iptv_seo_research_state.json` → `last_research_position`.

## Files

| File | Purpose |
| --- | --- |
| `iptv_seo_research_state.json` | Resume state, queues, anti-duplication |
| `keywords.csv` | Keyword opportunities (volumes/KD = N/A until SEMrush) |
| `domains.csv` | Domain checks already performed |
| `almost_expired_offline.csv` | **Separate table:** perfect/taken names whose **website is not online** and expiry is **≤ 90 days** (or already expired) |
| `taken_offline_watch.csv` | Offline/parked perfect names with later or unknown expiry |
| `taken_perfect_site_expiry.csv` | Full probe log for every perfect taken name |
| `check_taken_offline_expiry.py` | Pipeline step: RDAP expiry + HTTP live check |
| `TOP_OPPORTUNITIES.md` | Ranked actionable list |
| `serp_notes.md` | Observed SERP notes |

## Pipeline (every research batch)

1. Discover keyword + domain candidates.
2. Check availability (RDAP / registrar). Record in `domains.csv`.
3. **If the domain is a strong exact/close match but already taken:**
   - Probe whether the website is actually online (HTTP + DNS).
   - Read registry expiry from RDAP.
   - If the **site does not work** (no DNS, timeout, 5xx, parking/placeholder) **and** expiry is **within 90 days** (or past expiry / redemption): append to **`almost_expired_offline.csv`**.
   - If the site is down but expiry is later or unpublished: append to `taken_offline_watch.csv`.
4. Do **not** purchase. Re-check before acting — redemption and drop calendars differ by TLD (especially `.ca`).

## Scoring (provisional)

Demand (25) and KD (25) are **unscored** until SEMrush. Provisional score uses only:

- Commercial intent (15)
- SERP weakness (15)
- Cluster potential (10)
- Domain opportunity (10)

Max provisional score = **50**. A 🔥 JACKPOT flag is **not** used without verified volume + KD + SERP + domain together.

## Rules

- Never fabricate SEMrush numbers
- Never register/purchase domains from this research
- App-brand keywords (TiviMate, IPTV Smarters) are SEO topics, not domain recommendations
- Skip `.uk` names that contain `iptv`
- `.ie` registrations need an Irish connection (IEDR policy) even if RDAP looks free
