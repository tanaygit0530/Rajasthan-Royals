"""S2.4: competition-strength model, estimated from players who appear in several competitions.

Per legal ball faced:  y = context(innings x over, wickets-down) + env[comp x season] + bat[batter] - bowl[bowler] + e
fitted as sparse ridge (players penalised, context/env effectively unpenalised via column scaling), separately for
  y = runs off the bat     and     y = striker dismissed (linear probability).
Players link competitions, so env (conditions/rules) is separated from the quality of the players in a competition.
League strength = ball-weighted mean quality of the batters (and bowlers) who played in it.
Penalty chosen out-of-time: fit 2019-2025, score 2026 balls.
Outputs: v2_results/comp_strength/*.csv, v2_work/comp_strength/player_effects.parquet
"""
import time
import scipy.sparse as sp
from scipy.sparse.linalg import lsqr
from common import *

rng = seed_all()
B = pd.read_parquet(w('unified/balls.parquet'),
                    columns=['match_id', 'innings', 'over', 'wkts_before', 'batter', 'bowler', 'runs_bat', 'legal',
                             'striker_out', 'comp2', 'season', 'is_wide']).rename(columns={'comp2': 'comp'})
B = B[B.legal & B.batter.notna() & B.bowler.notna()].reset_index(drop=True)
B['cs'] = B.comp + '_' + B.season.astype(str)
B['ctx'] = 'i' + B.innings.astype(str) + '_o' + B.over.clip(1, 20).astype(str) + '_w' + B.wkts_before.clip(0, 8).astype(str)
print('legal balls', len(B))

cat = {c: pd.Categorical(B[c]) for c in ['ctx', 'cs', 'batter', 'bowler']}
sizes = {c: len(cat[c].categories) for c in cat}
print('columns', sizes)
UNPEN_SCALE = 100.0          # context + env columns scaled up -> penalty shrinks by 1/scale^2 (effectively free)


def design(idx):
    n = len(idx); blocks = []; off = 0
    for c, sign, scale in [('ctx', 1, UNPEN_SCALE), ('cs', 1, UNPEN_SCALE), ('batter', 1, 1.0), ('bowler', -1, 1.0)]:
        codes = cat[c].codes[idx]
        blocks.append(sp.csr_matrix((np.full(n, sign * scale), (np.arange(n), codes)), shape=(n, sizes[c])))
    return sp.hstack(blocks).tocsr()


def fit(idx, y, lam):
    X = design(idx)
    mu = y.mean()
    sol = lsqr(X, y - mu, damp=np.sqrt(lam), atol=1e-8, btol=1e-8, iter_lim=3000)[0]
    o = 0; out = {}
    for c, scale in [('ctx', UNPEN_SCALE), ('cs', UNPEN_SCALE), ('batter', 1.0), ('bowler', 1.0)]:
        out[c] = pd.Series(sol[o:o + sizes[c]] * scale, index=cat[c].categories); o += sizes[c]
    out['mu'] = mu
    return out


def predict(eff, idx):
    return (eff['mu'] + eff['ctx'].values[cat['ctx'].codes[idx]] + eff['cs'].values[cat['cs'].codes[idx]]
            + eff['batter'].values[cat['batter'].codes[idx]] - eff['bowler'].values[cat['bowler'].codes[idx]])


# ---------------- choose penalty out of time ----------------
tr = np.where(B.season <= 2025)[0]; te = np.where(B.season == 2026)[0]
rows = []
for target in ['runs_bat', 'striker_out']:
    y = B[target].astype(float).values
    for lam in [30, 100, 300, 1000, 3000]:
        t0 = time.time(); e = fit(tr, y[tr], lam)
        # 2026 env not estimable from training -> use same competition's 2025 env as forecast
        env25 = {k.replace('_2025', '_2026'): v for k, v in e['cs'].items() if k.endswith('_2025')}
        e2 = dict(e); e2['cs'] = e['cs'].reindex(cat['cs'].categories).fillna(pd.Series(env25)).fillna(0)
        p = predict(e2, te)
        e0 = dict(e2); e0['batter'] = e['batter'] * 0; e0['bowler'] = e['bowler'] * 0
        p0 = predict(e0, te)
        rows.append(dict(target=target, lam=lam, mse=np.mean((y[te] - p) ** 2), mse_ctx_env_only=np.mean((y[te] - p0) ** 2),
                         secs=round(time.time() - t0, 1)))
        print(rows[-1])
cv = pd.DataFrame(rows)
cv['skill_gain_pct'] = (1 - cv.mse / cv.mse_ctx_env_only) * 100
cv.to_csv(res('comp_strength/penalty_selection_2026_holdout.csv'), index=False)
best = cv.loc[cv.groupby('target').mse.idxmin()].set_index('target').lam.to_dict()
print('chosen penalty', best)

# ---------------- final fit on all seasons + league strength ----------------
allidx = np.arange(len(B))
E = {t: fit(allidx, B[t].astype(float).values, best[t]) for t in ['runs_bat', 'striker_out']}
pe = pd.DataFrame({'bat_runs': E['runs_bat']['batter'], 'bat_out': E['striker_out']['batter']}).join(
    pd.DataFrame({'bowl_runs': E['runs_bat']['bowler'], 'bowl_wkt': E['striker_out']['bowler']}), how='outer')
# sign convention: bowler effect enters as minus, so bowl_runs > 0 = concedes FEWER runs (good);
# for dismissals bowl_wkt > 0 means FEWER dismissals -> flip so positive = more wickets (good)
pe['bowl_wkt'] = -pe.bowl_wkt
pe['bat_out'] = pe.bat_out          # >0 = dismissed MORE (bad)
os.makedirs(w('comp_strength'), exist_ok=True)
pe.to_parquet(w('comp_strength/player_effects.parquet'))


def league_strength(eff_bat, eff_bowl, label):
    d = B[['cs', 'comp', 'season', 'batter', 'bowler']]
    bq = d.batter.map(eff_bat).values; wq = d.bowler.map(eff_bowl).values
    s = pd.DataFrame({'cs': d.cs, 'comp': d.comp, 'season': d.season, 'bq': bq, 'wq': wq})
    out = s.groupby(['comp', 'season']).agg(balls=('bq', 'size'), batter_quality=('bq', 'mean'), bowler_quality=('wq', 'mean'))
    out['metric'] = label
    return out


ls_runs = league_strength(pe.bat_runs, pe.bowl_runs, 'runs per ball')
ls_out = league_strength(-pe.bat_out, pe.bowl_wkt, 'dismissals per ball')
env = pd.DataFrame({'env_runs': E['runs_bat']['cs'], 'env_out': E['striker_out']['cs']})

# per-100-balls, relative to IPL of the same season (IPL = 0)
def rel(t):
    t = t.copy()
    for c in ['batter_quality', 'bowler_quality']:
        ipl = t.xs('IPL', level='comp')[c]
        t[c + '_vs_IPL'] = [(v - ipl.get(s, np.nan)) * 100 for (cmp, s), v in t[c].items()]
    return t


ls = rel(ls_runs).join(rel(ls_out)[['batter_quality_vs_IPL', 'bowler_quality_vs_IPL']], rsuffix='_out')
ls.round(4).to_csv(res('comp_strength/league_strength_by_season.csv'))
overall = ls.reset_index()
overall = overall[overall.season >= 2022].groupby('comp').apply(
    lambda d: pd.Series({'balls': d.balls.sum(),
                         'batters_runs_vs_IPL_per100': np.average(d.batter_quality_vs_IPL, weights=d.balls),
                         'bowlers_runs_saved_vs_IPL_per100': np.average(d.bowler_quality_vs_IPL, weights=d.balls),
                         'batters_outs_avoided_vs_IPL_per100': np.average(d.batter_quality_vs_IPL_out, weights=d.balls),
                         'bowlers_wkts_vs_IPL_per100': np.average(d.bowler_quality_vs_IPL_out, weights=d.balls)}),
    include_groups=False).sort_values('batters_runs_vs_IPL_per100', ascending=False)
overall.round(2).to_csv(res('comp_strength/league_strength_2022_26.csv'))
env.round(4).to_csv(res('comp_strength/environment_effects.csv'))
print(overall.round(2).to_string())

# ---------------- transfer sanity check: same players, IPL vs other comp (raw runs/100 balls) ----------------
pr = B.groupby(['batter', 'comp']).agg(n=('runs_bat', 'size'), r=('runs_bat', 'mean'))
pr = pr[pr.n >= 120].r.unstack()
tr_rows = []
for c in pr.columns:
    if c == 'IPL': continue
    both = pr[['IPL', c]].dropna()
    if len(both) >= 8:
        tr_rows.append(dict(comp=c, n_players=len(both), ipl_minus_comp_runs_per100=(both.IPL - both[c]).mean() * 100))
tr = pd.DataFrame(tr_rows).sort_values('ipl_minus_comp_runs_per100')
tr.round(2).to_csv(res('comp_strength/transfer_check_batters.csv'), index=False)
print(tr.round(2).to_string(index=False))
