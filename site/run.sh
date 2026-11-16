#!/usr/bin/env bash
# One command to run the evaluator site locally: export data -> encrypt -> build -> serve at http://localhost:4173
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env.local ] || { echo "Create site/.env.local with a line: SITE_PASSWORD=your-password"; exit 1; }
[ -d node_modules ] || npm install --no-audit --no-fund
if [ "${SKIP_EXPORT:-0}" != "1" ]; then (cd ../v2_code && ../.env_superr/bin/python s25_site_export.py); fi
npm run build
bash scripts/security_check.sh
echo "Open http://localhost:4173  (password in site/.env.local)"
npx vite preview --port 4173 --strictPort
