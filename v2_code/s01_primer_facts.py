"""S1: game-context facts for CRICKET_PRIMER.md, computed from the RR data pack.
Output: v2_results/primer/*.csv  (aggregates only - no ball-level data leaves v2_work)
"""
from common import *

b = rr('ball_by_ball.csv')
m = rr('matches.csv').merge(rr('competitions.csv')[['comp_id', 'comp_name', 'match_format']], on='comp_id')
m['season'] = m.match_date.str[:4].astype(int)
m['comp'] = np.where(m.comp_name.str.startswith('IPL'), 'IPL',
                     np.where(m.match_format.eq('T20I'), 'T20I', 'A-team'))
b = b[b.innings.isin([1, 2])].merge(m[['match_id', 'season', 'comp', 'win_team_id', 'revised_target',
                                       'first_inn_revised_overs', 'second_inn_revised_overs']], on='match_id')
et = b.extras_type.fillna('')
b['legal'] = ~et.isin(['wide', 'Overstep', 'other'])
b['total'] = b.runs + b.extras1_runs + b.extras_2_runs
b['phase'] = phase_of(b.overid)
b['wkt'] = b.is_wicket & ~b.dismissal_type.eq('Retire Out')

# 1. run rate and wicket rate by competition x season x phase
g = b.groupby(['comp', 'season', 'phase']).agg(runs=('total', 'sum'), legal=('legal', 'sum'), wkts=('wkt', 'sum'),
                                               sixes=('is_six', 'sum'), fours=('is_four', 'sum'))
g['run_rate'] = g.runs / g.legal * 6
g['balls_per_wkt'] = g.legal / g.wkts
g['balls_per_six'] = g.legal / g.sixes
g.round(2).to_csv(res('primer/run_rate_by_comp_season_phase.csv'))

# 2. innings totals (full 20-over, no revision) by comp x season
full = m[m.first_inn_revised_overs.isna() & m.second_inn_revised_overs.isna() & m.revised_target.isna()].match_id
inn = b[b.match_id.isin(full)].groupby(['match_id', 'innings', 'comp', 'season']).total.sum().reset_index()
t1 = inn[inn.innings == 1].groupby(['comp', 'season']).total.describe(percentiles=[.25, .5, .75])
t1['share_200plus'] = inn[inn.innings == 1].groupby(['comp', 'season']).total.apply(lambda s: (s >= 200).mean())
t1.round(2).to_csv(res('primer/first_innings_totals.csv'))

# 3. chase success by target band (decided, unrevised matches)
fi = inn[inn.innings == 1][['match_id', 'total', 'comp', 'season']]
mm = m.set_index('match_id')
sec_team = b[b.innings == 2].groupby('match_id').batting_team_id.first()
fi = fi[fi.match_id.isin(sec_team.index)].copy()
fi['chase_won'] = (fi.match_id.map(sec_team) == fi.match_id.map(mm.win_team_id)).astype(float)
fi = fi[fi.match_id.map(mm.win_team_id).notna()]
fi['band'] = pd.cut(fi.total, [0, 139, 159, 179, 199, 219, 400],
                    labels=['<140', '140-159', '160-179', '180-199', '200-219', '220+'])
fi['era'] = np.where(fi.season >= 2023, '2023-26', '2022')
ch = fi.groupby(['comp', 'era', 'band'], observed=True).chase_won.agg(['mean', 'size']).round(3)
ch.to_csv(res('primer/chase_success_by_target.csv'))

print(g.loc[['IPL']].round(2).to_string())
print(t1.round(1).to_string())
print(ch.to_string())
