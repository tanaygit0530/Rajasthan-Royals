# SupeRR Selector S2 – v2: how to reproduce every number

## What is here

| Path | Contents |
|---|---|
| `final_rankings.csv` | The submission: top-10 batters and bowlers (open ranking and "RR can buy"), with score, 80% interval, P(top 10), pressure balls, near-tie flag |
| `rankings/` | Full rankings for every eligible player, with all components |
| `report/` | Methodology report (`.md`, `.docx`, `.pdf`), executive summary, charts |
| `MODEL_COMPARISON.md`, `BASELINE_VS_V2.md`, `EXECUTIVE_SUMMARY.md` | Model evidence, comparison with v1, one-page summary |
| `cards/` | Scout cards (top 30 per list), value cards, sourced scouting notes |
| `value/` | Uncapped & Value Targets, price model, emerging tier, Phase 7 pool CSVs |
| `youth/` | Youth board, development-model backtest, comparables |
| `profiles/` | Player profile summary, data dictionary, reconciliation, spot-check |
| `models/`, `pressure/`, `context/`, `comp_strength/`, `explain/` | Every model comparison, backtest, ablation, sensitivity and diagnostic table |
| `idmap/`, `audit/`, `stats/`, `primer/` | Identity map, data audit, traditional stats, primer tables |

Every number in the report is read from these files by `v2_code/s21_report.py`; nothing is typed in by hand.

## Reproduce

Requirements: macOS/Linux, conda. Data: the RR pack in `02_data/` (confidential, not in the repository) and the public
Cricsheet/Wikipedia/Wikidata files in `data_public/` (re-downloadable; URLs and access dates in `data_public/SOURCES.md`).

```bash
conda env create -p .env_superr -f v2_code/environment.yml     # Python 3.11, pinned versions
bash v2_code/run_all.sh                                       # every stage, in order (~4-5 h on an 8 GB M2)
bash v2_code/run_all.sh --from s08                            # from a given stage onwards
bash v2_code/run_all.sh s13                                   # a single stage (prefix match)
.env_superr/bin/python v2_code/s21_report.py                  # rebuild report, summary, comparisons (pandoc + Chrome)
```

Seeds are fixed in `v2_code/common.py` (`SEED = 20261115`); thread counts are pinned. Long stages: `s07b_bootstrap`
(~45 min), `s10_ball_values` (~20 min), `s13_final` (~40 min incl. sensitivity), `s13b_ablation` (~30 min).

## Stage map

| Stage | Produces |
|---|---|
| s01-s02 | primer tables, data audit |
| s03, s05, s06 | Cricsheet parse, RR->Cricsheet identity map, unified ball table |
| s06b-d | match context (venues, knockouts, stakes, day/night, rain), dates of birth, roles |
| s07, s07b | competition / venue / player ridge model, bootstrap SEs |
| s08-s10 | win-probability and expected-outcome model comparisons; per-ball values for every cutoff |
| s11 | pressure-definition comparison |
| s12, s13b | skill backtest (M0-M8), clutch test, ablation, fairness, interval coverage |
| s13 | final ratings, intervals, P(top 10), sensitivity |
| s14, s15 | profile database; SHAP, player types, matchups |
| s16, s17 | capped status; prices, value lists, emerging tier, Phase 7 pools |
| s18, s20 | scout cards; youth board |
| s19, s21 | charts; report and companion documents |

## Rules followed

The RR pack never leaves this machine and is git-ignored. Only openly licensed public data is used (Cricsheet ODC-By,
Wikipedia CC BY-SA, Wikidata CC0). Every predictive model is evaluated on seasons it was not trained on. Qualitative notes
are labelled and never change a rank. Where a fancier model did not beat a simpler one out of time, the simpler one was kept.
