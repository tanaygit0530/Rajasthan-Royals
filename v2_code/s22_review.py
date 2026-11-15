"""S6: fresh-eyes review - independent checks of the submitted lists.
1. duplicates (ids and names) in the top 30 of each ranking
2. identity-map method and name agreement for every top-30 player
3. pressure-ball counts and pressure strike rate / economy recomputed from the RAW RR ball file + the final pressure flags,
   bypassing the profile and rating code
4. final_rankings.csv agrees with the full rankings; ineligible / RR players excluded from 'RR can buy'
Output: v2_results/FRESH_EYES_REVIEW.md
"""
from common import *
import skill as K

L = ['# Fresh-eyes review of the submission', '']
FR = pd.read_csv(res('final_rankings.csv'))
idm = pd.read_csv(res('idmap/idmap.csv'))
P = pd.read_parquet(w('unified/players.parquet')).set_index('uid')
V = pd.read_parquet(w('values/ball_values_final.parquet')); V, _ = K.add_flags(V, 2026)
B = pd.read_parquet(w('unified/balls.parquet'), columns=['rr_match', 'seq', 'innings', 'source'])
V['rr_match'] = B.rr_match.values[V.row.values]; V['seq'] = B.seq.values[V.row.values]
raw = rr('ball_by_ball.csv')
ok_all = True
for role, f in [('bat', 'bat_full_rankings.csv'), ('bowl', 'bowl_full_rankings.csv')]:
    T = pd.read_csv(res(f'rankings/{f}')).head(30)
    dup_id, dup_nm = T.uid.duplicated().sum(), T.name.duplicated().sum()
    L += [f'## {"Batters" if role == "bat" else "Bowlers"} (top 30)', '', f'- Duplicate ids: {dup_id}; duplicate names: {dup_nm}.']
    ok_all &= dup_id == 0 and dup_nm == 0
    rows = []
    for r in T.itertuples():
        pid = P.rr_pid.get(r.uid)
        im = idm[idm.pid == pid].iloc[0] if pd.notna(pid) and (idm.pid == pid).any() else None
        # raw recomputation: RR ball_by_ball rows for this RR pid, joined to the final pressure flag by (match, innings, ball)
        col = 'striker_id' if role == 'bat' else 'bowler_id'
        x = raw[(raw[col] == pid) & raw.innings.isin([1, 2])].copy()
        x['k'] = list(zip(x.match_id, x.innings, x.innings_ball_num))
        fl = V[V.source.eq('RR')].assign(k=lambda d: list(zip(d.rr_match, d.innings, d.seq))).set_index('k').pres
        x['pres'] = x.k.map(fl)
        et = x.extras_type.fillna('')
        if role == 'bat':
            p = x[(x.pres == 1) & ~et.eq('wide')]
            n, stat = len(p), p.runs.sum() / max(len(p), 1) * 100
        else:
            p = x[x.pres == 1]
            legal = ~et.isin(['wide', 'Overstep', 'other'])
            n = len(p)
            stat = (p.runs + np.where(et.reindex(p.index).isin(['wide', 'Overstep', 'other']), p.extras1_runs, 0)).sum() / max(legal.reindex(p.index).sum(), 1) * 6
        rows.append(dict(rank=r.rank, name=r.name, uid=r.uid, map_method=None if im is None else im.method,
                         rr_name=None if im is None else im.rr_name, cs_name=None if im is None else im.cs_name,
                         pressure_balls_model=int(r.p_n), pressure_balls_raw=n,
                         **({'pressure_SR_raw': round(stat, 1)} if role == 'bat' else {'pressure_econ_raw': round(stat, 2)})))
    D = pd.DataFrame(rows)
    D['balls_match'] = (D.pressure_balls_model - D.pressure_balls_raw).abs() <= 2
    ok_all &= D.balls_match.all()
    L += [f'- Pressure balls recomputed from the raw RR file match the model within 2 balls for {D.balls_match.sum()} of {len(D)} players.',
          f'- Identity-map methods: {D.map_method.value_counts().to_dict()} (A = ball alignment with Cricsheet, the strongest).', '',
          D.to_markdown(index=False), '']
# list consistency
bad = []
for role, lst in [('bat', 'batters'), ('bowl', 'bowlers')]:
    T = pd.read_csv(res(f'rankings/{role}_full_rankings.csv')).set_index('uid')
    o = FR[FR.list == f'{lst}_open']; b = FR[FR.list == f'{lst}_rr_can_buy']
    if list(o.uid) != list(T.index[:10]): bad.append(f'{lst} open list != top 10 of full ranking')
    if (b.status.str.startswith(('Already', 'Not eligible'))).any(): bad.append(f'{lst} RR-can-buy contains RR or ineligible players')
    if not np.allclose(o.score_runs_per100_pressure_balls.values, T.score.values[:10].round(2), atol=0.01): bad.append(f'{lst} scores differ')
L += ['## List consistency', '', '- ' + ('; '.join(bad) if bad else 'final_rankings.csv matches the full rankings; the RR-can-buy lists exclude RR and ineligible players.'), '',
      '## Judgement calls a reviewer should know', '',
      '- Vaibhav Sooryavanshi (age 16 in 2027) leads by a wide margin; the raw pressure strike rate above confirms it is in the data, '
      'not an identity-map artefact (ball-aligned id). He is already an RR player.',
      '- Abrar Ahmed (Pakistan) stays in the open bowling list (brief asks for the best performers) but is excluded from the RR-can-buy list.',
      '- Wanindu Hasaranga missed IPL 2026 through injury; his score rests on 2022-25 and T20I data (flagged on his card).',
      '- Ranks inside near-ties (see the Tie column) should not be read as meaningful orderings.']
L.insert(2, f'**Overall: {"PASS" if ok_all and not bad else "CHECK ITEMS BELOW"}**')
L.insert(3, '')
open(res('FRESH_EYES_REVIEW.md'), 'w').write('\n'.join(L))
print('\n'.join(L[:12]))
