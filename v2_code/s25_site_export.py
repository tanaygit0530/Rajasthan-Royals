"""S8: export precomputed, AGGREGATED outputs for the evaluator showcase site (site/).

Writes site/private_data/*.json (git-ignored; encrypted at site build time). Contains no ball-by-ball rows and no
data-pack files: only rankings, ratings with intervals, aggregated splits (per player x split), method tables and
sourced notes. Every number shown on the site comes from these files.
"""
import json
import shutil
import re
from common import *
import skill as K
from rr_fit_core import slots, BAT_SLOTS, BOWL_SLOTS
import s18_cards as C18          # moments() helper (main guarded)

OUT = os.path.join(ROOT, 'site', 'private_data'); os.makedirs(OUT, exist_ok=True)
rd = lambda p, **k: pd.read_csv(res(p), **k)


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 3)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return o.strftime('%Y-%m-%d')
    return o


def dump(name, obj):
    with open(os.path.join(OUT, name), 'w') as f:
        json.dump(clean(obj), f, separators=(',', ':'), allow_nan=False)
    print(name, f'{os.path.getsize(os.path.join(OUT, name)) / 1024:.0f} KB')


def recs(df, cols=None):
    d = df if cols is None else df[cols]
    return [clean(r) for r in d.replace({np.nan: None}).to_dict('records')]


ID = pd.read_parquet(w('profiles/player_identity.parquet')).set_index('uid')
CAP = pd.read_parquet(w('value/capped.parquet')).set_index('uid')
FULL = {r: rd(f'rankings/{r}_full_rankings.csv', index_col='uid') for r in ['bat', 'bowl']}
POOL = {r: rd(f'value/{r}_pool_all.csv', index_col='uid') for r in ['bat', 'bowl']}
FR = rd('final_rankings.csv')
VAL = {r: rd(f'value/{r}_uncapped_value_targets_full.csv', index_col='uid') for r in ['bat', 'bowl']}
YB = {r: pd.concat([rd(f'youth/{r}_board_u23.csv', index_col='uid').assign(board='u23'),
                    rd(f'youth/{r}_board_24_26.csv', index_col='uid').assign(board='24-26')]) for r in ['bat', 'bowl']}
YAR = rd('youth/allrounders_u23_top5.csv', index_col='uid')
NOTES = json.load(open(res('cards/scouting_notes.json')))
VD = rd('rr_fit/selector_verdicts.csv'); GAPS = rd('rr_fit/role_gaps.csv'); SHL = rd('rr_fit/role_shortlists.csv')
CAL = json.load(open(res('models/interval_calibration.json')))
PCH = json.load(open(res('pressure/chosen_pressure.json')))
CLU = {r: pd.read_parquet(w(f'explain/clusters_{r}.parquet')).cluster_label for r in ['bat', 'bowl']}
pmv = rd('value/price_model_validation.csv')
SIG = float(pmv.mae_log_model.mean() * 1.2533)          # normal-equivalent SD of log price
PMAX = float(pd.read_parquet(w('value/prices.parquet')).price_cr.max())   # highest price paid 2022-26: caps the range
Z80 = 1.2816

# ---------------- player universe ----------------
uids = set()
for r in ['bat', 'bowl']:
    uids |= set(FULL[r].index) | set(POOL[r].index) | set(YB[r].index) | set(VAL[r].index[:30])
uids |= set(YAR.index)
uids = sorted(u for u in uids if u in ID.index)


def age_of(u):
    a = ID.age_2027.get(u)
    return None if pd.isna(a) else int(np.floor(a))


def nation(u):
    for T in (FULL['bat'], FULL['bowl'], POOL['bat'], POOL['bowl']):
        if u in T.index and isinstance(T.nation.get(u), str):
            return T.nation.get(u)
    n = CAP.nationality.get(u) if 'nationality' in CAP else None
    return n if isinstance(n, str) else 'unknown'


def status(u):
    for T in (FULL['bat'], FULL['bowl'], POOL['bat'], POOL['bowl']):
        if u in T.index:
            return T.status.get(u), T.team27.get(u) if 'team27' in T else None
    for r in ['bat', 'bowl']:
        if u in YB[r].index:
            return YB[r].status_2027.get(u), None
    return None, None


def rating(u, r):
    T = FULL[r] if u in FULL[r].index else POOL[r] if u in POOL[r].index else None
    if T is None:
        return None
    x = T.loc[u]
    return dict(score=x.score, lo=x.score_lo, hi=x.score_hi, p_top10=x.p_top10,
                rank=int(FULL[r]['rank'].get(u)) if u in FULL[r].index else None,
                tier='established' if u in FULL[r].index else 'emerging', pressure_balls=x.p_n,
                obs_pressure=x.obs_pressure_rv100, obs_normal=x.obs_normal_rv100,
                role_label=x.role_label, role_pct=x.get('role_pct'))


def price(u):
    for r in ['bat', 'bowl']:
        if u in POOL[r].index:
            x = POOL[r].loc[u]
            # same rule as s17: a contracted player with no auction price on record was retained -> price not estimable
            known = bool(pd.notna(x.last_price_cr) or str(x.status).startswith('Open market'))
            p = x.pred_price_cr
            return dict(known=known and pd.notna(p), mid=p if known else None,
                        lo=p * np.exp(-Z80 * SIG) if known else None, hi=min(p * np.exp(Z80 * SIG), PMAX) if known else None,
                        last=x.last_price_cr, last_year=x.last_auction_year, value_per_cr=x.value_per_cr if known else None)
    return dict(known=False)


def badges(u):
    i = ID.loc[u]; b = []
    if isinstance(i.bat_hand, str): b.append({'RHB': 'Right-hand bat', 'LHB': 'Left-hand bat'}.get(i.bat_hand, i.bat_hand))
    if isinstance(i.bowl_type, str) and (i.bowl_balls_all or 0) >= 300: b.append(i.bowl_type)
    if i.spin_kind == 'wrist': b.append('Wrist spin')
    if bool(i.mystery_spinner) if pd.notna(i.mystery_spinner) else False: b.append('Mystery variations')
    if (i.keeper_share or 0) >= 0.5: b.append('Wicket-keeper')
    if (i.captain_matches or 0) >= 10: b.append('Captaincy experience')
    return b


VDi = VD.set_index('name')
players = {}
for u in uids:
    nm = re.sub(r' \(\d+\)$', '', str(ID.name.get(u)))
    st, team = status(u)
    y = None
    for r in ['bat', 'bowl']:
        if u in YB[r].index:
            q = YB[r].loc[u]
            y = dict(role=r, board=q.board, label=q.label, rank=int(q.board_rank), skill=q.skill, proj_1=q.proj_1,
                     proj_1_lo=q.proj_1_lo, proj_1_hi=q.proj_1_hi, proj_2=q.proj_2, proj_3=q.proj_3, balls=q.n)
            break
    v = VDi.loc[nm] if nm in VDi.index else None
    if isinstance(v, pd.DataFrame): v = v.iloc[0]
    players[u] = dict(
        id=u, name=nm, nation=nation(u), age=age_of(u), cap=CAP.status_2027.get(u, 'uncapped (no international)'),
        status=st, team27=team, badges=badges(u), slots=slots(u),
        type_bat=CLU['bat'].get(u), type_bowl=CLU['bowl'].get(u),
        pace_spin=ID.pace_spin.get(u), bowl_arm=ID.bowl_arm.get(u), spin_kind=ID.spin_kind.get(u), bat_hand=ID.bat_hand.get(u),
        bat=rating(u, 'bat'), bowl=rating(u, 'bowl'), price=price(u), youth=y,
        verdict=None if v is None else dict(verdict=v.verdict, risks=v.main_risks, alternative=v.alternative, form=v.form_trend))
dump('players.json', players)

# ---------------- rankings / lists ----------------
def lst(df, r, extra=()):
    return [dict(id=u, **{k: df.loc[u][k] for k in extra if k in df.columns}) for u in df.index if u in players]


lists = {}
for r in ['bat', 'bowl']:
    T = FULL[r]
    lists[r] = dict(open=[u for u in T.index if u in players],
                    buy=[u for u in T[T.buy_rank.notna()].sort_values('buy_rank').index if u in players],
                    value=[u for u in VAL[r].index[:30] if u in players],
                    youth=[u for u in YB[r][YB[r].board == 'u23'].sort_values('board_rank').index if u in players])
dump('rankings.json', dict(lists=lists, final=recs(FR)))

# ---------------- profiles ----------------
PR = pd.read_parquet(w('profiles/player_profiles.parquet'), filters=[('pid', 'in', uids)])
KEEP_BAT = ['innings', 'runs', 'balls', 'not_outs', 'average', 'strike_rate', 'fifties', 'hundreds', 'highest', 'boundary_pct',
            'dot_pct', 'fours', 'sixes', 'run_value_per100', 'balls_per_dismissal', 'pct_innings_30plus', 'share_pct']
KEEP_BOWL = ['innings', 'balls', 'runs', 'wickets', 'economy', 'average', 'strike_rate', 'dot_pct', 'boundary_pct', 'wides',
             'no_balls', 'three_w', 'four_w_plus', 'run_value_per100', 'speed_median', 'share_pct', 'wicket_share_pct']
SPLITS = ['all', 'comp2', 'phase', 'setting', 'recent', 'pres', 'season', 'pace_spin', 'bowl_type', 'bat_hand', 'dstyle',
          'shot_group', 'dismissal_type', 'knockout_v2']
PR = PR[PR.split.isin(SPLITS)]
best_fig = {}
profiles = {}
for u, g in PR.groupby('pid'):
    out = {}
    for role, keep in [('bat', KEEP_BAT), ('bowl', KEEP_BOWL)]:
        x = g[(g.role == role) & (g.metric.isin(keep + ['dismissal_share_pct']))]
        if x.empty:
            continue
        d = {}
        for (sp, sv), h in x.groupby(['split', 'split_value']):
            d.setdefault(sp, {})[str(sv)] = {m: v for m, v in zip(h.metric, h.value)}
        if 'comp2' in d:   # keep the 5 competitions with most balls
            d['comp2'] = dict(sorted(d['comp2'].items(), key=lambda kv: -(kv[1].get('balls') or 0))[:5])
        out[role] = d
    profiles[u] = out
for u in uids:
    p = profiles.setdefault(u, {})
    nm = players[u]['name']
    p['moments'] = {}
    for role in ['bat', 'bowl']:
        if players[u][role]:
            p['moments'][role] = C18.moments(u, role)
    p['notes'] = NOTES.get(nm, []) + NOTES.get(f'youth:{nm}', [])
    flags = []
    for role in ['bat', 'bowl']:
        rt = players[u][role]
        if rt:
            if (rt['pressure_balls'] or 0) < 200: flags.append(f'Small pressure sample ({int(rt["pressure_balls"])} balls, {role})')
            if rt['lo'] is not None and rt['lo'] < 0: flags.append(f'{"Batting" if role == "bat" else "Bowling"} interval includes below-average')
    if players[u]['age'] and players[u]['age'] >= 34: flags.append(f'Age {players[u]["age"]} on 1 Apr 2027')
    if any(n.get('type') == 'fitness' for n in p['notes']): flags.append('Fitness concerns in 2026 reporting')
    if str(players[u]['status']).startswith('Not eligible'): flags.append(players[u]['status'])
    if not players[u]['price'].get('known'): flags.append('Price not estimable (retained / no auction record)')
    p['flags'] = flags
    fit = []
    for s in players[u]['slots']:
        gg = GAPS[GAPS.slot == s]
        if len(gg):
            q = gg.iloc[0]
            fit.append(dict(slot=s, rr_best=q.rr_best, rr_best_score=q.rr_best_score, benchmark=q.benchmark_top10_median, gap=q.gap))
    p['rr_fit'] = fit
dump('profiles.json', profiles)

# ---------------- method ----------------
V = pd.read_parquet(w('values/ball_values_final.parquet'), columns=['row', 'source', 'season', 'legal', 'innings', 'li_norm'])
B = pd.read_parquet(w('unified/balls.parquet'), columns=['over'])
V['over'] = B.over.values[V.row.values]
r_ = V[V.source.eq('RR') & V.legal & V.season.between(2022, 2026)]
lev = r_.groupby(['innings', 'over']).li_norm.mean().unstack(0)
sk = {r: rd(f'models/skill_backtest_{r}_by_fold.csv') for r in ['bat', 'bowl']}
skt = {r: sk[r][sk[r].wcorr.notna()].groupby('model')[['wcorr', 'spearman', 'top10_hit', 'noise_ceiling_r']].mean().reset_index() for r in sk}
A = rd('models/ablation_by_fold.csv')
abl = {}
for r in ['bat', 'bowl']:
    P_ = A[A.role == r].pivot(index='cutoff', columns='variant', values='wcorr'); d = P_.sub(P_['full'], axis=0)
    abl[r] = recs(pd.DataFrame({'variant': P_.columns, 'mean': P_.mean().values, 'diff': d.mean().values, 'se': (d.std() / 2).values}))
wpcal = rd('models/wp_calibration.csv')
method = dict(
    leverage=dict(overs=list(lev.index), setting=list(lev[1]), chasing=list(lev[2])),
    pressure_defs=recs(rd('pressure/pressure_definitions.csv')), chosen_pressure=PCH,
    wp=recs(rd('models/wp_comparison.csv')),
    wp_calibration=recs(wpcal[wpcal.model.isin(['logistic', 'B0_baseline_replica'])]),
    xout=recs(rd('models/xoutcome_comparison.csv').rename(columns={'Unnamed: 0': 'model'})),
    skill={r: recs(skt[r]) for r in skt}, ablation=abl, calibration=CAL,
    fairness=recs(rd('models/fairness.csv')), sensitivity=recs(rd('models/sensitivity.csv')),
    league=recs(rd('comp_strength/league_strength_2022_26_with_se.csv')),
    venues=recs(rd('comp_strength/venue_effects_top60.csv').rename(columns={'Unnamed: 0': 'venue'}).head(25)),
    clutch={r: recs(rd(f'models/clutch_{r}.csv')) for r in ['bat', 'bowl']},
    shap=recs(rd('explain/shap_top_predictors.csv')), matchup_rel=recs(rd('explain/matchup_reliability.csv')))
dump('method.json', method)

# ---------------- strategy ----------------
SQ = rd('rr_fit/rr_squad_2026.csv')
plans = []
for s, g in SHL.groupby('slot', sort=False):
    tops = g[g.pick == 'top 3']
    for lab, (_, q) in zip(['A', 'B', 'C'], tops.iterrows()):
        plans.append(dict(slot=s, plan=lab, id=q.uid, name=q['name'], score=q.score, lo=q.score_lo, hi=q.score_hi,
                          p_top10=q.p_top10, trend=q.trend, status=q.status, price=q.get('price')))
    for _, q in g[g.pick == 'value pick'].iterrows():
        plans.append(dict(slot=s, plan='Value', id=q.uid, name=q['name'], score=q.score, lo=q.score_lo, hi=q.score_hi,
                          p_top10=q.p_top10, trend=q.trend, status=q.status, price=q.get('price')))
name2id = {players[u]['name']: u for u in players}
VD['id'] = VD.name.map(name2id)
strategy = dict(squad=recs(SQ), gaps=recs(GAPS), plans=plans, verdicts=recs(VD),
                value={r: recs(rd(f'value/{r}_uncapped_value_top10.csv')) for r in ['bat', 'bowl']},
                youth={r: recs(rd(f'youth/{r}_board_u23.csv')) for r in ['bat', 'bowl']}, allrounders=recs(YAR.reset_index()))
dump('strategy.json', strategy)

# ---------------- meta ----------------
sb, sw = skt['bat'].set_index('model'), skt['bowl'].set_index('model')
gap_b = sb.loc['M5_eb_overall_plus_gap', 'wcorr'] - sb.loc['M4_eb_overall', 'wcorr']
gap_w = sw.loc['M5_eb_overall_plus_gap', 'wcorr'] - sw.loc['M4_eb_overall', 'wcorr']
clear = {r: int((FULL[r].head(15).p_top10 >= 0.5).sum()) for r in FULL}
meta = dict(
    generated='2026-11-16', title='Who performs under pressure?', event='SupeRR Selector Season 2 - Round 1',
    pressure_definition=('A pressure ball is one where the next delivery can swing the match most: the top 25% of balls by '
                         'expected change in win probability.'),
    score_definition=f'Pressure Rating = runs a player is expected to add per 100 pressure balls above what the situation predicts (a wicket = {PCH["KW_runs_per_wicket"]:.1f} runs). 0 = average.',
    findings=[
        dict(title='"Clutch" is not a repeatable skill', text=f'Adding a player\'s pressure-minus-normal gap made next-season predictions worse (batters {gap_b:+.3f}, bowlers {gap_w:+.3f} correlation). Over-performers under pressure tend to fall back.'),
        dict(title='Overall skill, measured fairly, predicts pressure performance', text=f'Skill adjusted for situation, opposition, venue, era and league reaches r = {sb.loc["M4_eb_overall", "wcorr"]:.2f} (batters) and {sw.loc["M6_apm", "wcorr"]:.2f} (bowlers) against a noise ceiling of {sb.noise_ceiling_r.iloc[0]:.2f} and {sw.noise_ceiling_r.iloc[0]:.2f}.'),
        dict(title='The obvious formula does not work', text=f'A hand-weighted pressure formula (our v1) had no out-of-sample signal: r = {sb.loc["M2_baseline", "wcorr"]:+.2f} (batters), {sw.loc["M2_baseline", "wcorr"]:+.2f} (bowlers).')],
    certainty=f'Only {clear["bat"]} batter(s) and {clear["bowl"]} bowler(s) have a better-than-even chance of a top-10 place once uncertainty is calibrated; the rest of each top 10 are near-ties.',
    counts=dict(players=len(players), balls_public=1665310, competitions=15, seasons='2019-2026'),
    calibration=CAL, kw=PCH['KW_runs_per_wicket'])
dump('meta.json', meta)

# ---------------- sources ----------------
src = open(os.path.join(PUB, 'SOURCES.md')).read() if os.path.exists(os.path.join(PUB, 'SOURCES.md')) else ''
dump('sources.json', dict(markdown=src, licences=[
    dict(name='RR / Unstop data pack', licence='Competition use only; not redistributed (aggregates shown only)'),
    dict(name='Cricsheet', licence='Open Data Commons Attribution License (ODC-By 1.0)', url='https://cricsheet.org/'),
    dict(name='Wikipedia', licence='CC BY-SA 4.0', url='https://en.wikipedia.org/'),
    dict(name='Wikidata', licence='CC0', url='https://www.wikidata.org/'),
    dict(name='News reports (scout notes)', licence='Quoted briefly with links; opinion, not used in ratings')]))
shutil.copy(res('report/SupeRR_S2_v2_Methodology_Report.pdf'), os.path.join(OUT, 'report.pdf'))
print('players', len(players))
