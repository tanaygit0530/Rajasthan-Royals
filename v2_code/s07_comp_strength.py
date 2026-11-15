"""S2.4: competition-strength model, estimated from players who appear in several competitions.

Per ball:  y = context(innings x over x wickets-down) + env[comp x season] + venue + bat[batter] - bowl[bowler] + e
fitted as sparse ridge (players and venues penalised; context/env effectively unpenalised via column scaling) for
  runs_bat     runs off the bat, legal balls
  striker_out  striker dismissed, legal balls (linear probability)
  extras       wides + no-ball runs, ALL deliveries, bowler side only (no batter term) - so bowlers pay for
               wides/no-balls (gap fix, 15 Nov: the first version used legal balls only)
Players link competitions, so env (conditions/rules) is separated from the quality of the players in a competition;
the venue term stops home-ground scoring conditions being read as player skill (gap fix, 15 Nov).
League strength = ball-weighted mean quality of the batters (and bowlers) who played in it.
Penalty chosen out of time: fit 2019-2025, score 2026 balls; grid widened to 3..10000 (known issue: first fit chose
the grid edge).
Outputs: v2_results/comp_strength/*.csv, v2_work/comp_strength/{player_effects,venue_effects}.parquet, sol_*.npy
"""
import json
import time
import scipy.sparse as sp
from scipy.sparse.linalg import lsqr
from common import *

UNPEN_SCALE = 100.0          # context + env columns scaled up -> penalty shrinks by 1/scale^2 (effectively free)
TARGETS = {'runs_bat': dict(rows='legal', blocks=['ctx', 'cs', 'venue', 'batter', 'bowler']),
           'striker_out': dict(rows='legal', blocks=['ctx', 'cs', 'venue', 'batter', 'bowler']),
           'extras': dict(rows='all', blocks=['ctx', 'cs', 'bowler'])}
SIGN = {'ctx': 1, 'cs': 1, 'venue': 1, 'batter': 1, 'bowler': -1}
SCALE = {'ctx': UNPEN_SCALE, 'cs': UNPEN_SCALE, 'venue': 1.0, 'batter': 1.0, 'bowler': 1.0}


def load():
    B = pd.read_parquet(w('unified/balls.parquet'),
                        columns=['match_id', 'innings', 'over', 'wkts_before', 'batter', 'bowler', 'runs_bat', 'legal',
                                 'striker_out', 'comp2', 'season', 'wide', 'noball']).rename(columns={'comp2': 'comp'})
    C = pd.read_parquet(w('unified/match_context.parquet'), columns=['match_id', 'venue_key'])
    B = B[B.batter.notna() & B.bowler.notna()].merge(C, on='match_id', how='left').reset_index(drop=True)
    B['venue'] = B.venue_key.fillna('unknown')
    B['extras'] = (B.wide + B.noball).astype(float)
    B['cs'] = B.comp + '_' + B.season.astype(str)
    B['ctx'] = 'i' + B.innings.astype(str) + '_o' + B.over.clip(1, 20).astype(str) + '_w' + B.wkts_before.clip(0, 8).astype(str)
    cat = {c: pd.Categorical(B[c]) for c in ['ctx', 'cs', 'venue', 'batter', 'bowler']}
    return B, cat


def design(cat, idx, blocks, wts=None):
    n = len(idx); mats = []
    rw = np.ones(n) if wts is None else np.sqrt(wts)
    for c in blocks:
        codes = cat[c].codes[idx]; k = len(cat[c].categories)
        mats.append(sp.csr_matrix((rw * SIGN[c] * SCALE[c], (np.arange(n), codes)), shape=(n, k)))
    return sp.hstack(mats).tocsr()


def fit(cat, idx, y, lam, blocks, wts=None, x0=None, iter_lim=10000):
    X = design(cat, idx, blocks, wts)
    mu = np.average(y, weights=wts) if wts is not None else y.mean()
    yy = (y - mu) * (np.sqrt(wts) if wts is not None else 1)
    r = lsqr(X, yy, damp=np.sqrt(lam), atol=1e-8, btol=1e-8, iter_lim=iter_lim, x0=x0)
    sol = r[0]; o = 0; out = {'mu': mu, 'sol': sol, 'iters': r[2]}
    for c in blocks:
        k = len(cat[c].categories)
        out[c] = pd.Series(sol[o:o + k] * SCALE[c], index=cat[c].categories); o += k
    return out


def predict(cat, eff, idx, blocks):
    p = np.full(len(idx), eff['mu'])
    for c in blocks:
        p = p + SIGN[c] * eff[c].values[cat[c].codes[idx]]
    return p


def rows_for(B, kind, mask=None):
    m = B.legal.values if kind == 'legal' else np.ones(len(B), bool)
    if mask is not None:
        m = m & mask
    return np.where(m)[0]


def player_table(E):
    pe = pd.DataFrame({'bat_runs': E['runs_bat']['batter'], 'bat_out': E['striker_out']['batter']}).join(
        pd.DataFrame({'bowl_runs': E['runs_bat']['bowler'], 'bowl_wkt': -E['striker_out']['bowler'],
                      'bowl_extras': E['extras']['bowler']}), how='outer')
    # signs: bat_runs >0 good; bat_out >0 = dismissed MORE (bad); bowl_runs >0 = concedes fewer runs off the bat (good);
    # bowl_wkt >0 = more dismissals (good); bowl_extras >0 = concedes fewer wides/no-balls per delivery (good)
    pe['bowl_runs_total'] = pe.bowl_runs + pe.bowl_extras.fillna(0) * DELIV_PER_LEGAL
    return pe


def league_strength(B, pe):
    d = B[B.legal][['comp', 'season', 'batter', 'bowler']]
    s = pd.DataFrame({'comp': d.comp, 'season': d.season, 'bq_runs': d.batter.map(pe.bat_runs).values,
                      'wq_runs': d.bowler.map(pe.bowl_runs_total).values, 'bq_out': -d.batter.map(pe.bat_out).values,
                      'wq_out': d.bowler.map(pe.bowl_wkt).values})
    t = s.groupby(['comp', 'season']).agg(balls=('bq_runs', 'size'), bq_runs=('bq_runs', 'mean'), wq_runs=('wq_runs', 'mean'),
                                          bq_out=('bq_out', 'mean'), wq_out=('wq_out', 'mean'))
    for c in ['bq_runs', 'wq_runs', 'bq_out', 'wq_out']:
        ipl = t.xs('IPL', level='comp')[c]
        t[c + '_vs_IPL'] = [(v - ipl.get(se, np.nan)) * 100 for (cm, se), v in t[c].items()]
    o = t.reset_index()
    o = o[o.season >= 2022].groupby('comp').apply(lambda x: pd.Series({
        'balls': x.balls.sum(),
        'batters_runs_vs_IPL_per100': np.average(x.bq_runs_vs_IPL, weights=x.balls),
        'bowlers_runs_saved_vs_IPL_per100': np.average(x.wq_runs_vs_IPL, weights=x.balls),
        'batters_outs_avoided_vs_IPL_per100': np.average(x.bq_out_vs_IPL, weights=x.balls),
        'bowlers_wkts_vs_IPL_per100': np.average(x.wq_out_vs_IPL, weights=x.balls)}), include_groups=False)
    return t, o.sort_values('batters_runs_vs_IPL_per100', ascending=False)


GRID = {'runs_bat': [3, 10, 30, 100, 300, 1000, 3000, 10000], 'striker_out': [3, 10, 30, 100, 300, 1000, 3000, 10000],
        'extras': [30, 300, 3000, 30000]}
DELIV_PER_LEGAL = 1.0

if __name__ == '__main__':
    seed_all()
    B, cat = load()
    print('deliveries', len(B), flush=True)
    DELIV_PER_LEGAL = len(B) / B.legal.sum()
    print('deliveries', len(B), 'legal', int(B.legal.sum()), {c: len(cat[c].categories) for c in cat})
    # ---------------- choose penalty out of time ----------------
    tr_m = (B.season <= 2025).values; te_m = (B.season == 2026).values
    rows = []
    for target, spec in TARGETS.items():
        y = B[target].astype(float).values
        tr, te = rows_for(B, spec['rows'], tr_m), rows_for(B, spec['rows'], te_m)
        for lam in GRID[target]:
            t0 = time.time(); e = fit(cat, tr, y[tr], lam, spec['blocks'])
            # 2026 env not estimable from training -> same competition's 2025 env as the forecast
            env25 = {k.replace('_2025', '_2026'): v for k, v in e['cs'].items() if k.endswith('_2025')}
            e2 = dict(e); e2['cs'] = e['cs'].where(~e['cs'].index.str.endswith('_2026'), pd.Series(env25).reindex(e['cs'].index)).fillna(0)
            p = predict(cat, e2, te, spec['blocks'])
            e0 = dict(e2)
            for c in ('batter', 'bowler', 'venue'):
                if c in e0: e0[c] = e0[c] * 0
            p0 = predict(cat, e0, te, spec['blocks'])
            rows.append(dict(target=target, lam=lam, mse=np.mean((y[te] - p) ** 2), mse_ctx_env_only=np.mean((y[te] - p0) ** 2),
                             iters=e['iters'], converged=e['iters'] < 10000, secs=round(time.time() - t0, 1)))
            print(rows[-1], flush=True)
    cv = pd.DataFrame(rows)
    cv['skill_gain_pct'] = (1 - cv.mse / cv.mse_ctx_env_only) * 100
    cv.to_csv(res('comp_strength/penalty_selection_2026_holdout.csv'), index=False)
    best = cv.loc[cv.groupby('target').mse.idxmin()].set_index('target').lam.to_dict()
    edge = {t: best[t] in (min(GRID[t]), max(GRID[t])) for t in best}
    print('chosen penalty', best, 'at grid edge:', edge)

    # ---------------- final fit on all seasons ----------------
    E = {}
    for target, spec in TARGETS.items():
        idx = rows_for(B, spec['rows'])
        E[target] = fit(cat, idx, B[target].astype(float).values[idx], best[target], spec['blocks'])
        np.save(w(f'comp_strength/sol_{target}.npy'), E[target]['sol'])
        print('final fit', target, 'lsqr iterations', E[target]['iters'], '(cap 10000)', flush=True)
    json.dump({'lam': {k: float(v) for k, v in best.items()}, 'deliv_per_legal': DELIV_PER_LEGAL},
              open(w('comp_strength/fit_meta.json'), 'w'))
    pe = player_table(E)
    pe.to_parquet(w('comp_strength/player_effects.parquet'))
    ven = pd.DataFrame({'venue_runs': E['runs_bat']['venue'], 'venue_out': E['striker_out']['venue']})
    ven['legal_balls'] = B[B.legal].venue.value_counts().reindex(ven.index)
    ven.to_parquet(w('comp_strength/venue_effects.parquet'))
    (ven.assign(runs_per100=ven.venue_runs * 100, outs_per100=ven.venue_out * 100)
        .sort_values('legal_balls', ascending=False).head(60).round(3).to_csv(res('comp_strength/venue_effects_top60.csv')))

    t, overall = league_strength(B, pe)
    t.round(4).to_csv(res('comp_strength/league_strength_by_season.csv'))
    overall.round(2).to_csv(res('comp_strength/league_strength_2022_26.csv'))
    pd.DataFrame({'env_runs': E['runs_bat']['cs'], 'env_out': E['striker_out']['cs'], 'env_extras': E['extras']['cs']}) \
        .round(4).to_csv(res('comp_strength/environment_effects.csv'))
    print(overall.round(2).to_string())
    print('venue effects (runs off bat per 100 legal balls), busiest 15:')
    print((ven.sort_values('legal_balls', ascending=False).head(15).venue_runs * 100).round(2).to_string())

    # ---------------- transfer sanity check: same players, IPL vs other comp (raw runs/100 balls) ----------------
    L = B[B.legal]
    pr = L.groupby(['batter', 'comp']).agg(n=('runs_bat', 'size'), r=('runs_bat', 'mean'))
    pr = pr[pr.n >= 120].r.unstack()
    tr_rows = []
    for c in pr.columns:
        if c == 'IPL': continue
        both = pr[['IPL', c]].dropna()
        if len(both) >= 8:
            tr_rows.append(dict(comp=c, n_players=len(both), ipl_minus_comp_runs_per100=(both.IPL - both[c]).mean() * 100))
    pd.DataFrame(tr_rows).sort_values('ipl_minus_comp_runs_per100').round(2).to_csv(res('comp_strength/transfer_check_batters.csv'), index=False)
