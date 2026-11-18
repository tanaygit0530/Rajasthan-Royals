#!/usr/bin/env bash
# Reproduce every v2 output from the RR pack (02_data/) + Cricsheet zips (data_public/). One command per stage.
# Usage: bash v2_code/run_all.sh            (all stages)
#        bash v2_code/run_all.sh s07        (stages whose name starts with s07)
set -euo pipefail
cd "$(dirname "$0")"
PY=../.env_superr/bin/python
STAGES=(
  s01_primer_facts      # primer tables (run rates by era/phase)
  s02_audit             # data audit + dictionary
  s03_public            # parse Cricsheet zips -> public ball table
  s04_career_stats      # traditional batting/bowling stats (RR pack)
  s05_idmap             # RR player id -> Cricsheet id
  s06_unify             # unified ball/match/player tables
  s06b_context          # venue key, Cricsheet knockouts, IPL stakes, day/night, rain fixes, impact era
  s06c_dob              # Wikidata dates of birth (cached download; --refresh to re-fetch)
  s06d_roles            # roles, pressure-building credit, survivorship check
  s07_comp_strength     # competition strength (ridge: context + env + venue + players; extras target)
  s07b_bootstrap        # match bootstrap SEs for league strength (~40-60 min)
  s08_wp                # win-probability model comparison (rolling folds) + state table
  s09_xoutcome          # expected-outcome model comparison
  s10_ball_values       # per-ball WP, leverage, WPA, expectations for each cutoff (~20 min)
  s11_pressure_defs     # pressure-definition comparison
  s12_backtest          # player-skill backtest M0-M8 + clutch test
  s14_profiles          # player profile database (needs s11)
  s16_capped            # capped / uncapped status (nationality for s13)
  s13c_calibrate        # out-of-time interval calibration (widening factor used by s13)
  s13_final             # final ratings, intervals, sensitivity (~40 min)
  s13b_ablation         # out-of-time ablation, fairness, interval coverage (~30 min)
  s15_explain           # SHAP, clusters, matchups (needs s12, s14)
  s17_value             # prices, value lists, emerging tier, Phase 7 pools
  s20_youth             # youth board, development model backtest, comparables
  s18_cards             # scout cards
  s23_rr_fit            # RR squad fit, role gaps, shortlists, selector verdicts
  s19_charts            # report charts
  s21_report            # report, executive summary, model comparison, baseline vs v2 (pandoc + Chrome)
  s22_review            # fresh-eyes review (independent recomputation from the raw RR file)
  s26_final_pdf         # concise visual final report (8 pages) -> v2_results/report/final/
  s25_site_export       # aggregated JSON for the evaluator site (site/private_data, git-ignored)
)
# usage: run_all.sh            -> all stages
#        run_all.sh s07        -> stages starting with s07
#        run_all.sh --from s08 -> s08 and every later stage
FROM=""; [[ "${1:-}" == "--from" ]] && FROM="$2"; started=0
for s in "${STAGES[@]}"; do
  if [[ -n "$FROM" ]]; then [[ "$s" == "$FROM"* ]] && started=1; [[ $started -eq 1 ]] || continue; fi
  if [[ -n "$FROM" || $# -eq 0 || "$s" == "$1"* ]]; then
    echo "=== $s"; $PY "$s.py"
  fi
done
