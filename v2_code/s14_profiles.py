"""S3B: complete player profile database (every player in the unified data: RR pack 2022-26 + Cricsheet 2019-26).

Long format: one row per (player, role, split, split_value, metric). Splits: career, competition, season,
competition x season, last 12 months (to 2026-11-15), phase, pressure vs normal (chosen definition, s11), setting vs
chasing, knockout; RR-pack-only splits: vs pace/spin, vs 12 bowling types, vs batting hand, bowler speed band, shot
profile, delivery-style mix. Innings-level stats (50s, 100s, consistency, innings building) for constant-within-
innings splits.
Checks: (1) reconciliation - per-player split totals sum back to the ball table; (2) spot-check of 20 well-known
players' IPL season totals in the RR pack against Cricsheet's independent scorecards of the same matches.
Outputs: v2_work/profiles/player_profiles.parquet; v2_results/profiles/player_profiles_summary.csv,
         DATA_DICTIONARY.md, reconciliation.csv, spot_check_20.csv
"""
import json
from common import *

seed_all()
LAST12 = pd.Timestamp('2025-11-15')
B = pd.read_parquet(w('unified/balls.parquet'))
B['row'] = np.arange(len(B))
B = B[B.innings.isin([1, 2])]
C = pd.read_parquet(w('unified/match_context.parquet'), columns=['match_id', 'knockout_v2', 'venue_key'])
B = B.merge(C, on='match_id', how='left')
Vf = pd.read_parquet(w('values/pressure_flags_final.parquet'))
chosen = json.load(open(res('pressure/chosen_pressure.json')))['chosen']
# pressure flag for ALL balls 2019+ (thresholds from RR 2022-26, as in s11/skill)
import skill as K
Vall = pd.read_parquet(w('values/ball_values_final.parquet'))
Vall, _ = K.add_flags(Vall, 2026)
B['pres'] = B.row.map(pd.Series(Vall.pres.values, index=Vall.row.values))
B['xruns'] = B.row.map(pd.Series(Vall.xruns.values, index=Vall.row.values))
B['rv_bat'] = B.row.map(pd.Series(Vall.rv_bat.values, index=Vall.row.values))
B['rv_bowl'] = B.row.map(pd.Series(Vall.rv_bowl.values, index=Vall.row.values))
B['setting'] = np.where(B.innings == 1, 'setting', 'chasing')
B['recent'] = np.where(B.date >= LAST12, 'last_12_months', None)
B['comp_season'] = B.comp2 + '_' + B.season.astype(str)
B['all'] = 'career'
RISKY = {'Slog', 'Slog Sweep', 'Reverse Sweep', 'Paddle Scoop', 'Reverse Paddle Scoop', 'Switch', 'UpperCut', 'Hook Shot'}
B['shot_group'] = np.select([B.stroke.isin(RISKY), B.stroke.str.contains('defens|Defense', case=False, na=False),
                             B.stroke.str.contains('Drive|Cut|Pull|Flick|Sweep|Glance|Steer', na=False), B.stroke.notna()],
                            ['risky', 'defensive', 'orthodox attacking', 'nudge/other'], None)
spd = B.speed.where(((B.pace_spin == 'Pace') & B.speed.between(100, 165)) | ((B.pace_spin == 'Spin') & B.speed.between(60, 115)))
B['speed_ok'] = spd
B['speed_band'] = np.select([(B.pace_spin == 'Pace') & (spd < 130), (B.pace_spin == 'Pace') & spd.between(130, 140),
                             (B.pace_spin == 'Pace') & (spd > 140), (B.pace_spin == 'Spin') & (spd < 85),
                             (B.pace_spin == 'Spin') & spd.between(85, 95), (B.pace_spin == 'Spin') & (spd > 95)],
                            ['pace <130', 'pace 130-140', 'pace >140', 'spin <85', 'spin 85-95', 'spin >95'], None)
DSTYLE = {'Yorker': 'yorker', 'Wide Yorker': 'wide yorker', 'Knuckle': 'slower ball', 'Slow Bouncer': 'slower ball',
          'Off Cutter': 'cutter', 'Leg Cut': 'cutter', 'Bouncer': 'bouncer', 'Googly': 'variation (googly/carrom/back of hand)',
          'Carrom': 'variation (googly/carrom/back of hand)', 'Back of Hand': 'variation (googly/carrom/back of hand)',
          'Full Toss': 'full toss'}
B['dstyle'] = B.delivery.map(DSTYLE).fillna(pd.Series(np.where(B.delivery.notna(), 'stock', None), index=B.index))

BAT_SPLITS = ['all', 'comp2', 'season', 'comp_season', 'recent', 'phase', 'pres', 'setting', 'knockout_v2',
              'pace_spin', 'bowl_type', 'speed_band', 'shot_group']
BOWL_SPLITS = ['all', 'comp2', 'season', 'comp_season', 'recent', 'phase', 'pres', 'setting', 'knockout_v2', 'bat_hand',
               'dstyle']
INN_SPLITS = ['all', 'comp2', 'season', 'comp_season', 'recent', 'setting', 'knockout_v2']


def melt(df, pid, role, split):
    df = df.reset_index().rename(columns={pid: 'pid', split: 'split_value'})
    m = df.melt(id_vars=['pid', 'split_value'], var_name='metric', value_name='value')
    m['role'] = role; m['split'] = split
    return m


# ---------------- batting, ball level ----------------
f = B[B.faced & B.batter.notna()].copy()
f['dot'] = f.runs_bat.eq(0); f['bdry'] = f.is_four | f.is_six
outs = B[B.wkt_any & B.dismissed.notna() & B.wicket_kind.ne('retired out')][['dismissed', 'match_id', 'innings', 'wicket_kind', 'row']]
OUTROW = set(outs.row)
f['out_striker'] = f.row.isin(OUTROW) & f.dismissed.eq(f.batter)
# non-striker dismissals (run outs at the non-striker's end): attach to that player's split values via the ball
ns = B[B.row.isin(OUTROW) & B.dismissed.ne(B.batter) & B.dismissed.notna()].assign(batter=lambda d: d.dismissed, ns_out=1)
parts = []
for s in BAT_SPLITS:
    g = f.groupby(['batter', s], dropna=True).agg(balls=('runs_bat', 'size'), runs=('runs_bat', 'sum'),
                                                   outs=('out_striker', 'sum'), fours=('is_four', 'sum'),
                                                   sixes=('is_six', 'sum'), dots=('dot', 'sum'), rv_sum=('rv_bat', 'sum'))
    g['outs'] = g.outs + ns.groupby(['batter', s], dropna=True).ns_out.sum().reindex(g.index).fillna(0)
    g['strike_rate'] = g.runs / g.balls * 100; g['average'] = g.runs / g.outs.replace(0, np.nan)
    g['dot_pct'] = g.dots / g.balls * 100; g['boundary_pct'] = (g.fours + g.sixes) / g.balls * 100
    g['balls_per_dismissal'] = g.balls / g.outs.replace(0, np.nan); g['run_value_per100'] = g.rv_sum / g.balls * 100
    if s == 'shot_group':
        tot = g.groupby(level=0).balls.transform('sum'); g['share_pct'] = g.balls / tot * 100
    parts.append(melt(g.drop(columns='rv_sum'), 'batter', 'bat', s))
# dismissal types
dk = outs.merge(B[['row', 'all']], on='row').groupby(['dismissed', 'wicket_kind']).size()
dk = (dk / dk.groupby(level=0).transform('sum') * 100).rename('pct').reset_index()
parts.append(pd.DataFrame({'pid': dk.dismissed, 'split_value': dk.wicket_kind, 'metric': 'dismissal_share_pct', 'value': dk.pct,
                           'role': 'bat', 'split': 'dismissal_type'}))

# ---------------- batting, innings level ----------------
inn = f.groupby(['batter', 'match_id', 'innings']).agg(runs=('runs_bat', 'sum'), balls=('runs_bat', 'size'))
first = f[['batter', 'match_id', 'innings'] + [s for s in INN_SPLITS]].drop_duplicates(['batter', 'match_id', 'innings']).set_index(['batter', 'match_id', 'innings'])
inn = inn.join(first)
oi = outs.groupby(['dismissed', 'match_id', 'innings']).size().rename('out')
inn['out'] = oi.reindex(inn.index).fillna(0).clip(upper=1).values
f['bnum'] = f.groupby(['batter', 'match_id', 'innings']).cumcount() + 1
e10 = f[f.bnum <= 10].groupby(['batter', 'match_id', 'innings']).runs_bat.agg(['sum', 'size'])
l20 = f[f.bnum > 20].groupby(['batter', 'match_id', 'innings']).runs_bat.agg(['sum', 'size'])
inn['r10'] = e10['sum'].reindex(inn.index); inn['b10'] = e10['size'].reindex(inn.index)
inn['r20p'] = l20['sum'].reindex(inn.index); inn['b20p'] = l20['size'].reindex(inn.index)
inn = inn.reset_index()
for s in INN_SPLITS:
    g = inn.groupby(['batter', s], dropna=True).agg(innings=('runs', 'size'), not_outs=('out', lambda x: (x == 0).sum()),
                                                    fifties=('runs', lambda x: ((x >= 50) & (x < 100)).sum()),
                                                    hundreds=('runs', lambda x: (x >= 100).sum()),
                                                    ducks=('runs', lambda x: 0), highest=('runs', 'max'),
                                                    score_sd=('runs', 'std'), pct_innings_30plus=('runs', lambda x: (x >= 30).mean() * 100),
                                                    r10=('r10', 'sum'), b10=('b10', 'sum'), r20p=('r20p', 'sum'), b20p=('b20p', 'sum'))
    g['ducks'] = inn[(inn.runs == 0) & (inn.out == 1)].groupby(['batter', s]).size().reindex(g.index).fillna(0)
    g['sr_first_10_balls'] = g.r10 / g.b10 * 100; g['sr_after_20_balls'] = g.r20p / g.b20p.replace(0, np.nan) * 100
    parts.append(melt(g.drop(columns=['r10', 'b10', 'r20p', 'b20p']), 'batter', 'bat', s))

# ---------------- bowling ----------------
d = B[B.bowler.notna()].copy()
d['dot'] = d.legal & d.bowl_runs.eq(0); d['bdry'] = d.is_four | d.is_six
d['spd'] = d.speed_ok
for s in BOWL_SPLITS:
    g = d.groupby(['bowler', s], dropna=True).agg(balls=('legal', 'sum'), deliveries=('legal', 'size'), runs=('bowl_runs', 'sum'),
                                                  wickets=('bowl_wkt', 'sum'), dots=('dot', 'sum'), boundaries=('bdry', 'sum'),
                                                  wides=('is_wide', 'sum'), no_balls=('is_nb', 'sum'), rv_sum=('rv_bowl', 'sum'),
                                                  speed_median=('spd', 'median'), speed_p90=('spd', lambda x: x.quantile(0.9)))
    g['economy'] = g.runs / g.balls.replace(0, np.nan) * 6; g['average'] = g.runs / g.wickets.replace(0, np.nan)
    g['strike_rate'] = g.balls / g.wickets.replace(0, np.nan); g['dot_pct'] = g.dots / g.balls.replace(0, np.nan) * 100
    g['boundary_pct'] = g.boundaries / g.balls.replace(0, np.nan) * 100; g['run_value_per100'] = g.rv_sum / g.deliveries * 100
    if s == 'dstyle':
        g['share_pct'] = g.deliveries / g.groupby(level=0).deliveries.transform('sum') * 100
    parts.append(melt(g.drop(columns='rv_sum'), 'bowler', 'bowl', s))
bi = d.groupby(['bowler', 'match_id', 'innings']).agg(w=('bowl_wkt', 'sum'), r=('bowl_runs', 'sum'))
bi = bi.join(d.drop_duplicates(['bowler', 'match_id', 'innings']).set_index(['bowler', 'match_id', 'innings'])[INN_SPLITS]).reset_index()
for s in INN_SPLITS:
    g = bi.groupby(['bowler', s], dropna=True).agg(innings=('w', 'size'), three_w=('w', lambda x: (x == 3).sum()),
                                                   four_w_plus=('w', lambda x: (x >= 4).sum()), econ_sd_runs=('r', 'std'))
    parts.append(melt(g, 'bowler', 'bowl', s))
dkb = d[d.bowl_wkt].groupby(['bowler', 'wicket_kind']).size()
dkb = (dkb / dkb.groupby(level=0).transform('sum') * 100).rename('pct').reset_index()
parts.append(pd.DataFrame({'pid': dkb.bowler, 'split_value': dkb.wicket_kind, 'metric': 'wicket_share_pct', 'value': dkb.pct,
                           'role': 'bowl', 'split': 'dismissal_type'}))

PR = pd.concat(parts, ignore_index=True)
PR['split_value'] = PR.split_value.astype(str)
PR = PR[PR.value.notna()]
PR['value'] = PR.value.astype(float)

# ---------------- identity ----------------
P = pd.read_parquet(w('unified/players.parquet')); R = pd.read_parquet(w('unified/roles.parquet'))
hand = B[B.bat_hand.notna()].groupby('batter').bat_hand.agg(lambda s: s.mode().iat[0])
btype = B[B.bowl_type.notna()].groupby('bowler').bowl_type.agg(lambda s: s.mode().iat[0])
var = d[d.pace_spin.eq('Spin') & d.delivery.notna()].groupby('bowler').delivery.apply(
    lambda s: s.isin(['Googly', 'Carrom', 'Back of Hand', 'Chinaman']).mean())
xi = rr('playing_eleven.csv'); xi = xi[xi.is_played.astype(str).str.lower().eq('true')]
idm = pd.read_csv(res('idmap/idmap.csv')); U = idm[idm.method.str.match(r'^(A_|B1_|B2_)')].set_index('pid').cs.to_dict()
xi['uid'] = xi.player_id.map(lambda p: U.get(p, f'rr{int(p)}'))
wk = xi.groupby('uid').is_wk.apply(lambda s: s.astype(str).str.lower().eq('true').mean())
cap = xi.groupby('uid').is_captain.apply(lambda s: s.astype(str).str.lower().eq('true').sum())
ID = P.set_index('uid')[['name', 'cs_name', 'key_cricinfo', 'dob']].join(R.set_index('uid'))
ID['bat_hand'] = hand; ID['bowl_type'] = btype
ID['bowl_arm'] = ID.bowl_type.str.extract(r'^(Right|Left)-arm', expand=False).fillna(ID.bowl_type.str.contains('left', case=False, na=False).map({True: 'Left', False: None}))
ID['spin_kind'] = np.select([ID.bowl_type.str.contains('Leg-Break|Chinaman', na=False), ID.bowl_type.str.contains('offbreak|orthodox', na=False)],
                            ['wrist', 'finger'], None)
ID['mystery_share'] = var
ID['mystery_spinner'] = var.reindex(ID.index) >= 0.10
ID['keeper_share'] = wk; ID['captain_matches'] = cap
ID['age_2027'] = (pd.Timestamp('2027-04-01') - pd.to_datetime(ID.dob)).dt.days / 365.25
ID['bat_balls_all'] = f.groupby('batter').size(); ID['bowl_balls_all'] = d.groupby('bowler').legal.sum()
os.makedirs(w('profiles'), exist_ok=True)
PR.to_parquet(w('profiles/player_profiles.parquet'), index=False)
ID.reset_index().to_parquet(w('profiles/player_identity.parquet'), index=False)

# ---------------- wide summary ----------------
def pick(role, split, sv, metrics, pre):
    x = PR[(PR.role == role) & (PR.split == split) & (PR.split_value == sv) & PR.metric.isin(metrics)]
    return x.pivot_table(index='pid', columns='metric', values='value').add_prefix(pre)


S = ID[['name', 'age_2027', 'bat_hand', 'bowl_type', 'bat_role', 'bowl_role', 'pace_spin', 'keeper_share']].copy()
for pre, role, split, sv, ms in [
        ('bat_', 'bat', 'all', 'career', ['innings', 'runs', 'balls', 'average', 'strike_rate', 'fifties', 'hundreds', 'boundary_pct', 'dot_pct']),
        ('bat_ipl_', 'bat', 'comp2', 'IPL', ['runs', 'balls', 'average', 'strike_rate']),
        ('bat_12m_', 'bat', 'recent', 'last_12_months', ['runs', 'balls', 'strike_rate']),
        ('bat_pres_', 'bat', 'pres', '1', ['balls', 'strike_rate', 'run_value_per100']),
        ('bowl_', 'bowl', 'all', 'career', ['balls', 'wickets', 'economy', 'average', 'strike_rate', 'dot_pct']),
        ('bowl_ipl_', 'bowl', 'comp2', 'IPL', ['balls', 'wickets', 'economy']),
        ('bowl_12m_', 'bowl', 'recent', 'last_12_months', ['balls', 'wickets', 'economy']),
        ('bowl_pres_', 'bowl', 'pres', '1', ['balls', 'economy', 'run_value_per100'])]:
    S = S.join(pick(role, split, sv, ms, pre))
S.index.name = 'uid'
S = S[(S.bat_balls.fillna(0) + S.bowl_balls.fillna(0)) > 0]
S.round(2).to_csv(res('profiles/player_profiles_summary.csv'))

# ---------------- reconciliation ----------------
rec = []
car = PR[(PR.split == 'all')].pivot_table(index=['pid', 'role'], columns='metric', values='value', aggfunc='first')
for split in ['comp2', 'season', 'phase', 'setting']:
    for role, ms in [('bat', ['runs', 'balls']), ('bowl', ['runs', 'wickets', 'balls'])]:
        sm = PR[(PR.split == split) & (PR.role == role) & PR.metric.isin(ms)].groupby(['pid', 'metric']).value.sum().unstack()
        base = car.xs(role, level='role')[ms].reindex(sm.index)
        rec.append(dict(split=split, role=role, players=len(sm), max_abs_diff=float((sm[ms] - base).abs().max().max())))
tot_runs = PR[(PR.split == 'all') & (PR.role == 'bat') & (PR.metric == 'runs')].value.sum()
rec.append(dict(split='all players vs ball table', role='bat', players=0, max_abs_diff=float(abs(tot_runs - f.runs_bat.sum()))))
pd.DataFrame(rec).to_csv(res('profiles/reconciliation.csv'), index=False)

# ---------------- spot-check: RR-pack IPL season totals vs Cricsheet's own scorecards of the same matches ----------------
ov = pd.read_parquet(w('public/match_overlap.parquet'))
CB = pd.read_parquet(w('public/cs_balls.parquet'), columns=['match_id', 'striker_cs', 'runs_off_bat', 'wides', 'bowler_cs', 'noballs'])
CM = pd.read_parquet(w('public/cs_matches.parquet'), columns=['match_id', 'season', 'comp'])
CB = CB.merge(CM, on='match_id')
CB = CB[CB.match_id.isin(ov.cs_match) & CB.comp.eq('IPL')]
rr_ipl = f[f.source.eq('RR') & f.comp.eq('IPL') & f.rr_match.isin(ov.match_id)]
WELL = ['Virat Kohli', 'Shubman Gill', 'Jos Buttler', 'Yashasvi Jaiswal', 'Sanju Samson', 'Rohit Sharma', 'Suryakumar Yadav',
        'Heinrich Klaasen', 'Travis Head', 'Ruturaj Gaikwad', 'Faf du Plessis', 'Lokesh Rahul', 'Rishabh Pant', 'Nicholas Pooran',
        'Abhishek Sharma', 'Sai Sudharsan', 'Riyan Parag', 'Shivam Dube', 'Andre Russell', 'Hardik Pandya']
nm = P.set_index('uid').name
sel = [u for u in P.uid if nm.get(u) in WELL]
a = rr_ipl[rr_ipl.batter.isin(sel)].groupby(['batter', 'season']).agg(rr_runs=('runs_bat', 'sum'), rr_balls=('runs_bat', 'size'))
cbf = CB[CB.wides.fillna(0).eq(0)]
b_ = cbf[cbf.striker_cs.isin(sel)].groupby(['striker_cs', 'season']).agg(cs_runs=('runs_off_bat', 'sum'), cs_balls=('runs_off_bat', 'size'))
b_.index.names = ['batter', 'season']
sc = a.join(b_, how='outer').reset_index()
sc['name'] = sc.batter.map(nm); sc['runs_diff'] = sc.rr_runs - sc.cs_runs; sc['balls_diff'] = sc.rr_balls - sc.cs_balls
sc.to_csv(res('profiles/spot_check_20.csv'), index=False)

# ---------------- dictionary ----------------
mlist = PR.groupby(['role', 'split']).metric.unique().apply(lambda x: ', '.join(sorted(x)))
DD = ['# Player profile database: data dictionary (S3B)', '',
      f'- `v2_work/profiles/player_profiles.parquet` (local, not committed; derived from the confidential RR pack): '
      f'{len(PR):,} rows, {PR.pid.nunique():,} players. Columns: pid (Cricsheet identifier, or rr<id> for RR-only players), '
      'role (bat/bowl), split, split_value, metric, value.',
      '- `v2_work/profiles/player_identity.parquet`: name, date of birth (Wikidata, age only), batting hand, bowling type / arm / '
      'finger vs wrist spin, mystery-spinner flag (>= 10% googly/carrom/back-of-hand/chinaman deliveries), keeper share, captain '
      'matches, batting/bowling role, part-timer flag.',
      '- `v2_results/profiles/player_profiles_summary.csv`: one row per player, headline career / IPL / last-12-months / '
      'pressure metrics.', '',
      '## Splits', '',
      '| split | meaning | source |', '|---|---|---|',
      '| all | career 2019-26 (Cricsheet) / 2022-26 (RR pack) | both |', '| comp2 | competition (T20I split into full-member / associate games) | both |',
      '| season, comp_season | calendar year | both |', '| recent | last 12 months (from 2025-11-15) | both |',
      '| phase | PP (1-6), Middle (7-15), Death (16-20) | both |',
      f'| pres | pressure ball (1) vs normal (0), definition {chosen}, top 25% of RR legal balls 2022-26 | both |',
      '| setting | setting (1st innings) vs chasing | both |', '| knockout_v2 | knockout match (1) | both |',
      '| pace_spin, bowl_type | bowler faced: pace/spin, 12 bowling types | RR pack only |',
      '| speed_band | release speed band (pace 100-165, spin 60-115 km/h kept; other values treated as missing) | RR pack only |',
      '| shot_group | risky (slog, slog sweep, reverse sweep, scoops, switch, upper cut, hook), defensive, orthodox attacking, nudge/other | RR pack only |',
      '| bat_hand | batter faced (bowling) | RR pack only |', '| dstyle | delivery-style mix (yorker, wide yorker, slower ball, cutter, bouncer, variation, full toss, stock) | RR pack only |',
      '| dismissal_type | share of dismissals / wickets by type | both |', '',
      '## Metrics by role and split', '', mlist.reset_index().to_markdown(index=False), '',
      '## Definitions', '',
      '- Balls faced exclude wides; no-balls count. Bowler runs = runs off the bat + wides + no-ball runs (byes/leg-byes excluded). '
      'Bowler wickets exclude run outs, retired out, obstructing the field. Outs include non-striker run outs.',
      f'- run_value_per100 = 100 x mean over balls of (runs - expected runs) - KW x (dismissal - expected dismissal), '
      f'KW = {K.KW:.1f} runs per wicket (s11); bowlers: the mirror image.',
      '- sr_first_10_balls / sr_after_20_balls: innings building (strike rate on balls 1-10 vs 21+ of an innings).',
      '- score_sd, pct_innings_30plus: batting consistency; econ_sd_runs: spread of runs conceded per bowling innings.', '',
      '## Not derivable from the available data', '',
      '- Fielding (catches, run outs, stumpings by fielder): neither the RR pack nor Cricsheet csv2 names fielders '
      '(Cricsheet JSON does; not downloaded). Keeper status comes from the RR playing-XI flag.',
      '- Caught in the deep vs infield, field settings, pitch type, weather.',
      '- Batting hand and bowling type for players who appear only in Cricsheet (Cricsheet has no style fields).',
      '- Bowling speed: RR pack only, missing or implausible on part of the balls (see DATA_AUDIT).',
      '- Pace/spin is unknown for Cricsheet-only bowlers, so RR-only splits are blank for them.']
open(res('profiles/DATA_DICTIONARY.md'), 'w').write('\n'.join(DD))
print(pd.DataFrame(rec).to_string())
print(sc.groupby('name')[['runs_diff', 'balls_diff']].apply(lambda x: x.abs().sum()).to_string())
print('profile rows', len(PR), 'players', PR.pid.nunique())
