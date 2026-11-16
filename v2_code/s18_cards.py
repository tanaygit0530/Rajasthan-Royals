"""S5: scout cards for the top 30 of each open ranking and the top 5 of each value list.

Each card: (1) DATA panel - model score with 80% interval, P(top 10), rank range, pressure vs normal run value,
traditional pressure stats, phase and matchup splits (matchup shown only where that effect type is reliable, s15),
three biggest pressure performances (RR pack, by win-probability added) with date and opponent, computed risk flags;
(2) SCOUTING panel - labelled qualitative notes with sources (v2_results/cards/scouting_notes.json), never used to rank.
Outputs: v2_results/cards/SCOUT_CARDS_{batters,bowlers}.md, VALUE_CARDS.md
"""
import json
from common import *
import skill as K

N_TOP = 30
NOTES = json.load(open(res('cards/scouting_notes.json')))
PR = pd.read_parquet(w('profiles/player_profiles.parquet'))
ID = pd.read_parquet(w('profiles/player_identity.parquet')).set_index('uid')
CAP = pd.read_parquet(w('value/capped.parquet')).set_index('uid')
M = pd.read_parquet(w('unified/matches.parquet')).set_index('match_id')
V = pd.read_parquet(w('values/ball_values_final.parquet')); V, _ = K.add_flags(V, 2026)
V = V[V.source.eq('RR')]
CL = {r: pd.read_parquet(w(f'explain/clusters_{r}.parquet')).cluster_label for r in ['bat', 'bowl']}
MREL = pd.read_csv(res('explain/matchup_reliability.csv')).set_index('effect').reliability


def pv(pid, role, split, sv, metric):
    x = PR[(PR.pid == pid) & (PR.role == role) & (PR.split == split) & (PR.split_value == sv) & (PR.metric == metric)].value
    return float(x.iloc[0]) if len(x) else np.nan


def fmt_or_dash(x):
    return '-' if pd.isna(x) else f'{x:.0f}'


def f(x, d=1, pct=False):
    return '-' if pd.isna(x) else (f'{x:.{d}f}%' if pct else f'{x:.{d}f}')


def moments(pid, role, k=3):
    if role == 'bat':
        d = V[(V.batter == pid) & V.faced]
        g = d.groupby('match_id').agg(wpa=('bat_wpa', 'sum'), runs=('runs_bat', 'sum'), balls=('runs_bat', 'size'),
                                      pballs=('pres', 'sum'), opp=('bowl_team', 'first'), inn=('innings', 'first'))
    else:
        d = V[V.bowler == pid]
        g = d.groupby('match_id').agg(wpa=('bowl_wpa', 'sum'), runs=('bowl_runs', 'sum'), balls=('legal', 'sum'),
                                      wkts=('bowl_wkt', 'sum'), pballs=('pres', 'sum'), opp=('bat_team', 'first'), inn=('innings', 'first'))
    g = g[g.pballs >= 6].sort_values('wpa', ascending=False).head(k)
    out = []
    for mid, r in g.iterrows():
        dt = M.date.get(mid); ev = M.event.get(mid); ko = ' (knockout)' if M.knockout.get(mid) == 1 else ''
        what = f'{int(r.runs)} off {int(r.balls)}' if role == 'bat' else f'{int(r.balls // 6)}.{int(r.balls % 6)}-{int(r.runs)}-{int(r.wkts)}'
        out.append(f'{pd.Timestamp(dt):%d %b %Y} {ev}{ko} v {r.opp}, {"chasing" if r.inn == 2 else "setting"}: {what}, '
                   f'+{r.wpa * 100:.0f}% win probability ({int(r.pballs)} pressure balls)')
    return out


WIDTH_MED = {r: (lambda T: (T.score_hi - T.score_lo).head(30).median())(pd.read_csv(res(f'rankings/{r}_full_rankings.csv'))) for r in ['bat', 'bowl']}


def card(uid, r, role, header_rank):
    nm = r['name']
    st = []
    if r['p_n'] < 200: st.append(f'small pressure sample ({int(r.p_n)} balls)')
    if (r['score_hi'] - r['score_lo']) > 1.25 * WIDTH_MED[role]: st.append('interval much wider than typical (thin or inconsistent evidence)')
    if pd.notna(r['age']) and r['age'] >= 34: st.append(f'age {r.age:.0f} in 2027')
    if r.get('near_tie_with_next', False): st.append('statistical near-tie with the next-ranked player')
    if str(r['status']).startswith('Not eligible'): st.append(r['status'])
    if nm in NOTES and any(n['type'] == 'fitness' for n in NOTES[nm]): st.append('fitness concerns in 2026 reporting (see scouting panel)')
    if r.get('last_season', 2026) < 2026: st.append(f'no RR-pack balls in 2026 (last {int(r.last_season)})')
    cap = CAP.status_2027.get(uid, 'uncapped (no international)')
    typ = CL[role].get(uid, ID[('bat_role' if role == 'bat' else 'bowl_role')].get(uid, '-'))
    L = [f'### {header_rank}. {nm} ({r["nation"]})', '',
         f'*{typ} · age in 2027: {f(r.age, 0)} · {cap} · 2027 status: {r.status}*', '',
         '**Data (model outputs; RR pack 2022-26 for pressure numbers)**', '',
         f'- Pressure Reliability Score: **{r.score:.1f}** runs per 100 pressure balls above expectation '
         f'(80% interval {r.score_lo:.1f} to {r.score_hi:.1f}); P(top 10) = {r.p_top10:.0%}; plausible rank range {int(r.rank_lo)}-{int(r.rank_hi)}.',
         f'- Pressure balls: {int(r.p_n)}; observed run value per 100 balls: pressure {f(r.obs_pressure_rv100)}, normal '
         f'{f(r.obs_normal_rv100)} (the gap is not predictive - S4C - so it is shown, not scored).']
    if role == 'bat':
        L += [f'- Under pressure: SR {f(pv(uid, "bat", "pres", "1", "strike_rate"))}, dismissal every '
              f'{f(pv(uid, "bat", "pres", "1", "balls_per_dismissal"))} balls, boundary {f(pv(uid, "bat", "pres", "1", "boundary_pct"), pct=True)}, '
              f'dots {f(pv(uid, "bat", "pres", "1", "dot_pct"), pct=True)}. All situations (career T20, all sources): SR '
              f'{f(pv(uid, "bat", "all", "career", "strike_rate"))}, average {f(pv(uid, "bat", "all", "career", "average"))}.',
              f'- Phases (SR): PP {f(pv(uid, "bat", "phase", "PP", "strike_rate"))} · middle {f(pv(uid, "bat", "phase", "Middle", "strike_rate"))} '
              f'· death {f(pv(uid, "bat", "phase", "Death", "strike_rate"))}. Chasing SR {f(pv(uid, "bat", "setting", "chasing", "strike_rate"))} vs '
              f'setting {f(pv(uid, "bat", "setting", "setting", "strike_rate"))}.',
              f'- Matchup (reliable effect type, r = {MREL.get("batter: spin minus pace", np.nan):.2f}): run value per 100 balls vs pace '
              f'{f(pv(uid, "bat", "pace_spin", "Pace", "run_value_per100"))}, vs spin {f(pv(uid, "bat", "pace_spin", "Spin", "run_value_per100"))}.']
    else:
        L += [f'- Under pressure: economy {f(pv(uid, "bowl", "pres", "1", "economy"), 2)}, wicket every '
              f'{f(pv(uid, "bowl", "pres", "1", "strike_rate"))} balls, dots {f(pv(uid, "bowl", "pres", "1", "dot_pct"), pct=True)}, '
              f'boundaries {f(pv(uid, "bowl", "pres", "1", "boundary_pct"), pct=True)}. Career T20 (all sources): economy '
              f'{f(pv(uid, "bowl", "all", "career", "economy"), 2)}, average {f(pv(uid, "bowl", "all", "career", "average"))}.',
              f'- Phases (economy): PP {f(pv(uid, "bowl", "phase", "PP", "economy"), 2)} · middle {f(pv(uid, "bowl", "phase", "Middle", "economy"), 2)} '
              f'· death {f(pv(uid, "bowl", "phase", "Death", "economy"), 2)}. Speed (median, RR): {f(pv(uid, "bowl", "all", "career", "speed_median"))} km/h.',
              f'- Hand split (weak effect type, r = {MREL.get("bowler: vs left-handers minus vs right-handers", np.nan):.2f}; treat as noise): '
              f'economy vs LHB {f(pv(uid, "bowl", "bat_hand", "LHB", "economy"), 2)}, vs RHB {f(pv(uid, "bowl", "bat_hand", "RHB", "economy"), 2)}.']
    mo = moments(uid, role)
    L += ['- Biggest pressure performances (RR pack, by win probability added):'] + [f'  - {m}' for m in mo or ['none with 6+ pressure balls']]
    L += [f'- Risk flags (computed): {"; ".join(st) if st else "none"}.', '']
    L += ['**Scouting (qualitative, labelled; not used for ranking)**', '']
    if nm in NOTES:
        L += [f'- [{n["type"]}] {n["note"]} Source: [{n["source"]}]({n["url"]}).' for n in NOTES[nm]]
    else:
        L += ['- No recent public reporting checked for this player (not in the researched shortlist).']
    return '\n'.join(L + ['', '---', ''])



def main():
    for role, nice in [('bat', 'batters'), ('bowl', 'bowlers')]:
        T = pd.read_csv(res(f'rankings/{role}_full_rankings.csv'), index_col='uid')
        out = [f'# Scout cards: top {N_TOP} {nice} (open ranking)', '',
               'Score = predicted run value per 100 pressure balls next season (hierarchical Bayes, S4D). '
               'Data panels come from model outputs; scouting panels are labelled qualitative notes (2026-11-15).', '']
        for uid, r in T.head(N_TOP).iterrows():
            out.append(card(uid, r, role, int(r['rank'])))
        open(res(f'cards/SCOUT_CARDS_{nice}.md'), 'w').write('\n'.join(out))
    vo = ['# Scout cards: Uncapped & Value Targets (top 5 per list)', '']
    for role, nice in [('bat', 'batters'), ('bowl', 'bowlers')]:
        p = res(f'value/{role}_uncapped_value_top10.csv')
        if not os.path.exists(p):
            continue
        T = pd.read_csv(res(f'value/{role}_pool_all.csv'), index_col='uid')
        top = pd.read_csv(p, index_col='uid').head(5)
        vo += [f'## {nice.title()}', '']
        for i, (uid, _) in enumerate(top.iterrows(), 1):
            r = T.loc[uid]
            vo.append(card(uid, r, role, i).replace('**Data (model', f'*Tier: {r.tier} · predicted 2027 price Rs {r.pred_price_cr:.1f} cr '
                                                    f'(last auction: {f(r.last_price_cr, 2)} cr) · value per crore {r.value_per_cr:.1f}*\n\n**Data (model'))
    open(res('cards/VALUE_CARDS.md'), 'w').write('\n'.join(vo))
    print('cards written')

    # ---------------- youth cards (S5C): top 5 batters + top 5 bowlers aged <= 23 ----------------
    # Minors policy: cricket data and age only; no personal details. Lower-resolution notes (public match reporting) are
    # labelled and never enter the projections.
    CP = pd.read_csv(res('youth/comparables.csv')) if os.path.exists(res('youth/comparables.csv')) else pd.DataFrame()
    UB = pd.read_parquet(w('unified/balls.parquet'), columns=['batter', 'bowler', 'comp2', 'season', 'legal'])
    UB = UB[UB.legal & (UB.season >= 2022)]
    yo = ['# Youth scout cards (age 23 and under on 1 April 2027)', '',
          'Data: competition-, venue- and opponent-adjusted run value per 100 balls (all leagues 2019-26), projections from the '
          'backtested development model (`youth/YOUTH_REPORT.md`). Nationality comes from international records, else Wikidata - '
          'verify before bidding where it is shown as from Wikidata or unknown. Minors policy: cricket information and age only.', '']
    for role, nice, col in [('bat', 'Batters', 'batter'), ('bowl', 'Bowlers', 'bowler')]:
        p = res(f'youth/{role}_board_u23.csv')
        if not os.path.exists(p):
            continue
        Y = pd.read_csv(p, index_col='uid').head(5)
        yo += [f'## {nice}', '']
        for uid, r in Y.iterrows():
            comp = UB[UB[col] == uid].comp2.value_counts(normalize=True).head(4)
            cps = CP[(CP.uid == uid) & (CP.role == role)] if len(CP) else pd.DataFrame()
            nat = CAP.nationality.get(uid, 'unknown') if 'nationality' in CAP else '-'
            src = 'international record' if pd.notna(CAP.intl_team.get(uid)) else ('Wikidata' if nat not in ('unknown', 'India') else 'inferred / unknown')
            yo += [f'### {int(r.board_rank)}. {r["name"]} - {r.label}', '',
                   f'*Age {int(r.age)} on 1 Apr 2027 · {nat} ({src}) · {r.cap_status} · 2027 status: {r.status_2027}*', '',
                   '**Data**', '',
                   f'- Adjusted skill: **{r.skill:.1f}** runs per 100 balls vs average (SE {r.se:.1f}; {int(r.n)} balls). '
                   f'{r.sample_flag if isinstance(r.sample_flag, str) and r.sample_flag else "Sample adequate."}',
                   f'- Projection, next season: {r.proj_1:.1f} (80% interval {r.proj_1_lo:.1f} to {r.proj_1_hi:.1f}); in 2 seasons {r.proj_2:.1f}; '
                   f'in 3 seasons {r.proj_3:.1f}.',
                   '- Balls since 2022 by competition: ' + ', '.join(f'{k} {v:.0%}' for k, v in comp.items()) + '.',
                   '- Historical comparables (same age, similar adjusted skill in 2019-21 -> skill 2024-26): ' +
                   ('; '.join(f'{c.comparable} ({c.comp_skill_at_same_age:.0f} -> {fmt_or_dash(c.comp_later_skill)})' for c in cps.itertuples()) if len(cps) else 'none found') + '.',
                   '', '**Lower-resolution reports (labelled; not used in projections)**', '']
            notes = NOTES.get(f'youth:{r["name"]}', [])
            yo += [f'- {n["note"]} Source: [{n["source"]}]({n["url"]}).' for n in notes] or ['- None collected.']
            yo += ['', '---', '']
    open(res('cards/YOUTH_CARDS.md'), 'w').write('\n'.join(yo))
    print('youth cards written')



if __name__ == '__main__':
    main()
