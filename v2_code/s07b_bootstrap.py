"""S2.4b: match-level bootstrap standard errors for league strength (known issue: SEs were missing).

Resample matches with replacement (multinomial match weights), refit the three ridge models at the chosen
penalties, warm-started from the full-data solution, and recompute league strength on the original ball mix.
Usage: python s07b_bootstrap.py [n_reps]   (default 60). Runs in the background (~40-60 min on an M2).
Outputs: v2_results/comp_strength/league_strength_2022_26_with_se.csv, v2_work/comp_strength/boot_reps.parquet
"""
import sys
import json
import time
import s07_comp_strength as S
from common import *

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
rng = seed_all()
B, cat = S.load()
meta = json.load(open(w('comp_strength/fit_meta.json')))
S.DELIV_PER_LEGAL = meta['deliv_per_legal']
lam = meta['lam']
x0 = {t: np.load(w(f'comp_strength/sol_{t}.npy')) for t in S.TARGETS}
mcodes, muniq = pd.factorize(B.match_id)
reps = []
t_start = time.time()
for r in range(N):
    cnt = rng.multinomial(len(muniq), np.full(len(muniq), 1 / len(muniq)))
    wb = cnt[mcodes].astype(float)
    E = {}
    for t, spec in S.TARGETS.items():
        idx = S.rows_for(B, spec['rows'], wb > 0)
        E[t] = S.fit(cat, idx, B[t].astype(float).values[idx], lam[t], spec['blocks'], wts=wb[idx], x0=x0[t], iter_lim=1500)
    _, o = S.league_strength(B, S.player_table(E))
    reps.append(o.assign(rep=r).reset_index())
    el = time.time() - t_start
    print(f'rep {r + 1}/{N} done, {el / 60:.1f} min elapsed, ~{el / (r + 1) * (N - r - 1) / 60:.0f} min left', flush=True)
R = pd.concat(reps)
R.to_parquet(w('comp_strength/boot_reps.parquet'), index=False)
cols = ['batters_runs_vs_IPL_per100', 'bowlers_runs_saved_vs_IPL_per100', 'batters_outs_avoided_vs_IPL_per100', 'bowlers_wkts_vs_IPL_per100']
point = pd.read_csv(res('comp_strength/league_strength_2022_26.csv'), index_col='comp')
se = R.groupby('comp')[cols].std().add_suffix('_se')
lo = R.groupby('comp')[cols].quantile(0.05).add_suffix('_p05'); hi = R.groupby('comp')[cols].quantile(0.95).add_suffix('_p95')
out = point.join(se).join(lo).join(hi)
out = out[['balls'] + [k + s for k in cols for s in ('', '_se', '_p05', '_p95')]]
out.round(2).to_csv(res('comp_strength/league_strength_2022_26_with_se.csv'))
print(out[['balls'] + [k + s for k in cols for s in ('', '_se')]].round(2).to_string())
