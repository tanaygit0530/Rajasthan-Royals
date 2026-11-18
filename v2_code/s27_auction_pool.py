"""S10: the IPL 2027 auction pool - every rated player NOT retained by any team (released + open market), ranked,
and the youngsters available in that pool.

Inputs: value/{bat,bowl}_pool_all.csv (calibrated ratings, established 150+ and emerging 40-149 pressure balls; s17),
youth/{bat,bowl}_youth_all.csv (s20), price model validation (range), retention statuses (s13 / config).
Open-market players were not on a 2026 IPL roster: they still have to register for the auction (flagged).
Outputs: v2_results/auction_pool/*.csv, AUCTION_POOL.md, FINAL_SUBMISSION/IPL2027_Auction_Pool_Lists.xlsx
"""
from common import *
from rr_fit_core import slots, BAT_SLOTS, BOWL_SLOTS

OUT = res('auction_pool'); os.makedirs(OUT, exist_ok=True)
pmv = pd.read_csv(res('value/price_model_validation.csv')); SIG = float(pmv.mae_log_model.mean() * 1.2533); Z = 1.2816
PMAX = float(pd.read_parquet(w('value/prices.parquet')).price_cr.max())
POOLS = ('In auction pool', 'Open market')
ID = pd.read_parquet(w('profiles/player_identity.parquet')).set_index('uid')
_PR = pd.read_parquet(w('profiles/player_profiles.parquet'), filters=[('split', '==', 'comp2'), ('metric', '==', 'balls')])


def assoc_share(role):
    x = _PR[_PR.role == role].pivot_table(index='pid', columns='split_value', values='value', aggfunc='sum').fillna(0)
    return (x.get('T20I-Assoc', 0) / x.sum(1)).rename('assoc_share')
L = ['# IPL 2027 auction pool: players not retained by any team', '',
     'Ranked by calibrated Pressure Rating (runs per 100 pressure balls above expectation). Established = 150+ RR-pack pressure '
     'balls; emerging = 40-149 (wider ranges). "Released by" = in the auction pool after the 17 Nov 2026 retentions; '
     '"open market" = not on a 2026 IPL roster and must register for the auction. Price = estimated range (P10-P90) from past '
     'auctions, not shown for players without an auction record.', '']
book = {}
for role, SL, nice in [('bat', BAT_SLOTS, 'Batters'), ('bowl', BOWL_SLOTS, 'Bowlers')]:
    T = pd.read_csv(res(f'value/{role}_pool_all.csv'), index_col='uid')
    T = T[T.status.astype(str).str.startswith(POOLS)].sort_values('score', ascending=False).copy()
    T.insert(0, 'pool_rank', np.arange(1, len(T) + 1))
    T['available_as'] = T.status.str.replace('In auction pool (released by ', 'Released by ', regex=False).str.replace(')', '', regex=False) \
        .str.replace('Open market (not on a 2026 IPL roster', 'Open market (must register)', regex=False)
    def _roles(u):
        r_ = ', '.join(s for s in slots(u) if s in SL)
        if r_: return r_
        if role == 'bowl': return {'Spin': 'Spin bowler', 'Pace': 'Pace bowler'}.get(ID.pace_spin.get(u), 'Bowler')
        return 'Batter'
    T['roles'] = [_roles(u) for u in T.index]
    T['assoc_share'] = assoc_share(role).reindex(T.index).fillna(0)
    T['evidence_flag'] = np.where(T.assoc_share >= 0.5, 'mostly associate T20Is (weaker opposition)', '')
    known = T.last_price_cr.notna() | T.status.str.startswith('Open market')
    T['price_lo_cr'] = np.where(known, T.pred_price_cr * np.exp(-Z * SIG), np.nan)
    T['price_hi_cr'] = np.where(known, np.minimum(T.pred_price_cr * np.exp(Z * SIG), PMAX), np.nan)
    cols = ['pool_rank', 'name', 'nation', 'age', 'tier', 'roles', 'score', 'score_lo', 'score_hi', 'p_n', 'cap_status', 'available_as',
            'last_price_cr', 'price_lo_cr', 'price_hi_cr', 'evidence_flag']
    O = T[cols].copy(); O['age'] = np.floor(O.age)
    O['tier'] = O.tier.str.split(' ').str[0]
    O = O.rename(columns={'score': 'rating', 'score_lo': 'low80', 'score_hi': 'high80', 'p_n': 'pressure_balls'})
    O.round(2).to_csv(os.path.join(OUT, f'{role}_auction_pool.csv'), index_label='uid')
    book[f'{nice} - auction pool'] = O.round(2)
    show = O.head(20).copy()
    show['range'] = [f'{a:.0f} to {b:.0f}' for a, b in zip(show.low80, show.high80)]
    L += [f'## {nice} in the auction pool ({len(O)} rated; top 20)', '',
          show[['pool_rank', 'name', 'nation', 'age', 'tier', 'roles', 'rating', 'range', 'available_as', 'evidence_flag']].round(1).to_markdown(index=False), '']
    # youngsters
    Y = pd.read_csv(res(f'youth/{role}_youth_all.csv'), index_col='uid')
    Y = Y[Y.status_2027.astype(str).str.startswith(POOLS)].copy()
    Y['rating'] = T.score.reindex(Y.index)
    Y['available_as'] = Y.status_2027.str.replace('In auction pool (released by ', 'Released by ', regex=False).str.replace(')', '', regex=False) \
        .str.replace('Open market (not on a 2026 IPL roster', 'Open market (must register)', regex=False)
    for grp, lo, hi in [('u23', 0, 23), ('24_26', 24, 26)]:
        G = Y[Y.age.between(lo, hi)].sort_values('proj_1', ascending=False).copy()
        G.insert(0, 'youth_rank', np.arange(1, len(G) + 1))
        G = G[['youth_rank', 'name', 'age', 'cap_status', 'label', 'n', 'proj_1', 'proj_1_lo', 'proj_1_hi', 'proj_3', 'rating', 'sample_flag', 'available_as']]
        G.round(2).to_csv(os.path.join(OUT, f'{role}_youth_available_{grp}.csv'), index_label='uid')
        book[f'{nice} - youth {"U23" if grp == "u23" else "24-26"}'] = G.round(2)
        if grp == 'u23':
            g = G.head(15).copy(); g['range'] = [f'{a:.0f} to {b:.0f}' for a, b in zip(g.proj_1_lo, g.proj_1_hi)]
            L += [f'## Youngsters available (age 23 or under on 1 Apr 2027) - {nice.lower()} ({len(G)}; top 15)', '',
                  'Projection = adjusted skill per 100 balls in all situations (all leagues; a different scale from the Pressure Rating). '
                  '"Rating" = Pressure Rating where the player has 40+ RR-pack pressure balls.', '',
                  g[['youth_rank', 'name', 'age', 'label', 'n', 'proj_1', 'range', 'rating', 'available_as']].round(1).to_markdown(index=False), '']
open(os.path.join(OUT, 'AUCTION_POOL.md'), 'w').write('\n'.join(L))
os.makedirs(os.path.join(ROOT, 'FINAL_SUBMISSION'), exist_ok=True)
with pd.ExcelWriter(os.path.join(ROOT, 'FINAL_SUBMISSION', 'IPL2027_Auction_Pool_Lists.xlsx')) as xw:
    pd.DataFrame({'About': [L[2], 'Sources: IPL 2027 retention lists (17 Nov 2026, cited in v2_code/config/); ratings from v2 pipeline.']}).to_excel(xw, 'README', index=False)
    for k, v in book.items():
        v.to_excel(xw, k[:31])
print('\n'.join(L))
