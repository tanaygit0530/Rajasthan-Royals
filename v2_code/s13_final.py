"""S4D: final Pressure Reliability Score, intervals, P(top 10), sensitivity, ablation, fairness.

Final model (chosen from the S4B backtest, see SKILL_REPORT.md): hierarchical Bayesian overall skill
(theta_i: run value per ball vs context expectation, prior centred on competition-adjusted all-league skill (APM) and
an age curve), fitted on RR-pack balls 2022-26. The pressure-specific effect delta_i is estimated but NOT used for
ranking, because it does not predict next-season pressure performance (S4C).
Score = predicted run value per 100 pressure balls next season = 100 x (theta_i + d0).
Eligibility (as the baseline): >= 150 RR-pack pressure balls 2022-26 and last appearance 2025 or later.
Outputs: v2_results/final_rankings.csv, v2_results/rankings/*.csv, v2_results/models/{sensitivity,ablation,fairness}.csv
"""
import sys
import json
from scipy.stats import spearmanr
from common import *
import skill as K

seed_all()
QUICK = '--quick' in sys.argv
P = pd.read_parquet(w('unified/players.parquet'))
ROLE_T = pd.read_parquet(w('unified/roles.parquet'))
ID = pd.read_parquet(w('profiles/player_identity.parquet')).set_index('uid')
MIN_P, LAST = 150, 2025
DRAWS = 2000

# ---------------- auction status: baseline rules + trades/retirements to 15 Nov 2026 (Wikipedia 'List of 2027 IPL personnel
# changes', CC BY-SA). Retention deadline was 15 Nov 2026; retained/released lists not yet published -> refresh before 16 Dec auction
mp = rr('competition_team_player_mapping.csv'); cp = rr('competitions.csv')
mp = mp.merge(cp[['comp_id', 'match_format']], on='comp_id')
idm = pd.read_csv(res('idmap/idmap.csv')); U = idm[idm.method.str.match(r'^(A_|B1_|B2_)')].set_index('pid').cs.to_dict()
mp['uid'] = mp.player_id.map(lambda p: U.get(p, f'rr{int(p)}'))
intl = mp[(mp.match_format == 'T20I') | mp.comp_id.isin([2670, 3289])]
NAT = intl.groupby('uid').team_name.agg(lambda s: s.value_counts().index[0]).str.replace(' A$', '', regex=True)
IPL26 = mp[mp.comp_id == 3298].drop_duplicates('uid').set_index('uid').team_name
# nationality: RR-pack international team, else the team of the player's international appearances in Cricsheet
# (all formats, all years; s16), else India (domestic Indian players have no international record)
_cap = pd.read_parquet(w('value/capped.parquet')).set_index('uid')
NAT = NAT.combine_first(_cap.nationality.dropna()) if 'nationality' in _cap else NAT.combine_first(_cap.intl_team.dropna().str.replace(' A$', '', regex=True))
TRADES = {'Kuldeep Yadav': 'Lucknow Super Giants', 'Rishabh Pant': 'Delhi Capitals', 'T Natarajan': 'Sunrisers Hyderabad',
          'Liam Livingstone': 'Chennai Super Kings', 'Jack Edwards': 'Chennai Super Kings', 'Khaleel Ahmed': 'Sunrisers Hyderabad',
          'Nathan Ellis': 'Sunrisers Hyderabad', 'Hardik Pandya': 'Punjab Kings', 'Arshdeep Singh': 'Mumbai Indians',
          'Zeeshan Ansari': 'Delhi Capitals', 'Harshal Patel': 'Gujarat Titans'}
ABBR = {'Chennai Super Kings': 'CSK', 'Mumbai Indians': 'MI', 'Rajasthan Royals': 'RR', 'Punjab Kings': 'PBKS',
        'Royal Challengers Bengaluru': 'RCB', 'Delhi Capitals': 'DC', 'Kolkata Knight Riders': 'KKR',
        'Sunrisers Hyderabad': 'SRH', 'Gujarat Titans': 'GT', 'Lucknow Super Giants': 'LSG'}


def status(name, uid):
    team = TRADES.get(name, IPL26.get(uid)); nat = NAT.get(uid, 'India')
    if nat == 'Pakistan': return team, 'Not eligible (Pakistan national)'
    if name == 'Harry Brook': return None, 'Not eligible (IPL ban through 2027)'
    if name == 'Andre Russell': return None, 'Not eligible (retired from IPL)'
    if name == 'Ajinkya Rahane': return None, 'Not eligible (retired, 30 Jul 2026)'
    if team == 'Rajasthan Royals': return team, 'Already RR'
    if isinstance(team, str): return team, f'Under contract ({ABBR.get(team, team)}); only if released'
    return None, 'Open market (not on a 2026 IPL roster)'


# Final configuration chosen by the out-of-time ablation (s13b; MODEL_COMPARISON.md). A component is kept only if
# removing it lowers next-season accuracy, and a prior may not reuse the RR-pack balls of the likelihood (that would
# count the same balls twice and make intervals falsely narrow).
#   age curve: removing it never hurt -> dropped (both roles)
#   bowlers: prior from public (Cricsheet, non-RR) matches only -> best variant, better in 4 of 4 folds
#   batters: no skill prior (RR-pack hierarchical model only) -> within 1 SE of the best batter variant; the best
#            point predictor (prior fitted on the same RR balls) is reported as a sensitivity check only
#   pressure-specific effect: hurts both roles -> estimated, not used to rank
FINAL = {'bat': dict(apm_src=None, use_age=False), 'bowl': dict(apm_src='cs', use_age=False)}


def fit_role(role, pdef=None, min_p=MIN_P, last=LAST, draws=DRAWS, use_age=None, apm_src='final'):
    use_age = FINAL[role]['use_age'] if use_age is None else use_age
    apm_src = FINAL[role]['apm_src'] if apm_src == 'final' else apm_src
    if pdef:
        os.environ['PDEF'] = pdef
    V = pd.read_parquet(w('values/ball_values_final.parquet'))
    V, thr = K.add_flags(V, 2026, d=pdef or K.PDEF)
    A = K.apm(2026, src=apm_src or 'all')
    F = K.features(V, 2026, role, A, P, ROLE_T)
    F['age_actual'] = F.age
    F['age'] = F.age if use_age else 28.0
    if apm_src is None:
        F['M6_apm'] = 0.0
    elif apm_src == 'cs':     # players with no public-league balls get the population prior (APM = 0 = average)
        nb = A['apm_bat_n' if role == 'bat' else 'apm_bowl_n'].reindex(F.index).fillna(0)
        F['M6_apm'] = F.M6_apm.where(nb > 0, 0.0)
    F['M6_apm'] = F.M6_apm.fillna(F.M6_apm.median())
    th, de, summ = K.bayes_fit(F, F.attrs['var_ball'], draws=draws, warm=draws)
    F['theta'] = th.mean(0); F['delta'] = de.mean(0)
    el = (F.p_n >= min_p) & (F.last_season >= last)
    return F, th, de, summ, el, thr


def table(role, F, th, de, summ, el):
    d0 = summ['d0'][0]
    idx = np.where(el.values)[0]
    S = (th[:, idx] + d0) * 100
    T = F[el].copy()
    T['score'] = S.mean(0); T['score_lo'] = np.percentile(S, 10, 0); T['score_hi'] = np.percentile(S, 90, 0)
    R = (-S).argsort(1).argsort(1) + 1
    T['p_top10'] = (R <= 10).mean(0); T['rank_lo'] = np.percentile(R, 10, 0).astype(int); T['rank_hi'] = np.percentile(R, 90, 0).astype(int)
    T = T.sort_values('score', ascending=False); T['rank'] = np.arange(1, len(T) + 1)
    # near-tie: posterior probability that this player is ahead of the next one
    order = [list(T.index).index(p) for p in T.index]
    pos = {p: i for i, p in enumerate(F[el].index)}
    ahead = []
    for a, b in zip(T.index[:-1], T.index[1:]):
        ahead.append(float((S[:, pos[a]] > S[:, pos[b]]).mean()))
    T['p_ahead_of_next'] = ahead + [np.nan]
    T['near_tie_with_next'] = T.p_ahead_of_next < 0.6
    T['pressure_tendency'] = T.delta * 100     # shrunk pressure-minus-normal effect: descriptive only, not used to rank
    nm = P.set_index('uid').name
    T['name'] = T.index.map(nm)
    st = [status(n, u) for n, u in zip(T.name, T.index)]
    T['team27'] = [s[0] for s in st]; T['status'] = [s[1] for s in st]
    T['nation'] = [NAT.get(u, 'India') for u in T.index]
    T['buyable'] = ~T.status.str.startswith(('Already', 'Not eligible'))
    T['buy_rank'] = np.nan; T.loc[T.buyable, 'buy_rank'] = np.arange(1, T.buyable.sum() + 1)
    rcol = 'bat_role' if role == 'bat' else 'bowl_role'
    T['role_label'] = ID[rcol].reindex(T.index).astype(str)
    T['role_pct'] = T.groupby('role_label').score.rank(pct=True) * 100
    T['obs_pressure_rv100'] = T.p_raw * 100; T['obs_normal_rv100'] = T.n_raw * 100
    T['apm_rv100'] = T.M6_apm * 100
    T['age'] = T.age_actual
    return T


COLS = ['rank', 'name', 'nation', 'team27', 'status', 'buy_rank', 'score', 'score_lo', 'score_hi', 'p_top10', 'rank_lo',
        'rank_hi', 'p_ahead_of_next', 'near_tie_with_next', 'p_n', 'n_n', 'obs_pressure_rv100', 'obs_normal_rv100',
        'apm_rv100', 'pressure_tendency', 'age', 'role_label', 'role_pct', 'ipl_share', 'last_season']

if __name__ == '__main__':
    os.makedirs(res('rankings'), exist_ok=True)
    finals, base_top = {}, {}
    for role in ['bat', 'bowl']:
        F, th, de, summ, el, thr = fit_role(role)
        T = table(role, F, th, de, summ, el)
        T[COLS].round(4).to_csv(res(f'rankings/{role}_full_rankings.csv'), index_label='uid')
        finals[role] = T; base_top[role] = list(T.index[:10])
        json.dump({k: list(v) for k, v in summ.items()}, open(res(f'rankings/{role}_posterior_hyper.json'), 'w'))
        print(role, 'eligible', len(T), 'pressure threshold', round(thr, 5), flush=True)
        print(T[['rank', 'name', 'status', 'score', 'score_lo', 'score_hi', 'p_top10', 'p_n']].head(12).round(3).to_string(), flush=True)
    rows = []
    for role, T in finals.items():
        for kind, sub in [('open', T.head(10)), ('rr_can_buy', T[T.buyable].head(10))]:
            for r in sub.itertuples():
                rows.append(dict(list=f'{"batters" if role == "bat" else "bowlers"}_{kind}', position=int(r.rank if kind == 'open' else r.buy_rank),
                                 open_rank=int(r.rank), uid=r.Index, name=r.name, nation=r.nation, status=r.status,
                                 score_runs_per100_pressure_balls=round(r.score, 2), interval_80_lo=round(r.score_lo, 2),
                                 interval_80_hi=round(r.score_hi, 2), p_top10=round(r.p_top10, 3), pressure_balls=int(r.p_n),
                                 near_tie_with_next=bool(r.near_tie_with_next)))
    pd.DataFrame(rows).to_csv(res('final_rankings.csv'), index=False)
    if QUICK:
        sys.exit()

    # ---------------- sensitivity ----------------
    sens = []
    def cmp(role, name, T2):
        T = finals[role]; com = T.index.intersection(T2.index)
        sens.append(dict(role=role, variant=name, top10_kept=len(set(base_top[role]) & set(T2.index[:10])),
                         base_top10_in_variant_top15=len(set(base_top[role]) & set(T2.index[:15])),
                         spearman=spearmanr(T.loc[com, 'score'], T2.loc[com, 'score'])[0], n=len(T2),
                         **{T.loc[p, 'name']: (int(T2.index.get_loc(p)) + 1 if p in T2.index else None) for p in base_top[role]}))
        print(sens[-1]['role'], name, sens[-1]['top10_kept'], round(sens[-1]['spearman'], 3), flush=True)
    for role in ['bat', 'bowl']:
        T = finals[role]
        for pdef in ['D2_leverage_phase', 'D3_baseline_PI', 'D7_leverage_stakes', 'D6_close_game', 'D5_wicket_stress']:
            F, th, de, summ, el, _ = fit_role(role, pdef=pdef, draws=1000)
            cmp(role, f'pressure definition {pdef}', table(role, F, th, de, summ, el))
        os.environ['PDEF'] = K.PCFG['chosen']
        F, th, de, summ, el, _ = fit_role(role, draws=1000, min_p=0, last=0)
        for nm_, mp_, ls_ in [('eligibility 100 pressure balls', 100, 2025), ('eligibility 200 pressure balls', 200, 2025),
                              ('eligibility: last season 2024+', 150, 2024)]:
            cmp(role, nm_, table(role, F, th, de, summ, (F.p_n >= mp_) & (F.last_season >= ls_)))
        el0 = (F.p_n >= MIN_P) & (F.last_season >= LAST)
        Fe = F[el0]
        apm_all = K.apm(2026)['apm_bat_rv' if role == 'bat' else 'apm_bowl_rv']
        for nm_, col in [('rank by M4 (EB overall, RR only)', 'M4_eb_overall'), ('rank by M6 (APM, all leagues)', 'APM'),
                         ('rank incl. pressure-specific effect (theta + delta)', None)]:
            s = (Fe.theta + Fe.delta) if col is None else apm_all.reindex(Fe.index) if col == 'APM' else Fe[col]
            T2 = Fe.assign(score=s).sort_values('score', ascending=False)
            cmp(role, nm_, T2)
        T2 = Fe.assign(score=Fe.p_raw).sort_values('score', ascending=False); cmp(role, 'rank by raw observed pressure run value', T2)
        for nm_, kw in [('with age curve', dict(use_age=True)), ('prior: APM from RR pack (double counts)', dict(apm_src='rr')),
                        ('prior: APM from public leagues only', dict(apm_src='cs')), ('prior: APM all leagues (double counts)', dict(apm_src='all')),
                        ('no skill prior', dict(apm_src=None))]:
            if kw.get('apm_src', 'x') == FINAL[role]['apm_src']:
                continue
            F2, th2, de2, s2, el2, _ = fit_role(role, draws=1000, **kw)
            cmp(role, f'final model {nm_}', table(role, F2, th2, de2, s2, el2))
    pd.DataFrame(sens).round(3).to_csv(res('models/sensitivity.csv'), index=False)

