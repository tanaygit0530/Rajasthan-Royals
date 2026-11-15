"""S4A(i): win-probability model comparison with rolling, season-ahead validation (no leakage).

State features are built only from information available before the ball:
  chase:   runs needed, balls left, wickets in hand, required rate, + context
  setting: score, balls left, wickets in hand, current rate, score vs par, + context
  context: par_prev  = mean full-innings first-innings total in the same competition over the previous 365 days
                       (era term: captures the Impact-Player-era scoring jump without a hand-set dummy)
           venue_dev = shrunk mean of (first-innings total - par_prev) at the venue in EARLIER matches
           elo_diff  = batting minus bowling team Elo before the match (all competitions, K=24)
           knockout, impact_era (IPL 2023+), is_intl
Families: logistic regression (engineered terms), sklearn HGB, LightGBM, XGBoost (all monotone in the obvious
directions), and an equal-weight logit blend of the three GBMs. Baseline replica B0 = the baseline's features
(need, balls, wickets, rate, team tier, is_ipl), HGB, trained on the RR pack only (as the baseline was).
Folds: train seasons <= c (all sources), test season c+1 on RR-pack balls, c = 2022..2025.
Outputs: v2_work/wp/match_feats.parquet, state.parquet; v2_results/models/wp_comparison.csv, wp_calibration.csv,
         wp_by_phase.csv, WP_REPORT.md, chosen.json
"""
import json
import time
import lightgbm as lgb
import xgboost as xgb
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import log_loss, brier_score_loss, roc_auc_score
from common import *

seed_all()
NT = 4


# ============ match-level features (all leak-free) ============
def overs_to_balls(o):
    o = pd.to_numeric(o, errors='coerce')
    return np.floor(o) * 6 + np.round((o - np.floor(o)) * 10)


def build_match_feats():
    M = pd.read_parquet(w('unified/matches.parquet'))
    C = pd.read_parquet(w('unified/match_context.parquet'))
    CM = pd.read_parquet(w('public/cs_matches.parquet')).set_index('match_id')
    rm = rr('matches.csv'); rm['match_id'] = 'rr' + rm.match_id.astype(str); rm = rm.set_index('match_id')
    B = pd.read_parquet(w('unified/balls.parquet'), columns=['match_id', 'innings', 'legal', 'wkt_any'])
    inn = B.groupby(['match_id', 'innings']).agg(lb=('legal', 'sum'), wk=('wkt_any', 'sum')).unstack()
    M = M.merge(C[['match_id', 'venue_key', 'knockout_v2', 'impact_era', 'target_v2', 'chase_balls_v2', 'rain_fix']], on='match_id', how='left')
    M = M.set_index('match_id')
    rr_ = M.source.eq('RR')
    sched = (pd.to_numeric(CM.overs, errors='coerce') * 6).reindex(M.index).fillna(120)
    M['inn1_balls'] = np.where(rr_, rm.first_inn_revised_overs.reindex(M.index).fillna(120), sched)
    cs_chase = overs_to_balls(CM.target_overs).reindex(M.index)
    M['chase_balls'] = np.where(rr_, rm.second_inn_revised_overs.reindex(M.index).fillna(120), cs_chase.fillna(sched))
    M['target'] = np.where(rr_, rm.revised_target.reindex(M.index), pd.to_numeric(CM.target_runs, errors='coerce').reindex(M.index))
    # rain fixes from s06b (RR games with a shortened first innings and no recorded target)
    rf = M.rain_fix.fillna(False).astype(bool)
    M.loc[rf, 'target'] = M.loc[rf, 'target_v2']; M.loc[rf, 'chase_balls'] = M.loc[rf, 'chase_balls_v2']
    M['target'] = M.target.fillna(M.inn1_total + 1)
    # Cricsheet: first innings cut short by rain (method set, not all out, fewer balls than scheduled)
    lb1 = inn[('lb', 1)].reindex(M.index); wk1 = inn[('wk', 1)].reindex(M.index)
    cut = ~rr_ & CM.method.reindex(M.index).notna() & (wk1 < 10) & (lb1 < M.inn1_balls)
    M.loc[cut, 'inn1_balls'] = lb1[cut]
    # a few Cricsheet T20 records carry a non-T20 'overs' value (e.g. 50): T20 innings are capped at 120 balls
    M['inn1_balls'] = M.inn1_balls.clip(1, 120); M['chase_balls'] = M.chase_balls.clip(1, 120)
    M['date'] = pd.to_datetime(M.date)
    M = M.reset_index().sort_values(['date', 'match_id']).reset_index(drop=True)

    # par_prev: competition first-innings par over the previous 365 days (full innings only), shrunk to all-comp par
    full = M[(M.inn1_balls >= 120) & M.inn1_total.notna()][['match_id', 'date', 'comp2', 'inn1_total']]
    def prior_mean(dates, ref_dates, vals):
        cs = np.concatenate([[0], np.cumsum(vals)]); d = dates.values.astype('datetime64[D]')
        r = ref_dates.values.astype('datetime64[D]')
        hi = np.searchsorted(d, r, side='left'); lo = np.searchsorted(d, r - np.timedelta64(365, 'D'), side='left')
        return cs[hi] - cs[lo], hi - lo
    fa = full.sort_values('date')
    gs, gn = prior_mean(fa.date, M.date, fa.inn1_total.values)
    gpar = np.where(gn > 0, gs / np.maximum(gn, 1), fa.inn1_total.mean())
    M['par_prev'] = np.nan
    for comp, d in M.groupby('comp2'):
        f = fa[fa.comp2 == comp]
        s, n = prior_mean(f.date, d.date, f.inn1_total.values)
        M.loc[d.index, 'par_prev'] = (s + 15 * gpar[d.index]) / (n + 15)
    # venue_dev: earlier matches at the venue, (total - par_prev), shrunk with k=10
    M['dev'] = np.where(M.inn1_balls >= 120, M.inn1_total - M.par_prev, np.nan)
    M['venue_dev'] = 0.0
    for v, d in M.groupby('venue_key'):
        dv = d.dev.fillna(0).values; has = d.dev.notna().values.astype(float)
        cs_ = np.concatenate([[0], np.cumsum(dv)])[:-1]; cn = np.concatenate([[0], np.cumsum(has)])[:-1]
        M.loc[d.index, 'venue_dev'] = np.where(v == 'unknown', 0, cs_ / (cn + 10))
    # Elo
    elo = {}; ea, eb = [], []
    for r in M.itertuples():
        a, b_ = r.team1, r.team2
        ra, rb = elo.get(a, 1500.0), elo.get(b_, 1500.0)
        ea.append(ra); eb.append(rb)
        if isinstance(r.winner, str) and r.winner in (a, b_):
            ex = 1 / (1 + 10 ** ((rb - ra) / 400)); s = 1.0 if r.winner == a else 0.0
            elo[a] = ra + 24 * (s - ex); elo[b_] = rb - 24 * (s - ex)
    M['elo_team1'] = ea; M['elo_team2'] = eb
    M['is_intl'] = M.comp2.str.startswith('T20I') | M.comp2.eq('A-team')
    keep = ['match_id', 'source', 'comp', 'comp2', 'season', 'date', 'team1', 'team2', 'winner', 'bat_first', 'inn1_total',
            'inn1_balls', 'chase_balls', 'target', 'par_prev', 'venue_dev', 'elo_team1', 'elo_team2', 'knockout_v2',
            'impact_era', 'is_intl', 'venue_key']
    MF = M[keep].copy()
    MF['knockout_v2'] = MF.knockout_v2.fillna(0).astype(int); MF['impact_era'] = MF.impact_era.fillna(0).astype(int)
    return MF


# ============ ball-level state ============
TIER_A = {'India', 'Australia', 'England', 'South Africa', 'New Zealand', 'Pakistan', 'Sri Lanka', 'West Indies',
          'Afghanistan', 'Bangladesh', 'Chennai Super Kings', 'Mumbai Indians', 'Rajasthan Royals', 'Punjab Kings',
          'Royal Challengers Bengaluru', 'Delhi Capitals', 'Kolkata Knight Riders', 'Sunrisers Hyderabad',
          'Gujarat Titans', 'Lucknow Super Giants'}
TIER_B = {'Ireland', 'Zimbabwe', 'Scotland', 'Netherlands', 'India A', 'Pakistan A', 'Sri Lanka A', 'Bangladesh A', 'Afghanistan A'}


CRR_K = 18   # balls: early in an innings the run rate is shrunk toward the competition par rate


def crr_shrunk(sc, lb, par):
    """current run rate shrunk toward par: as if CRR_K balls had already been bowled at par. Without this, one
    boundary off ball 1 implies a rate of 24 and the projected total (and win probability) swings wildly."""
    return (sc + par / 120 * CRR_K) / (lb + CRR_K) * 6


def build_state(MF):
    cols = ['source', 'match_id', 'innings', 'over', 'seq', 'bat_team', 'bowl_team', 'legal', 'season', 'score_before',
            'legal_before', 'wkts_before', 'phase', 'comp2']
    B = pd.read_parquet(w('unified/balls.parquet'), columns=cols)
    B = B.merge(MF.drop(columns=['source', 'season', 'comp2']), on='match_id', how='left')
    t1 = B.bat_team.eq(B.team1)
    B['elo_diff'] = np.where(t1, B.elo_team1 - B.elo_team2, B.elo_team2 - B.elo_team1)
    B['balls_left'] = np.where(B.innings == 1, B.inn1_balls, B.chase_balls) - B.legal_before
    B['wih'] = 10 - B.wkts_before
    B['need'] = np.where(B.innings == 2, B.target - B.score_before, np.nan)
    B['rrr'] = np.clip(B.need / np.maximum(B.balls_left, 1) * 6, -6, 60)
    B['crr_raw'] = B.score_before / np.maximum(B.legal_before, 1) * 6          # baseline-style (volatile early on)
    B['crr'] = crr_shrunk(B.score_before, B.legal_before, B.par_prev)
    B['score_vs_par'] = B.score_before - B.par_prev * B.legal_before / 120
    B['bat_won'] = np.where(B.winner.isna(), np.nan, (B.bat_team == B.winner).astype(float))
    tier = lambda s: np.where(s.isin(TIER_A), 1, np.where(s.isin(TIER_B), 2, 3))
    B['level'] = np.maximum(tier(B.bat_team), tier(B.bowl_team))
    B['is_ipl'] = B.comp.eq('IPL').astype(int)
    for c in ['knockout_v2', 'impact_era', 'is_intl']:
        B[c] = B[c].fillna(0).astype(int)
    f32 = ['par_prev', 'venue_dev', 'elo_diff', 'balls_left', 'need', 'rrr', 'crr', 'crr_raw', 'score_vs_par', 'bat_won']
    B[f32] = B[f32].astype('float32')
    return B


F2 = ['need', 'balls_left', 'wih', 'rrr', 'par_prev', 'venue_dev', 'elo_diff', 'knockout_v2', 'impact_era', 'is_intl']
M2 = [-1, 1, 1, -1, 0, 0, 1, 0, 0, 0]
F1 = ['score_before', 'balls_left', 'wih', 'crr', 'inn1_balls', 'score_vs_par', 'par_prev', 'venue_dev', 'elo_diff',
      'knockout_v2', 'impact_era', 'is_intl']
M1 = [1, 1, 1, 0, 0, 1, -1, -1, 1, 0, 0, 0]
FB2 = ['need', 'balls_left', 'wih', 'rrr', 'level', 'is_ipl']; MB2 = [-1, 1, 1, -1, 0, 0]
FB1 = ['score_before', 'balls_left', 'wih', 'crr_raw', 'inn1_balls', 'level', 'is_ipl']; MB1 = [1, 1, 1, 0, 0, 0, 0]


def lr_design(d, inn):
    if inn == 2:
        X = d[F2].copy()
        X['lneed'] = np.log1p(d.need.clip(0)); X['lballs'] = np.log1p(d.balls_left.clip(0))
        X['wxb'] = d.wih * d.balls_left / 120; X['need_per_wkt'] = d.need / (d.wih + 1)
        X['rrr2'] = d.rrr ** 2; X['need_x_par'] = d.need / d.par_prev
    else:
        X = d[F1].copy()
        X['proj'] = d.score_before + d.crr * d.balls_left / 6; X['proj_vs_par'] = X.proj - d.par_prev * d.inn1_balls / 120
        X['wxb'] = d.wih * d.balls_left / 120
    return X.fillna(0).values


class Fam:
    def __init__(self, name, inn, feats=None, mono=None):
        self.name, self.inn = name, inn
        self.feats = feats or (F2 if inn == 2 else F1); self.mono = mono or (M2 if inn == 2 else M1)

    def fit(self, d):
        y = d.bat_won.values; X = d[self.feats].values
        n = self.name
        if n == 'logistic':
            self.m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)).fit(lr_design(d, self.inn), y)
        elif n in ('hgb', 'B0_baseline_replica'):
            self.m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=200,
                                                    l2_regularization=1.0, monotonic_cst=self.mono, random_state=SEED,
                                                    early_stopping=False).fit(X, y)
        elif n == 'lightgbm':
            self.m = lgb.LGBMClassifier(n_estimators=500, learning_rate=0.05, num_leaves=31, min_child_samples=400,
                                        subsample=0.7, subsample_freq=1, colsample_bytree=0.9, reg_lambda=1.0,
                                        monotone_constraints=self.mono, random_state=SEED, n_jobs=NT, deterministic=True,
                                        force_row_wise=True, verbose=-1).fit(X, y)
        elif n == 'xgboost':
            self.m = xgb.XGBClassifier(n_estimators=500, learning_rate=0.05, max_depth=6, min_child_weight=50, subsample=0.7,
                                       colsample_bytree=0.9, tree_method='hist', monotone_constraints=tuple(self.mono),
                                       random_state=SEED, n_jobs=NT).fit(X, y)
        return self

    def raw(self, d):
        if self.name == 'logistic':
            return self.m.predict_proba(lr_design(d, self.inn))[:, 1]
        return self.m.predict_proba(d[self.feats].values)[:, 1]


def terminal(d, p, inn):
    if inn == 2:
        p = np.where(d.need.values <= 0, 1.0, p)
        p = np.where((d.need.values > 0) & ((d.wih.values <= 0) | (d.balls_left.values <= 0)), np.where(d.need.values == 1, 0.5, 0.0), p)
    return np.clip(p, 1e-4, 1 - 1e-4)


def logit(p): p = np.clip(p, 1e-5, 1 - 1e-5); return np.log(p / (1 - p))


def blend(ps): return 1 / (1 + np.exp(-np.mean([logit(p) for p in ps], axis=0)))


FAMS = ['logistic', 'hgb', 'lightgbm', 'xgboost']

if __name__ == '__main__':
    t00 = time.time()
    MF = build_match_feats()
    os.makedirs(w('wp'), exist_ok=True)
    MF.to_parquet(w('wp/match_feats.parquet'), index=False)
    S = build_state(MF)
    S.to_parquet(w('wp/state.parquet'), index=False)
    print('state rows', len(S), f'{time.time() - t00:.0f}s', flush=True)
    D = S[S.bat_won.notna() & S.innings.isin([1, 2]) & (S.balls_left > 0) & (S.season >= 2019)]
    rows, preds = [], []
    for c in [2022, 2023, 2024, 2025]:
        for inn in (1, 2):
            tr = D[(D.season <= c) & (D.innings == inn)]
            te = D[(D.season == c + 1) & (D.innings == inn) & D.source.eq('RR')]
            P = {}
            for fam in FAMS:
                t0 = time.time(); m = Fam(fam, inn).fit(tr); P[fam] = terminal(te, m.raw(te), inn)
                print(c, inn, fam, f'{time.time() - t0:.0f}s', flush=True)
            P['blend_gbm'] = terminal(te, blend([P['hgb'], P['lightgbm'], P['xgboost']]), inn)
            trb = tr[tr.source.eq('RR')]
            fb, mb = (FB2, MB2) if inn == 2 else (FB1, MB1)
            P['B0_baseline_replica'] = terminal(te, Fam('B0_baseline_replica', inn, fb, mb).fit(trb).raw(te), inn)
            P['B0_feats_all_data'] = terminal(te, Fam('B0_baseline_replica', inn, fb, mb).fit(tr).raw(te), inn)
            y = te.bat_won.values
            for k, p in P.items():
                rows.append(dict(cutoff=c, test_season=c + 1, innings=inn, model=k, n=len(y), logloss=log_loss(y, p),
                                 brier=brier_score_loss(y, p), auc=roc_auc_score(y, p)))
                preds.append(pd.DataFrame({'model': k, 'innings': inn, 'test_season': c + 1, 'phase': te.phase.values,
                                           'y': y, 'p': p.astype('float32')}))
    R = pd.DataFrame(rows)
    os.makedirs(res('models'), exist_ok=True)
    R.to_csv(res('models/wp_comparison_by_fold.csv'), index=False)
    S_ = R.groupby(['innings', 'model'])[['logloss', 'brier', 'auc']].mean().reset_index().sort_values(['innings', 'logloss'])
    S_.round(4).to_csv(res('models/wp_comparison.csv'), index=False)
    PP = pd.concat(preds)
    PP['bin'] = np.clip((PP.p * 10).astype(int), 0, 9)
    cal = PP.groupby(['innings', 'model', 'bin']).agg(n=('y', 'size'), mean_pred=('p', 'mean'), obs=('y', 'mean')).reset_index()
    cal.round(4).to_csv(res('models/wp_calibration.csv'), index=False)
    ph = PP.groupby(['innings', 'model', 'phase']).apply(lambda d: brier_score_loss(d.y, d.p), include_groups=False).rename('brier').reset_index()
    ph.round(4).to_csv(res('models/wp_by_phase.csv'), index=False)
    # choose: lowest mean test log-loss per innings; prefer simpler family if within 0.001 (honesty rule)
    order = ['logistic', 'hgb', 'lightgbm', 'xgboost', 'blend_gbm']
    chosen = {}
    for inn in (1, 2):
        s = S_[(S_.innings == inn) & S_.model.isin(order)].set_index('model').logloss
        best = s.min()
        chosen[inn] = next(m for m in order if s[m] <= best + 0.001)
    json.dump({str(k): v for k, v in chosen.items()}, open(res('models/wp_chosen.json'), 'w'))
    ece = cal.assign(gap=lambda d: (d.mean_pred - d.obs).abs() * d.n).groupby(['innings', 'model']).apply(
        lambda d: d.gap.sum() / d.n.sum(), include_groups=False).rename('ECE').reset_index()
    tab = S_.merge(ece, on=['innings', 'model']).round(4)
    L = ['# Win-probability model comparison (S4A)', '',
         'Rolling season-ahead folds: train on all sources up to season c, test on RR-pack balls of season c+1 '
         '(c = 2022..2025), mean over the four folds. ECE = expected calibration error over 10 probability bins.', '',
         tab.to_markdown(index=False), '',
         f'- Chosen (lowest log-loss; a simpler family wins if within 0.001): first innings **{chosen[1]}**, chase **{chosen[2]}**.',
         '- `B0_baseline_replica` = the baseline\'s feature set and model class trained on the RR pack only; '
         '`B0_feats_all_data` = same features trained on RR + Cricsheet. The gap between B0 and the chosen model is the value '
         'of the v2 context features (par/era, venue, Elo) and the public data.',
         '- Note: the baseline\'s own first-innings WP was a composite (resources model -> projected target -> chase WP); '
         'the replica uses a direct classifier on its features, so the first-innings comparison is approximate.']
    open(res('models/WP_REPORT.md'), 'w').write('\n'.join(L))
    print('\n'.join(L)); print(f'total {time.time() - t00:.0f}s')
