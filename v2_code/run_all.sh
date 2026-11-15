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
)
for s in "${STAGES[@]}"; do
  if [[ $# -eq 0 || "$s" == "$1"* ]]; then
    echo "=== $s"; $PY "$s.py"
  fi
done
