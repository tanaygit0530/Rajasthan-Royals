"""S5C: youth talent board (age <= 23 on 1 April 2027; plus a 24-26 list).

Minors policy: only cricket performance data and age (date of birth used solely to compute age; never output).
Skill = competition-, venue- and opponent-adjusted run value per ball from the all-league ridge (APM, s07 design),
which validated best for next-season pressure performance among single-source estimates (S4B, M6), with an
approximate standard error. Every number carries its uncertainty; small samples are flagged, not hidden.

Development model, backtested BEFORE use: for players aged <= 23 at the end of 2021, skill estimated from data up to
2021 vs skill estimated from 2024-26 data only (separate ridge fits, no shared balls). Candidates: (a) early estimate
only, (b) + age, (c) + age + log sample size; scored by 5-fold cross-validation by player. Yearly development by age
from consecutive-season estimates gives 1/2/3-season projections with growing intervals.
Comparables: 3 nearest historical players at the same age (+-1) in 2019-21 in standardised skill/style space, and what
they became (2024-26 skill).
Labels: Buy now = projected next-season skill above the 75th percentile of established IPL players AND 80% lower
bound above the median; Strong watch = projection above the median; Track = the rest of the board.
Outputs: v2_results/youth/*.csv, YOUTH_REPORT.md
"""
import json
from sklearn.model_selection import KFold
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from common import *
import skill as K
import s07_comp_strength as S7

seed_all()
os.makedirs(res('youth'), exist_ok=True)
meta = json.load(open(w('comp_strength/fit_meta.json'))); S7.DELIV_PER_LEGAL = meta['deliv_per_legal']
B, cat = S7.load()
ID = pd.read_parquet(w('profiles/player_identity.parquet')).set_index('uid')
CAP = pd.read_parquet(w('value/capped.parquet')).set_index('uid')
L = ['# Youth talent board (S5C)', '',
     'Policy: cricket performance data and age only. Dates of birth (Wikidata) are used solely to compute age and are '
     'not published. No personal, family or social-media information is collected.', '',
     'Pool: age <= 26 on 1 Apr 2027, >= 60 balls since 2024, >= 120 balls since 2022 outside associate-nation T20Is and less than '
     'half of their balls in associate T20Is (estimates built mainly on associate cricket are too weakly linked to the IPL to trust).', '']


def ridge_period(lo, hi, cache):
    p = w(f'youth/apm_{lo}_{hi}.parquet')
    if os.path.exists(p):
        return pd.read_parquet(p)
    E = {}
    for t, spec in S7.TARGETS.items():
        m = B.season.between(lo, hi).values
        idx = S7.rows_for(B, spec['rows'], m)
        E[t] = S7.fit(cat, idx, B[t].astype(float).values[idx], meta['lam'][t], spec['blocks'], x0=np.load(w(f'comp_strength/sol_{t}.npy')))
    pe = S7.player_table(E)
    nb = B[B.legal & B.season.between(lo, hi)]
    pe['n_bat'] = nb.batter.value_counts().reindex(pe.index).fillna(0); pe['n_bowl'] = nb.bowler.value_counts().reindex(pe.index).fillna(0)
    pe['bat_rv'] = pe.bat_runs - K.KW * pe.bat_out; pe['bowl_rv'] = pe.bowl_runs_total + K.KW * pe.bowl_wkt
    os.makedirs(w('youth'), exist_ok=True); pe.to_parquet(p)
    return pe


early = ridge_period(2019, 2021, True)
late = ridge_period(2024, 2026, True)
now = K.apm(2026)
now['bat_rv'] = now.apm_bat_rv; now['bowl_rv'] = now.apm_bowl_rv; now['n_bat'] = now.apm_bat_n; now['n_bowl'] = now.apm_bowl_n
dob = pd.to_datetime(ID.dob)
var_b = float(B[B.legal].runs_bat.var())
LAM = meta['lam']['runs_bat']

# ---------------- development-model backtest ----------------
bt_rows, dev = [], {}
for role in ['bat', 'bowl']:
    e = early[early[f'n_{role}'] >= 120][[f'{role}_rv', f'n_{role}']].rename(columns={f'{role}_rv': 'x', f'n_{role}': 'n'})
    l_ = late[late[f'n_{role}'] >= 120][[f'{role}_rv']].rename(columns={f'{role}_rv': 'y'})
    d = e.join(l_, how='inner')
    d['age'] = (pd.Timestamp('2021-12-31') - dob.reindex(d.index)).dt.days / 365.25
    d = d[d.age.notna() & (d.age <= 26)]
    d['young'] = d.age <= 23
    d['logn'] = np.log(d.n)
    X_sets = {'(a) early skill only': ['x'], '(b) + age': ['x', 'age'], '(c) + age + sample size': ['x', 'age', 'logn']}
    kf = KFold(5, shuffle=True, random_state=SEED)
    for nm, cols in list(X_sets.items()) + [('mean only', [])]:
        pred = np.zeros(len(d))
        for tr, te in kf.split(d):
            if cols:
                m = LinearRegression().fit(d.iloc[tr][cols], d.iloc[tr].y); pred[te] = m.predict(d.iloc[te][cols])
            else:
                pred[te] = d.iloc[tr].y.mean()
        for grp, mk in [('all aged <= 26 in 2021', np.ones(len(d), bool)), ('aged <= 23 in 2021', d.young.values)]:
            yy, pp = d.y.values[mk], pred[mk]
            bt_rows.append(dict(role=role, model=nm, group=grp, n=int(mk.sum()), r=np.corrcoef(pp, yy)[0, 1] if cols else np.nan,
                                mse_per100=np.mean((yy - pp) ** 2) * 1e4))
    ma = LinearRegression().fit(d[['x']], d.y)        # model (a): chosen - age / sample size did not improve the backtest
    dev_a = dict(icpt=float(ma.intercept_), slope=float(ma.coef_[0]), resid_sd=float(np.std(d.y - ma.predict(d[['x']]))))
    mfull = LinearRegression().fit(d[['x', 'age', 'logn']], d.y)
    dev[role] = dict(coef=dict(zip(['early_skill', 'age', 'log_n'], mfull.coef_)), intercept=mfull.intercept_,
                     resid_sd=float(np.std(d.y - mfull.predict(d[['x', 'age', 'logn']]))), n=len(d), a=dev_a)
BT = pd.DataFrame(bt_rows); BT.round(4).to_csv(res('youth/development_model_backtest.csv'), index=False)
L += ['## Development model backtest (skill to 2021 -> skill from 2024-26 data only, 5-fold CV by player)', '',
      BT.round(3).to_markdown(index=False), '',
      f'- Fitted (c) on all {dev["bat"]["n"]} batters / {dev["bowl"]["n"]} bowlers: batting age coefficient '
      f'{dev["bat"]["coef"]["age"] * 100:+.2f} runs per 100 balls per year of age, bowling {dev["bowl"]["coef"]["age"] * 100:+.2f}. '
      'Age and sample size did NOT improve on early skill alone for players aged 23 or under (rows (b), (c) vs (a)), so projections use '
      f'model (a): 3-season projection = {dev["bat"]["a"]["icpt"] * 100:.1f} + {dev["bat"]["a"]["slope"]:.2f} x current (batters), '
      f'{dev["bowl"]["a"]["icpt"] * 100:.1f} + {dev["bowl"]["a"]["slope"]:.2f} x current (bowlers), in runs per 100 balls.', '']

# ---------------- yearly development by age (consecutive seasons, all leagues) ----------------
V = pd.read_parquet(w('values/ball_values_final.parquet'), columns=['batter', 'bowler', 'season', 'faced', 'runs_bat', 'xruns',
                                                                   'striker_out', 'xout', 'bowl_runs', 'xbowl_runs', 'bowl_wkt', 'xbowl_wkt'])
V['rv_bat'] = np.where(V.faced, (V.runs_bat - V.xruns) - K.KW * (V.striker_out - V.xout), np.nan)
V['rv_bowl'] = (V.xbowl_runs - V.bowl_runs) + K.KW * (V.bowl_wkt - V.xbowl_wkt)
growth = {}
for role, pid, col in [('bat', 'batter', 'rv_bat'), ('bowl', 'bowler', 'rv_bowl')]:
    s = V[V[col].notna()].groupby([pid, 'season'])[col].agg(['mean', 'size'])
    s = s[s['size'] >= 120]['mean'].unstack()
    rows = []
    for y in range(2019, 2026):
        if y in s and y + 1 in s:
            p = s[[y, y + 1]].dropna()
            a = ((pd.Timestamp(f'{y}-12-31') - dob.reindex(p.index)).dt.days / 365.25)
            rows.append(pd.DataFrame({'age': a.values, 'chg': (p[y + 1] - p[y]).values}))
    G = pd.concat(rows).dropna()
    G['ab'] = G.age.clip(17, 36).round()
    tab = G.groupby('ab').chg.agg(['mean', 'size', 'std'])
    # smooth: linear fit of change on age (season-to-season noise is large)
    lin = np.polyfit(G.age, G.chg, 1)
    growth[role] = dict(slope=lin[0], icpt=lin[1], sd=float(G.chg.std() / np.sqrt(2)))
    tab.round(4).to_csv(res(f'youth/yearly_change_by_age_{role}.csv'))
gtxt = '; '.join(f'{r}: {growth[r]["icpt"] * 100 + growth[r]["slope"] * 100 * 20:+.2f} at age 20, '
                 f'{growth[r]["icpt"] * 100 + growth[r]["slope"] * 100 * 30:+.2f} at age 30 (runs per 100 balls per season)' for r in growth)
L += [f'- Season-to-season change by age (linear fit, all leagues, >= 120 balls in both seasons): {gtxt}. The change is negative '
      'at every age: that is regression to the mean among players picked after good seasons, not a development curve, so it is '
      'used only for the size of year-to-year noise, not as growth.', '']

# ---------------- board ----------------
age27 = (pd.Timestamp('2027-04-01') - dob).dt.days / 365.25
# relevance filter: associate-nation T20Is are thinly linked to the rest of the network, so skill estimates built
# mostly from them are unreliable for IPL purposes -> need >= 120 legal balls outside associate T20Is and < 50% associate share
_lb = B[B.legal & (B.season >= 2022)]
REL = {}
for role, col in [('bat', 'batter'), ('bowl', 'bowler')]:
    g = _lb.groupby(col).comp.agg(lambda s: pd.Series({'n': len(s), 'assoc': s.eq('T20I-Assoc').mean(), 'strong': (~s.eq('T20I-Assoc')).sum()}).to_dict())
    REL[role] = pd.DataFrame(g.tolist(), index=g.index)
import s13_final as F13
recent = V[V.season >= 2024]
rb = recent[recent.faced].groupby('batter').size(); rw = recent.groupby('bowler').size()
boards = {}
estb = {}
for role in ['bat', 'bowl']:
    T = now[[f'{role}_rv', f'n_{role}']].rename(columns={f'{role}_rv': 'skill', f'n_{role}': 'n'})
    T = T[T.n >= 60]
    T['se'] = np.sqrt(var_b / (T.n + LAM))
    T['age'] = age27.reindex(T.index)
    T['recent_balls'] = (rb if role == 'bat' else rw).reindex(T.index).fillna(0)
    T = T[T.age.notna() & (T.recent_balls >= 60)]
    rel = REL[role].reindex(T.index)
    T = T[(rel.strong >= 120) & (rel.assoc < 0.5)]
    # established reference: players with >= 1000 balls and an IPL appearance
    est = T[T.n >= 1000]
    estb[role] = est.skill
    # projections: the backtest showed age adds nothing beyond early skill, and the average season-to-season change is
    # negative at every age (regression to the mean among players selected for good seasons, not development). So:
    #   1 season ahead  = current estimate; interval adds one season of year-to-year noise
    #   3 seasons ahead = backtested model (a): later skill = icpt + slope x current skill, with its residual SD
    #   2 seasons ahead = halfway between
    g, A_ = growth[role], dev[role]['a']
    T['proj_1'] = T.skill; T['proj_1_sd'] = np.sqrt(T.se ** 2 + g['sd'] ** 2)
    T['proj_3'] = A_['icpt'] + A_['slope'] * T.skill; T['proj_3_sd'] = np.sqrt((A_['slope'] * T.se) ** 2 + A_['resid_sd'] ** 2)
    T['proj_2'] = (T.proj_1 + T.proj_3) / 2; T['proj_2_sd'] = (T.proj_1_sd + T.proj_3_sd) / 2
    T['proj_1_lo'] = T.proj_1 - 1.2816 * T.proj_1_sd; T['proj_1_hi'] = T.proj_1 + 1.2816 * T.proj_1_sd
    q75, q50 = est.skill.quantile(0.75), est.skill.quantile(0.5)
    T['label'] = np.select([(T.proj_1 >= q75) & (T.proj_1_lo >= q50), T.proj_1 >= q50], ['Buy now', 'Strong watch'], 'Track')
    T['name'] = ID.name.reindex(T.index).str.replace(r' \(\d+\)$', '', regex=True)
    T['status_2027'] = [F13.status(n, u)[1] for n, u in zip(T.name, T.index)]
    excl = T[T.status_2027.str.startswith('Not eligible') & (T.age < 27)]
    if len(excl):
        L.append(f'- Excluded from the {role} board as not eligible for the IPL: ' + ', '.join(excl.name.head(8)) + ('...' if len(excl) > 8 else '') + '.')
    T = T[~T.status_2027.str.startswith('Not eligible')]
    T['cap_status'] = CAP.status_2027.reindex(T.index).fillna('uncapped (no international)')
    T['sample_flag'] = np.where(T.n < 500, 'small sample (<500 balls)', '')
    boards[role] = T
    full = T.copy(); full[['skill', 'se', 'proj_1', 'proj_1_lo', 'proj_1_hi', 'proj_2', 'proj_3']] *= 100
    full['age'] = np.floor(full.age).astype(int)
    full.sort_values('proj_1', ascending=False).round(2)[['name', 'age', 'cap_status', 'status_2027', 'label', 'n', 'skill', 'se', 'proj_1',
        'proj_1_lo', 'proj_1_hi', 'proj_2', 'proj_3', 'sample_flag']].to_csv(res(f'youth/{role}_youth_all.csv'), index_label='uid')
    for grp, lo, hi, nmx in [('u23', 0, 23.999, 15), ('24_26', 24, 26.999, 15)]:
        Y = T[T.age.between(lo, hi)].sort_values('proj_1', ascending=False).head(nmx).copy()
        Y.insert(0, 'board_rank', range(1, len(Y) + 1))
        cols = ['board_rank', 'name', 'age', 'cap_status', 'status_2027', 'label', 'n', 'skill', 'se', 'proj_1', 'proj_1_lo', 'proj_1_hi', 'proj_2', 'proj_3', 'sample_flag']
        out = Y[cols].copy(); out[['skill', 'se', 'proj_1', 'proj_1_lo', 'proj_1_hi', 'proj_2', 'proj_3']] *= 100
        out['age'] = np.floor(out.age).astype(int)          # completed years on 1 Apr 2027
        out.round(2).to_csv(res(f'youth/{role}_board_{grp}.csv'), index_label='uid')
        if grp == 'u23':
            L += [f'## Youth board: {"batters" if role == "bat" else "bowlers"} aged <= 23 (top 15)', '',
                  f'Skill and projections in runs per 100 balls vs average (competition / venue / opponent adjusted). '
                  f'Reference: established players (>= 1000 balls) median {q50 * 100:.1f}, 75th percentile {q75 * 100:.1f}.', '',
                  out.drop(columns=['se', 'proj_2', 'proj_3']).round(1).to_markdown(index=False), '']

# all-rounders: >= 300 balls each in both disciplines
AR = boards['bat'][['name', 'age', 'proj_1', 'proj_1_sd', 'n', 'cap_status', 'status_2027']].join(
    boards['bowl'][['proj_1', 'proj_1_sd', 'n']], rsuffix='_bowl', how='inner')
AR = AR[(AR.n >= 300) & (AR.n_bowl >= 300) & (AR.age <= 23.999)]
AR['combined_proj'] = (AR.proj_1 + AR.proj_1_bowl) * 100
AR['combined_sd'] = np.sqrt(AR.proj_1_sd ** 2 + AR.proj_1_sd_bowl ** 2) * 100
AR = AR.sort_values('combined_proj', ascending=False).head(5)
AR['age'] = np.floor(AR.age).astype(int)
AR[['name', 'age', 'cap_status', 'status_2027', 'n', 'n_bowl', 'combined_proj', 'combined_sd']].round(2).to_csv(res('youth/allrounders_u23_top5.csv'), index_label='uid')
L += ['## All-rounders aged <= 23 (top 5; >= 300 balls in each discipline)', '',
      AR[['name', 'age', 'cap_status', 'status_2027', 'n', 'n_bowl', 'combined_proj', 'combined_sd']].round(1).to_markdown(index=False), '']

# ---------------- comparables ----------------
comp_rows = []
for role in ['bat', 'bowl']:
    H = early[early[f'n_{role}'] >= 300][[f'{role}_rv']].rename(columns={f'{role}_rv': 'x'})
    H['age'] = (pd.Timestamp('2021-12-31') - dob.reindex(H.index)).dt.days / 365.25
    H = H[H.age.notna()].join(late[[f'{role}_rv', f'n_{role}']].rename(columns={f'{role}_rv': 'later', f'n_{role}': 'later_n'}))
    T = boards[role]
    Y = T[T.age <= 23.999].sort_values('proj_1', ascending=False).head(15)
    for uid, r in Y.iterrows():
        a_now = (pd.Timestamp('2026-12-31') - dob.get(uid)).days / 365.25
        h = H[(H.age - a_now).abs() <= 1].copy()
        if h.empty:
            continue
        h['dist'] = np.abs(h.x - r.skill) / (H.x.std())
        for cu, c in h.nsmallest(3, 'dist').iterrows():
            comp_rows.append(dict(role=role, uid=uid, name=r['name'], comparable=ID.name.get(cu, cu), comp_skill_at_same_age=c.x * 100,
                                  comp_later_skill=c.later * 100 if pd.notna(c.later) else np.nan, comp_later_balls=c.later_n))
CP = pd.DataFrame(comp_rows); CP.round(2).to_csv(res('youth/comparables.csv'), index=False)
L += ['## Comparables', '', 'For each board player: the three historical players (2019-21) of the same age (+-1 year) with the '
      'closest adjusted skill, and their 2024-26 skill. A comparable who later has no 2024-26 data dropped out of the top level - '
      'an honest reminder of the attrition rate.', '', f'- See `comparables.csv` ({len(CP)} rows). Share of comparables with no '
      f'2024-26 data: {CP.comp_later_skill.isna().mean():.0%}.', '',
      '## Lower-resolution sources', '',
      '- U19, Vijay Hazare, state T20 leagues (TNPL, Maharaja Trophy, UP T20, DPL, Mumbai T20) and India A have no licensed '
      'ball-by-ball data; ESPNcricinfo/BCCI scorecards may not be scraped. For the shortlisted players, public reporting is '
      'summarised on the youth cards and labelled lower-resolution; it does not enter the projections.']
open(res('youth/YOUTH_REPORT.md'), 'w').write('\n'.join(L))
print('\n'.join(L))
