# Research log — SupeRR Selector S2, v2

The plan is in `~/.claude/plans/jolly-yawning-metcalfe.md` and was approved on 15 Nov 2026.
Entries are listed newest first within each stage. Every decision gives the reason and the evidence file.

## Task list
| # | Task | Status |
|---|---|---|
| S0.1 | `.gitignore` guard for `02_data/`, `data_public/`, `v2_work/`, pickles | done |
| S0.2 | Conda env `.env_superr` (py3.11 + lightgbm, xgboost, numpyro, statsmodels…) | done |
| S0.3 | Diagnose baseline non-reproducibility | done (cross-machine, not random) |
| S0.4 | Separate project git repo (local); GitHub private remote | local done; remote awaiting user |
| S1 | CRICKET_PRIMER.md (cited research) | done |
| S2.1 | Data audit + data dictionary | done |
| S2.2 | Cricsheet download (48 MB) + parse | done; dedupe vs RR pack next |
| S2.3 | Player identity map (+ manual check of top 200) | todo |
| S2.4 | Competition-strength model | todo |
| S3.1 | Feature build + FEATURES.md | todo |
| S3.2 | Pressure-definition comparison | todo |
| S4A | WP + expected-outcome model comparison (rolling by season) | todo |
| S4B | Player-skill model comparison (M0–M7) | todo |
| S4C | Is clutch repeatable? | todo |
| S4D | Final score, sensitivity, ablation, fairness | todo |
| S5 | Scout cards (~30 per list) | todo |
| S6 | Deliverables in `v2_results/` + fresh-eyes review | todo |

## S2 — Data audit and public data

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
