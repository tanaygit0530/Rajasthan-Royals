# Features (v2)

Every feature is built only from information available **before** the ball or season it describes. The out-of-time
evidence for each keep/drop decision is in the files named in the last column.

## Ball state (win-probability and expected-outcome models; `v2_code/s08_wp.py`)

| Feature | Definition | Status | Evidence |
|---|---|---|---|
| runs needed, balls left, wickets in hand | chase state; rain targets from the RR pack or Cricsheet (2 RR games fixed in s06b) | kept | `models/WP_REPORT.md` |
| required run rate | need / balls left x 6 | kept | same |
| score, balls left, wickets in hand | first-innings state | kept | same |
| current run rate | shrunk toward the competition par: (score + par/120 x 18) / (balls + 18) x 6 | kept (shrunk version) | raw rate made WP swing on the first balls of an innings, inflating powerplay leverage; fixed 15 Nov |
| score vs par | score - par x balls/120 | kept | same |
| par_prev (era) | competition's mean full-innings first-innings total over the previous 365 days, shrunk to the all-competition par | kept | captures the Impact-Player-era jump (IPL par 162 -> 186) |
| venue_dev | shrunk mean of (first-innings total - par) at the venue in earlier matches | kept | |
| elo_diff | batting minus bowling team Elo before the match (K = 24, all competitions) | kept | |
| knockout, impact_era, is_intl | flags | kept | |
| team tier, is_ipl (baseline) | hand-set tiers | dropped | baseline replica worse out of time (`WP_REPORT.md`) |

## Pressure (`s10_ball_values.py`, `s11_pressure_defs.py`)

| Feature | Status | Evidence |
|---|---|---|
| learned leverage (outcome mix from a 7-class model) | **chosen** | `pressure/PRESSURE_DEFS.md` |
| phase-mix leverage, baseline PI (x1.2 knockouts), leverage x qualification stakes | sensitivity only | same; `models/sensitivity.csv` |
| required-rate gap, wicket stress, close-game window | sensitivity only (lower capture / reliability) | same |
| qualification stakes (Monte Carlo) | tested via D7; not needed | `context/CONTEXT_REPORT.md` |
| day/night (IPL double-headers), dew | no detectable effect; not used | `context/CONTEXT_REPORT.md` |

## Player skill (`skill.py`, `s12_backtest.py`, `s13b_ablation.py`)

| Feature | Status | Evidence |
|---|---|---|
| run value per ball on all RR balls (overall skill, hierarchical shrinkage) | **kept** | `models/skill_backtest_*` |
| pressure-minus-normal gap | estimated, **not used to rank** (hurts prediction) | `models/skill_backtest_*`, `models/ablation.csv` |
| public-league adjusted skill (ridge APM, competition/venue/opponent adjusted, non-RR matches only) | **kept for bowlers**, not for batters | `models/ablation.csv` |
| APM fitted on the same RR balls | not used (double counts the likelihood's balls) | `models/ablation.csv` |
| age curve | dropped (never improved prediction) | `models/ablation.csv` |
| pressure-building credit (dots -> partner wickets) | descriptive; credit is just dot rate; no separate skill (split-half r ~ 0) | `context/ROLES_REPORT.md` |
| role (batting position / bowling phase mix) | used for role-relative percentiles on cards, not in the score | `rankings/*` |
| style features (phase run value, vs pace/spin, boundary %, dot %) | LightGBM on these predicted worse than the Bayesian model; used to explain only | `explain/EXPLAIN_REPORT.md` |
| matchups | batter spin-vs-pace reliable (shown on cards); left-arm and hand splits are noise (not shown as findings) | `explain/matchup_reliability.csv` |

## Not available

Fielding by player, pitch, weather, field placements; batting hand / bowling type / speed outside the RR pack.
