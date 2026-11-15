"""S2.8: player roles, bowler pressure-building credit, and the survivorship check for next-season validation.

(a) Roles (for role-relative ratings): batting position derived from order of arrival in every innings (works for
    both sources; checked against the RR pack's batting_order); batter role from median position, 2022-26 balls.
    Bowler role from phase mix of legal balls; pace/spin from the RR pack where known; part-timer flag.
(b) Pressure building: does a tight over raise the chance of a wicket at the OTHER end in the next over?
    Over-level OLS: partner wickets next over ~ dots this over + boundaries this over + over x wickets-down + comp.
    Bowler credit = his dots/boundaries x those coefficients (expected wickets created for partners), and a
    bowler-specific residual whose split-half reliability tells us if a 'squeeze skill' beyond dots exists.
(c) Survivorship: next-season validation only sees players who are picked again. Retention rate by quartile of the
    season's performance shows how strong that selection is.
Outputs: v2_work/unified/roles.parquet, pressure_build.parquet; v2_results/context/ROLES_REPORT.md + csvs
"""
import statsmodels.formula.api as smf
from common import *

rng = seed_all()
B = pd.read_parquet(w('unified/balls.parquet'), columns=['match_id', 'innings', 'seq', 'over', 'batter', 'non_striker',
    'bowler', 'bat_pos', 'pace_spin', 'legal', 'faced', 'runs_bat', 'bowl_runs', 'bowl_wkt', 'is_four', 'is_six',
    'wkts_before', 'phase', 'comp', 'comp2', 'season', 'source'])
L = ['# Roles, pressure building, survivorship (S2.8)', '']

# ---------------- (a) batting position by order of arrival ----------------
arr = pd.concat([B[['match_id', 'innings', 'seq', 'batter']].rename(columns={'batter': 'uid'}).assign(o=0),
                 B[['match_id', 'innings', 'seq', 'non_striker']].rename(columns={'non_striker': 'uid'}).assign(o=1)]).dropna()
arr = arr.sort_values(['match_id', 'innings', 'seq', 'o']).drop_duplicates(['match_id', 'innings', 'uid'])
arr['pos'] = arr.groupby(['match_id', 'innings']).cumcount() + 1
POS = arr.set_index(['match_id', 'innings', 'uid']).pos
chk = B[B.source.eq('RR') & B.bat_pos.notna()].drop_duplicates(['match_id', 'innings', 'batter'])
chk = chk.assign(pos=POS.reindex(pd.MultiIndex.from_frame(chk[['match_id', 'innings', 'batter']])).values)
L.append(f'- Derived batting position equals the RR batting_order in {(chk.pos == chk.bat_pos).mean():.1%} of RR '
         f'innings (differences: openers swapping ends on ball 1).')

recent = B[B.season >= 2022]
bi = arr.merge(recent[['match_id']].drop_duplicates(), on='match_id')
bf = recent[recent.faced].groupby(['match_id', 'innings', 'batter']).size().rename('balls').reset_index()
bi = bi.merge(bf.rename(columns={'batter': 'uid'}), on=['match_id', 'innings', 'uid'], how='left').fillna({'balls': 0})
bat_role = bi.groupby('uid').apply(lambda d: pd.Series({
    'bat_innings': len(d), 'bat_pos_median': d.pos.median(),
    'bat_pos_wmean': np.average(d.pos, weights=d.balls + 1)}), include_groups=False)
bat_role['bat_role'] = pd.cut(bat_role.bat_pos_median, [0, 2.5, 3.5, 5.5, 7.5, 12],
                              labels=['Opener', 'No.3', 'Middle (4-5)', 'Finisher (6-7)', 'Lower order (8+)'])

lb = recent[recent.legal & recent.bowler.notna()]
ph = lb.groupby(['bowler', 'phase']).size().unstack(fill_value=0)
share = ph.div(ph.sum(1), axis=0)
nmat = lb.groupby('bowler').match_id.nunique()
bowl_role = pd.DataFrame({'bowl_balls': ph.sum(1), 'pp_share': share.get('PP'), 'mid_share': share.get('Middle'),
                          'death_share': share.get('Death'), 'balls_per_match': ph.sum(1) / nmat})
bowl_role['bowl_role'] = np.select([bowl_role.pp_share >= 0.45, bowl_role.death_share >= 0.40, bowl_role.mid_share >= 0.60],
                                   ['Powerplay', 'Death', 'Middle overs'], 'Multi-phase')
bowl_role['part_timer'] = bowl_role.balls_per_match < 12
ps = B[B.pace_spin.notna()].groupby('bowler').pace_spin.agg(lambda s: s.mode().iat[0])
bowl_role['pace_spin'] = ps.reindex(bowl_role.index)
R = bat_role.join(bowl_role, how='outer')
R.index.name = 'uid'
R.reset_index().to_parquet(w('unified/roles.parquet'), index=False)
L += ['', '## Role counts (players with >= 200 balls faced / bowled, 2022-26)', '',
      bat_role[bi.groupby('uid').balls.sum().reindex(bat_role.index).fillna(0) >= 200].bat_role.value_counts().to_frame().to_markdown(), '',
      bowl_role[bowl_role.bowl_balls >= 200].groupby(['bowl_role', 'pace_spin'], dropna=False).size().unstack(fill_value=0).to_markdown()]

# ---------------- (b) pressure building ----------------
lg = B[B.bowler.notna()]
O = lg.groupby(['match_id', 'innings', 'over'], sort=True).agg(
    bowler=('bowler', lambda s: s.mode().iat[0]), legal=('legal', 'sum'),
    dots=('bowl_runs', lambda s: 0), wkts=('bowl_wkt', 'sum'), wkts_before=('wkts_before', 'first'),
    comp=('comp2', 'first'), season=('season', 'first')).reset_index()
O['dots'] = lg[lg.legal & lg.bowl_runs.eq(0)].groupby(['match_id', 'innings', 'over']).size() \
    .reindex(pd.MultiIndex.from_frame(O[['match_id', 'innings', 'over']])).fillna(0).values
O['bdry'] = lg[lg.is_four | lg.is_six].groupby(['match_id', 'innings', 'over']).size() \
    .reindex(pd.MultiIndex.from_frame(O[['match_id', 'innings', 'over']])).fillna(0).values
O = O.sort_values(['match_id', 'innings', 'over']).reset_index(drop=True)
nx = O.groupby(['match_id', 'innings']).shift(-1)
O['next_wkts'] = nx.wkts; O['next_bowler'] = nx.bowler; O['next_over'] = nx.over
O = O[O.next_over.eq(O.over + 1) & O.next_bowler.ne(O.bowler) & O.legal.ge(6)].copy()
O['ow'] = O.over.clip(1, 20).astype(str) + '_' + O.wkts_before.clip(0, 7).astype(str)
fit = smf.ols('next_wkts ~ dots + bdry + wkts + C(ow) + C(comp)', data=O).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(O.match_id)[0]})
co = fit.params[['dots', 'bdry', 'wkts']]; se = fit.bse[['dots', 'bdry', 'wkts']]
L += ['', '## Pressure building: partner wickets in the next over (OLS, match-clustered SE)', '',
      f'- Overs used: {len(O):,} (complete overs followed by a different bowler).',
      f'- Each extra dot ball this over: {co.dots:+.4f} partner wickets next over (SE {se.dots:.4f}); each boundary '
      f'conceded: {co.bdry:+.4f} (SE {se.bdry:.4f}); a wicket this over: {co.wkts:+.4f} (SE {se.wkts:.4f}).',
      f'- Base rate of a wicket in an over: {O.next_wkts.mean():.3f}. A 4-dot over vs a 1-dot over adds '
      f'{3 * co.dots:+.4f} expected partner wickets ({3 * co.dots / O.next_wkts.mean():+.1%} relative).']
O['credit'] = co.dots * O.dots + co.bdry * O.bdry
O['resid'] = fit.resid
O['half'] = pd.factorize(O.match_id)[0] % 2
pb = O[O.season >= 2022].groupby(['bowler', 'half']).agg(n=('resid', 'size'), credit=('credit', 'mean'), resid=('resid', 'mean')).unstack()
pb = pb[(pb['n'] >= 40).all(1)]
r_credit = np.corrcoef(pb['credit'][0], pb['credit'][1])[0, 1]
r_resid = np.corrcoef(pb['resid'][0], pb['resid'][1])[0, 1]
L += [f'- Split-half reliability (odd vs even matches, bowlers with >= 40 qualifying overs in each half, n={len(pb)}): '
      f'dot/boundary-based credit r = {r_credit:.2f}; bowler-specific "squeeze" residual beyond dots r = {r_resid:.2f}.',
      '- Use: the credit (driven by dots and boundaries) enters S4 as a candidate bowler feature; it is kept only if it '
      'improves next-season prediction. A residual near zero reliability means no separate squeeze skill is claimed.']
PB = O[O.season >= 2022].groupby('bowler').agg(overs=('credit', 'size'), pb_credit_per_over=('credit', 'mean'),
                                                 pb_resid_per_over=('resid', 'mean'))
PB.reset_index().to_parquet(w('unified/pressure_build.parquet'), index=False)

# ---------------- (c) survivorship ----------------
rows = []
ipl = B[B.comp.eq('IPL')]
for s in range(2019, 2026):
    cur, nxt = ipl[ipl.season == s], ipl[ipl.season == s + 1]
    nxt_players = set(nxt.batter) | set(nxt.bowler) | set(nxt.non_striker)
    bt = cur[cur.faced].groupby('batter').agg(balls=('runs_bat', 'size'), sr=('runs_bat', 'mean'))
    bt = bt[bt.balls >= 60]
    bt['q'] = pd.qcut(bt.sr.rank(method='first'), 4, labels=['Q1 worst', 'Q2', 'Q3', 'Q4 best'])
    for q, d in bt.groupby('q', observed=True):
        rows.append(dict(role='batter (strike rate)', season=s, quartile=q, n=len(d), retained=d.index.isin(nxt_players).mean()))
    bw = cur[cur.legal].groupby('bowler').agg(balls=('bowl_runs', 'size'), rpb=('bowl_runs', 'mean'))
    bw = bw[bw.balls >= 60]
    bw['q'] = pd.qcut((-bw.rpb).rank(method='first'), 4, labels=['Q1 worst', 'Q2', 'Q3', 'Q4 best'])
    for q, d in bw.groupby('q', observed=True):
        rows.append(dict(role='bowler (economy)', season=s, quartile=q, n=len(d), retained=d.index.isin(nxt_players).mean()))
S = pd.DataFrame(rows)
S.to_csv(res('context/survivorship_ipl.csv'), index=False)
st = S.groupby(['role', 'quartile']).apply(lambda d: np.average(d.retained, weights=d.n), include_groups=False).unstack().round(2)
L += ['', '## Survivorship: share of IPL players (>= 60 balls) who play IPL again next season, by quartile, 2019-25', '',
      st.to_markdown(), '',
      '- Consequence for S4: the next-season target is missing more often for poor performers (selection on the '
      'outcome), so scoring models only on retained players understates how badly any model rates the dropped players. '
      'S4 therefore (1) reports dropout by predicted-rating decile for every model, (2) re-scores models with '
      'inverse-probability-of-retention weights, and (3) also scores on all-competition next-season balls (players '
      'dropped from the IPL often still play T20Is or other leagues).']
os.makedirs(res('context'), exist_ok=True)
open(res('context/ROLES_REPORT.md'), 'w').write('\n'.join(L))
print('\n'.join(L))
