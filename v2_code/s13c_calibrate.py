"""S4D (iii): calibrate the width of the skill intervals out of time.

The 80% intervals of the first final model covered only ~68-74% of next-season outcomes in the backtest (s13b). Here we
refit the FINAL configuration (s13_final.FINAL) on each fold c = 2022..2025 and find a single widening factor w per role
such that 80% posterior-predictive intervals cover 80% of next-season pressure run values:
    predictive draw = mean_theta + w x (theta_draw - mean_theta) + d0 + ball-level noise / sqrt(target balls)
w = 1 means the model's own uncertainty was right. s13_final applies w to every interval and to P(top 10).
Outputs: v2_results/models/interval_calibration.json, interval_calibration_by_fold.csv
"""
import json
from common import *
import skill as K
import s13_final as F13

seed_all()
P = pd.read_parquet(w('unified/players.parquet')); ROLE_T = pd.read_parquet(w('unified/roles.parquet'))
rows, store = [], {'bat': [], 'bowl': []}
for role in ['bat', 'bowl']:
    cfg = F13.FINAL[role]
    for c in [2022, 2023, 2024, 2025]:
        V = pd.read_parquet(w(f'values/ball_values_{c}.parquet')); V, _ = K.add_flags(V, c)
        A = K.apm(c, src=cfg['apm_src'] or 'all')
        F = K.features(V, c, role, A, P, ROLE_T)
        F['age'] = F.age if cfg['use_age'] else 28.0
        if cfg['apm_src'] is None:
            F['M6_apm'] = 0.0
        elif cfg['apm_src'] == 'cs':
            nb = A['apm_bat_n' if role == 'bat' else 'apm_bowl_n'].reindex(F.index).fillna(0)
            F['M6_apm'] = F.M6_apm.where(nb > 0, 0.0)
        F['M6_apm'] = F.M6_apm.fillna(F.M6_apm.median()) if F.M6_apm.notna().any() else 0.0
        th, de, summ = K.bayes_fit(F, F.attrs['var_ball'], draws=1000, warm=1000)
        d = K.role_view(V[(V.season == c + 1) & V.source.eq('RR')], role)
        T = d[d.pres == 1].groupby('pid').rv.agg(['mean', 'size']).rename(columns={'mean': 'y', 'size': 'yn'})
        T = T[T.yn >= 30]
        E = F[F.all_n >= 60].join(T, how='inner')
        ix = [F.index.get_loc(p) for p in E.index]
        store[role].append(dict(th=th[:, ix], d0=summ['d0'][0], noise=np.sqrt(F.attrs['var_ball'] / E.yn.values), y=E.y.values, cutoff=c))
        print(role, c, len(E), flush=True)


def coverage(role, wf, rng):
    hit = n = 0
    for s in store[role]:
        mu = s['th'].mean(0)
        pp = mu + wf * (s['th'] - mu) + s['d0'] + rng.normal(0, 1, s['th'].shape) * s['noise']
        lo, hi = np.percentile(pp, 10, 0), np.percentile(pp, 90, 0)
        hit += np.sum((s['y'] >= lo) & (s['y'] <= hi)); n += len(s['y'])
    return hit / n


cal = {}
for role in ['bat', 'bowl']:
    grid = np.round(np.arange(1.0, 6.01, 0.25), 2)
    cov = [coverage(role, g, np.random.default_rng(SEED)) for g in grid]
    for g, cv in zip(grid, cov):
        rows.append(dict(role=role, widen=g, coverage_80=cv))
    ok = [g for g, cv in zip(grid, cov) if cv >= 0.80]
    cal[role] = dict(widen=float(ok[0]) if ok else float(grid[-1]), coverage_before=float(cov[0]),
                     coverage_after=float(cov[grid.tolist().index(ok[0])] if ok else cov[-1]))
    for s in store[role]:   # per-fold coverage at the chosen factor
        rng = np.random.default_rng(SEED)
        mu = s['th'].mean(0); pp = mu + cal[role]['widen'] * (s['th'] - mu) + s['d0'] + rng.normal(0, 1, s['th'].shape) * s['noise']
        lo, hi = np.percentile(pp, 10, 0), np.percentile(pp, 90, 0)
        rows.append(dict(role=role, widen=cal[role]['widen'], cutoff=s['cutoff'], coverage_80=float(np.mean((s['y'] >= lo) & (s['y'] <= hi)))))
pd.DataFrame(rows).round(4).to_csv(res('models/interval_calibration_by_fold.csv'), index=False)
json.dump(cal, open(res('models/interval_calibration.json'), 'w'), indent=1)
print(cal)
