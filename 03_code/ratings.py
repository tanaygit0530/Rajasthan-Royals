"""Stage 2: player pressure ratings from player-match aggregates; shrinkage, bootstrap, reliability, sensitivity."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
U = os.environ.get('DATA_DIR') or (os.path.join(HERE, 'data') if os.path.isdir(os.path.join(HERE, 'data')) else os.path.join(HERE, '..', '02_data'))
U = os.path.join(U, '')
OUT = os.path.join(HERE, 'out') + os.sep
os.makedirs(OUT, exist_ok=True)

import numpy as np, pandas as pd
B = pd.read_pickle(OUT + 'balls.pkl')
mp = pd.read_csv(U + 'competition_team_player_mapping.csv')
NAME = mp.drop_duplicates('player_id', keep='last').set_index('player_id').player_name
IPL26 = mp[mp.comp_id == 3298].drop_duplicates('player_id').set_index('player_id').team_name
COMP = ['x_main', 'x_rae', 'x_surv']

def ball_frame(B, role, recency=True):
    if role == 'bat':
        d = B[B.faced].copy(); d['pid'] = d.striker_id; d['w'] = d.w_bat if recency else d.w_bat / d.w_rec
        d['x_main'] = d.bat_wpa * 100; d['x_rae'] = (d.runs - d.xruns) * 100
        d['x_surv'] = (d.xout - d.striker_out) * 100
        d['bx_runs'] = d.runs; d['bx_out'] = d.striker_out.astype(int); d['bx_bnd'] = (d.is_four | d.is_six).astype(int)
        d['bx_dot'] = (d.runs == 0).astype(int); d['bx_ball'] = 1
    else:
        d = B[B.legal | B.is_wide | B.is_nb].copy(); d['pid'] = d.bowler_id
        d['w'] = d.w_bowl if recency else d.w_bowl / d.w_rec
        d['x_main'] = d.bowl_wpa * 100; d['x_rae'] = (d.xbowl_runs - d.bowl_runs) * 100
        d['x_surv'] = (d.bowl_wkt.astype(float) - d.xbowl_wkt) * 100
        d['bx_runs'] = d.bowl_runs; d['bx_out'] = d.bowl_wkt.astype(int); d['bx_bnd'] = (d.is_four | d.is_six).astype(int)
        d['bx_dot'] = (d.legal & (d.bowl_runs == 0)).astype(int); d['bx_ball'] = d.legal.astype(int)
    return d

def pm_table(d, thr):
    """player x match x pressure-flag sums"""
    d = d.assign(pres=(d.PI >= thr).astype(int))
    for c in COMP:
        d[c + '_w'] = d[c] * d.w; d[c + '_w2'] = d[c] ** 2 * d.w
    aggs = {c: 'sum' for c in [x + s for x in COMP for s in ['_w', '_w2']] + ['w', 'bx_runs', 'bx_out', 'bx_bnd', 'bx_dot', 'bx_ball']}
    g = d.groupby(['pid', 'match_id', 'pres']).agg({**aggs, 'season': 'first', 'is_ipl': 'first', 'x_main': ['sum', 'size']})
    g.columns = [a if b in ('sum', 'first') and a != 'x_main' else f'{a}_{b}' for a, b in g.columns]
    return g.reset_index()

def reliability_k(pm, c, pres, ids):
    """split-half (odd/even match) reliability of per-ball weighted mean -> shrinkage constant k (balls)."""
    x = pm[(pm.pres == pres) & pm.pid.isin(ids)].assign(h=lambda d: d.match_id % 2)
    h = x.groupby(['pid', 'h'])[[c + '_w', 'w']].sum()
    hm = (h[c + '_w'] / h.w).unstack().dropna()
    r = hm.corr().iloc[0, 1]
    rel = 2 * r / (1 + r) if r > 0 else 0.0
    nbar = x.groupby('pid').w.sum().median()
    k = nbar * (1 - rel) / rel if rel > 0.02 else 1e4
    return float(np.clip(k, 20, 1e4)), float(r), float(rel)

def metrics(pm, ids=None, kfix=None):
    """pm: player-match rows (possibly resampled). Returns per-player metric frame + fitted constants."""
    if ids is not None: pm = pm[pm.pid.isin(ids)]
    P, N = pm[pm.pres == 1], pm[pm.pres == 0]
    sP, sN = P.groupby('pid').sum(numeric_only=True), N.groupby('pid').sum(numeric_only=True)
    idx = sP.index if ids is None else pd.Index(ids)
    sP, sN = sP.reindex(idx).fillna(0), sN.reindex(idx).fillna(0)
    o = pd.DataFrame(index=idx); K = {} if kfix is None else kfix
    for c in COMP:
        rawP = sP[c + '_w'] / sP.w; rawN = sN[c + '_w'] / sN.w
        if kfix is None:
            K[c + '_kn'], K[c + '_rn'], K[c + '_reln'] = reliability_k(pm, c, 0, idx)
            K[c + '_kp'], K[c + '_rp'], K[c + '_relp'] = reliability_k(pm, c, 1, idx)
            K[c + '_mun'] = sN[c + '_w'].sum() / sN.w.sum()
        nest = (sN[c + '_w'] + K[c + '_kn'] * K[c + '_mun']) / (sN.w + K[c + '_kn'])
        if kfix is None:  # prior for pressure = regression of pressure raw on normal estimate
            wts = sP.w.values; X = np.column_stack([np.ones(len(idx)), nest.values])
            beta = np.linalg.lstsq(X * np.sqrt(wts)[:, None], rawP.values * np.sqrt(wts), rcond=None)[0]
            K[c + '_a'], K[c + '_b'] = float(beta[0]), float(beta[1])
            K[c + '_sdraw'] = float(rawP.std())
        prior = K[c + '_a'] + K[c + '_b'] * nest
        o[c] = (sP[c + '_w'] + K[c + '_kp'] * prior) / (sP.w + K[c + '_kp'])
        o[c + '_n'] = nest; o[c + '_raw'] = rawP
    o['delta'] = o.x_rae - o.x_rae_n
    if kfix is None: K['delta_sdraw'] = float((o.x_rae_raw - (sN.x_rae_w / sN.w)).std())
    sp = P[P.x_main_size >= 6]
    pos = (sp.x_main_sum > 0).groupby(sp.pid).agg(['sum', 'count']).reindex(idx).fillna(0)
    if kfix is None:
        K['mu_c'] = float(pos['sum'].sum() / max(pos['count'].sum(), 1))
        K['consistency_sdraw'] = float((pos['sum'] / pos['count'].replace(0, np.nan) * 100).std())
    o['consistency'] = (pos['sum'] + 10 * K['mu_c']) / (pos['count'] + 10) * 100
    o['spells'] = pos['count']; o['pos_spells'] = pos['sum']
    o['p_balls'] = sP.bx_ball; o['p_w'] = sP.w; o['n_balls'] = sN.bx_ball
    o['p_matches'] = P.groupby('pid').match_id.nunique().reindex(idx)
    o['p_runs'] = sP.bx_runs; o['p_outs'] = sP.bx_out; o['p_bnd'] = sP.bx_bnd; o['p_dot'] = sP.bx_dot
    o['n_runs'] = sN.bx_runs; o['n_outs'] = sN.bx_out
    o['ipl_share'] = (P.is_ipl * P.bx_ball).groupby(P.pid).sum().reindex(idx) / sP.bx_ball
    o['last_season'] = pm.groupby('pid').season.max().reindex(idx)
    return o, K

W = {'x_main': 0.35, 'x_rae': 0.20, 'x_surv': 0.15, 'consistency': 0.15, 'delta': 0.15}
def score(t, K, W=W, ref=None):
    """weighted sum of components, each centred on the pool and scaled by the RAW (unshrunk) spread,
    so a component the data cannot measure reliably is pulled together and contributes little."""
    ref = t if ref is None else ref
    return sum(wt * (t[c] - ref[c].mean()) / K[(c + '_sdraw') if c in ('delta', 'consistency') else c + '_sdraw'] for c, wt in W.items())

def run(role, thr_q=0.75, recency=True, min_p=150, Wt=W, boot=0, quiet=False):
    d = ball_frame(B, role, recency)
    thr = B.loc[B.legal, 'PI'].quantile(thr_q)
    pm = pm_table(d, thr)
    allm, _ = metrics(pm)
    elig = allm[(allm.p_balls >= min_p) & (allm.last_season >= 2025)].index
    pmE = pm[pm.pid.isin(elig)]
    t, ks = metrics(pmE)
    t['rating'] = score(t, ks, Wt)
    t = t.sort_values('rating', ascending=False); t['rank'] = np.arange(1, len(t) + 1)
    t['name'] = t.index.map(NAME); t['ipl26'] = t.index.map(IPL26)
    if boot:
        # fix shrinkage constants & pool reference so bootstrap measures player-level noise only
        kfix = ks
        rng = np.random.default_rng(11)
        g = {p: x for p, x in pmE.groupby('pid')}
        mids = {p: x.match_id.unique() for p, x in g.items()}
        ids = t.index.values; S = np.zeros((boot, len(ids)))
        for r in range(boot):
            parts = []
            for p in ids:
                pick = rng.choice(mids[p], len(mids[p]))
                cnt = pd.Series(pick).value_counts()
                x = g[p][g[p].match_id.isin(cnt.index)]
                parts.append(x.loc[x.index.repeat(x.match_id.map(cnt).values)])
            tb, _ = metrics(pd.concat(parts), ids=ids, kfix=kfix)
            S[r] = score(tb, ks, Wt, ref=t).values
        R = (-S).argsort(1).argsort(1) + 1
        t['p_top10'] = (R <= 10).mean(0)
        t['rank_lo'] = np.percentile(R, 10, axis=0).round().astype(int)
        t['rank_hi'] = np.percentile(R, 90, axis=0).round().astype(int)
        t['rating_lo'] = np.percentile(S, 10, axis=0); t['rating_hi'] = np.percentile(S, 90, axis=0)
    if not quiet: print(role, 'thr', round(thr, 3), 'eligible', len(t)); print({k: round(v, 3) for k, v in ks.items()})
    return t, pm, ks, thr

if __name__ == '__main__':
    import sys
    nb = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    for role in ['bat', 'bowl']:
        t, pm, ks, thr = run(role, boot=nb)
        t.to_pickle(OUT + f'{role}_table.pkl'); pm.to_pickle(OUT + f'{role}_pm.pkl')
        cols = ['rank', 'name', 'ipl26', 'p_balls', 'p_matches', 'rating', 'x_main', 'x_rae', 'x_surv', 'consistency', 'delta'] + \
               (['p_top10', 'rank_lo', 'rank_hi'] if nb else [])
        print(t[cols].head(25).round(2).to_string())
