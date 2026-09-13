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
| `TOP_OPPORTUNITIES.md` | Ranked actionable list |
| `serp_notes.md` | Observed SERP notes |

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
