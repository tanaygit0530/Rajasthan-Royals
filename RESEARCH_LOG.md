# Research log — SupeRR Selector S2, v2

The plan is in `~/.claude/plans/jolly-yawning-metcalfe.md` and was approved on 15 Nov 2026.
Entries are listed newest first within each stage. Every decision gives the reason and the evidence file.

## Task list
| # | Task | Status |
|---|---|---|
| S0.1 | `.gitignore` guard for `02_data/`, `data_public/`, `v2_work/`, pickles | done |
| S0.2 | Conda env `.env_superr` (py3.11 + lightgbm, xgboost, numpyro, statsmodels…) | done |
| S0.3 | Diagnose baseline non-reproducibility | done (cross-machine, not random) |
| S0.4 | Separate project git repo; GitHub private remote `tanaygit0530/Rajasthan-Royals` | done |
| S1 | CRICKET_PRIMER.md (cited research) | done |
| S2.1 | Data audit + data dictionary | done |
| S2.2 | Cricsheet download (48 MB) + parse + dedupe/unify | done |
| S2.3 | Player identity map (+ manual check of top 200) | done (99.07% of balls) |
| S2.4 | Competition-strength model (v2: + venue term, + extras target, λ grid 3–10,000) | done |
| S2.4b | Match-bootstrap SEs for league strength (`s07b_bootstrap.py`, 60 reps, 47 min) | done |
| S2.6 | Match context: venue key, Cricsheet knockouts, IPL qualification stakes, day/night, rain fixes, impact era (`s06b_context.py`) | done |
| S2.7 | Dates of birth from Wikidata (CC0) for the age curve (`s06c_dob.py`) | done |
| S2.8 | Roles, bowler pressure-building credit, survivorship check (`s06d_roles.py`) | done |
| S4-gap | Gap-review commitments carried into S4 (era term, age curve, role-relative, pressure-building, stakes, day/night, survivorship IPW) | done - tested; age curve and stakes/day-night did not help and are not used |
| S3.1 | Feature build + FEATURES.md | done |
| S3B | Player profile database + DATA_DICTIONARY + reconciliation (exact) + 20-player Cricsheet spot check | done |
| S4E | SHAP top predictors, player-type clustering, matchup model | done |
| S3.2 | Pressure-definition comparison | done (learned leverage) |
| S4A | WP + expected-outcome model comparison (rolling by season) | done (logistic WP; HGB xOutcome) |
| S4B | Player-skill model comparison (M0–M8) | done |
| S4C | Is clutch repeatable? | done (no) |
| S4D | Final score, sensitivity, ablation, fairness, interval coverage | done |
| S5 | Scout cards (30 per list) + sourced scouting notes | done |
| S5B | Value hunting: capped status, emerging tier, upside backtest, price model, value lists + 5 cards each | done |
| S5C | Youth board, development-model backtest, comparables, 10 cards | done (lower-resolution manual reads not collected - see open items) |
| P7 | Auction optimiser | waiting for the Phase 7 brief; 5B/5C output pool CSVs in a documented format |
| S6 | Deliverables in `v2_results/` + fresh-eyes review | done (review PASS) |

## Scope changes

**15 Nov — Phases 5B (value hunting) and 5C (youth scouting) added by the user.** The feasibility check and the user's decisions:
- **No licensed ball-by-ball data** exists for state T20 leagues (TNPL, Maharaja, UP T20, DPL, Mumbai T20), U19, Vijay Hazare, Cooch Behar, Vinoo Mankad, CK Nayudu or India A. The scorecard sites (ESPNcricinfo, BCCI) forbid scraping.
  → **Decision:** model only on Cricsheet SMAT 2019–23, the RR pack's A-team Asia Cups, IPL and overseas leagues. For the shortlisted top ~30, read a few public pages per player by hand, cite them, and mark them "lower-resolution".
- **SMAT on Cricsheet stops in 2024** (8 matches in 2024, none in 2025–26). This is a major recency gap for uncapped Indian players, and it will be stated in the report.
- **Age:** from Wikidata (CC0) via ESPNcricinfo IDs. 31,077 cricketers have a date of birth there, and Cricsheet has the ESPNcricinfo key for 18,653 of its 18,698 people. For minors, the date of birth is used only to compute age.
- **Capped status:** from Cricsheet T20I, ODI and Test registries (28 MB to download when 5B starts).
- **Prices:** from Wikipedia auction pages (CC BY-SA).
- **Phase 7 optimiser:** the user will paste the brief later. Until then, 5B and 5C write their pools to a documented CSV format.
- **Order:** 5B and 5C run after core S4. The plan addendum is in `~/.claude/plans/jolly-yawning-metcalfe.md`.

**15 Nov — Phase 3B (full player profile database) added by the user.** Feasibility by field is recorded in the plan addendum:
- **RR pack only:** style, stroke, delivery and speed fields. Speed is present on 61% of balls and needs outlier cleaning (maximum 1,456 km/h). `delivery_style` includes Yorker 4,212, Wide Yorker 1,448, Slow Ball, Knuckle, Carrom, Googly and Doosra.
- **Cricsheet only:** fielding.
- **Not derivable:** caught in the deep vs infield.
- **Two-pass build:** pressure columns are filled after S4A.
- **Profile pages:** pages for every player wait for the Phase 7 brief. The report appendix covers top candidates.

## S3-S6 — Models, ratings and deliverables (15 Nov 2026)

- **WP (S4A).** Logistic regression beat HGB / LightGBM / XGBoost / blend out of time on both innings (log-loss 0.634 / 0.402 vs baseline replica 0.695 / 0.463); trees overfit match-level features; stronger regularisation tested on one fold and still lost. Expected outcomes: sklearn HGB (+1.5% over cell means).
- **Bug found and fixed:** raw current run rate made first-ball WP swing (first-over leverage 2.5x average). Run rate now shrunk toward par for the first 18 balls; whole chain s08-s19 rerun. First-over leverage now 1.9x setting / 0.9x chasing.
- **Pressure (S3.2).** Learned leverage kept by the pre-set rule; other definitions are sensitivity checks.
- **Skill backtest (S4B/C).** Baseline formula: r = -0.02 (bat) / -0.12 (bowl) with next-season pressure run value. Overall-skill models ~0.19-0.24; noise ceiling 0.44 / 0.34. Adding a pressure-specific gap hurts (clutch not repeatable).
- **Final model (S4D).** Hierarchical Bayes overall skill; bowlers with a public-league-only APM prior; batters without prior; no age curve. Found and fixed a double-counting problem (prior fitted on the same RR balls) that made intervals ~3x too narrow. 80% interval coverage in the backtest: 68% bat / 74% bowl (stated in report).
- **Fairness.** Residuals by IPL-heavy / T20I-heavy / public-heavy groups all within ~1 SE of zero.
- **Value (S5B).** Prices 2022-26 from Wikipedia; price model beats a capped x overseas median baseline in 2 of 3 auctions; retained players without an auction price excluded from value lists.
- **Youth (S5C).** Pool restricted to players with real non-associate cricket; Pakistan nationals excluded; development model backtest shows age adds nothing beyond early skill, so projections use early skill only.
- **Status data.** Wikipedia 2027 page: retention deadline 15 Nov (some reports 17 Nov), auction 16 Dec in Goa, Harshal Patel SRH->GT (15 Nov), Rahane retired. Nationality now from international records, else Wikidata (verify flagged cases).
- **Fresh-eyes review: PASS** (no duplicates; all top-30 ids ball-aligned; raw recomputed pressure balls match 60/60).

**16 Nov — the three optional items**
- **Interval calibration (s13c).** Refit the final configuration on each fold; raw 80% intervals covered 70% (bat) / 73% (bowl). Widening by 2.75x / 3.0x restores 81% / 80%. Applied to all intervals and P(top 10). Consequence: only 1 batter (Sooryavanshi) and 2 bowlers (Bumrah, Narine) have P(top 10) > 50%; the rest of each top 10 is a near-tie. Report wording now computed from the data.
- **Report limitation added:** early first-innings leverage (1.9x in over 1) explained; ratings unaffected (they use all balls).
- **Youth lower-resolution reads:** cricket-only public reporting for 20 shortlisted players saved in `cards/scouting_notes.json` (keys `youth:<name>`), cited; never used in projections. Nationality for 9 players with no international/Wikidata record taken from cited reports (`youth/manual_nationality.csv`) — Sameer Minhas (Pakistan) now correctly excluded as IPL-ineligible.

**16 Nov — S7: from ranking to selection (RR fit)**
- `s23_rr_fit.py`: RR 2026 roster (27, 9 overseas incl. replacements vs a squad limit of 8), role slots, gaps vs league benchmark, best-3 + value pick per slot, form trends (descriptive), selector verdicts.
- Biggest RR pressure gaps: middle-overs spin (Bishnoi 5.3 vs benchmark 12.2) and middle order 4-5 (Hetmyer 4.7 vs 11.5). Opening is RR's strength (Sooryavanshi).
- Priority targets: Narine, Noor Ahmad, Mujeeb (spin); Suryakumar, Klaasen, Pooran (middle order). Medical check first: Tim David, Bumrah, Rashid, Salt, Hasaranga, Varun, Pathirana.
- Predicted prices hidden for retained players never auctioned (model cannot price them). New report section 6.

### Open items
- Re-run `s13_final.py` -> `s22_review.py` when 2027 retention lists are published (before 16 Dec).
- Phase 7 optimiser: waiting for the brief; pools in `v2_results/value/phase7_pool_*.csv`.

## S2 — Data audit and public data

**15 Nov — gap review: fixes for the 10 gaps + 3 known issues** (user: "solve all the gaps and the known issue")
- **Venue (gap 1).** One `venue_key` across sources: 95 of 98 RR venue ids named from paired Cricsheet matches (vote share ≥ 0.6); Cricsheet's 298 names collapse to 286 keys with 26 known renames (e.g. Feroz Shah Kotla → Arun Jaitley, Sardar Patel → Narendra Modi). Venue now a penalised term in the competition-strength ridge. `v2_results/context/rr_venue_to_cricsheet.csv`.
- **Extras (gap 2).** Wides + no-ball runs are a third ridge target over all deliveries with a bowler term; bowler runs-saved = runs-off-bat effect + extras effect × deliveries per legal ball.
- **Pressure building (gap 3).** Over-level OLS (254k overs, match-clustered SE): each dot ball raises partner wickets next over by +0.0034 (SE 0.0010), i.e. a 4-dot vs 1-dot over adds +3.2% relative. Split-half r of the dot/boundary credit 0.83; of the bowler-specific residual beyond dots 0.02 → no separate "squeeze skill"; the credit is a candidate S4 feature only. `v2_results/context/ROLES_REPORT.md`.
- **Age (gap 4).** Wikidata SPARQL (P2697 ESPNcricinfo id → P569 DOB), 31,018 rows, generic query, DOB used only to compute age. Ball-weighted coverage: 96–100% in every franchise league and RR IPL/T20I; 53% Cricsheet T20I (associates); 67% RR A-team. `v2_results/context/dob_coverage.csv`.
- **Roles (gap 5).** Batting position from order of arrival (equals RR `batting_order` in 99.9% of innings); batter role from median position; bowler role from phase mix; part-timer flag. Pace/spin known only for RR-pack bowlers (Cricsheet has no bowling style) — stated limitation.
- **Knockouts in Cricsheet (gap 6).** Cricsheet has no stage field; playoff games carry no `match_number`. Rule: un-numbered games on/after the last numbered game of a numbered tournament (tournament = comp + event, new instance after a > 60-day gap so BBL Dec–Jan seasons stay whole). 399 knockouts; IPL exactly 4 per season 2019–26; T20 World Cup 11 of 12 semis/finals 2021–26.
- **Qualification stakes (gap 7).** Monte Carlo (4,000 sims per match, coin-flip remaining results, random tie-break) of P(qualify | win) − P(qualify | lose) per team for every IPL league game 2022–26; playoffs = 1. Median league game 0.20; in the last 14 league games, 47% of team-games have stakes < 0.05 (dead rubber) and 10% > 0.5. `v2_work/unified/team_stakes.parquet`.
- **Day/night & dew (gap 8).** The RR timestamp column holds dates only, so day/night comes from IPL double-headers (lower match number = afternoon). Dew check: spin economy in the second innings at night 8.51 vs first innings 8.53 — no aggregate dew effect; day/night kept as a covariate to test in S4, not as an adjustment.
- **Impact Player era (gap 9).** First-innings runs after over 10 with 1–2 wickets down rose by ~12–15 runs in 2023+ vs 2019–22 (small samples per cell). S4A gives the WP model an era term and lets wicket value depend on era.
- **Survivorship (gap 10).** IPL retention next season (≥ 60 balls): batters worst quartile 75% vs best 94%; bowlers 69% vs 90%. S4 scoring adds dropout-by-decile, inverse-probability-of-retention weights and all-competition next-season targets.
- **Rain (known issue).** 34 = RR matches with any reduced overs (audit); 23 = with a revised target (baseline/report). Difference = 9 no-result/abandoned + 2 completed games with a shortened first innings and no target: rr19959 gets target 132 / 66 balls from Cricsheet; rr16753 has no public target → equal-overs par (flagged `rain_fix`). Baseline modelled both as 120-ball chases.
- **λ grid (known issue).** Widened to 3–10,000 (extras 30–30,000); edge check printed.
- **Venue key bug found and fixed.** The first refit merged different grounds sharing a name ("County Ground" = Taunton, Northampton, Bristol, Chelmsford, Derby, Hove), giving a spurious +14.5 effect. Key is now name | city (empty city strings filled; Hove = Brighton).
- **Convergence.** lsqr cap raised 3,000 → 10,000; final fits converged in 4,581 (runs), 1,734 (dismissals), 2,322 (extras) iterations. Chosen penalties: runs 100, dismissals 1,000, extras 300 — none at the grid edge.
- **Bootstrap SEs (known issue, done).** 60 match-bootstrap reps (47 min). League quality, runs per 100 balls vs IPL (SE in brackets), batters / bowlers incl. extras: MLC −3.4 (0.9) / −5.9 (0.8); ILT20 −3.6 (0.7) / −1.9 (0.7); T20I-Full −4.5 (0.5) / −2.5 (0.4); CPL −6.3 (0.7) / −4.4 (0.7); BBL −6.5 (0.8) / −6.1 (0.8); SA20 −7.2 (0.6) / −3.1 (0.7); PSL −8.2 (0.7) / −2.8 (0.8); LPL −9.3 (0.9) / −4.8 (0.8); T20 Blast −11.7 (0.7) / −9.1 (0.7); BPL −12.3 (0.9) / −9.0 (0.8); A-team −12.6 (0.9) / −8.8 (0.9); SMAT −13.4 (0.6) / −9.4 (0.6); CSA −16.1 (0.9) / −11.0 (1.0); Super Smash −16.3 (1.1) / −11.4 (1.2); T20I-Assoc −17.6 (0.8) / −9.4 (0.6). Every league is clearly below the IPL (all > 2 SE); neighbours within ~1.5 runs (e.g. MLC/ILT20, CPL/BBL) are not distinguishable. Adding venue moved the associate T20I gap from −25.1 to −17.6 (part of it was ground conditions). `v2_results/comp_strength/league_strength_2022_26_with_se.csv`.
- **Venue effects** (runs off the bat per 100 legal balls vs average ground): Eden Gardens +11.3, Wankhede +10.7, Chinnaswamy +10.1, Sawai Mansingh (Jaipur) −2.4, Chepauk −6.6. `v2_results/comp_strength/venue_effects_top60.csv`.
- `v2_code/run_all.sh` added: one command per stage, in dependency order.

**15 Nov — competition strength, refit with T20I split** (final for now; `v2_results/comp_strength/`)
- **T20I split.** T20I-Full = both teams are full members (706 matches). T20I-Assoc = any associate team involved (2,396).
- **League pool quality, 2022–26** (runs per 100 balls vs IPL, batters / bowlers):

  | League | Batters | Bowlers |
  |---|---|---|
  | IPL | 0 | 0 |
  | ILT20 | −4.5 | −1.8 |
  | MLC | −4.5 | −6.1 |
  | **T20I-Full** | **−5.9** | **−2.4** |
  | BBL | −7.0 | −6.5 |
  | CPL | −7.3 | −4.6 |
  | SA20 | −7.6 | −3.7 |
  | PSL | −9.0 | −2.6 |
  | LPL | −11.3 | −4.0 |
  | Blast | −13.0 | −10.2 |
  | A-team | −15.1 | −9.7 |
  | BPL | −15.8 | −8.8 |
  | SMAT | −16.9 | −10.9 |
  | CSA | −18.4 | −13.4 |
  | Super Smash | −19.2 | −14.0 |
  | T20I-Assoc | −25.1 | −12.9 |

- **Answer to the brief's "IPL vs T20I" question:** full-member T20Is are close to the IPL in player quality. The raw T20I gap was almost entirely associate games.
- **Penalty.** The runs penalty moved to λ=30, the edge of the grid. MSE barely changes between 30 and 100 (2.7449 vs 2.7457), so this is a flat optimum. **To do:** extend the grid down to 10 when the final pipeline runs.
- **Uncertainty.** The per-season table (`league_strength_by_season.csv`) shows year-to-year stability. A match-bootstrap for standard errors would take about 27 minutes (40 s per fit × 2 targets × 20 resamples) and is **deferred until the user approves it**.

**15 Nov — competition strength, first fit** (`s07_comp_strength.py`)
- **Model.** Sparse ridge on 1.6M legal balls, 2019–26: context (innings × over × wickets down) + competition×season environment + batter effect − bowler effect. Fitted separately for runs off the bat and for striker dismissed. Context and environment are effectively unpenalised (column scaling ×100). Players link the competitions.
- **Penalty chosen out of time** (train ≤2025, score 2026): λ=100 for runs, λ=1000 for dismissals.
  - Player effects cut the 2026 runs MSE by **1.5%** relative to context and environment alone. Per-ball runs are mostly noise, so this is a real signal.
  - For dismissals the gain is only **0.05%**. Dismissal skill is almost invisible ball by ball. This matches the baseline's near-zero split-half r for wicket components, and it means dismissal and wicket terms must be heavily shrunk.
- **League pool quality, 2022–26** (runs per 100 balls vs IPL, batters / bowlers): IPL 0/0, ILT20 −4.7/−0.8, MLC −4.7/−4.7, CPL −6.8/−3.8, SA20 −7.2/−3.2, BBL −7.9/−5.5, PSL −8.8/−2.2, LPL −10.2, Blast −13.4, BPL −14.5, A-team −15.2, SMAT −15.4, CSA −17.4, Super Smash −17.4.
  - T20I came out at −19.1 as a single bucket, which mixes in associate nations. **Fix:** split into T20I-Full (both teams full members) and T20I-Assoc, then refit.
- **Raw transfer check** (same batters, IPL vs other league, raw runs per 100 balls): this mixes quality with conditions and era. Batters score 10 more per 100 balls in the IPL than in the BBL, but 7 fewer than in the Blast. That is consistent with the environment effects, not a contradiction. It is kept only as a sanity table.

**15 Nov — unified ball table** (`s06_unify.py`)
- **Contents:** all RR-pack matches, with their rich fields, plus Cricsheet matches not in the RR pack. That gives 1,665,310 balls, 7,288 matches and 6,754 players.
- **Player key:** the Cricsheet ID, or `rr<id>` for RR players with no Cricsheet match.
- **RR reconciliation is exact:** off-the-bat runs 269,506 = 269,506, total runs 284,203 = 284,203, wickets 10,868 = 10,868. Two RR rows had extras with no type (1 run each) and are counted as "other extras". "Retired out" counts as a wicket.
- 16 public innings have 121–122 legal balls. These are real umpire miscounts, mostly in associate T20Is, and are harmless (balls left is clipped at 0).

**15 Nov — identity map done** (`s05_idmap.py` → `v2_results/idmap/`)
- **Match pairing.** RR matches were paired with Cricsheet matches on date (±1 day) plus both innings totals. 782 of 867 paired. On aligned balls, runs agreed for a median of 100% of balls, and every paired match agreed on at least 90%.
  - The 85 unpaired matches are the 29 A-team Asia Cup games (not in Cricsheet) and **every Afghanistan T20I**. **Cricsheet's t20s archive has no Afghanistan matches at all** (0 of 3,649). I did not look into why.
- **Method A, ball alignment.** Deliveries were aligned over by over, and each aligned ball cast a vote linking RR striker, bowler and non-striker IDs to Cricsheet IDs. 866 players were mapped this way, with a median vote share of 1.0. Only one player was below 0.9: Brandon Glover, 20 balls, share 0.84, still correct.
- **Fallback for the rest.** A link is accepted only when it is *unique across the whole Cricsheet register*:
  - B1, exact full name: 28 players.
  - B2, first initial plus surname: 14 players. This applies only when the Cricsheet name is in initials form or starts with the same first name.
  - **Two wrong links were caught and removed** by that rule: Mohammad Saleem Safi→Mansoor Safi and Mohammad Chowdhury→Mrittunjoy Chowdhury.
  - Fuzzy-only candidates (5) are kept for review and **not used** in modelling.
- **Result.** 908 of 959 RR players are mapped, covering **99.07% of RR balls**. No Cricsheet ID is shared by two RR players. 51 remain unmapped, mostly Afghan and Bangladeshi A-team players with ambiguous or absent records. They are listed, not dropped, and are rated on RR data alone.
- **Manual check of the top 200 by balls.** 196 are ball-aligned with share 1.0 and the surname inside the Cricsheet name. The other 4 were checked by hand and are all correct: Hasaranga = "PWH de Silva", Varun Chakravarthy = "CV Varun", Sooryavanshi = "V Suryavanshi", and Ibrahim Zadran is a unique exact name.

**15 Nov — Cricsheet parsed** (`s03_public.py`, 29 s): 7,203 matches and 1.65M balls (men's T20, 2019+, 6-ball overs). Only 0.01% of balls lack a registry ID.
- Coverage gaps: SMAT has just 8 matches in 2024 and none in 2025–26. Unofficial T20Is contribute 1 match. The Hundred is excluded because it is a 100-ball format.
- Licence: ODC-By. Details are in `data_public/SOURCES.md`.

**15 Nov — RR pack audit** (`v2_results/audit/DATA_AUDIT.md`):
- **Coverage:** 867 matches with ball data. 16 abandoned matches have none.
- **Duplicate names:** 3 names are shared by 2 different player IDs (Abdul Samad, Basil Hameed, Haider Ali). IDs are always used, never names.
- **Bowling labels:** 47 bowlers carry more than one `bowling_type` label. Use each bowler's most common label.
- **`bowl_speed`:** 0 on 14–52% of balls, depending on competition and season. **Dropped.**
- **`delivery_style`:** missing on less than 1% of balls. Kept as a matchup proxy.
- **Rain-revised matches:** 34 by the matches.csv columns, but the baseline report says 23. Check which one the baseline actually used.
- **No-balls:** `other` extras (264) are 1-run no-balls. The baseline already treats them as illegal.

## S0 — Setup and reproducibility

**15 Nov — git.** The project now has its **own** git repo (`git init` in the project folder, branch `main`). The first commit is `dda0e62`, with 38 files. It is not connected to the home-folder repo or any remote. Ignored and confirmed: `02_data/`, `data_public/`, `v2_work/`, `.env_superr/`, `03_code/out/`. A GitHub remote has not been created yet: that needs `gh auth login` and the user's choice of a private repo.

**15 Nov — determinism resolved.** I ran the quick baseline (N_SEEDS=2) twice on this Mac. The maximum difference in wp, LI, xruns, WPA and rating was **0.0**. So the baseline *is* deterministic on one machine. The rank changes against `04_outputs` come from a different machine and library versions (the outputs were produced on Claude's servers). Combined with gaps of 0.01–0.03 between ranks 2–10, small numerical differences reorder the near-ties. **Actions for v2:** pin the exact environment (`v2_code/environment.yml`), pin threads in `common.py`, and report near-ties as ties.
- The environment `.env_superr` has Python 3.11, pandas 2.2.3, scikit-learn 1.5.2, LightGBM 4.7.0, XGBoost 3.4.2, NumPyro 0.22.0 and JAX 0.7.1.

**15 Nov — baseline rerun on this Mac (full 40-seed run, 300 bootstraps).**
- Batters: the same 10 players as `04_outputs`, but ranks 5/6 and 8/9/10 swap.
- Bowlers: Krunal Pandya (#8) drops out and Bhuvneshwar Kumar comes in at #10. Ranks 4–7 reorder.
- Rating gaps between ranks 2–10 are about 0.01–0.03, smaller than the bootstrap intervals (about ±0.4). So the lower half of each list is a statistical tie, and small numerical differences reorder it.
- It is not yet clear whether this is machine and library version differences or real run-to-run randomness. A test is running: the quick `N_SEEDS=2` pipeline twice on this Mac, then a diff.

**15 Nov — confidentiality.** `~` is a git repo with a GitHub remote. The project is untracked, but a `git add .` from `~` would upload the data pack. I added a project `.gitignore` and confirmed with `git check-ignore`.
