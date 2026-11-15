"""S4D (ii): ablation and fairness, both judged OUT OF TIME on the S4B folds (train <= c, score season c+1).

Ablations of the final model (hierarchical Bayes overall skill, theta):
  full | no APM prior (public data + competition adjustment off) | APM from RR-pack matches only (no public data)
  | no age curve | + pressure-specific effect (theta + delta)
Fairness: residuals of the full model (target minus fold-calibrated prediction) by player group - IPL-heavy
(>= 70% of RR balls in IPL), T20I/A-team-heavy (<= 30%), mixed - and by public-data volume. A fair model has
group mean residuals near zero.
Outputs: v2_results/models/ablation.csv, fairness.csv
"""
from common import *
import skill as K

seed_all()
P = pd.read_parquet(w('unified/players.parquet')); ROLE_T = pd.read_parquet(w('unified/roles.parquet'))


def wcorr(a, b, w_):
    m = np.isfinite(a) & np.isfinite(b); a, b, w_ = a[m], b[m], w_[m]
    am, bm = np.average(a, weights=w_), np.average(b, weights=w_)
    return np.sum(w_ * (a - am) * (b - bm)) / np.sqrt(np.sum(w_ * (a - am) ** 2) * np.sum(w_ * (b - bm) ** 2))


def target(V, c, role, minb=30):
    d = K.role_view(V[(V.season == c + 1) & V.source.eq('RR')], role)
    t = d[d.pres == 1].groupby('pid').rv.agg(['mean', 'size']).rename(columns={'mean': 'y', 'size': 'yn'})
    return t[t.yn >= minb]


abl, fair, cover = [], [], []
for role in ['bat', 'bowl']:
    for c in [2022, 2023, 2024, 2025]:
        V = pd.read_parquet(w(f'values/ball_values_{c}.parquet')); V, _ = K.add_flags(V, c)
        A = K.apm(c); Ar = K.apm(c, src='rr'); Ac = K.apm(c, src='cs')
        F0 = K.features(V, c, role, A, P, ROLE_T)
        T = target(V, c, role)
        col = 'apm_bat_rv' if role == 'bat' else 'apm_bowl_rv'
        nocs = Ac['apm_bat_n' if role == 'bat' else 'apm_bowl_n'].reindex(F0.index).fillna(0) == 0
        # all variants below use no age curve except 'full' (the age curve was dropped by the first ablation round)
        variants = {'full': F0.copy(), 'no APM prior (no public data, no competition adjustment)': F0.assign(M6_apm=0.0, age=28.0),
                    'APM from RR-pack only (no public data)': F0.assign(M6_apm=Ar[col].reindex(F0.index), age=28.0),
                    'no age curve': F0.assign(age=28.0),
                    'public-only APM prior (no double counting)': F0.assign(M6_apm=Ac[col].reindex(F0.index).where(~nocs, 0.0), age=28.0)}
        preds = {}
        for name, F in variants.items():
            F['M6_apm'] = F.M6_apm.fillna(F.M6_apm.median()) if F.M6_apm.notna().any() else 0.0
            th, de, _ = K.bayes_fit(F, F0.attrs['var_ball'], draws=800, warm=800)
            preds[name] = pd.Series(th.mean(0), index=F.index)
            if name == 'full':
                preds['full + pressure-specific effect'] = pd.Series((th + de).mean(0), index=F.index)
            if name.startswith('public-only'):
                E0 = F[F.all_n >= 60].join(T, how='inner'); ix = [F.index.get_loc(p_) for p_ in E0.index]
                sd_noise = np.sqrt(F0.attrs['var_ball'] / E0.yn.values)
                rng_ = np.random.default_rng(SEED)
                pp = th[:, ix] + de.mean() + rng_.normal(0, 1, (th.shape[0], len(ix))) * sd_noise
                lo, hi = np.percentile(pp, 10, 0), np.percentile(pp, 90, 0)
                cover.append(dict(role=role, cutoff=c, coverage_80=float(np.mean((E0.y.values >= lo) & (E0.y.values <= hi))), n=len(E0)))
        E = F0[F0.all_n >= 60].join(T, how='inner')
        for name, p in preds.items():
            abl.append(dict(role=role, cutoff=c, variant=name, wcorr=wcorr(p.reindex(E.index).values, E.y.values, E.yn.values.astype(float)), n=len(E)))
        # fairness on the full model
        pf = preds['full'].reindex(E.index).values
        cal = np.polyfit(pf, E.y.values, 1, w=np.sqrt(E.yn.values))
        E = E.assign(resid=(E.y - np.polyval(cal, pf)) * 100,
                     group=np.select([E.ipl_share >= 0.7, E.ipl_share <= 0.3], ['IPL-heavy', 'T20I/A-team-heavy'], 'mixed'),
                     pub=np.where(E.pub_n >= E.all_n, 'more public-league balls than RR balls', 'mostly RR-pack balls'))
        for gcol in ['group', 'pub']:
            for g, d in E.groupby(gcol):
                fair.append(dict(role=role, cutoff=c, grouping=gcol, group=g, n=len(d),
                                 mean_resid_per100=np.average(d.resid, weights=d.yn), sd=d.resid.std()))
        print(role, c, {k: round(v['wcorr'], 3) for k, v in zip(preds, abl[-len(preds):])}, flush=True)
A_ = pd.DataFrame(abl); F_ = pd.DataFrame(fair)
A_.round(4).to_csv(res('models/ablation_by_fold.csv'), index=False)
F_.round(3).to_csv(res('models/fairness_by_fold.csv'), index=False)
a = A_.groupby(['role', 'variant']).wcorr.agg(['mean', 'std']).round(3)
f = F_.groupby(['role', 'grouping', 'group']).apply(lambda d: pd.Series({'players_total': d.n.sum(),
     'mean_resid_per100': np.average(d.mean_resid_per100, weights=d.n),
     'se': np.sqrt(np.sum((d.n * d.sd) ** 2 / np.maximum(d.n, 1))) / d.n.sum()}), include_groups=False).round(2)
a.to_csv(res('models/ablation.csv')); f.to_csv(res('models/fairness.csv'))
pd.DataFrame(cover).to_csv(res('models/interval_coverage.csv'), index=False)
print(pd.DataFrame(cover).to_string())
print(a.to_string()); print(f.to_string())
