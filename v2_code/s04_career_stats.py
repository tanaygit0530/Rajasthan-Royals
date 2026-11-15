"""Traditional batting & bowling stats per player from the RR data pack (IPL + T20I, 2022-26).
Split by competition (IPL / T20I / A-team / All). Output: v2_results/stats/{batting,bowling}_stats.csv
Counting rules: wides are not balls faced; no-balls are; byes/leg-byes not charged to bowler;
run-outs / retired-out / obstructing not bowler wickets; 'not out' = batted and not dismissed in that innings.
"""
from common import *

b = rr('ball_by_ball.csv')
m = rr('matches.csv').merge(rr('competitions.csv')[['comp_id', 'comp_name', 'match_format']], on='comp_id')
m['comp'] = np.where(m.comp_name.str.startswith('IPL'), 'IPL', np.where(m.match_format.eq('T20I'), 'T20I', 'A-team'))
b = b[b.innings.isin([1, 2])].merge(m[['match_id', 'comp']], on='match_id')
et = b.extras_type.fillna('')
b['wide'] = et.eq('wide'); b['nb'] = et.isin(['Overstep', 'other'])
b['legal'] = ~(b.wide | b.nb)
mp = rr('competition_team_player_mapping.csv')
NAME = mp.drop_duplicates('player_id', keep='last').set_index('player_id').player_name
NAME = pd.concat([NAME, b.drop_duplicates('striker_id').set_index('striker_id').striker_name,
                  b.drop_duplicates('bowler_id').set_index('bowler_id').bowler_name])
NAME = NAME[~NAME.index.duplicated()]

# ---------------- batting: one row per player-innings ----------------
f = b[~b.wide]
inn = f.groupby(['striker_id', 'match_id', 'innings', 'comp']).agg(
    runs=('runs', 'sum'), balls=('runs', 'size'), fours=('is_four', 'sum'), sixes=('is_six', 'sum'),
    dots=('runs', lambda s: (s == 0).sum())).reset_index().rename(columns={'striker_id': 'pid'})
# batters dismissed without facing (e.g. run out as non-striker on 0 balls) still count as innings
outs = b[b.is_wicket & b.dismissed_player_id.notna() & ~b.dismissal_type.eq('Retire Out')]
outs = outs.groupby(['dismissed_player_id', 'match_id', 'innings', 'comp']).size().rename('out').reset_index() \
    .rename(columns={'dismissed_player_id': 'pid'})
outs['pid'] = outs.pid.astype(int)
inn = inn.merge(outs, on=['pid', 'match_id', 'innings', 'comp'], how='outer').fillna(
    {'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0, 'dots': 0, 'out': 0})
inn['out'] = inn.out.clip(upper=1)


def bat_table(d):
    g = d.groupby('pid').agg(matches=('match_id', 'nunique'), innings=('match_id', 'size'), not_outs=('out', lambda s: (s == 0).sum()),
                             runs=('runs', 'sum'), balls=('balls', 'sum'), outs=('out', 'sum'), highest=('runs', 'max'),
                             fifties=('runs', lambda s: ((s >= 50) & (s < 100)).sum()), hundreds=('runs', lambda s: (s >= 100).sum()),
                             ducks=('runs', lambda s: 0), fours=('fours', 'sum'), sixes=('sixes', 'sum'), dots=('dots', 'sum'))
    g['ducks'] = d[(d.runs == 0) & (d.out == 1)].groupby('pid').size().reindex(g.index).fillna(0).astype(int)
    hs_no = d.sort_values(['runs', 'out']).groupby('pid').tail(1).set_index('pid')
    g['highest'] = hs_no.runs.astype(int).astype(str) + np.where(hs_no.out == 0, '*', '')
    g['average'] = (g.runs / g.outs.replace(0, np.nan)).round(2)
    g['strike_rate'] = (g.runs / g.balls.replace(0, np.nan) * 100).round(2)
    g['balls_per_dismissal'] = (g.balls / g.outs.replace(0, np.nan)).round(1)
    g['boundary_pct'] = ((g.fours + g.sixes) / g.balls.replace(0, np.nan) * 100).round(1)
    g['dot_pct'] = (g.dots / g.balls.replace(0, np.nan) * 100).round(1)
    return g


bat = []
for comp, d in [('All', inn)] + list(inn.groupby('comp')):
    t = bat_table(d); t['comp'] = comp; bat.append(t)
bat = pd.concat(bat).reset_index()
# matches actually played (playing XI incl. impact subs who came on), not just matches batted in
xi = rr('playing_eleven.csv'); xi = xi[xi.is_played.astype(str).str.lower().eq('true')].merge(m[['match_id', 'comp']], on='match_id')
xi = xi[xi.match_id.isin(b.match_id)]
MP = pd.concat([xi.assign(comp='All'), xi]).groupby(['player_id', 'comp']).match_id.nunique()
bat['matches'] = [MP.get((p, c), np.nan) for p, c in zip(bat.pid, bat.comp)]
bat.insert(1, 'name', bat.pid.map(NAME))
bat = bat.sort_values(['comp', 'runs'], ascending=[True, False])
int_cols = ['innings', 'not_outs', 'runs', 'balls', 'outs', 'fifties', 'hundreds', 'ducks', 'fours', 'sixes', 'dots']
bat[int_cols] = bat[int_cols].astype(int)
bat.to_csv(res('stats/batting_stats.csv'), index=False)

# ---------------- bowling: one row per player-innings ----------------
b['bowl_runs'] = b.runs + np.where(b.wide | b.nb, b.extras1_runs, 0)
b['bowl_wkt'] = b.is_wicket & ~b.dismissal_type.isin(['RunOut', 'Retire Out', 'Obstracting the field', 'Obstructing the field'])
bi = b.groupby(['bowler_id', 'match_id', 'innings', 'comp']).agg(
    balls=('legal', 'sum'), runs=('bowl_runs', 'sum'), wkts=('bowl_wkt', 'sum'),
    dots=('bowl_runs', lambda s: 0), wides=('wide', 'sum'), nbs=('nb', 'sum')).reset_index().rename(columns={'bowler_id': 'pid'})
bi['dots'] = b[b.legal & (b.bowl_runs == 0)].groupby(['bowler_id', 'match_id', 'innings']).size() \
    .reindex(pd.MultiIndex.from_frame(bi[['pid', 'match_id', 'innings']])).fillna(0).values
bd = b[b.is_four | b.is_six].groupby(['bowler_id', 'match_id', 'innings']).size()
bi['bdry'] = bd.reindex(pd.MultiIndex.from_frame(bi[['pid', 'match_id', 'innings']])).fillna(0).values


def bowl_table(d):
    g = d.groupby('pid').agg(matches=('match_id', 'nunique'), innings=('match_id', 'size'), balls=('balls', 'sum'),
                             runs=('runs', 'sum'), wickets=('wkts', 'sum'), dots=('dots', 'sum'), boundaries=('bdry', 'sum'),
                             wides=('wides', 'sum'), no_balls=('nbs', 'sum'),
                             three_w=('wkts', lambda s: (s == 3).sum()), four_w=('wkts', lambda s: (s == 4).sum()),
                             five_w_plus=('wkts', lambda s: (s >= 5).sum()))
    best = d.sort_values(['wkts', 'runs'], ascending=[False, True]).groupby('pid').head(1).set_index('pid')
    g['best'] = best.wkts.astype(int).astype(str) + '/' + best.runs.astype(int).astype(str)
    g['overs'] = (g.balls // 6).astype(int).astype(str) + '.' + (g.balls % 6).astype(int).astype(str)
    g['economy'] = (g.runs / g.balls.replace(0, np.nan) * 6).round(2)
    g['average'] = (g.runs / g.wickets.replace(0, np.nan)).round(2)
    g['strike_rate'] = (g.balls / g.wickets.replace(0, np.nan)).round(1)
    g['dot_pct'] = (g.dots / g.balls.replace(0, np.nan) * 100).round(1)
    g['boundary_pct'] = (g.boundaries / g.balls.replace(0, np.nan) * 100).round(1)
    return g


bowl = []
for comp, d in [('All', bi)] + list(bi.groupby('comp')):
    t = bowl_table(d); t['comp'] = comp; bowl.append(t)
bowl = pd.concat(bowl).reset_index()
bowl['matches'] = [MP.get((p, c), np.nan) for p, c in zip(bowl.pid, bowl.comp)]
bowl.insert(1, 'name', bowl.pid.map(NAME))
bowl = bowl.sort_values(['comp', 'wickets'], ascending=[True, False])
ic = ['innings', 'balls', 'runs', 'wickets', 'dots', 'boundaries', 'wides', 'no_balls', 'three_w', 'four_w', 'five_w_plus']
bowl[ic] = bowl[ic].astype(int)
bowl.to_csv(res('stats/bowling_stats.csv'), index=False)

pd.set_option('display.width', 250)
A = bat[bat.comp == 'All']
print('BATTING (IPL + T20I, 2022-26) players:', len(A))
print(A[['name', 'matches', 'innings', 'not_outs', 'runs', 'balls', 'highest', 'average', 'strike_rate', 'fifties', 'hundreds', 'fours', 'sixes']].head(15).to_string(index=False))
W = bowl[bowl.comp == 'All']
print('\nBOWLING players:', len(W))
print(W[['name', 'matches', 'overs', 'runs', 'wickets', 'best', 'economy', 'average', 'strike_rate', 'dot_pct', 'four_w', 'five_w_plus']].head(15).to_string(index=False))
