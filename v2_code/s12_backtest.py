"""S4B + S4C: player-skill model comparison on NEXT-SEASON pressure performance (rolling, no leakage), and the
'is clutch repeatable?' test.

For cutoff c = 2022..2025: features from seasons <= c (ball values from models fitted on <= c, APM ridge refit on
<= c); target = mean run value per pressure ball in season c+1 on RR-pack balls (players with >= 30 such balls).
Models:
  M0 raw pressure mean | M1 recency-weighted raw | M2 baseline composite (03_code/ratings.py logic)
  M3 EB-shrunk pressure mean | M4 EB overall, NO pressure term | M5 M4 + EB-shrunk pressure gap
  M6 ridge APM (all competitions; competition, venue, opponent adjusted) | M7 linear stack (trained on earlier folds)
  M8 hierarchical Bayesian (NumPyro): overall skill with APM + age-curve prior, plus a partially pooled pressure effect
Metrics: ball-weighted correlation, Spearman, MSE (models in run-value units; M2 is a score so MSE after a linear
calibration on the previous fold), top-10 hit rate, vs the noise ceiling (split-half reliability of the target).
Survivorship: dropout by predicted decile, inverse-probability-of-retention weighted correlation, all-competition target.
Clutch (S4C): reliability of the pressure gap; M5 vs M4 and the posterior sig_d in M8.
Outputs: v2_results/models/skill_backtest_*.csv, SKILL_REPORT.md; v2_work/skill/bt_{role}.parquet
"""
import sys
import json
import time
from scipy.stats import spearmanr
from common import *
import skill as K

seed_all()
ROLES = sys.argv[1:] or ['bat', 'bowl']
P = pd.read_parquet(w('unified/players.parquet'))
ROLE_T = pd.read_parquet(w('unified/roles.parquet'))
MODELS = ['M0_raw_pressure', 'M1_recency_raw', 'M2_baseline', 'M3_eb_pressure', 'M4_eb_overall', 'M5_eb_overall_plus_gap',
          'M6_apm', 'M7_stack', 'M8_bayes']
STACK_X = {'bat': ['M3_eb_pressure', 'M4_eb_overall', 'gap_eb', 'M6_apm', 'age', 'age2', 'log_n'],
           'bowl': ['M3_eb_pressure', 'M4_eb_overall', 'gap_eb', 'M6_apm', 'age', 'age2', 'log_n', 'dot_rate']}


def wcorr(a, b, w_):
    m = np.isfinite(a) & np.isfinite(b); a, b, w_ = a[m], b[m], w_[m]
    am, bm = np.average(a, weights=w_), np.average(b, weights=w_)
    return np.sum(w_ * (a - am) * (b - bm)) / np.sqrt(np.sum(w_ * (a - am) ** 2) * np.sum(w_ * (b - bm) ** 2))


def target(V, c, role, src='RR', minb=30):
    d = K.role_view(V[V.season == c + 1], role)
    if src == 'RR':
        d = d[d.source.eq('RR')]
    d = d[d.pres == 1].assign(h=lambda z: z.match_id.factorize()[0] % 2)
    t = d.groupby('pid').rv.agg(['mean', 'size']).rename(columns={'mean': 'y', 'size': 'yn'})
    hh = d.groupby(['pid', 'h']).rv.mean().unstack()
    t = t[t.yn >= minb]
    hh = hh.reindex(t.index).dropna()
    r = hh.corr().iloc[0, 1]
    return t, 2 * r / (1 + r)


def prep(F):
    F = F.copy()
    F['age'] = F.age.fillna(F.age.median()); F['age2'] = (F.age - 28) ** 2
    F['log_n'] = np.log1p(F.all_n)
    if 'dot_rate' in F:
        F['dot_rate'] = F.dot_rate.fillna(F.dot_rate.median())
    F['M6_apm'] = F.M6_apm.fillna(F.M6_apm.median())
    return F


for role in ROLES:
    t00 = time.time()
    rows, store, ret_rows, clutch = [], [], [], []
    hist = []   # (features, target) of earlier folds for the stack
    for c in [2022, 2023, 2024, 2025]:
        V = pd.read_parquet(w(f'values/ball_values_{c}.parquet'))
        V, thr = K.add_flags(V, c)
        A = K.apm(c)
        F = prep(K.features(V, c, role, A, P, ROLE_T))
        F['M2_baseline'] = K.baseline_composite(V, c, role).reindex(F.index)
        th, de, summ = K.bayes_fit(F, F.attrs['var_ball'])
        F['M8_bayes'] = (th + de).mean(0)
        F['M8_theta'] = th.mean(0); F['M8_delta'] = de.mean(0)
        clutch.append(dict(role=role, cutoff=c, **{f'post_{k}_mean': v[0] for k, v in summ.items()},
                           **{f'post_{k}_sd': v[1] for k, v in summ.items()}, k_gap=F.attrs['kg'], tau2_gap=F.attrs['tau2g'],
                           var_ball=F.attrs['var_ball']))
        T, rel_t = target(V, c, role)
        Ta, rel_ta = target(V, c, role, src='all')
        E = F.join(T, how='inner')
        E = E[E.all_n >= 60]
        # stack: fit on earlier folds' pairs (weighted by target balls)
        if hist:
            H = pd.concat(hist)
            Xh = H[STACK_X[role]].values; mu_, sd_ = Xh.mean(0), Xh.std(0) + 1e-9
            from sklearn.linear_model import Ridge
            st = Ridge(alpha=1.0).fit((Xh - mu_) / sd_, H.y.values, sample_weight=H.yn.values)
            E['M7_stack'] = st.predict((E[STACK_X[role]].values - mu_) / sd_)
            F['M7_stack'] = st.predict((F[STACK_X[role]].values - mu_) / sd_)
            cal = np.polyfit(H.M2_baseline.values, H.y.values, 1, w=np.sqrt(H.yn.values))
            E['M2_cal'] = np.polyval(cal, E.M2_baseline)
        else:
            E['M7_stack'] = np.nan; E['M2_cal'] = np.nan
        hist.append(E.assign(cutoff=c))
        w_ = E.yn.values.astype(float)
        obs_top = set(E.y.sort_values(ascending=False).head(10).index)
        for m in MODELS:
            p = E[m].values.astype(float)
            if not np.isfinite(p).any():
                continue
            pm = E['M2_cal'].values if m == 'M2_baseline' else p
            top = set(E[m].sort_values(ascending=False).head(10).index)
            rows.append(dict(role=role, cutoff=c, test_season=c + 1, model=m, n_players=len(E), wcorr=wcorr(p, E.y.values, w_),
                             spearman=spearmanr(p, E.y.values, nan_policy='omit')[0],
                             mse=np.average((E.y.values - pm) ** 2, weights=w_) if np.isfinite(pm).any() else np.nan,
                             top10_hit=len(top & obs_top) / 10, target_reliability=rel_t,
                             noise_ceiling_r=np.sqrt(max(rel_t, 0))))
        rows.append(dict(role=role, cutoff=c, test_season=c + 1, model='zero (league average)', n_players=len(E), wcorr=np.nan,
                         spearman=np.nan, mse=np.average(E.y.values ** 2, weights=w_), top10_hit=np.nan,
                         target_reliability=rel_t, noise_ceiling_r=np.sqrt(max(rel_t, 0))))
        # all-competition next-season target (players dropped from IPL often still play elsewhere)
        Ea = F.join(Ta, how='inner'); Ea = Ea[Ea.all_n >= 60]
        for m in ['M4_eb_overall', 'M5_eb_overall_plus_gap', 'M6_apm', 'M8_bayes', 'M3_eb_pressure']:
            ret_rows.append(dict(role=role, cutoff=c, model=m, kind='all_competitions_target',
                                 wcorr=wcorr(Ea[m].values, Ea.y.values, Ea.yn.values.astype(float)), n=len(Ea)))
        # survivorship: who with >= 60 pressure balls by c plays (>= 1 RR pressure ball) in c+1?
        pool = F[F.p_n >= 60].copy()
        nxt = set(K.role_view(V[(V.season == c + 1) & V.source.eq('RR')], role).pid)
        pool['retained'] = pool.index.isin(nxt).astype(int)
        pool['dec'] = pd.qcut(pool.M8_bayes.rank(method='first'), 5, labels=False)
        for dq, g in pool.groupby('dec'):
            ret_rows.append(dict(role=role, cutoff=c, model='M8_bayes', kind=f'retention_quintile_{dq + 1}', wcorr=g.retained.mean(), n=len(g)))
        from sklearn.linear_model import LogisticRegression
        lr = LogisticRegression().fit(pool[['M8_bayes', 'age']].values, pool.retained.values)
        pr = pd.Series(lr.predict_proba(pool[['M8_bayes', 'age']].values)[:, 1], index=pool.index)
        Ei = E[E.index.isin(pool.index)]
        if len(Ei) > 20:
            ipw = Ei.yn.values / pr.reindex(Ei.index).clip(0.2).values
            for m in ['M3_eb_pressure', 'M4_eb_overall', 'M5_eb_overall_plus_gap', 'M6_apm', 'M8_bayes']:
                ret_rows.append(dict(role=role, cutoff=c, model=m, kind='ipw_weighted', wcorr=wcorr(Ei[m].values, Ei.y.values, ipw), n=len(Ei)))
        store.append(F.assign(cutoff=c).join(T, how='left'))
        print(role, c, 'n eval', len(E), 'target rel', round(rel_t, 3), f'{time.time() - t00:.0f}s', flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(res(f'models/skill_backtest_{role}_by_fold.csv'), index=False)
    pd.DataFrame(ret_rows).to_csv(res(f'models/skill_survivorship_{role}.csv'), index=False)
    pd.DataFrame(clutch).to_csv(res(f'models/clutch_{role}.csv'), index=False)
    S = pd.concat(store); S.index.name = 'pid'
    S.reset_index().to_parquet(w(f'skill/bt_{role}.parquet'), index=False)
    print(R.groupby('model')[['wcorr', 'spearman', 'mse', 'top10_hit', 'noise_ceiling_r']].mean().round(4).to_string())
