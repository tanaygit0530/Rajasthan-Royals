"""S2.6: match context that the first build lacked (gap review, 15 Nov 2026).

  1. venue_key     one key per ground across RR pack + Cricsheet (RR venue ids named via paired matches;
                   Cricsheet names normalised + known renames merged)
  2. knockout_v2   RR: knock_out/stage (as before). Cricsheet: un-numbered matches played after the last numbered
                   match of a numbered tournament (Cricsheet gives no stage field; playoffs/semis/finals carry no
                   match_number)
  3. stakes        IPL league games: P(qualify | win) - P(qualify | lose) per team, Monte Carlo over the remaining
                   fixtures (coin-flip results, random tie-break), using only results known before the match
  4. day_night     IPL double-header days: lower match number = afternoon ('day'), other IPL games 'night';
                   all other competitions 'unknown' (the RR timestamp column holds dates only)
  5. rain fixes    RR matches with a shortened first innings but no recorded target -> target/overs from the paired
                   Cricsheet match where available
  6. impact_era    IPL 2023+ (Impact Player substitute rule)
Outputs: v2_work/unified/match_context.parquet, team_stakes.parquet; v2_results/context/*.csv, CONTEXT_REPORT.md
"""
import re
import zipfile
from common import *

rng = seed_all()
M = pd.read_parquet(w('unified/matches.parquet'))
CM = pd.read_parquet(w('public/cs_matches.parquet'))
ov = pd.read_parquet(w('public/match_overlap.parquet'))
rm = rr('matches.csv')
teams = rr('teams.csv').drop_duplicates('team_id').set_index('team_id').team_name
L = ['# Match context build (S2.6)', '']

# ---------------- Cricsheet match_number (not kept by s03) ----------------
mn = {}
for f in sorted(os.listdir(os.path.join(PUB, 'zips'))):
    key = f.split('_male')[0]
    with zipfile.ZipFile(os.path.join(PUB, 'zips', f)) as z:
        for n in z.namelist():
            if n.endswith('_info.csv'):
                txt = z.read(n).decode('utf-8')
                g = re.search(r'^info,match_number,(\d+)', txt, re.M)
                mn[f"{key}_{n.replace('_info.csv', '')}"] = int(g.group(1)) if g else np.nan
CM['match_number'] = CM.match_id.map(mn)

# ---------------- 1. venues ----------------
RENAME = {  # same ground, different (sponsor / official) names in Cricsheet
    'feroz shah kotla': 'arun jaitley stadium', 'sardar patel stadium': 'narendra modi stadium',
    'punjab cricket association is bindra stadium': 'punjab cricket association stadium',
    'westpac stadium': 'sky stadium', 'metricon stadium': 'heritage bank stadium',
    'brisbane cricket ground': 'the gabba', 'woolloongabba': 'the gabba', 'the rose bowl': 'the ageas bowl',
    'rose bowl': 'the ageas bowl', 'hampshire bowl': 'the ageas bowl', 'utilita bowl': 'the ageas bowl',
    'sophia gardens': 'sophia gardens cardiff', 'dubai international cricket stadium': 'dubai international stadium',
    'sheikh zayed stadium': 'zayed cricket stadium', 'bharat ratna shri atal bihari vajpayee ekana cricket stadium': 'ekana cricket stadium',
    'maharashtra cricket association stadium': 'mca stadium pune', 'subrata roy sahara stadium': 'mca stadium pune',
    'dr dy patil sports academy': 'dy patil stadium', 'dr. dy patil sports academy': 'dy patil stadium',
    'ma chidambaram stadium chepauk': 'ma chidambaram stadium', 'm.chinnaswamy stadium': 'm chinnaswamy stadium',
    'rajiv gandhi international cricket stadium': 'rajiv gandhi international stadium',
    'himachal pradesh cricket association stadium': 'hpca stadium', 'barsapara stadium': 'barsapara cricket stadium',
    'national stadium karachi': 'national stadium', 'gaddafi stadium lahore': 'gaddafi stadium'}


def vkey(v):
    if not isinstance(v, str) or not v:
        return None
    k = v.split(',')[0].lower().replace('.', ' ').replace("'", '')
    k = ' '.join(k.split())
    return 'cs:' + RENAME.get(k, k)


# name alone is ambiguous ('County Ground' = Taunton, Hove, Bristol, Chelmsford, Northampton...) -> key = name | city;
# missing city filled with the most common city recorded for that ground name
_nm = CM.venue.map(vkey)
_city = CM.city.replace('', np.nan).replace({'Hove': 'Brighton'}).fillna(CM.groupby(_nm).city.transform(lambda s: s.mode().iat[0] if s.notna().any() else None))
_city = _city.fillna(CM.venue.str.split(',').str[-1].str.strip().where(CM.venue.str.contains(','))).replace({'Hove': 'Brighton'}).fillna('')
CM['venue_key'] = _nm + '|' + _city.str.lower().str.strip()
# RR venue id -> Cricsheet venue key by vote over paired, well-aligned matches
pv = ov[ov.aligned].merge(rm[['match_id', 'venue_id']], on='match_id').merge(CM[['match_id', 'venue_key']].rename(
    columns={'match_id': 'cs_match'}), on='cs_match')
vv = pv.groupby(['venue_id', 'venue_key']).size().rename('n').reset_index().sort_values('n', ascending=False)
vtop = vv.drop_duplicates('venue_id').set_index('venue_id')
vtop['share'] = vtop.n / pv.groupby('venue_id').size()
RRV = {vid: (r.venue_key if r.share >= 0.6 else f'rr:{vid}') for vid, r in vtop.iterrows()}
rm['venue_key'] = rm.venue_id.map(lambda x: RRV.get(x, f'rr:{x}'))
vtop.reset_index().to_csv(res('context/rr_venue_to_cricsheet.csv'), index=False)
L += [f'- Venues: RR venue ids named via paired matches: {sum(not v.startswith("rr:") for v in RRV.values())} of '
      f'{rm.venue_id.nunique()} (vote share >= 0.6); the rest keep an RR-only key. Cricsheet distinct venue names '
      f'{CM.venue.nunique()} -> keys {CM.venue_key.nunique()} after normalisation and {len(RENAME)} known renames.']

# ---------------- 2. knockouts in Cricsheet ----------------
CM['date'] = pd.to_datetime(CM.date)
# tournament instance = same comp + event, new instance after a >60-day gap (BBL etc. span Dec-Jan)
CM = CM.sort_values(['comp_key', 'event', 'date']).reset_index(drop=True)
_ek = CM.comp_key + '|' + CM.event.fillna('')
_new = _ek.ne(_ek.shift()) | CM.date.diff().dt.days.gt(60)
CM['ev'] = _ek + '|' + _new.cumsum().astype(str)
g = CM.groupby('ev')
numbered_share = g.match_number.apply(lambda s: s.notna().mean())
last_numbered = CM[CM.match_number.notna()].groupby('ev').date.max()
CM['knockout_v2'] = (CM.ev.map(numbered_share).ge(0.6) & CM.match_number.isna() & g.date.transform('size').ge(8)
                     & (CM.date >= CM.ev.map(last_numbered))).astype(int)
ko = CM[CM.knockout_v2 == 1]
ko.groupby(['comp', 'season']).size().rename('knockouts').to_csv(res('context/cricsheet_knockouts_by_comp.csv'))
# check against known structure: IPL 2019-21 have 4 playoff games a season (3 in 2020+? -> Q1, Elim, Q2, Final = 4)
L += [f'- Cricsheet knockouts identified: {len(ko)} matches. IPL by season: '
      f'{ko[ko.comp == "IPL"].groupby("season").size().to_dict()} (expected 4 per season: Q1, Eliminator, Q2, Final).']

# ---------------- 3. IPL qualification stakes (RR pack, 2022-26) ----------------
ipl = M[(M.source == 'RR') & (M.comp == 'IPL')][['match_id', 'date', 'season', 'stage']].copy()
ipl['rid'] = ipl.match_id.str[2:].astype(int)
ipl = ipl.merge(rm[['match_id', 'match_number', 'home_team_id', 'away_team_id', 'win_team_id']].rename(
    columns={'match_id': 'rid'}), on='rid')
lg = ipl[ipl.stage.eq('League')].sort_values(['season', 'date', 'match_number']).reset_index(drop=True)
NSIM = 4000
st_rows = []
for s, d in lg.groupby('season'):
    T = sorted(set(d.home_team_id) | set(d.away_team_id)); ti = {t: i for i, t in enumerate(T)}
    h = d.home_team_id.map(ti).values; a = d.away_team_id.map(ti).values
    win = d.win_team_id.map(ti).values  # NaN = no result -> 1 point each
    for k in range(len(d)):
        base = np.zeros(len(T))
        for j in range(k):
            if np.isnan(win[j]): base[h[j]] += 1; base[a[j]] += 1
            else: base[int(win[j])] += 2
        rest = np.arange(k + 1, len(d))
        out = {}
        for forced in (h[k], a[k]):
            P = np.tile(base, (NSIM, 1)); P[:, forced] += 2
            hw = rng.random((NSIM, len(rest))) < 0.5
            np.add.at(P, (np.repeat(np.arange(NSIM), len(rest)), np.where(hw, h[rest], a[rest]).ravel()), 2)
            P = P + rng.random(P.shape) * 0.5                      # random tie-break (NRR stand-in)
            rank = (-P).argsort(1).argsort(1)
            out[forced] = (rank < 4).mean(0)
        p_h_win, p_h_lose = out[h[k]][h[k]], out[a[k]][h[k]]
        p_a_win, p_a_lose = out[a[k]][a[k]], out[h[k]][a[k]]
        for team, pw, pl in [(T[h[k]], p_h_win, p_h_lose), (T[a[k]], p_a_win, p_a_lose)]:
            st_rows.append(dict(match_id=d.match_id.iloc[k], season=s, team=teams.get(team), p_qual_if_win=pw,
                                p_qual_if_lose=pl, stakes=pw - pl, games_before=k))
TS = pd.DataFrame(st_rows)
ko_rr = ipl[~ipl.stage.eq('League')].match_id
TS = pd.concat([TS, pd.DataFrame([dict(match_id=m_, team=teams.get(t_), stakes=1.0, p_qual_if_win=np.nan,
                                       p_qual_if_lose=np.nan, season=ipl.set_index('match_id').season[m_])
                                  for m_ in ko_rr for t_ in ipl.set_index('match_id').loc[m_, ['home_team_id', 'away_team_id']]])],
               ignore_index=True)
TS.to_parquet(w('unified/team_stakes.parquet'), index=False)
TS.groupby('season').stakes.describe().round(3).to_csv(res('context/ipl_stakes_by_season.csv'))
late = TS[TS.games_before >= 56]
L += [f'- IPL qualification stakes (Monte Carlo, {NSIM} sims/match, coin-flip remaining results): league-game '
      f'median {TS[TS.games_before.notna()].stakes.median():.2f}; last 14 league games: share with stakes < 0.05 '
      f'(dead rubber for that team) = {(late.stakes < 0.05).mean():.0%}, share with stakes > 0.5 = '
      f'{(late.stakes > 0.5).mean():.0%}. Playoff games set to 1.0.']

# ---------------- 4. day / night (IPL double-headers) ----------------
ip_cs = CM[CM.comp.eq('IPL') & CM.match_id.isin(M.match_id)][['match_id', 'date', 'match_number']]   # exclude Cricsheet copies of RR-pack games
ip_rr = ipl[['match_id', 'date', 'match_number']]
both = pd.concat([ip_rr, ip_cs]); both['date'] = pd.to_datetime(both.date)
both['n_day'] = both.groupby('date').match_id.transform('size')
both['first'] = both.groupby('date').match_number.transform('min').eq(both.match_number)
both['day_night'] = np.where((both.n_day >= 2) & both['first'], 'day', 'night')
DN = both.set_index('match_id').day_night

# ---------------- 5. rain fixes ----------------
gap = rm[rm.first_inn_revised_overs.notna() & rm.revised_target.isna() & ~rm.result.str.contains('No Result|Abandoned', na=False)]
fix = gap[['match_id', 'first_inn_revised_overs']].merge(ov, on='match_id', how='left').merge(
    CM[['match_id', 'target_runs', 'target_overs']].rename(columns={'match_id': 'cs_match'}), on='cs_match', how='left')
fix.to_csv(res('context/rain_fix_candidates.csv'), index=False)
RAIN = {}
for r in fix.itertuples():
    if pd.notna(r.target_runs):
        RAIN['rr' + str(r.match_id)] = (float(r.target_runs), float(r.target_overs) * 6 if pd.notna(r.target_overs) else r.first_inn_revised_overs)
    else:  # no public target: equal overs, par target = first-innings total + 1 (flagged)
        RAIN['rr' + str(r.match_id)] = (np.nan, r.first_inn_revised_overs)
n_rev = rm.revised_target.notna().sum(); n_short = rm[['first_inn_revised_overs', 'second_inn_revised_overs', 'revised_target']].notna().any(axis=1).sum()
L += [f'- Rain: {n_short} RR matches have reduced overs (the audit count); {n_rev} have a revised target (the baseline/report '
      f'count). The {n_short - n_rev} in between are {n_short - n_rev - len(gap)} no-result/abandoned games (no chase) plus '
      f'{len(gap)} completed games with a shortened first innings and no recorded target: '
      + '; '.join(f'{k}: target {v[0]}, chase balls {v[1]}' for k, v in RAIN.items())
      + '. The baseline treated these as a full 120-ball chase of first-innings total + 1.']

# ---------------- assemble ----------------
C = M[['match_id', 'source', 'comp', 'comp2', 'season', 'knockout', 'revised_target', 'inn2_overs']].copy()
rr_vk = ('rr' + rm.match_id.astype(str)).to_frame('match_id').assign(venue_key=rm.venue_key.values).set_index('match_id').venue_key
C['venue_key'] = C.match_id.map(rr_vk).fillna(C.match_id.map(CM.set_index('match_id').venue_key)).fillna('unknown')
C['knockout_v2'] = np.where(C.source.eq('RR'), C.knockout, C.match_id.map(CM.set_index('match_id').knockout_v2)).astype(int)
C['day_night'] = C.match_id.map(DN).fillna('unknown')
C['impact_era'] = (C.comp.eq('IPL') & C.season.ge(2023)).astype(int)
C['target_v2'] = C.revised_target; C['chase_balls_v2'] = C.inn2_overs
for k, (tg, bl) in RAIN.items():
    C.loc[C.match_id == k, 'target_v2'] = tg; C.loc[C.match_id == k, 'chase_balls_v2'] = bl
C['rain_fix'] = C.match_id.isin(RAIN.keys())
C.drop(columns=['revised_target', 'inn2_overs']).to_parquet(w('unified/match_context.parquet'), index=False)

# ---------------- diagnostics: dew (spin, IPL, by innings x day/night) and impact-era wicket cost ----------------
B = pd.read_parquet(w('unified/balls.parquet'), columns=['match_id', 'innings', 'over', 'legal', 'bowl_runs', 'bowl_wkt',
                                                         'pace_spin', 'total', 'wkts_before', 'comp', 'season', 'source'])
B = B[B.comp.eq('IPL')].merge(C[['match_id', 'day_night', 'impact_era']], on='match_id')
dew = B[B.pace_spin.notna()].groupby(['pace_spin', 'day_night', 'innings']).apply(
    lambda d: pd.Series({'balls': d.legal.sum(), 'econ': d.bowl_runs.sum() / d.legal.sum() * 6,
                         'wkts_per_24': d.bowl_wkt.sum() / d.legal.sum() * 24}), include_groups=False).round(2)
dew.to_csv(res('context/dew_check_ipl.csv'))
L += ['', '## Dew check (IPL 2022-26, RR pack): economy by innings and day/night', '', dew.reset_index().to_markdown(index=False)]
# runs scored after over 10 by wickets lost at over 10, before vs after Impact Player
inn = B.groupby(['match_id', 'innings'])
B['runs_after'] = inn.total.transform('sum') - inn.total.cumsum() + B.total
at10 = B[(B.over == 11)].groupby(['match_id', 'innings']).first().reset_index()
at10 = at10[at10.innings == 1]
wc = at10.groupby(['impact_era', at10.wkts_before.clip(0, 6)]).runs_after.agg(['mean', 'size']).round(1).unstack(0)
wc.to_csv(res('context/impact_era_wicket_cost.csv'))
L += ['', '## Impact Player era: first-innings runs scored after over 10, by wickets already lost (0 = pre-2023, 1 = 2023+)', '',
      wc.to_markdown()]
os.makedirs(res('context'), exist_ok=True)
open(res('context/CONTEXT_REPORT.md'), 'w').write('\n'.join(L))
print('\n'.join(L))
