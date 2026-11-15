"""S2.5: one unified ball table = RR pack (all its matches, rich fields) + Cricsheet matches NOT in the RR pack.

Player key `uid`: Cricsheet identifier when known, else 'rr<player_id>' (RR players not in Cricsheet).
Outputs (v2_work/unified/): balls.parquet, matches.parquet, players.parquet
"""
from common import *

# ---------------- RR side ----------------
b = rr('ball_by_ball.csv'); b = b[b.innings.isin([1, 2])].copy()
m = rr('matches.csv').merge(rr('competitions.csv')[['comp_id', 'comp_name', 'match_format']], on='comp_id', how='left')
t = rr('teams.csv').drop_duplicates('team_id').set_index('team_id').team_name
idm = pd.read_csv(res('idmap/idmap.csv'))
idm = idm[idm.method.str.match(r'^(A_|B1_|B2_)')]
U = idm.set_index('pid').cs.to_dict()
uid = lambda s: s.map(lambda p: U.get(p, f'rr{int(p)}') if pd.notna(p) else None)

m['comp'] = np.where(m.comp_name.str.startswith('IPL'), 'IPL', np.where(m.match_format.eq('T20I'), 'T20I', 'A-team'))
m['date'] = pd.to_datetime(m.match_date)
m['knockout'] = (m.knock_out.eq(1) | m.stage.isin(['Final', 'Qualifier', 'Eliminator', 'Semi Final'])).astype(int)
et = b.extras_type.fillna('')
R = pd.DataFrame({
    'source': 'RR', 'match_id': 'rr' + b.match_id.astype(str), 'innings': b.innings, 'over': b.overid,
    'seq': b.innings_ball_num, 'bat_team': b.batting_team_id.map(t), 'bowl_team': b.bowling_team_id.map(t),
    'batter': uid(b.striker_id), 'non_striker': uid(b.non_striker_id), 'bowler': uid(b.bowler_id),
    'runs_bat': b.runs, 'wide': np.where(et.eq('wide'), b.extras1_runs, 0),
    'noball': np.where(et.isin(['Overstep', 'other']), b.extras1_runs, 0),
    'byes': np.where(et.eq('byes'), b.extras1_runs, 0), 'legbyes': np.where(et.eq('legbyes'), b.extras1_runs, 0),
    'extras_other': b.extras_2_runs + np.where(et.isin(['Penalty', '']), b.extras1_runs, 0),
    'is_wide': et.eq('wide'), 'is_nb': et.isin(['Overstep', 'other']),
    'wicket_kind': b.dismissal_type.fillna(''), 'dismissed': uid(b.dismissed_player_id),
    'is_four': b.is_four, 'is_six': b.is_six,
    # RR-only rich fields
    'bat_hand': b.batting_type, 'bowl_type': b.bowling_type, 'pace_spin': b.pace_or_spin, 'bat_pos': b.batting_order,
    'stroke': b.stroke, 'delivery': b.delivery_style, 'line': b.on_or_off, 'over_around': b.over_or_around,
    'speed': b.bowl_speed.where(b.bowl_speed > 0)})
R['rr_match'] = b.match_id.values

WK_NORM = {'Caught': 'caught', 'Bowled': 'bowled', 'LBW': 'lbw', 'RunOut': 'run out', 'Stump': 'stumped',
           'Hit Wicket': 'hit wicket', 'Retire Out': 'retired out', 'Obstracting the field': 'obstructing the field',
           'Obstructing the field': 'obstructing the field', '': ''}
R['wicket_kind'] = R.wicket_kind.map(WK_NORM)

RM = pd.DataFrame({'match_id': 'rr' + m.match_id.astype(str), 'source': 'RR', 'comp': m.comp, 'event': m.comp_name,
                   'date': m.date, 'season': m.date.dt.year, 'team1': m.home_team, 'team2': m.away_team,
                   'venue': 'rr_venue_' + m.venue_id.astype(str), 'country': m.venue_country,
                   'toss_winner': m.toss_win_team_id.map(t), 'toss_decision': m.toss_opted.str.lower(),
                   'winner': m.win_team_id.map(t), 'revised_target': m.revised_target,
                   'inn1_overs': m.first_inn_revised_overs, 'inn2_overs': m.second_inn_revised_overs,
                   'knockout': m.knockout, 'stage': m.stage})

# ---------------- Cricsheet side (exclude matches already in RR pack) ----------------
CB = pd.read_parquet(w('public/cs_balls.parquet')); CM = pd.read_parquet(w('public/cs_matches.parquet'))
ov = pd.read_parquet(w('public/match_overlap.parquet'))
keep = ~CM.match_id.isin(ov.cs_match)
CM = CM[keep]; CB = CB[CB.match_id.isin(CM.match_id)].copy()
CB = CB[CB.innings.isin([1, 2])]
wk = CB.wicket_type.fillna('')
# a second dismissal on the same ball (rare) is kept in other_* - treat as run-out style non-bowler dismissal
C = pd.DataFrame({
    'source': 'CS', 'match_id': CB.match_id, 'innings': CB.innings, 'over': CB.over, 'seq': CB.seq + 1,
    'bat_team': CB.batting_team, 'bowl_team': CB.bowling_team,
    'batter': CB.striker_cs, 'non_striker': CB.non_striker_cs, 'bowler': CB.bowler_cs,
    'runs_bat': CB.runs_off_bat, 'wide': CB.wides, 'noball': CB.noballs, 'byes': CB.byes, 'legbyes': CB.legbyes,
    'extras_other': CB.penalty, 'is_wide': CB.wides > 0, 'is_nb': CB.noballs > 0,
    'wicket_kind': wk.replace({'caught and bowled': 'caught', 'retired hurt': 'retired hurt'}),
    'dismissed': CB.player_dismissed_cs,
    'is_four': CB.runs_off_bat.eq(4) & CB.get('non_boundary', pd.Series(index=CB.index)).isna(),
    'is_six': CB.runs_off_bat.eq(6)})
CMM = pd.DataFrame({'match_id': CM.match_id, 'source': 'CS', 'comp': CM.comp, 'event': CM.event, 'date': pd.to_datetime(CM.date),
                    'season': CM.season, 'team1': CM.team1, 'team2': CM.team2, 'venue': CM.venue, 'country': None,
                    'toss_winner': CM.toss_winner, 'toss_decision': CM.toss_decision, 'winner': CM.winner,
                    'revised_target': np.where(CM.method.notna(), CM.target_runs, np.nan),
                    'inn1_overs': np.nan, 'inn2_overs': np.where(CM.method.notna(), CM.target_overs, np.nan),
                    'knockout': np.nan, 'stage': None, 'outcome': CM.outcome})

B = pd.concat([R, C], ignore_index=True)
M = pd.concat([RM, CMM], ignore_index=True)
# T20I split: both teams ICC full members vs any associate team involved
FULL = {'India', 'Australia', 'England', 'South Africa', 'New Zealand', 'Pakistan', 'Sri Lanka', 'West Indies',
        'Afghanistan', 'Bangladesh', 'Zimbabwe', 'Ireland'}
full_game = M.team1.isin(FULL) & M.team2.isin(FULL)
M['comp2'] = np.where(M.comp.eq('T20I'), np.where(full_game, 'T20I-Full', 'T20I-Assoc'),
                      np.where(M.comp.eq('Unofficial T20I'), 'T20I-Assoc', M.comp))

# ---------------- derived per-ball fields (source-independent) ----------------
B['legal'] = ~(B.is_wide | B.is_nb)
B['total'] = B.runs_bat + B.wide + B.noball + B.byes + B.legbyes + B.extras_other
B['bowl_runs'] = B.runs_bat + B.wide + B.noball
NONBOWL = {'run out', 'retired out', 'retired hurt', 'obstructing the field', 'retired not out', ''}
B['bowl_wkt'] = ~B.wicket_kind.isin(NONBOWL)
B['wkt_any'] = B.wicket_kind.ne('') & ~B.wicket_kind.isin({'retired hurt', 'retired not out'})
B['striker_out'] = B.wkt_any & (B.dismissed == B.batter) & B.wicket_kind.ne('retired out')
B['faced'] = ~B.is_wide
B = B.merge(M[['match_id', 'comp', 'comp2', 'season', 'date']], on='match_id', how='left')
B = B.sort_values(['match_id', 'innings', 'seq'], kind='stable').reset_index(drop=True)
g = B.groupby(['match_id', 'innings'], sort=False)
B['score_before'] = g.total.cumsum() - B.total
B['legal_before'] = g.legal.cumsum() - B.legal.astype(int)
B['wkts_before'] = g.wkt_any.cumsum() - B.wkt_any.astype(int)
B['phase'] = phase_of(B.over)

tot = B.groupby(['match_id', 'innings']).total.sum().unstack()
M['inn1_total'] = M.match_id.map(tot.get(1)); M['inn2_total'] = M.match_id.map(tot.get(2))
first_bat = B[B.innings == 1].groupby('match_id').bat_team.first()
M['bat_first'] = M.match_id.map(first_bat)

# ---------------- players ----------------
people = pd.read_csv(os.path.join(PUB, 'people.csv')).set_index('identifier')
idm_all = pd.read_csv(res('idmap/idmap.csv'))
names = {}
for r in idm_all.itertuples():
    k = U.get(r.pid, f'rr{int(r.pid)}')
    names[k] = r.rr_name
ids = pd.unique(pd.concat([B.batter, B.bowler, B.non_striker]).dropna())
P = pd.DataFrame({'uid': ids})
P['name'] = P.uid.map(names).fillna(P.uid.map(people.unique_name))
P['cs_name'] = P.uid.map(people.unique_name)
P['key_cricinfo'] = P.uid.map(people.key_cricinfo)
rrpid = {U.get(p, f'rr{int(p)}'): p for p in idm_all.pid}
P['rr_pid'] = P.uid.map(rrpid)

os.makedirs(w('unified'), exist_ok=True)
B.to_parquet(w('unified/balls.parquet'), index=False)
M.to_parquet(w('unified/matches.parquet'), index=False)
P.to_parquet(w('unified/players.parquet'), index=False)

# ---------------- checks ----------------
print('balls', len(B), 'matches', B.match_id.nunique(), 'players', len(P))
print(B.groupby(['source', 'comp']).match_id.nunique().unstack(0).fillna(0).astype(int).to_string())
rrb = rr('ball_by_ball.csv'); rrb = rrb[rrb.innings <= 2]
chk = dict(runs=(B[B.source == 'RR'].runs_bat.sum(), rrb.runs.sum()),
           total=(B[B.source == 'RR'].total.sum(), (rrb.runs + rrb.extras1_runs + rrb.extras_2_runs).sum()),
           wickets=(B[B.source == 'RR'].wkt_any.sum(), rrb.is_wicket.sum()))
print('RR reconciliation (unified, raw):', chk)
print('Cricsheet: share of balls with null batter/bowler id:', B.loc[B.source == 'CS', ['batter', 'bowler']].isna().mean().round(5).to_dict())
print('legal balls/innings > 120:', int((B.groupby(['match_id', 'innings']).legal.sum() > 120).sum()))
