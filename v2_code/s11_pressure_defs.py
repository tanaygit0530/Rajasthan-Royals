"""S3.2: compare pressure definitions on RR-pack balls 2022-26 (the brief's data).

Candidates (flag = top 25% of RR legal balls unless binary by construction):
  D1_leverage        learned leverage index li (expected |dWP| of the next ball, model outcome mix)
  D2_leverage_phase  baseline-style leverage (phase-average outcome mix)
  D3_baseline_PI     D2 x 1.2 in knockouts (the baseline's exact pressure index)
  D4_rrr_gap         chase only: required rate minus par rate (top 25% of chase balls)
  D5_wicket_stress   wickets down minus expected wickets down at this ball
  D6_close_game      |WP - 0.5| <= 0.2
  D7_leverage_stakes li x (0.75 + 0.5 x qualification stakes) (IPL league stakes; knockouts 1; others neutral)
Criteria:
  (a) capture   share of total |WPA| (sum of |bat_wpa| on faced balls) on flagged balls / share of balls flagged
  (b) reliability of player performance on flagged balls: split-half (odd/even matches), Spearman-Brown corrected,
      for WPA-over-expected and run value (players with >= 60 flagged balls); and of the pressure-minus-normal gap
  (c) year-to-year correlation of flagged-ball run value (players with >= 30 flagged balls in consecutive seasons)
Run value: rv = (runs - xruns) - KW (out - xout), KW = runs-equivalent of a wicket estimated by OLS of WPA on the two
parts (bowler: (xbowl_runs - bowl_runs) + KW (wkt - xwkt)).
Outputs: v2_results/pressure/pressure_definitions.csv, PRESSURE_DEFS.md, chosen_pressure.json;
         v2_work/values/pressure_flags_final.parquet
"""
import json
from common import *

seed_all()
V = pd.read_parquet(w('values/ball_values_final.parquet'))
V = V[V.source.eq('RR') & V.season.between(2022, 2026)].copy()
V['match_n'] = V.match_id.str[2:].astype(int)
L_ = V.legal
# ---- KW from data ----
f = V[V.faced]
Xo = np.column_stack([f.runs_bat - f.xruns, f.striker_out - f.xout, np.ones(len(f))])
cb = np.linalg.lstsq(Xo, f.bat_wpa.values, rcond=None)[0]
KW = float(-cb[1] / cb[0])
V['rv_bat'] = np.where(V.faced, (V.runs_bat - V.xruns) - KW * (V.striker_out - V.xout), np.nan)
V['rv_bowl'] = (V.xbowl_runs - V.bowl_runs) + KW * (V.bowl_wkt - V.xbowl_wkt)


def top25(x, base_mask):
    thr = np.nanquantile(x[base_mask], 0.75)
    return (x >= thr).astype(int)


stakes_f = np.where(V.knockout == 1, 1.0, V.stakes_bat.fillna(0.5))
D = {
    'D1_leverage': top25(V.li.values, L_.values),
    'D2_leverage_phase': top25(V.li_phase.values, L_.values),
    'D3_baseline_PI': top25((V.li_phase * np.where(V.knockout == 1, 1.2, 1.0)).values, L_.values),
    'D4_rrr_gap': np.where(V.innings == 2, top25(V.rrr_gap.fillna(-99).values, (L_ & V.innings.eq(2)).values), 0),
    'D5_wicket_stress': top25(V.wkt_stress.values, L_.values),
    'D6_close_game': V.close.values,
    'D7_leverage_stakes': top25((V.li * (0.75 + 0.5 * stakes_f)).values, L_.values),
}
for k, v in D.items():
    V[k] = v


def sb(r): return 2 * r / (1 + r) if r > -1 else np.nan


def player_rel(d, pid, val, flag, minb=60):
    x = d[d[flag] == 1].assign(h=lambda z: z.match_n % 2)
    n = x.groupby(pid).size(); ok = n[n >= minb].index
    h = x[x[pid].isin(ok)].groupby([pid, 'h'])[val].mean().unstack().dropna()
    return (sb(h.corr().iloc[0, 1]) if len(h) > 10 else np.nan), len(h)


def gap_rel(d, pid, val, flag, minb=60):
    d = d.assign(h=d.match_n % 2)
    n = d[d[flag] == 1].groupby(pid).size(); ok = n[n >= minb].index
    g = d[d[pid].isin(ok)].groupby([pid, 'h', flag])[val].mean().unstack()
    gap = (g[1] - g[0]).unstack().dropna()
    return sb(gap.corr().iloc[0, 1]) if len(gap) > 10 else np.nan


def yty(d, pid, val, flag, minb=30):
    s = d[d[flag] == 1].groupby([pid, 'season'])[val].agg(['mean', 'size'])
    s = s[s['size'] >= minb]['mean'].unstack()
    pairs = [(s[y], s[y + 1]) for y in range(2022, 2026) if y in s and y + 1 in s]
    a = pd.concat([pd.concat([p, q], axis=1).dropna().set_axis(['a', 'b'], axis=1) for p, q in pairs])
    return a.corr().iloc[0, 1], len(a)


rows = []
fb = V[V.faced]; bw = V
tot_bat = fb.bat_wpa.abs().sum(); tot_bowl = bw.bowl_wpa.abs().sum()
for k in D:
    r = dict(definition=k, share_balls=V.loc[L_, k].mean())
    r['capture_eff_bat'] = (fb.bat_wpa.abs() * fb[k]).sum() / tot_bat / fb[k].mean()
    r['capture_eff_bowl'] = (bw.bowl_wpa.abs() * bw[k]).sum() / tot_bowl / bw[k].mean()
    for role, d, pid, wv, rv in [('bat', fb, 'batter', 'bat_wpa_oe', 'rv_bat'), ('bowl', bw, 'bowler', 'bowl_wpa_oe', 'rv_bowl')]:
        r[f'{role}_rel_wpa'], r[f'{role}_n'] = player_rel(d, pid, wv, k)
        r[f'{role}_rel_rv'], _ = player_rel(d, pid, rv, k)
        r[f'{role}_rel_gap_rv'] = gap_rel(d, pid, rv, k)
        r[f'{role}_yty_rv'], r[f'{role}_yty_pairs'] = yty(d, pid, rv, k)
    rows.append(r); print({a: (round(b, 3) if isinstance(b, float) else b) for a, b in r.items()}, flush=True)
T = pd.DataFrame(rows)
os.makedirs(res('pressure'), exist_ok=True)
T.round(3).to_csv(res('pressure/pressure_definitions.csv'), index=False)

# selection rule (fixed before looking): D1 unless another definition is at least as good on BOTH capture efficiency
# (mean of bat/bowl) and mean player reliability of run value (bat/bowl), and strictly better on one.
T['capture'] = T[['capture_eff_bat', 'capture_eff_bowl']].mean(1)
T['rel'] = T[['bat_rel_rv', 'bowl_rel_rv']].mean(1)
d1 = T.set_index('definition').loc['D1_leverage']
better = T[(T.capture >= d1.capture) & (T.rel >= d1.rel) & ((T.capture > d1.capture) | (T.rel > d1.rel))]
chosen = better.sort_values('capture', ascending=False).definition.iloc[0] if len(better) else 'D1_leverage'
json.dump({'chosen': chosen, 'KW_runs_per_wicket': KW}, open(res('pressure/chosen_pressure.json'), 'w'))
keep = ['row', 'match_id', 'innings', 'season', 'batter', 'bowler'] + list(D)
V[keep].to_parquet(w('values/pressure_flags_final.parquet'), index=False)
show = T[['definition', 'share_balls', 'capture_eff_bat', 'capture_eff_bowl', 'bat_rel_wpa', 'bat_rel_rv', 'bat_rel_gap_rv',
          'bat_yty_rv', 'bowl_rel_wpa', 'bowl_rel_rv', 'bowl_rel_gap_rv', 'bowl_yty_rv']]
Lr = ['# Pressure-definition comparison (S3.2)', '',
      f'RR-pack balls 2022-26. Run value uses KW = {KW:.1f} runs per wicket (OLS of batter WPA on runs and dismissals '
      'over expectation). Reliability = split-half (odd/even matches), Spearman-Brown corrected, players with >= 60 '
      'flagged balls. `rel_gap` = reliability of (flagged minus unflagged) run value, i.e. a pressure-specific skill. '
      'yty = season-to-season correlation (>= 30 flagged balls in both seasons).', '',
      show.round(3).to_markdown(index=False), '',
      f'- Rule fixed in advance: keep D1 (learned leverage) unless another definition is at least as good on both capture '
      f'and reliability and strictly better on one. **Chosen: {chosen}.** The others are kept as sensitivity checks (S4D).']
open(res('pressure/PRESSURE_DEFS.md'), 'w').write('\n'.join(Lr))
print('\n'.join(Lr))
