#!/usr/bin/env bash
# Checks the BUILT site (dist/) before deploying: nothing readable without the password, noindex in place.
set -u; cd "$(dirname "$0")/.."; fail=0
ok(){ echo "PASS  $1"; }; bad(){ echo "FAIL  $1"; fail=1; }
[ -d dist ] || { echo "run npm run build first"; exit 1; }
# 1. no plaintext player names / stats keys from the data in any shipped file
for n in Sooryavanshi Bumrah Narine "pressure_balls\":" "obs_pressure\":" "Left-knee impact injury" "Jofra Archer"; do
  if grep -rqa -- "$n" dist; then bad "plaintext '$n' found in dist"; else ok "no plaintext '$n'"; fi; done
# 2. no unencrypted data or report files shipped
[ -z "$(find dist -name '*.json' ! -name 'key.json' ! -name 'vercel.json' ! -path '*/enc/*' -o -name '*.csv' -o -name '*.parquet' -o -name '*.pdf' | grep -v '^$')" ] && ok "no raw json/csv/parquet/pdf files" || bad "raw data files present"
grep -rqa '%PDF' dist && bad "PDF bytes visible" || ok "report PDF is encrypted"
[ -z "$(find dist -name '*.map')" ] && ok "no source maps" || bad "source maps present"
ls dist | grep -q private_data && bad "private_data copied into dist" || ok "private_data not in dist"
grep -q '"files"' dist/enc/key.json && ! grep -q 'SITE_PASSWORD' -r dist && ok "password not in build" || bad "password leak?"
# 3. noindex everywhere
grep -q 'noindex' dist/index.html && ok "meta robots noindex" || bad "meta noindex missing"
grep -q 'Disallow: /' dist/robots.txt && ok "robots.txt disallows all" || bad "robots.txt"
grep -q 'X-Robots-Tag' dist/_headers && grep -q 'X-Robots-Tag' vercel.json && ok "X-Robots-Tag header (Netlify + Vercel)" || bad "header config"
exit $fail
