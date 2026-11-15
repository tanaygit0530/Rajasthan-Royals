"""SupeRR Selector S2 - pressure pipeline.
Stage 1: clean ball-by-ball, build match state, train win-probability models,
compute leverage (pressure) and per-ball batter/bowler WPA + expected-run baselines.
Output: out/balls.pkl
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
U = os.environ.get('DATA_DIR') or (os.path.join(HERE, 'data') if os.path.isdir(os.path.join(HERE, 'data')) else os.path.join(HERE, '..', '02_data'))
U = os.path.join(U, '')
OUT = os.path.join(HERE, 'out') + os.sep
os.makedirs(OUT, exist_ok=True)

import numpy as np, pandas as pd, os
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import brier_score_loss, roc_auc_score, log_loss

# ---- 40-seed averaged gradient boosting: removes run-to-run noise from the random validation split ----
class AvgHGB:
    SEEDS = tuple(range(int(os.environ.get('SEED0', 0)), int(os.environ.get('SEED0', 0)) + int(os.environ.get('N_SEEDS', 40))))
    def __init__(self, kind='clf', **params):
        self.kind, self.params = kind, {k: v for k, v in params.items() if k != 'random_state'}
    def get_params(self):
        return dict(kind=self.kind, **self.params)
    def fit(self, X, y):
        C = HistGradientBoostingClassifier if self.kind == 'clf' else HistGradientBoostingRegressor
        self.models = [C(random_state=s, **self.params).fit(X, y) for s in self.SEEDS]
        return self
    def predict_proba(self, X):
        return np.mean([m.predict_proba(X) for m in self.models], axis=0)
    def predict(self, X):
        return np.mean([m.predict(X) for m in self.models], axis=0)

b = pd.read_csv(U + 'ball_by_ball.csv', low_memory=False)
m = pd.read_csv(U + 'matches.csv')
c = pd.read_csv(U + 'competitions.csv')
m = m.merge(c[['comp_id', 'comp_name', 'match_format']], on='comp_id', how='left')

# ---------- team tiers (opposition strength) ----------
TIER_A = {'India','Australia','England','South Africa','New Zealand','Pakistan','Sri Lanka',
          'West Indies','Afghanistan','Bangladesh','Chennai Super Kings','Mumbai Indians','Rajasthan Royals',
          'Punjab Kings','Royal Challengers Bengaluru','Delhi Capitals','Kolkata Knight Riders',
          'Sunrisers Hyderabad','Gujarat Titans','Lucknow Super Giants'}
TIER_B = {'Ireland','Zimbabwe','Scotland','Netherlands','India A','Pakistan A','Sri Lanka A',
          'Bangladesh A','Afghanistan A'}
teams = pd.read_csv(U + 'teams.csv')[['team_id','team_name']].drop_duplicates('team_id')
tier = {r.team_id: (1 if r.team_name in TIER_A else 2 if r.team_name in TIER_B else 3) for r in teams.itertuples()}
TIER_W = {1: 1.0, 2: 0.75, 3: 0.4}

m['is_ipl'] = m.comp_name.str.startswith('IPL').astype(int)
m['season'] = m.match_date.str[:4].astype(int)
m['knockout'] = (m.knock_out.eq(1) | m.stage.isin(['Final','Qualifier','Eliminator','Semi Final'])).astype(int)

# ---------- cleaning ----------
b = b[b.innings.isin([1, 2])].copy()            # drop super overs
b = b.merge(m[['match_id','win_team_id','revised_target','first_inn_revised_overs','second_inn_revised_overs',
               'is_ipl','season','knockout','match_date','home_team','away_team']], on='match_id', how='inner')
b = b.sort_values(['match_id','innings','overid','over_ball_num']).reset_index(drop=True)
et = b.extras_type.fillna('')
b['is_wide'] = et.eq('wide')
b['is_nb'] = et.isin(['Overstep', 'other'])
b['legal'] = ~(b.is_wide | b.is_nb)
b['faced'] = ~b.is_wide                          # balls faced by batter
b['total'] = b.runs + b.extras1_runs + b.extras_2_runs
# runs charged to bowler: off bat + wides + no-ball penalty (byes/leg-byes excluded)
b['bowl_runs'] = b.runs + np.where(b.is_wide | b.is_nb, b.extras1_runs, 0)
NOT_BOWLER = {'RunOut','Retire Out','Obstracting the field','Obstructing the field'}
b['bowl_wkt'] = b.is_wicket & ~b.dismissal_type.isin(NOT_BOWLER)
b['striker_out'] = b.is_wicket & (b.dismissed_player_id == b.striker_id) & ~b.dismissal_type.eq('Retire Out')

g = b.groupby(['match_id','innings'])
b['score_before'] = g.total.cumsum() - b.total
b['legal_before'] = g.legal.cumsum() - b.legal.astype(int)
b['wkts_before'] = g.is_wicket.cumsum() - b.is_wicket.astype(int)
inn1_tot = b[b.innings == 1].groupby('match_id').total.sum()
b['inn1_total'] = b.match_id.map(inn1_tot)
b['target'] = np.where(b.revised_target.notna(), b.revised_target, b.inn1_total + 1)
b['balls_avail'] = np.where(b.innings == 1, b.first_inn_revised_overs.fillna(120), b.second_inn_revised_overs.fillna(120))
b['tgt_balls'] = b.second_inn_revised_overs.fillna(120)
b['opp_tier'] = np.where(True, b.bowling_team_id.map(tier), 0)
b['bat_tier'] = b.batting_team_id.map(tier)
b['level'] = np.maximum(b.opp_tier, b.bat_tier)  # 1 = both strong
b['bat_won'] = (b.batting_team_id == b.win_team_id).astype(float)
b['has_result'] = b.win_team_id.notna()
b['phase'] = pd.cut(b.overid, [0, 6, 15, 20], labels=['PP', 'Middle', 'Death']).astype(str)
print('balls', len(b), 'matches', b.match_id.nunique())

# ---------- win-probability models ----------
def f2(rn, bl, wk, lvl, ipl):
    bl = np.maximum(bl, 0)
    return np.column_stack([rn, bl, wk, np.clip(rn / np.maximum(bl, 1) * 6, 0, 36), lvl, ipl])
def f1(sc, bl, wk, ba, lvl, ipl):
    bb = np.maximum(ba - bl, 0)
    return np.column_stack([sc, bl, wk, sc / np.maximum(bb, 1) * 6, ba, lvl, ipl])

tr = b[b.has_result].copy()
t2 = tr[tr.innings == 2]
X2 = f2(t2.target - t2.score_before, t2.tgt_balls - t2.legal_before, 10 - t2.wkts_before, t2.level, t2.is_ipl)
t1 = tr[tr.innings == 1]
X1 = f1(t1.score_before, t1.balls_avail - t1.legal_before, 10 - t1.wkts_before, t1.balls_avail, t1.level, t1.is_ipl)
P = dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200, l2_regularization=1.0)
mod2 = AvgHGB('clf', monotonic_cst=[-1, 1, 1, -1, 0, 0], **P)
mod1 = AvgHGB('clf', monotonic_cst=[1, -1, 1, 0, -1, 0, 0], **P); mod1.SEEDS = (0,)  # comparison model only (not used for pressure)

# out-of-fold validation (grouped by match so no leakage)
report = {}
for name, mod, X, y, grp in [('inn2', mod2, X2, t2.bat_won.values, t2.match_id.values),
                             ('inn1', mod1, X1, t1.bat_won.values, t1.match_id.values)]:
    oof = np.zeros(len(y))
    for tri, tei in GroupKFold(5).split(X, y, grp):
        mm = HistGradientBoostingClassifier(random_state=0, **mod.params).fit(X[tri], y[tri]); oof[tei] = mm.predict_proba(X[tei])[:, 1]  # validation only: single seed
    report[name] = dict(auc=roc_auc_score(y, oof), brier=brier_score_loss(y, oof), logloss=log_loss(y, oof),
                        base_brier=brier_score_loss(y, np.full(len(y), y.mean())))
    mod.fit(X, y)
print(pd.DataFrame(report).round(4))
pd.DataFrame(report).to_csv(OUT + 'wp_validation.csv')

# ---- first innings: resources model (expected remaining runs) -> projected target -> chase WP ----
full1 = t1[(t1.balls_avail == 120)]
Xr = np.column_stack([full1.balls_avail - full1.legal_before, 10 - full1.wkts_before, full1.level, full1.is_ipl])
yr = (full1.inn1_total - full1.score_before).values
resm = AvgHGB('reg', monotonic_cst=[1, 1, 0, 0], max_iter=300, learning_rate=0.05,
                                     min_samples_leaf=300).fit(Xr, yr)
resid = yr - resm.predict(Xr)
blb = np.clip((full1.balls_avail - full1.legal_before).values // 12, 0, 10)
sd_tab = pd.Series(resid).groupby(blb).std().reindex(range(11)).interpolate().bfill().values
# lookup of chase-start WP per (target, balls, level, ipl)
TG = np.arange(0, 351)
ZQ = np.linspace(-2.2, 2.2, 23); ZW = np.exp(-ZQ ** 2 / 2); ZW /= ZW.sum()
_cache = {}
def chase_start(tg, tb, lvl, ipl):
    out = np.empty(len(tg))
    for key in set(zip(tb, lvl, ipl)):
        if key not in _cache:
            kb, kl, ki = key
            _cache[key] = mod2.predict_proba(f2(TG, np.full(len(TG), kb), np.full(len(TG), 10),
                                                np.full(len(TG), kl), np.full(len(TG), ki)))[:, 1]
        msk = (tb == key[0]) & (lvl == key[1]) & (ipl == key[2])
        out[msk] = _cache[key][np.clip(np.round(tg[msk]).astype(int), 0, 350)]
    return out

def wp(inn, sc, lb, wk, r):
    """Batting team win prob for a state (score, legal balls bowled, wickets lost) of innings inn."""
    sc, lb, wk = np.asarray(sc, float), np.asarray(lb, float), np.asarray(wk, float)
    if inn == 2:
        need = r.target.values - sc; bl = r.tgt_balls.values - lb; wih = 10 - wk
        p = mod2.predict_proba(f2(need, bl, wih, r.level.values, r.is_ipl.values))[:, 1]
        return np.where(need <= 0, 1.0, np.where((wih <= 0) | (bl <= 0), np.where(need == 1, 0.5, 0.0), p))
    ba = r.balls_avail.values; bl = np.maximum(ba - lb, 0); wih = np.maximum(10 - wk, 0)
    # scale remaining-resources for reduced-overs innings via balls left
    rem = np.where((bl <= 0) | (wih <= 0), 0.0,
                   resm.predict(np.column_stack([bl, wih, r.level.values, r.is_ipl.values])))
    sd = np.where(rem > 0, sd_tab[np.clip(bl // 12, 0, 10).astype(int)], 0.0)
    tb, lv, ip = r.tgt_balls.values.astype(int), r.level.values.astype(int), r.is_ipl.values.astype(int)
    p = np.zeros(len(sc))
    for z, w in zip(ZQ, ZW):
        p += w * (1 - chase_start(sc + rem + z * sd + 1, tb, lv, ip))
    return p

# validation of the composed first-innings WP (in-sample resources model, AUC on outcome)
_p1 = wp(1, t1.score_before.values, t1.legal_before.values, t1.wkts_before.values, t1)
report['inn1_resources'] = dict(auc=roc_auc_score(t1.bat_won, _p1), brier=brier_score_loss(t1.bat_won, _p1),
                                logloss=log_loss(t1.bat_won, np.clip(_p1, 1e-4, 1 - 1e-4)),
                                base_brier=brier_score_loss(t1.bat_won, np.full(len(t1), t1.bat_won.mean())))
print(pd.DataFrame(report).round(4)); pd.DataFrame(report).to_csv(OUT + 'wp_validation.csv')

# ---------- per-ball WP, leverage, attributable WPA ----------
OUTC = [(0, 0), (1, 0), (2, 0), (4, 0), (6, 0), (0, 1)]  # (runs, wicket)
parts = []
for inn in (1, 2):
    r = b[b.innings == inn].copy()
    sc, lb, wk = r.score_before.values, r.legal_before.values, r.wkts_before.values
    wp0 = wp(inn, sc, lb, wk, r)
    # empirical outcome mix by phase & innings (legal balls)
    L = b[(b.innings == inn) & b.legal]
    oc = np.select([L.is_wicket, L.total >= 6, L.total >= 4, L.total >= 2, L.total == 1], [5, 4, 3, 2, 1], 0)
    mix = pd.crosstab(L.phase, oc, normalize='index')
    li = np.zeros(len(r))
    for k, (rr, w) in enumerate(OUTC):
        pk = r.phase.map(mix[k]).values
        li += pk * np.abs(wp(inn, sc + rr, lb + 1, wk + w, r) - wp0)
    # batter-attributable: bat runs + striker dismissal; bowler: bowl runs + bowler wicket
    nlb = lb + r.legal.values
    wp_bat = wp(inn, sc + r.runs.values + np.where(r.is_wide | r.is_nb, 1, 0), nlb, wk + r.striker_out.values, r)
    wp_bowl = wp(inn, sc + r.bowl_runs.values, nlb, wk + r.bowl_wkt.values, r)
    r['wp_before'] = wp0; r['li_raw'] = li
    # batter WPA excludes the extras-penalty run on no-balls (credited to bowler, not batter): subtract it back out
    wp_nb_only = wp(inn, sc + np.where(r.is_wide | r.is_nb, 1, 0), lb, wk, r)  # reference = before the ball (+nb penalty)
    r['bat_wpa'] = np.where(r.faced, wp_bat - wp_nb_only, 0.0)
    r['bowl_wpa'] = -(wp_bowl - wp0)   # positive = good for bowler
    parts.append(r)
b = pd.concat(parts).sort_index()
b['LI'] = b.li_raw / b.loc[b.legal, 'li_raw'].mean()
b['PI'] = b.LI * np.where(b.knockout == 1, 1.2, 1.0)    # pressure index

# ---------- expected-run / dismissal baselines (context, not player) ----------
ctx = ['innings', 'overid', 'wkts_before', 'level', 'is_ipl', 'pace']
b['pace'] = (b.pace_or_spin == 'Pace').astype(int)
F = b[b.faced]
Xc = F[ctx].values
reg = AvgHGB('reg', max_iter=200, learning_rate=0.05, min_samples_leaf=300).fit(Xc, F.runs.values)
clf = AvgHGB('clf', max_iter=200, learning_rate=0.05, min_samples_leaf=300).fit(Xc, F.striker_out.values)
b['xruns'] = 0.0; b['xout'] = 0.0
b.loc[b.faced, 'xruns'] = reg.predict(Xc); b.loc[b.faced, 'xout'] = clf.predict_proba(Xc)[:, 1]
Bw = b
Xb = Bw[ctx].values
b['xbowl_runs'] = AvgHGB('reg', max_iter=200, learning_rate=0.05, min_samples_leaf=300).fit(Xb, Bw.bowl_runs.values).predict(Xb)
L = b.legal
clfw = AvgHGB('clf', max_iter=200, learning_rate=0.05, min_samples_leaf=300).fit(b.loc[L, ctx].values, b.loc[L, 'bowl_wkt'].values)
b['xbowl_wkt'] = np.where(L, clfw.predict_proba(Xb)[:, 1], 0.0)

# ---------- weights ----------
REC = {2022: 0.6, 2023: 0.7, 2024: 0.8, 2025: 0.9, 2026: 1.0}
b['w_rec'] = b.season.map(REC)
b['w_bat'] = b.w_rec * b.bowling_team_id.map(tier).map(TIER_W)   # batter judged on bowling quality faced
b['w_bowl'] = b.w_rec * b.batting_team_id.map(tier).map(TIER_W)  # bowler judged on batting quality faced
b.to_pickle(OUT + 'balls.pkl')
print('saved', b.shape)
