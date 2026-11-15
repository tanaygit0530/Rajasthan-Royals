# Research log — SupeRR Selector S2, v2

The plan is in `~/.claude/plans/jolly-yawning-metcalfe.md` and was approved on 15 Nov 2026.
Entries are listed newest first within each stage. Every decision gives the reason and the evidence file.

## Task list
| # | Task | Status |
|---|---|---|
| S0.1 | `.gitignore` guard for `02_data/`, `data_public/`, `v2_work/`, pickles | done |
| S0.2 | Conda env `.env_superr` (py3.11 + lightgbm, xgboost, numpyro, statsmodels…) | in progress |
| S0.3 | Diagnose baseline non-reproducibility | in progress |
| S1 | CRICKET_PRIMER.md (cited research) | in progress |
| S2.1 | Data audit + data dictionary | todo |
| S2.2 | Cricsheet download (~80 MB) + dedupe vs RR pack | todo |
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

## S0 — Setup and reproducibility

**15 Nov — baseline rerun on this Mac (full 40-seed run, 300 bootstraps).**
- Batters: the same 10 players as `04_outputs`, but ranks 5/6 and 8/9/10 swap.
- Bowlers: Krunal Pandya (#8) drops out and Bhuvneshwar Kumar comes in at #10. Ranks 4–7 reorder.
- Rating gaps between ranks 2–10 are about 0.01–0.03, smaller than the bootstrap intervals (about ±0.4). So the lower half of each list is a statistical tie, and small numerical differences reorder it.
- It is not yet clear whether this is machine and library version differences or real run-to-run randomness. A test is running: the quick `N_SEEDS=2` pipeline twice on this Mac, then a diff.

**15 Nov — confidentiality.** `~` is a git repo with a GitHub remote. The project is untracked, but a `git add .` from `~` would upload the data pack. I added a project `.gitignore` and confirmed with `git check-ignore`.
