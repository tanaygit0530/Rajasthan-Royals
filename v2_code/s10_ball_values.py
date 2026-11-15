"""S4A(iii): per-ball values for every cutoff, so later backtests never use a model that saw the future.

For cutoff c in {2022, 2023, 2024, 2025} the chosen WP and expected-outcome models are fitted on seasons <= c and
applied to balls of seasons <= c+1 (features for the backtest = seasons <= c; target season c+1 is scored
out-of-sample). Cutoff 'final' fits on everything and is used for the submitted ratings.

Per ball:
  wp0          batting-team win probability before the ball (first-innings end states use the chase model at the
               start of the chase, so both innings live on one scale)
  li           leverage: sum_k p_k |WP(after outcome k) - wp0|, k in {0,1,2,3,4,6,OUT}, p_k from the multinomial
               outcome model at this state (learned mix); li_phase = same with a phase-average mix (baseline style)
  bat_wpa      WP change from the batter's outcome (runs off bat + his dismissal), faced balls only
  bat_xwpa     expected bat_wpa at this state (outcome mix) -> bat_wpa_oe = bat_wpa - bat_xwpa
  bowl_wpa     -(WP change from runs charged to bowler + bowler wicket); bowl_xwpa similarly
  xruns, xout, xbowl_runs, xbowl_wkt   context expectations
Pressure-definition inputs (S3.2): li, li_phase, rrr_gap (chase: required rate - par rate), wkt_stress
(wickets down - expected wickets down at this ball), close (|wp0 - 0.5| <= 0.2), stakes (IPL team stakes; knockouts = 1).
Outputs: v2_work/values/ball_values_{c}.parquet
"""
import sys
import json
import time
from common import *
import s08_wp as W
import s09_xoutcome as X

seed_all()
OUTC = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (6, 0), (0, 1)]
cut_arg = sys.argv[1:] or ['2022', '2023', '2024', '2025', 'final']
chosen_wp = json.load(open(res('models/wp_chosen.json')))
chosen_x = json.load(open(res('models/xout_chosen.json')))

S = X.load()          # state + outcomes, seasons >= 2019, innings 1-2; index = row of unified/balls.parquet
if os.environ.get('SMOKE'):   # quick test on a match sample
    S = S[S.match_id.isin(pd.Series(S.match_id.unique()).sample(300, random_state=1))]
Bx = pd.read_parquet(w('unified/balls.parquet'), columns=['match_id', 'innings', 'seq', 'batter', 'bowler', 'non_striker',
                                                          'is_wide', 'is_nb', 'wide', 'noball', 'legal'])
TS = pd.read_parquet(w('unified/team_stakes.parquet'))
stk = TS.groupby(['match_id', 'team']).stakes.mean()


class WP:
    def __init__(self, d):
        self.m = {}
        for inn in (1, 2):
            tr = d[d.bat_won.notna() & (d.innings == inn) & (d.balls_left > 0)]
            fam = chosen_wp[str(inn)]
            if fam == 'blend_gbm':
                self.m[inn] = [W.Fam(f, inn).fit(tr) for f in ('hgb', 'lightgbm', 'xgboost')]
            else:
                self.m[inn] = [W.Fam(fam, inn).fit(tr)]

    def _raw(self, inn, f):
        ps = [m.raw(f) for m in self.m[inn]]
        return ps[0] if len(ps) == 1 else W.blend(ps)

    def __call__(self, base, sc, lb, wk):
        """WP for the batting team of each row of `base` at state (score, legal balls bowled, wickets)."""
        f = base.copy()
        f['score_before'] = sc; f['legal_before'] = lb; f['wkts_before'] = wk
        bal = np.where(f.innings == 1, f.inn1_balls, f.chase_balls)
        f['balls_left'] = bal - lb; f['wih'] = 10 - wk
        f['need'] = np.where(f.innings == 2, f.target - sc, np.nan)
        f['rrr'] = np.clip(f.need / np.maximum(f.balls_left, 1) * 6, -6, 60)
        f['crr'] = W.crr_shrunk(sc, lb, f.par_prev)
        f['crr_raw'] = sc / np.maximum(lb, 1) * 6
        f['score_vs_par'] = sc - f.par_prev * lb / 120
        p = np.full(len(f), np.nan)
        i2 = (f.innings == 2).values
        if i2.any():
            g = f[i2]; p[i2] = W.terminal(g, self._raw(2, g), 2)
        i1 = ~i2
        if i1.any():
            g = f[i1]; done = ((g.balls_left <= 0) | (g.wih <= 0)).values
            q = np.empty(len(g))
            if (~done).any():
                q[~done] = self._raw(1, g[~done])
            if done.any():   # innings over: 1 - chase WP at the start of the chase
                h = g[done].copy()
                h['innings'] = 2; h['need'] = h.score_before + 1; h['balls_left'] = h.chase_balls; h['wih'] = 10
                h['rrr'] = np.clip(h.need / h.balls_left * 6, -6, 60); h['elo_diff'] = -h.elo_diff
                q[done] = 1 - self._raw(2, h)
            p[i1] = np.clip(q, 1e-4, 1 - 1e-4)
        return p


for cut in cut_arg:
    t0 = time.time()
    c = 9999 if cut == 'final' else int(cut)
    tr = S[S.season <= c]
    wpm = WP(tr)
    xm_mc = X.XModel('lgbm_multiclass').fit(tr)
    xfam = chosen_x['bat_runs_mse']
    xm = xm_mc if xfam == 'lgbm_multiclass' else X.XModel(xfam).fit(tr)
    print(cut, 'models fitted', f'{time.time() - t0:.0f}s', flush=True)
    A = S[S.season <= c + 1] if cut != 'final' else S
    idx = A.index.values
    sc, lb, wk = A.score_before.values.astype(float), A.legal_before.values.astype(float), A.wkts_before.values.astype(float)
    wp0 = wpm(A, sc, lb, wk)
    pm = xm_mc.predict(A); pc = pm['pcls']
    px = pm if xm is xm_mc else xm.predict(A)
    # phase-average outcome mix (baseline-style), from training data
    ftr = tr[tr.faced]
    mixp = pd.crosstab([ftr.innings, ftr.phase], ftr.cls, normalize='index').reindex(columns=range(7), fill_value=0)
    pp = mixp.reindex(pd.MultiIndex.from_arrays([A.innings, A.phase])).fillna(0).values
    li = np.zeros(len(A)); li_ph = np.zeros(len(A)); xwpa = np.zeros(len(A))
    for k, (r, wkt) in enumerate(OUTC):
        d = wpm(A, sc + r, lb + 1, wk + wkt) - wp0
        li += pc[:, k] * np.abs(d); li_ph += pp[:, k] * np.abs(d); xwpa += pc[:, k] * d
    Bb = Bx.loc[idx]
    pen = (Bb.wide.values + Bb.noball.values).astype(float)      # wide / no-ball runs are not the batter's
    nlb = lb + Bb.legal.values
    wp_ref = wpm(A, sc + pen, lb, wk)
    wp_bat = wpm(A, sc + pen + A.runs_bat.values, nlb, wk + A.striker_out.values)
    wp_bowl = wpm(A, sc + A.bowl_runs.values, nlb, wk + A.bowl_wkt.values)
    faced = A.faced.values
    V = pd.DataFrame({
        'row': idx, 'match_id': A.match_id.values, 'innings': A.innings.values, 'seq': Bb.seq.values,
        'season': A.season.values, 'comp2': A.comp2.values, 'source': A.source.values, 'phase': A.phase.values,
        'batter': Bb.batter.values, 'bowler': Bb.bowler.values, 'bat_team': A.bat_team.values, 'bowl_team': A.bowl_team.values,
        'faced': faced, 'legal': Bb.legal.values, 'runs_bat': A.runs_bat.values, 'striker_out': A.striker_out.values,
        'bowl_runs': A.bowl_runs.values, 'bowl_wkt': A.bowl_wkt.values, 'knockout': A.knockout_v2.values,
        'wp0': wp0, 'li': li, 'li_phase': li_ph,
        'bat_wpa': np.where(faced, wp_bat - wp_ref, 0.0), 'bat_xwpa': np.where(faced, xwpa, 0.0),
        'bowl_wpa': -(wp_bowl - wp0), 'bowl_xwpa': -xwpa,
        'xruns': px['xruns'], 'xout': px['xout'], 'xbowl_runs': px['xbowl_runs'], 'xbowl_wkt': px['xbowl_wkt']})
    V['bat_wpa_oe'] = V.bat_wpa - V.bat_xwpa
    V['bowl_wpa_oe'] = V.bowl_wpa - V.bowl_xwpa
    # pressure-definition inputs
    V['rrr_gap'] = np.where(A.innings.values == 2, A.rrr.values - A.par_prev.values / 20, np.nan)
    ew = tr.groupby(tr.innings.astype(str) + '_' + tr.legal_before.clip(0, 120).astype(str)).wkts_before.mean()
    V['wkt_stress'] = A.wkts_before.values - (A.innings.astype(str) + '_' + A.legal_before.clip(0, 120).astype(str)).map(ew).fillna(0).values
    V['close'] = (np.abs(wp0 - 0.5) <= 0.2).astype(int)
    st = pd.Series(list(zip(A.match_id, A.bat_team))).map(stk)
    V['stakes_bat'] = np.where(A.knockout_v2.values == 1, 1.0, st.values.astype(float))
    st2 = pd.Series(list(zip(A.match_id, A.bowl_team))).map(stk)
    V['stakes_bowl'] = np.where(A.knockout_v2.values == 1, 1.0, st2.values.astype(float))
    V['li_norm'] = V.li / V.loc[V.legal & V.season.ge(2022), 'li'].mean()
    fl = V.select_dtypes('float64').columns
    V[fl] = V[fl].astype('float32')
    os.makedirs(w('values'), exist_ok=True)
    V.to_parquet(w(f'values/ball_values_{cut}.parquet'), index=False)
    print(cut, 'done', len(V), f'{time.time() - t0:.0f}s', flush=True)
