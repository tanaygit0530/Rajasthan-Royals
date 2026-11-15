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
| S2.4 | Competition-strength model | done (bootstrap SE pending approval) |
| S3.1 | Feature build + FEATURES.md | todo |
| S3B | Player profile database (all players, all splits) + DATA_DICTIONARY + reconciliation + 20-player spot check; pressure columns after S4A | todo |
| S4E | SHAP top predictors, player-type clustering, matchup model | todo |
| S3.2 | Pressure-definition comparison | todo |
| S4A | WP + expected-outcome model comparison (rolling by season) | todo |
| S4B | Player-skill model comparison (M0–M7) | todo |
| S4C | Is clutch repeatable? | todo |
| S4D | Final score, sensitivity, ablation, fairness | todo |
| S5 | Scout cards (~30 per list) | todo |
| S5B | Value hunting: capped status, emerging tier (40+ pressure balls), upside backtest, price model, value list + 5 cards each | todo (after S4) |
| S5C | Youth board: age (Wikidata), development model + comparables, top 15/15/5 board, 10 cards, youth strategy section | todo (after S4) |
| P7 | Auction optimiser | waiting for the Phase 7 brief; 5B/5C output pool CSVs in a documented format |
| S6 | Deliverables in `v2_results/` + fresh-eyes review | todo |

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

## S2 — Data audit and public data

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
