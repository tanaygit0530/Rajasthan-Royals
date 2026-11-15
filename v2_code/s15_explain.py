"""S4E: (1) what predicts next-season pressure performance (LightGBM + built-in SHAP, leak-free cutoff features),
(2) player-type clustering, (3) matchup model.

(1) For each cutoff c, style features are computed from balls <= c only (run value per 100 by phase, vs pace / spin,
    setting vs chasing, boundary %, dot %, death-overs share, ...) and joined to the backtest features (s12). A small
    LightGBM is trained on folds <= c-1 and scored on fold c (same targets as s12); SHAP = pred_contrib on all folds.
(2) Clusters on career profile features (standardised), k-means, k chosen by silhouette among k = 3..8 with
    bootstrap stability (adjusted Rand index over 30 resamples) as a tie-break.
(3) Matchups (RR pack, where hand / bowling type are known): league table of run value by batting hand x bowling type
    x phase (EB-shrunk); player-specific pace-vs-spin and vs-left-arm effects with split-half reliability, to show
    which matchup effects are real and which are noise.
Outputs: v2_results/explain/*.csv, EXPLAIN_REPORT.md; v2_work/explain/clusters_{role}.parquet
"""
import lightgbm as lgb
from scipy.stats import spearmanr
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.preprocessing import StandardScaler
from common import *
import skill as K

seed_all()
os.makedirs(res('explain'), exist_ok=True); os.makedirs(w('explain'), exist_ok=True)
UB = pd.read_parquet(w('unified/balls.parquet'), columns=['pace_spin', 'bowl_type', 'bat_hand'])
L = ['# What drives pressure performance, player types, matchups (S4E)', '']


def style_feats(V, c, role):
    d = K.role_view(V[V.season <= c], role)
    d = d.assign(pace_spin=UB.pace_spin.values[d.row.values], bat_hand=UB.bat_hand.values[d.row.values])
    g = lambda m: d[m].groupby('pid').rv.mean() * 100
    F = pd.DataFrame({f'rv_{p}': g(d.phase.eq(p)) for p in ['PP', 'Middle', 'Death']})
    F['rv_setting'] = g(d.innings.eq(1)); F['rv_chasing'] = g(d.innings.eq(2))
    F['death_share'] = d.groupby('pid').phase.apply(lambda s: s.eq('Death').mean())
    F['pp_share'] = d.groupby('pid').phase.apply(lambda s: s.eq('PP').mean())
    if role == 'bat':
        F['rv_vs_pace'] = g(d.pace_spin.eq('Pace')); F['rv_vs_spin'] = g(d.pace_spin.eq('Spin'))
        F['boundary_pct'] = d.groupby('pid').runs_bat.apply(lambda s: s.isin([4, 6]).mean() * 100)
        F['dot_pct'] = d.groupby('pid').runs_bat.apply(lambda s: s.eq(0).mean() * 100)
        F['sr'] = d.groupby('pid').runs_bat.mean() * 100
    else:
        F['rv_vs_lhb'] = g(d.bat_hand.eq('LHB')); F['rv_vs_rhb'] = g(d.bat_hand.eq('RHB'))
        F['econ'] = d.groupby('pid').bowl_runs.sum() / d.groupby('pid').legal.sum() * 6
        F['wkt_rate'] = d.groupby('pid').bowl_wkt.mean() * 100
        F['is_spin'] = d.groupby('pid').pace_spin.apply(lambda s: (s == 'Spin').mean() if s.notna().any() else np.nan)
    return F


# ---------------- (1) SHAP ----------------
BASEF = ['M4_eb_overall', 'gap_eb', 'M6_apm', 'age', 'log_n', 'p_n', 'pub_n']
shap_rows, perf_rows = [], []
for role in ['bat', 'bowl']:
    bt = pd.read_parquet(w(f'skill/bt_{role}.parquet'))
    bt['log_n'] = np.log1p(bt.all_n)
    parts = []
    for c in [2022, 2023, 2024, 2025]:
        V = pd.read_parquet(w(f'values/ball_values_{c}.parquet'))
        V, _ = K.add_flags(V, c)
        sf = style_feats(V, c, role)
        b = bt[bt.cutoff == c].set_index('pid').drop(columns=['pp_share', 'death_share'], errors='ignore').join(sf)
        parts.append(b.assign(cutoff=c))
    D = pd.concat(parts)
    extra = ['bat_pos'] if role == 'bat' else ['dot_rate']
    FE = BASEF + extra + [c for c in sf.columns]
    D = D[D.all_n >= 60]
    E = D[D.y.notna() & (D.yn >= 30)]
    prm = dict(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=40, subsample=0.8, subsample_freq=1,
               colsample_bytree=0.8, reg_lambda=5.0, random_state=SEED, n_jobs=4, deterministic=True, force_row_wise=True, verbose=-1)
    for c in [2023, 2024, 2025]:
        tr, te = E[E.cutoff < c], E[E.cutoff == c]
        m = lgb.LGBMRegressor(**prm).fit(tr[FE], tr.y, sample_weight=tr.yn)
        p = m.predict(te[FE])
        perf_rows.append(dict(role=role, test_cutoff=c, model='LightGBM on profile features', wcorr=np.corrcoef(p, te.y)[0, 1],
                              spearman=spearmanr(p, te.y)[0], n=len(te)))
        perf_rows.append(dict(role=role, test_cutoff=c, model='M8_bayes (s12)', wcorr=np.corrcoef(te.M8_bayes, te.y)[0, 1],
                              spearman=spearmanr(te.M8_bayes, te.y)[0], n=len(te)))
    m = lgb.LGBMRegressor(**prm).fit(E[FE], E.y, sample_weight=E.yn)
    contrib = m.predict(E[FE], pred_contrib=True)[:, :-1]
    imp = pd.Series(np.abs(contrib).mean(0), index=FE).sort_values(ascending=False)
    sign = pd.Series([np.corrcoef(E[f].fillna(E[f].median()), contrib[:, i])[0, 1] for i, f in enumerate(FE)], index=FE)
    for f_ in imp.index:
        shap_rows.append(dict(role=role, feature=f_, mean_abs_shap=imp[f_], direction=np.sign(sign[f_])))
SH = pd.DataFrame(shap_rows); PF = pd.DataFrame(perf_rows)
SH.round(5).to_csv(res('explain/shap_top_predictors.csv'), index=False); PF.round(4).to_csv(res('explain/profile_model_vs_bayes.csv'), index=False)
NICE = {'M4_eb_overall': 'overall run value (all situations, RR pack, shrunk)', 'gap_eb': 'pressure-minus-normal gap (shrunk)',
        'M6_apm': 'opponent/competition-adjusted skill from all leagues (APM)', 'age': 'age', 'log_n': 'experience (balls, log)',
        'p_n': 'pressure balls seen', 'pub_n': 'balls in other leagues', 'bat_pos': 'batting position', 'dot_rate': 'dot-ball rate',
        'rv_PP': 'run value in powerplay', 'rv_Middle': 'run value in middle overs', 'rv_Death': 'run value at the death',
        'rv_setting': 'run value setting a total', 'rv_chasing': 'run value chasing', 'death_share': 'share of balls at the death',
        'pp_share': 'share of balls in powerplay', 'rv_vs_pace': 'run value vs pace', 'rv_vs_spin': 'run value vs spin',
        'boundary_pct': 'boundary %', 'dot_pct': 'dot %', 'sr': 'strike rate', 'rv_vs_lhb': 'run value vs left-handers',
        'rv_vs_rhb': 'run value vs right-handers', 'econ': 'economy', 'wkt_rate': 'wicket rate', 'is_spin': 'spinner'}
for role in ['bat', 'bowl']:
    t = SH[SH.role == role].head(8).assign(meaning=lambda d: d.feature.map(NICE),
                                            effect=lambda d: d.direction.map({1.0: 'higher -> better', -1.0: 'higher -> worse'}))
    L += [f'## Top predictors of next-season pressure run value: {"batters" if role == "bat" else "bowlers"}', '',
          t[['feature', 'meaning', 'mean_abs_shap', 'effect']].round(4).to_markdown(index=False), '']
pf = PF.groupby(['role', 'model'])[['wcorr', 'spearman']].mean().round(3)
L += ['Out-of-time check of the profile LightGBM (train on earlier folds, test on the next):', '', pf.to_markdown(), '',
      '- SHAP is descriptive: it shows what the profile model leans on. Ratings use the model that predicts best out of time (s12).', '']

# ---------------- (2) clusters ----------------
PR = pd.read_parquet(w('profiles/player_profiles.parquet'))
ID = pd.read_parquet(w('profiles/player_identity.parquet')).set_index('uid')


def wide(role, split, sv, metrics):
    x = PR[(PR.role == role) & (PR.split == split) & (PR.split_value == sv) & PR.metric.isin(metrics)]
    return x.pivot_table(index='pid', columns='metric', values='value')


crow = []
for role in ['bat', 'bowl']:
    if role == 'bat':
        base = wide('bat', 'all', 'career', ['balls', 'strike_rate', 'boundary_pct', 'dot_pct', 'balls_per_dismissal'])
        for ph in ['PP', 'Middle', 'Death']:
            base = base.join(wide('bat', 'phase', ph, ['balls', 'strike_rate']).add_suffix(f'_{ph}'))
        base = base[base.balls >= 500]
        X = pd.DataFrame({'sr': base.strike_rate, 'bdry': base.boundary_pct, 'dot': base.dot_pct,
                          'bpd': np.log(base.balls_per_dismissal), 'pos': ID.bat_pos_median.reindex(base.index),
                          **{f'share_{ph}': base[f'balls_{ph}'] / base.balls for ph in ['PP', 'Middle', 'Death']}})
    else:
        base = wide('bowl', 'all', 'career', ['balls', 'economy', 'strike_rate', 'dot_pct', 'boundary_pct'])
        for ph in ['PP', 'Middle', 'Death']:
            base = base.join(wide('bowl', 'phase', ph, ['balls', 'economy']).add_suffix(f'_{ph}'))
        base = base[base.balls >= 500]
        X = pd.DataFrame({'econ': base.economy, 'sr': np.log(base.strike_rate), 'dot': base.dot_pct, 'bdry': base.boundary_pct,
                          **{f'share_{ph}': base[f'balls_{ph}'] / base.balls for ph in ['PP', 'Middle', 'Death']}})
    X = X.fillna(X.median()); Z = StandardScaler().fit_transform(X)
    rng = np.random.default_rng(SEED); best = None
    for k in range(3, 9):
        km = KMeans(k, n_init=10, random_state=SEED).fit(Z)
        sil = silhouette_score(Z, km.labels_, sample_size=min(3000, len(Z)), random_state=SEED)
        aris = []
        for _ in range(30):
            ix = rng.choice(len(Z), len(Z)); kb = KMeans(k, n_init=5, random_state=SEED).fit(Z[ix])
            aris.append(adjusted_rand_score(km.labels_, kb.predict(Z)))
        crow.append(dict(role=role, k=k, silhouette=sil, stability_ari=np.mean(aris)))
    cr = pd.DataFrame(crow); cr = cr[cr.role == role]
    ok = cr[cr.stability_ari >= 0.6]
    kbest = int((ok if len(ok) else cr).sort_values('silhouette', ascending=False).k.iloc[0])
    km = KMeans(kbest, n_init=20, random_state=SEED).fit(Z)
    X['cluster'] = km.labels_
    prof = X.groupby('cluster').mean().round(2); prof['n'] = X.groupby('cluster').size()
    # plain-language labels from the cluster centres
    def lab(r):
        if role == 'bat':
            pos = 'finisher' if (r.share_Death >= 0.35 or r.pos >= 6) else 'top-order' if r.share_PP >= 0.4 else 'middle-order'
            style = 'aggressive' if r.sr > X.sr.median() + 5 else 'accumulator' if r.sr < X.sr.median() - 5 else 'balanced'
            return f'{pos} {style}'
        if r.share_PP >= 0.35 and r.share_Death >= 0.25:
            ph = 'new-ball + death'
        else:
            ph = {'PP': 'new-ball', 'Middle': 'middle-overs', 'Death': 'death'}[max(['PP', 'Middle', 'Death'], key=lambda p: r[f'share_{p}'])]
        cost = 'economical' if r.econ < X.econ.median() - 0.3 else 'expensive' if r.econ > X.econ.median() + 0.3 else 'average-economy'
        return f'{ph} {cost}'
    prof['label'] = prof.apply(lab, axis=1)
    X['cluster_label'] = X.cluster.map(prof.label)
    X.to_parquet(w(f'explain/clusters_{role}.parquet'))
    prof.to_csv(res(f'explain/clusters_{role}.csv'))
    L += [f'## Player types: {"batters" if role == "bat" else "bowlers"} (k = {kbest}; >= 500 career balls)', '',
          prof.to_markdown(), '']
pd.DataFrame(crow).round(3).to_csv(res('explain/cluster_k_selection.csv'), index=False)

# ---------------- (3) matchups ----------------
V = pd.read_parquet(w('values/ball_values_final.parquet')); V, _ = K.add_flags(V, 2026)
V = V[V.source.eq('RR')].copy()
V['bat_hand'] = UB.bat_hand.values[V.row.values]; V['bowl_type'] = UB.bowl_type.values[V.row.values]
V['pace_spin'] = UB.pace_spin.values[V.row.values]
f = V[V.faced & V.bat_hand.notna() & V.bowl_type.notna()]
cell = f.groupby(['bat_hand', 'bowl_type', 'phase']).rv_bat.agg(['mean', 'size'])
mu = f.rv_bat.mean(); k0 = 400
cell['rv_per100_shrunk'] = ((cell['mean'] * cell['size'] + k0 * mu) / (cell['size'] + k0) - mu) * 100
cell.reset_index().round(4).to_csv(res('explain/matchup_league_table.csv'), index=False)
tab = cell.rv_per100_shrunk.unstack('phase').round(1)
# player-specific matchup effects and their reliability
f = f.assign(h=f.match_id.factorize()[0] % 2)
def split_rel(df, pid, grp, a, b, minb=60):
    x = df[df[grp].isin([a, b])].groupby([pid, 'h', grp]).rv_bat.agg(['mean', 'size']).unstack(grp)
    x = x[(x['size'] >= minb / 2).all(1)]
    gap = (x['mean'][a] - x['mean'][b]).unstack('h').dropna()
    r = gap.corr().iloc[0, 1]
    return 2 * r / (1 + r), len(gap)
r_ps, n_ps = split_rel(f, 'batter', 'pace_spin', 'Spin', 'Pace')
f['arm'] = np.where(f.bowl_type.str.startswith('Left'), 'Left', 'Right')
r_la, n_la = split_rel(f, 'batter', 'arm', 'Left', 'Right')
fb = V[V.bat_hand.notna()].assign(h=lambda d: d.match_id.factorize()[0] % 2)
xb = fb.groupby(['bowler', 'h', 'bat_hand']).rv_bowl.agg(['mean', 'size']).unstack('bat_hand')
xb = xb[(xb['size'] >= 30).all(1)]
gb = (xb['mean']['LHB'] - xb['mean']['RHB']).unstack('h').dropna(); rb = gb.corr().iloc[0, 1]; r_hand = 2 * rb / (1 + rb)
mrel = pd.DataFrame([dict(effect='batter: spin minus pace', reliability=r_ps, players=n_ps),
                     dict(effect='batter: left-arm minus right-arm bowling', reliability=r_la, players=n_la),
                     dict(effect='bowler: vs left-handers minus vs right-handers', reliability=r_hand, players=len(gb))])
mrel.round(3).to_csv(res('explain/matchup_reliability.csv'), index=False)
L += ['## Matchups (RR pack)', '', 'League-wide run value per 100 balls for the batter vs the average ball (shrunk, k = 400), '
      'by batting hand x bowling type x phase:', '', tab.to_markdown(), '',
      'Are player-specific matchup gaps real? Split-half reliability (odd/even matches, Spearman-Brown):', '',
      mrel.round(3).to_markdown(index=False), '',
      '- Reliability near zero means an individual player\'s apparent matchup weakness is mostly noise at this sample size; '
      'scout cards only call out a player matchup when it is large AND the reliability of that effect type is meaningful.']
open(res('explain/EXPLAIN_REPORT.md'), 'w').write('\n'.join(L))
print('\n'.join(L))
