"""S4A(ii): expected-outcome (context-only) model comparison, rolling season-ahead folds.

Batter view, per faced ball: outcome class in {0,1,2,3,4,6,OUT} (5 -> 4, 7+ -> 6; OUT = striker dismissed).
Bowler view, per delivery: runs charged to the bowler (incl. wides/no-balls) and bowler wicket.
Context features only (no player traits): innings, over, ball of innings, wickets down, balls left, runs needed,
required/current rate, score vs par, par_prev (era), venue_dev, elo_diff, knockout, impact era, is_intl.
Families: T0 cell means (innings x over x wickets, the simplest baseline); HGB regressor+classifier (baseline-style);
LightGBM regressor+classifier; LightGBM multinomial over the 7 classes (gives the full outcome mix used for leverage).
Folds: train seasons <= c (all sources), test c+1 on RR-pack balls, c = 2022..2025.
Outputs: v2_results/models/xoutcome_comparison.csv, XOUT_REPORT.md, xout_chosen.json
"""
import json
import time
import lightgbm as lgb
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import log_loss
from common import *

seed_all()
NT = 4
XF = ['innings', 'over', 'legal_before', 'wkts_before', 'balls_left', 'need', 'rrr', 'crr', 'score_vs_par', 'par_prev',
      'venue_dev', 'elo_diff', 'knockout_v2', 'impact_era', 'is_intl']
CLS_RUNS = np.array([0, 1, 2, 3, 4, 6])


def load():
    S = pd.read_parquet(w('wp/state.parquet'))
    B = pd.read_parquet(w('unified/balls.parquet'), columns=['runs_bat', 'striker_out', 'faced', 'bowl_runs', 'bowl_wkt'])
    S = pd.concat([S, B], axis=1)
    S = S[S.innings.isin([1, 2]) & (S.season >= 2019)]
    r = S.runs_bat.clip(0, 6).replace({5: 4})
    S['cls'] = np.where(S.striker_out, 6, np.searchsorted(CLS_RUNS, r)).astype(int)
    S['need'] = S.need.fillna(-1); S['rrr'] = S.rrr.fillna(-1)
    return S


def lgb_reg(X, y):
    return lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=63, min_child_samples=500, subsample=0.7,
                             subsample_freq=1, random_state=SEED, n_jobs=NT, deterministic=True, force_row_wise=True,
                             verbose=-1).fit(X, y)


def lgb_clf(X, y, multi=False):
    return lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=63, min_child_samples=500, subsample=0.7,
                              subsample_freq=1, random_state=SEED, n_jobs=NT, deterministic=True, force_row_wise=True,
                              verbose=-1, **({'objective': 'multiclass'} if multi else {})).fit(X, y)


def cell(d):
    return d.innings.astype(str) + '_' + d.over.clip(1, 20).astype(str) + '_' + d.wkts_before.clip(0, 8).astype(str)


class XModel:
    """fit on faced balls (batter view) and deliveries (bowler view); predict xruns, xout, p(class), xbowl_runs, xbowl_wkt"""

    def __init__(self, fam): self.fam = fam

    def fit(self, d):
        f = d[d.faced]; X = f[XF].values; Xb = d[XF].values
        if self.fam == 'T0_cell_means':
            k = cell(f); self.tr = f.groupby(k).runs_bat.mean(); self.to = f.groupby(k).striker_out.mean()
            kb = cell(d); self.tbr = d.groupby(kb).bowl_runs.mean(); self.tbw = d.groupby(kb).bowl_wkt.mean()
            self.g = (f.runs_bat.mean(), f.striker_out.mean(), d.bowl_runs.mean(), d.bowl_wkt.mean())
        elif self.fam == 'hgb_separate':
            P = dict(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=300, random_state=SEED, early_stopping=False)
            self.r = HistGradientBoostingRegressor(**P).fit(X, f.runs_bat.values)
            self.o = HistGradientBoostingClassifier(**P).fit(X, f.striker_out.values)
            self.br = HistGradientBoostingRegressor(**P).fit(Xb, d.bowl_runs.values)
            self.bw = HistGradientBoostingClassifier(**P).fit(Xb, d.bowl_wkt.values)
        elif self.fam == 'lgbm_separate':
            self.r = lgb_reg(X, f.runs_bat.values); self.o = lgb_clf(X, f.striker_out.values)
            self.br = lgb_reg(Xb, d.bowl_runs.values); self.bw = lgb_clf(Xb, d.bowl_wkt.values)
        elif self.fam == 'lgbm_multiclass':
            self.mc = lgb_clf(X, f.cls.values, multi=True)
            self.rbar = f[f.cls < 6].groupby('cls').runs_bat.mean().reindex(range(6)).fillna(pd.Series(dict(enumerate(CLS_RUNS)))).values
            self.br = lgb_reg(Xb, d.bowl_runs.values); self.bw = lgb_clf(Xb, d.bowl_wkt.values)
        return self

    def predict(self, d):
        X = d[XF].values; out = {}
        if self.fam == 'T0_cell_means':
            k = cell(d)
            out['xruns'] = k.map(self.tr).fillna(self.g[0]).values; out['xout'] = k.map(self.to).fillna(self.g[1]).values
            out['xbowl_runs'] = k.map(self.tbr).fillna(self.g[2]).values; out['xbowl_wkt'] = k.map(self.tbw).fillna(self.g[3]).values
        elif self.fam == 'lgbm_multiclass':
            p = self.mc.predict_proba(X); out['pcls'] = p
            out['xruns'] = p[:, :6] @ self.rbar; out['xout'] = p[:, 6]
            out['xbowl_runs'] = self.br.predict(X); out['xbowl_wkt'] = self.bw.predict_proba(X)[:, 1]
        else:
            out['xruns'] = self.r.predict(X); out['xout'] = self.o.predict_proba(X)[:, 1]
            out['xbowl_runs'] = self.br.predict(X); out['xbowl_wkt'] = self.bw.predict_proba(X)[:, 1]
        return out


FAMS = ['T0_cell_means', 'hgb_separate', 'lgbm_separate', 'lgbm_multiclass']

if __name__ == '__main__':
    t00 = time.time()
    S = load()
    rows = []
    for c in [2022, 2023, 2024, 2025]:
        tr = S[S.season <= c]; te = S[(S.season == c + 1) & S.source.eq('RR')]
        tf = te.faced.values
        for fam in FAMS:
            t0 = time.time(); m = XModel(fam).fit(tr); p = m.predict(te)
            r = dict(cutoff=c, test_season=c + 1, model=fam,
                     bat_runs_mse=np.mean((te.runs_bat.values[tf] - p['xruns'][tf]) ** 2),
                     bat_out_logloss=log_loss(te.striker_out.values[tf], np.clip(p['xout'][tf], 1e-5, 1 - 1e-5)),
                     bowl_runs_mse=np.mean((te.bowl_runs.values - p['xbowl_runs']) ** 2),
                     bowl_wkt_logloss=log_loss(te.bowl_wkt.values, np.clip(p['xbowl_wkt'], 1e-5, 1 - 1e-5)),
                     secs=round(time.time() - t0))
            if 'pcls' in p:
                r['outcome7_logloss'] = log_loss(te.cls.values[tf], p['pcls'][tf], labels=range(7))
            rows.append(r); print(r, flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(res('models/xoutcome_comparison_by_fold.csv'), index=False)
    A = R.groupby('model')[['bat_runs_mse', 'bat_out_logloss', 'bowl_runs_mse', 'bowl_wkt_logloss', 'outcome7_logloss']].mean()
    A = A.loc[FAMS]
    A.round(5).to_csv(res('models/xoutcome_comparison.csv'))
    # choose per target, simpler wins within 0.1% relative
    ch = {}
    for t in ['bat_runs_mse', 'bat_out_logloss', 'bowl_runs_mse', 'bowl_wkt_logloss']:
        best = A[t].min(); ch[t] = next(m for m in FAMS if A.loc[m, t] <= best * 1.001)
    json.dump(ch, open(res('models/xout_chosen.json'), 'w'))
    rel = (A[['bat_runs_mse', 'bat_out_logloss', 'bowl_runs_mse', 'bowl_wkt_logloss']] / A.loc['T0_cell_means', ['bat_runs_mse', 'bat_out_logloss', 'bowl_runs_mse', 'bowl_wkt_logloss']] - 1) * 100
    L = ['# Expected-outcome model comparison (S4A)', '',
         'Context-only models; rolling season-ahead folds (train <= c on all sources, test c+1 on RR-pack balls, c = 2022..2025).', '',
         A.round(5).to_markdown(), '', '% change vs T0 cell means (negative = better):', '', rel.round(2).to_markdown(), '',
         f'- Chosen per target (a simpler family wins if within 0.1%): {ch}.',
         '- The multinomial model also provides the next-ball outcome mix used for the leverage index (S4A iii).']
    open(res('models/XOUT_REPORT.md'), 'w').write('\n'.join(L))
    print('\n'.join(L)); print(f'total {time.time() - t00:.0f}s')
