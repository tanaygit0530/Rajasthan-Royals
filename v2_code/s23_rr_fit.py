"""S7: from ranking to selection - RR squad fit, role gaps, role shortlists, form trends, selector verdicts.

Squad: RR's 2026 IPL roster in the RR pack (27 players) with trades/retirements to 15 Nov 2026 (none involve RR);
2027 retentions are not published, so every 2026 player is assumed retained (stated assumption).
Ratings: the same calibrated Pressure Reliability Score as the main lists (established 150+ pressure balls and
emerging 40-149 tiers, s17 pools). Players with < 40 RR pressure balls: shown with no score.
Slots (a player can fill several): batting - opener, No.3, middle order (4-5), finisher (6-7), left-handed top-6;
bowling - powerplay pace, death pace, middle-overs spin, wrist spin, left-arm (pace or spin).
Gap = slot benchmark (median score of the 10 best eligible players in that slot) - RR's best in the slot.
Form trend (descriptive, NOT in the score - a recency-weighted model did not predict better in S4B): run value per 100
balls in the last 12 months vs 2022 to 12 months ago, all competitions.
Verdict rules (decision support; qualitative flags used only as risks, per hard rule 3):
  Core (already RR) | Not eligible | Medical check first (fitness flag in 2026 reporting) | Priority target (fills one of
  RR's two biggest gaps, P(top 10) >= 20%, available) | Target (top-10 score, available) | Value / back-up option.
Outputs: v2_results/rr_fit/*.csv, RR_FIT_REPORT.md, SELECTOR_VERDICTS.md
"""
import json
from common import *
import s13_final as F13

os.makedirs(res('rr_fit'), exist_ok=True)
ID = pd.read_parquet(w('profiles/player_identity.parquet')).set_index('uid')
CAP = pd.read_parquet(w('value/capped.parquet')).set_index('uid')
NOTES = json.load(open(res('cards/scouting_notes.json')))
POOL = {r: pd.read_csv(res(f'value/{r}_pool_all.csv'), index_col='uid') for r in ['bat', 'bowl']}
FULL = {r: pd.read_csv(res(f'rankings/{r}_full_rankings.csv'), index_col='uid') for r in ['bat', 'bowl']}
for r in POOL:   # P(top 10) from the main (established) ranking where available
    POOL[r]['p_top10'] = FULL[r].p_top10.reindex(POOL[r].index).fillna(POOL[r].p_top10)
mp = rr('competition_team_player_mapping.csv')
idm = pd.read_csv(res('idmap/idmap.csv')); U = idm[idm.method.str.match(r'^(A_|B1_|B2_)')].set_index('pid').cs.to_dict()
sq = mp[(mp.comp_id == 3298) & mp.team_name.eq('Rajasthan Royals')].copy()
sq['uid'] = sq.player_id.map(lambda p: U.get(p, f'rr{int(p)}'))
SQUAD = set(sq.uid)
L = ['# From ranking to selection: Rajasthan Royals fit (S7)', '',
     'Squad = RR\'s 2026 roster (27 players); 2027 retentions not yet published, so all are assumed retained. Scores are the '
     'calibrated Pressure Reliability Scores used in the main lists (runs per 100 pressure balls above expectation).', '']

from rr_fit_core import slots, BAT_SLOTS, BOWL_SLOTS   # shared with the site exporter
rows = []
for role, SL in [('bat', BAT_SLOTS), ('bowl', BOWL_SLOTS)]:
    T = POOL[role]
    for uid, r in T.iterrows():
        for s in slots(uid):
            if s in SL:
                rows.append(dict(slot=s, role=role, uid=uid, name=r['name'], score=r.score, score_lo=r.score_lo, score_hi=r.score_hi,
                                 p_top10=r.p_top10, tier=r.tier, status=r.status, buyable=r.buyable, nation=r.nation,
                                 age=r.age, pred_price_cr=r.pred_price_cr, price_known=r.get('price_known', True), in_rr=uid in SQUAD))
S = pd.DataFrame(rows)

# ---------------- form trend ----------------
V = pd.read_parquet(w('values/ball_values_final.parquet'), columns=['row', 'batter', 'bowler', 'faced', 'runs_bat', 'xruns', 'striker_out',
                                                                   'xout', 'bowl_runs', 'xbowl_runs', 'bowl_wkt', 'xbowl_wkt', 'season'])
D = pd.read_parquet(w('unified/balls.parquet'), columns=['date']).date.values
V['date'] = pd.to_datetime(D[V.row.values])
import skill as K
V['rv_bat'] = np.where(V.faced, (V.runs_bat - V.xruns) - K.KW * (V.striker_out - V.xout), np.nan)
V['rv_bowl'] = (V.xbowl_runs - V.bowl_runs) + K.KW * (V.bowl_wkt - V.xbowl_wkt)
cut = pd.Timestamp('2025-11-16')
def trend(uid, role):
    col, pid = ('rv_bat', 'batter') if role == 'bat' else ('rv_bowl', 'bowler')
    d = V[(V[pid] == uid) & V[col].notna() & (V.season >= 2022)]
    rec, old = d[d.date >= cut][col], d[d.date < cut][col]
    if len(rec) < 60 or len(old) < 120:
        return pd.Series({'recent_rv100': rec.mean() * 100 if len(rec) else np.nan, 'base_rv100': old.mean() * 100 if len(old) else np.nan,
                          'recent_balls': len(rec), 'trend': 'insufficient recent data'})
    diff = (rec.mean() - old.mean()) * 100
    se = np.sqrt(rec.var() / len(rec) + old.var() / len(old)) * 100
    t = 'rising' if diff > 1.5 * se else 'falling' if diff < -1.5 * se else 'steady'
    return pd.Series({'recent_rv100': rec.mean() * 100, 'base_rv100': old.mean() * 100, 'recent_balls': len(rec), 'trend': t})

# ---------------- RR squad table ----------------
sqt = []
for u in sq.uid:
    nm = ID.name.get(u, sq[sq.uid == u].player_name.iloc[0])
    b = POOL['bat'].loc[u] if u in POOL['bat'].index else None
    w_ = POOL['bowl'].loc[u] if u in POOL['bowl'].index else None
    sqt.append(dict(uid=u, name=nm, nation=F13.NAT.get(u, 'India'), overseas=F13.NAT.get(u, 'India') != 'India',
                    age_2027=ID.age_2027.get(u), slots=', '.join(slots(u)),
                    bat_score=None if b is None else round(b.score, 1), bowl_score=None if w_ is None else round(w_.score, 1),
                    bat_rank=FULL['bat']['rank'].get(u), bowl_rank=FULL['bowl']['rank'].get(u)))
SQ = pd.DataFrame(sqt).sort_values(['bat_score', 'bowl_score'], ascending=False)
SQ.to_csv(res('rr_fit/rr_squad_2026.csv'), index=False)
n_os = int(SQ.overseas.sum())
L += [f'## RR squad (2026 roster): {len(SQ)} players, {n_os} overseas', '',
      f'IPL rules allow 8 overseas players in a squad and 4 in the XI; the 2026 roster lists {n_os} (it includes in-season replacement '
      'signings), so at least one overseas player must go and every overseas signing has to displace someone. Players with no score '
      'have fewer than 40 RR-pack pressure balls.', '',
      SQ[['name', 'nation', 'age_2027', 'slots', 'bat_score', 'bat_rank', 'bowl_score', 'bowl_rank']].round(1).to_markdown(index=False), '']

# ---------------- gaps ----------------
gaps = []
for s, g in S.groupby('slot'):
    elig = g[~g.status.str.startswith('Not eligible')].sort_values('score', ascending=False)
    bench = elig.head(10).score.median()
    rrp = g[g.in_rr].sort_values('score', ascending=False)
    best = rrp.iloc[0] if len(rrp) else None
    gaps.append(dict(slot=s, benchmark_top10_median=bench, rr_best=None if best is None else best['name'],
                     rr_best_score=np.nan if best is None else best.score, gap=bench - (best.score if best is not None else 0),
                     rr_players_in_slot=len(rrp), rr_depth_above_benchmark=int((rrp.score >= bench).sum())))
G = pd.DataFrame(gaps).sort_values('gap', ascending=False)
G.round(2).to_csv(res('rr_fit/role_gaps.csv'), index=False)
top_gaps = list(G.slot.head(2))
L += ['## Where RR is weakest under pressure (gap = slot benchmark - RR\'s best; bigger = weaker)', '',
      G.round(1).to_markdown(index=False), '',
      f'- **Biggest gaps: {top_gaps[0]} and {top_gaps[1]}.** A slot with no rated RR player has a gap equal to the full benchmark.',
      '- Venue: Jaipur plays about 2.4 runs per 100 balls below an average ground and Guwahati about 3.8 above (s07); neither is '
      'extreme enough to change these priorities.', '']

# ---------------- shortlists ----------------
sh = []
for s in G.slot:
    g = S[(S.slot == s) & S.buyable & ~S.in_rr].sort_values('score', ascending=False)
    pick = g.head(3).assign(pick='top 3')
    val = g[(g.pred_price_cr <= 3) & g.price_known & ~g.uid.isin(pick.uid)].head(1).assign(pick='value pick')
    sh.append(pd.concat([pick, val]))
SH = pd.concat(sh)
# a predicted price is meaningless for players retained without ever being auctioned (salary far above the model's range)
SH['pred_price_cr'] = SH.pred_price_cr.where(SH.price_known.astype(bool))
SH['price'] = [f'{p:.1f}' if pd.notna(p) else 'unknown (retained)' for p in SH.pred_price_cr]
tr = pd.DataFrame([trend(u, r) for u, r in zip(SH.uid, SH.role)], index=SH.index)
SH = pd.concat([SH, tr], axis=1)
SH.round(2).to_csv(res('rr_fit/role_shortlists.csv'), index=False)
L += ['## Shortlists: best three available per slot, plus a value pick (predicted price <= Rs 3 cr)', '',
      'Available = not RR and not ineligible; most are under contract and only available if released. Form trend is descriptive: '
      'last 12 months vs 2022 to 12 months ago, all competitions (rising / falling = difference above 1.5 standard errors).', '']
for s in G.slot:
    t = SH[SH.slot == s][['pick', 'name', 'nation', 'score', 'score_lo', 'score_hi', 'p_top10', 'age', 'price', 'trend', 'status']].rename(columns={'price': 'pred price (Rs cr)'})
    L += [f'### {s}', '', t.round(1).to_markdown(index=False), '']

# ---------------- verdicts ----------------
def fitness_flag(nm):
    return any(n.get('type') == 'fitness' for n in NOTES.get(nm, []))


ver = []
cands = pd.concat([FULL['bat'].head(10).assign(role='bat'), FULL['bowl'].head(10).assign(role='bowl')])
cands = pd.concat([cands, POOL['bat'].loc[[u for u in SH[SH.role == 'bat'].uid.unique() if u not in cands.index and u in POOL['bat'].index]].assign(role='bat'),
                   POOL['bowl'].loc[[u for u in SH[SH.role == 'bowl'].uid.unique() if u not in cands.index and u in POOL['bowl'].index]].assign(role='bowl')])
for uid, r in cands.iterrows():
    sl = [s for s in slots(uid) if s in (BAT_SLOTS if r.role == 'bat' else BOWL_SLOTS)]
    st = str(r.status); nm = r['name']
    if uid in SQUAD:
        v = 'Core - already RR'
    elif st.startswith('Not eligible'):
        v = 'Not eligible'
    elif fitness_flag(nm):
        v = 'Medical check first'
    elif any(s in top_gaps for s in sl) and r.p_top10 >= 0.20:
        v = 'Priority target'
    elif pd.notna(r.get('rank')) and r.get('rank', 99) <= 10:
        v = 'Target'
    else:
        v = 'Value / back-up option'
    # alternative: next best available in the player's main slot
    alt = '-'
    if sl:
        g = S[(S.slot == sl[0]) & S.buyable & ~S.in_rr & (S.uid != uid)].sort_values('score', ascending=False)
        alt = g.name.iloc[0] if len(g) else '-'
    t = trend(uid, r.role)
    risks = []
    if fitness_flag(nm): risks.append('2026 fitness reports')
    if pd.notna(r.age) and r.age >= 34: risks.append(f'age {int(r.age)} on 1 Apr 2027')
    if r.score_lo < 0: risks.append('interval includes below-average')
    if t.trend == 'falling': risks.append('form falling')
    if 'price_known' in r and r.price_known is False: risks.append('price unknown (retained)')
    if st.startswith('Under contract'): risks.append('available only if released')
    ver.append(dict(role=r.role, name=nm, nation=r.nation, verdict=v, slots=', '.join(sl) or '-', score=r.score,
                    interval=f'{r.score_lo:.1f} to {r.score_hi:.1f}', p_top10=r.p_top10, form_trend=t.trend,
                    main_risks='; '.join(risks) or 'none flagged', alternative=alt, status=st))
VD = pd.DataFrame(ver)
order = ['Priority target', 'Target', 'Value / back-up option', 'Medical check first', 'Core - already RR', 'Not eligible']
VD['o'] = VD.verdict.map({k: i for i, k in enumerate(order)})
VD = VD.sort_values(['o', 'score'], ascending=[True, False]).drop(columns='o')
VD.round(3).to_csv(res('rr_fit/selector_verdicts.csv'), index=False)
SV = ['# Selector verdicts', '',
      'Decision support, not a replacement for judgement. Verdicts combine the calibrated model score, RR\'s role gaps and '
      'labelled qualitative risk flags (fitness reports are used only to flag risk, never to change a score).', '']
for v in order:
    t = VD[VD.verdict == v]
    if len(t):
        SV += [f'## {v} ({len(t)})', '']
        for r in t.itertuples():
            SV += [f'- **{r.name}** ({r.nation}, {"bat" if r.role == "bat" else "bowl"}) - fills: {r.slots}. Score {r.score:.1f} '
                   f'({r.interval}), P(top 10) {r.p_top10:.0%}, form {r.form_trend}. Risks: {r.main_risks}. If unavailable: {r.alternative}.']
        SV.append('')
open(res('rr_fit/SELECTOR_VERDICTS.md'), 'w').write('\n'.join(SV))
L += ['## Selector verdicts (summary)', '', VD.groupby('verdict').name.apply(lambda s: ', '.join(s)).reindex(order).dropna().to_frame('players').to_markdown(), '',
      'Full verdicts with risks and alternatives: `SELECTOR_VERDICTS.md`.']
open(res('rr_fit/RR_FIT_REPORT.md'), 'w').write('\n'.join(L))
print('\n'.join(L[:60]))
