"""S5B: value hunting - uncapped and low-priced pressure performers.

1. Auction prices 2022-2026 parsed from Wikipedia (CC BY-SA) 'personnel changes' pages (rendered HTML, cached in
   data_public/wikipedia/), names matched to player ids (exact / unique fuzzy >= 92 within the modelled pool).
2. Price model: log(price) ~ capped, overseas, age, role, model skill estimate (theta at the season before the
   auction, from the S4B backtest cutoffs - so no future information), IPL experience. Validated out of time
   (fit auctions <= s, predict auction s+1) against a simple baseline (median by capped x overseas).
3. Emerging tier: players with 40-149 RR pressure balls, rated by the same final Bayesian model (wider intervals).
4. Upside backtest: do the model's early estimates for players who were UNCAPPED at cutoff c predict their later
   pressure performance as well as for capped players? (small sample; reported as such)
5. Value list: available (not RR, not ineligible) players who are uncapped OR have a predicted 2027 price <= Rs 3 cr,
   with >= 40 pressure balls; ranked by predicted pressure run value; value per crore =
   (score - replacement level) / predicted price, replacement = 25th percentile score of the eligible pool.
6. Pool CSVs for the Phase 7 optimiser (documented format).
Outputs: v2_results/value/*.csv, VALUE_REPORT.md; v2_work/value/prices.parquet
"""
import io
import re
import json
from rapidfuzz import fuzz, process
from common import *
import skill as K
import s13_final as F13

seed_all()
WK = os.path.join(PUB, 'wikipedia')
P = pd.read_parquet(w('unified/players.parquet')).set_index('uid')
CAP = pd.read_parquet(w('value/capped.parquet')).set_index('uid')
ID = pd.read_parquet(w('profiles/player_identity.parquet')).set_index('uid')
L = ['# Value hunting: uncapped and low-priced pressure performers (S5B)', '']

# ---------------- 1. prices ----------------
rows = []
for y in [2022, 2023, 2024, 2025, 2026]:
    h = json.load(open(os.path.join(WK, f'ipl_personnel_{y}_html.json')))['parse']['text']
    for t in pd.read_html(io.StringIO(h)):
        cols = [' '.join(map(str, c)) if isinstance(c, tuple) else str(c) for c in t.columns]
        t.columns = cols
        pc = [c for c in cols if 'uction' in c and 'rice' in c]
        nc = [c for c in cols if c.split(' ')[0] == 'Name']
        if not pc or not nc:
            continue
        bc = [c for c in cols if 'ase' in c and 'rice' in c]
        tc = [c for c in cols if f'{y} IPL team' in c or f'IPL {y} Team' in c]
        cc = [c for c in cols if 'Capped' in c or c.startswith('Category')]
        d = pd.DataFrame({'year': y, 'name_wiki': t[nc[0]].astype(str), 'price_lakh': t[pc[0]],
                          'base_lakh': t[bc[0]] if bc else np.nan, 'team': t[tc[0]] if tc else None,
                          'country': t[[c for c in cols if c.startswith('Country')][0]] if any(c.startswith('Country') for c in cols) else None,
                          'cap_wiki': t[cc[0]] if cc else None})
        rows.append(d)
PZ = pd.concat(rows, ignore_index=True)
PZ['name_wiki'] = PZ.name_wiki.str.replace(r'\[.*?\]|[†‡*^#]', '', regex=True).str.strip()
num = lambda s: pd.to_numeric(s.astype(str).str.replace(r'[^0-9.]', '', regex=True), errors='coerce')
PZ['price_cr'] = num(PZ.price_lakh) / 100; PZ['base_cr'] = num(PZ.base_lakh) / 100
PZ = PZ[PZ.price_cr.notna() & PZ.price_cr.gt(0)].drop_duplicates(['year', 'name_wiki'])
# name -> uid: exact on RR name / Cricsheet full name, else unique fuzzy >= 92 among modelled players
people = pd.read_csv(os.path.join(PUB, 'people.csv')).set_index('identifier')
pool = P[P.index.isin(ID[(ID.bat_balls_all.fillna(0) + ID.bowl_balls_all.fillna(0)) > 0].index)]
cand = pd.concat([pool.name.rename('n'), people.name.reindex(pool.index).rename('n'), pool.cs_name.rename('n')]).dropna()
cand = cand.reset_index().rename(columns={'index': 'uid', 'uid': 'uid'}).drop_duplicates()
norm = lambda s: re.sub(r'[^a-z ]', '', str(s).lower().replace('.', ' ')).strip()
cand['k'] = cand.n.map(norm)
ex = cand.groupby('k').uid.unique()
keys = cand.k.tolist()
def match(nm):
    k = norm(nm)
    if k in ex.index and len(ex[k]) == 1:
        return ex[k][0], 'exact'
    hits = process.extract(k, keys, scorer=fuzz.token_sort_ratio, limit=5)
    u = {cand.uid.iloc[i]: s for _, s, i in hits if s >= 92}
    return (list(u)[0], 'fuzzy') if len(u) == 1 else (None, 'unmatched')
mm = PZ.name_wiki.map(match)
PZ['uid'] = [m[0] for m in mm]; PZ['match'] = [m[1] for m in mm]
os.makedirs(w('value'), exist_ok=True); os.makedirs(res('value'), exist_ok=True)
for c_ in ['price_lakh', 'base_lakh', 'team', 'country', 'cap_wiki']:
    PZ[c_] = PZ[c_].astype(str)
PZ.to_parquet(w('value/prices.parquet'), index=False)
PZ[['year', 'name_wiki', 'uid', 'match', 'price_cr', 'base_cr', 'team']].assign(name_model=PZ.uid.map(P.name)) \
    .to_csv(res('value/auction_prices_matched.csv'), index=False)
L += [f'- Auction prices parsed: {len(PZ)} sales 2022-26; matched to modelled players: {PZ.uid.notna().sum()} '
      f'({PZ.uid.notna().mean():.0%}; exact {int((PZ.match == "exact").sum())}, fuzzy {int((PZ.match == "fuzzy").sum())}). '
      f'Sales per year: {PZ.groupby("year").size().to_dict()}.']

# ---------------- 2. price model (out-of-time) ----------------
bt = pd.concat([pd.read_parquet(w(f'skill/bt_{r}.parquet')).assign(role=r) for r in ['bat', 'bowl']])
bt['theta'] = bt.M8_theta
sk = bt.pivot_table(index=['pid', 'cutoff'], columns='role', values='theta').reset_index()
sk.columns = ['uid', 'cutoff', 'skill_bat', 'skill_bowl']
D = PZ[PZ.uid.notna() & PZ.year.between(2023, 2026)].copy()
D['cutoff'] = D.year - 1
D = D.merge(sk, on=['uid', 'cutoff'], how='left')
nat = F13.NAT
D['overseas'] = ~D.uid.map(lambda u: nat.get(u, 'India')).eq('India')
D['capped'] = D.uid.map(CAP.capped_2027).fillna(False).astype(bool)   # proxy: current status
D['age'] = (pd.to_datetime(D.year.astype(str) + '-04-01') - pd.to_datetime(D.uid.map(ID.dob))).dt.days / 365.25
D['bowler'] = D.uid.map(ID.bowl_balls_all).fillna(0) > D.uid.map(ID.bat_balls_all).fillna(0)
D['prev_price'] = [PZ[(PZ.uid == u) & (PZ.year < y)].sort_values('year').price_cr.iloc[-1] if ((PZ.uid == u) & (PZ.year < y)).any() else np.nan
                   for u, y in zip(D.uid, D.year)]
D['skill'] = np.where(D.bowler, D.skill_bowl, D.skill_bat)
D['skill_max'] = D[['skill_bat', 'skill_bowl']].max(1)
X_COLS = ['capped', 'overseas', 'age', 'age2', 'bowler', 'skill', 'skill_max', 'has_skill', 'log_prev', 'has_prev', 'mega']
def design(d):
    X = pd.DataFrame(index=d.index)
    X['capped'] = d.capped.astype(float); X['overseas'] = d.overseas.astype(float)
    X['age'] = d.age.fillna(26); X['age2'] = (X.age - 27) ** 2; X['bowler'] = d.bowler.astype(float)
    X['skill'] = d.skill.fillna(0) * 100; X['skill_max'] = d.skill_max.fillna(0) * 100; X['has_skill'] = d.skill.notna().astype(float)
    X['log_prev'] = np.log(d.prev_price.fillna(1)); X['has_prev'] = d.prev_price.notna().astype(float)
    X['mega'] = (d.get('year', pd.Series(2027, index=d.index)) == 2025).astype(float)
    return X[X_COLS]
from sklearn.linear_model import Ridge
pm_rows = []
for s in [2024, 2025, 2026]:
    tr, te = D[D.year < s], D[D.year == s]
    if len(te) < 10:
        continue
    m = Ridge(alpha=1.0).fit(design(tr), np.log(tr.price_cr))
    p = m.predict(design(te))
    base = tr.groupby(['capped', 'overseas']).price_cr.median()
    pb = np.log([base.get((c, o), tr.price_cr.median()) for c, o in zip(te.capped, te.overseas)])
    pm_rows.append(dict(test_auction=s, n=len(te), mae_log_model=np.mean(np.abs(np.log(te.price_cr) - p)),
                        mae_log_baseline=np.mean(np.abs(np.log(te.price_cr) - pb)),
                        corr_model=np.corrcoef(p, np.log(te.price_cr))[0, 1]))
PMV = pd.DataFrame(pm_rows); PMV.round(3).to_csv(res('value/price_model_validation.csv'), index=False)
pmod = Ridge(alpha=1.0).fit(design(D), np.log(D.price_cr))
coef = pd.Series(pmod.coef_, index=X_COLS)
L += ['', '## Price model (out-of-time)', '', PMV.round(3).to_markdown(index=False), '',
      f'- Coefficients on log price (all auctions 2023-26): {coef.round(3).to_dict()}.',
      '- `mae_log` = mean absolute error of log price (0.69 = off by a factor of 2 on average). Auction prices depend on '
      'team needs and bidding wars, so the model is a rough guide to the likely price band, not a forecast of the hammer price.']

# ---------------- 3. emerging tier + final pool ----------------
pools = {}
for role in ['bat', 'bowl']:
    Fr, th, de, summ, el, _ = F13.fit_role(role, min_p=40, last=2025, draws=1500)
    T = F13.table(role, Fr, th, de, summ, el)
    T['tier'] = np.where(T.p_n >= 150, 'established (150+ pressure balls)', 'emerging (40-149 pressure balls)')
    T['capped_2027'] = T.index.map(CAP.capped_2027).fillna(False).astype(bool)
    T['cap_status'] = T.index.map(CAP.status_2027).fillna('uncapped (no international)')
    lp = PZ[PZ.uid.notna()].sort_values('year').groupby('uid').last()
    T['last_auction_year'] = lp.year.reindex(T.index); T['last_price_cr'] = lp.price_cr.reindex(T.index)
    Dq = pd.DataFrame({'capped': T.capped_2027, 'overseas': ~T.nation.eq('India'), 'age': T.age,
                       'bowler': role == 'bowl', 'skill': T.score / 100, 'skill_max': T.score / 100,
                       'prev_price': T.last_price_cr, 'year': 2027}, index=T.index)
    T['pred_price_cr'] = np.exp(pmod.predict(design(Dq))).clip(0.3, 30)
    repl = T[T.tier.str.startswith('established')].score.quantile(0.25)
    T['value_per_cr'] = (T.score - repl) / T.pred_price_cr
    T['replacement_level'] = repl
    pools[role] = T
    T.round(4).to_csv(res(f'value/{role}_pool_all.csv'), index_label='uid')

# ---------------- 4. upside backtest ----------------
up = []
capdate = None
I_first = pd.read_parquet(w('value/capped.parquet')).set_index('uid').first_intl
for role in ['bat', 'bowl']:
    b = pd.read_parquet(w(f'skill/bt_{role}.parquet'))
    for c in [2022, 2023, 2024]:
        x = b[(b.cutoff == c) & (b.all_n >= 60)].copy()
        # realised pressure run value in all later RR seasons (c+1 .. 2026), from the final ball values
        x['uncapped_then'] = ~(pd.to_datetime(x.pid.map(I_first)) <= pd.Timestamp(f'{c}-12-31'))
        later = []
        for s in range(c + 1, 2027):
            y = b[(b.cutoff == s - 1)][['pid', 'y', 'yn']]
            later.append(y)
        Y = pd.concat(later).dropna().groupby('pid').apply(lambda d: pd.Series({'y_later': np.average(d.y, weights=d.yn), 'n_later': d.yn.sum()}), include_groups=False)
        x = x.merge(Y, left_on='pid', right_index=True)
        for g, d in x.groupby('uncapped_then'):
            if len(d) >= 8:
                up.append(dict(role=role, cutoff=c, group='uncapped at cutoff' if g else 'capped at cutoff', n=len(d),
                               corr_theta_vs_later=np.corrcoef(d.M8_theta, d.y_later)[0, 1],
                               corr_raw_pressure_vs_later=np.corrcoef(d.p_raw.fillna(0), d.y_later)[0, 1]))
UP = pd.DataFrame(up); UP.round(3).to_csv(res('value/upside_backtest.csv'), index=False)
L += ['', '## Upside backtest: do early estimates for uncapped players hold up?', '',
      UP.groupby(['role', 'group'])[['n', 'corr_theta_vs_later', 'corr_raw_pressure_vs_later']].mean().round(3).to_markdown(), '',
      '- Correlation of the model estimate at cutoff c with the player\'s pressure run value in all later RR seasons. '
      'Uncapped samples are small (tens of players), so treat differences between groups as indicative only.']

# ---------------- 5. value lists ----------------
for role in ['bat', 'bowl']:
    T = pools[role]
    # a contracted player with no auction price on record was retained (often at a high salary): price unknown -> only
    # eligible for the value list if uncapped (uncapped retention salaries are capped low)
    T['price_known'] = T.last_price_cr.notna() | T.status.str.startswith('Open market')
    V_ = T[T.buyable & (~T.capped_2027 | ((T.pred_price_cr <= 3.0) & T.price_known))].copy()
    V_ = V_.sort_values('score', ascending=False)
    V_['value_rank'] = np.arange(1, len(V_) + 1)
    V_.round(4).to_csv(res(f'value/{role}_uncapped_value_targets_full.csv'), index_label='uid')
    show = V_.head(10)[['value_rank', 'name', 'nation', 'cap_status', 'tier', 'status', 'score', 'score_lo', 'score_hi',
                        'p_n', 'age', 'pred_price_cr', 'value_per_cr']]
    show.round(2).to_csv(res(f'value/{role}_uncapped_value_top10.csv'), index_label='uid')
    L += ['', f'## Uncapped & Value Targets: {"batters" if role == "bat" else "bowlers"} (top 10)', '',
          show.round(2).to_markdown(index=False)]

# ---------------- 6. Phase 7 pools ----------------
for role in ['bat', 'bowl']:
    T = pools[role]
    cols = ['name', 'nation', 'cap_status', 'tier', 'status', 'team27', 'buyable', 'score', 'score_lo', 'score_hi', 'p_top10',
            'p_n', 'age', 'role_label', 'last_price_cr', 'pred_price_cr', 'price_known', 'value_per_cr']
    T[cols].round(4).to_csv(res(f'value/phase7_pool_{role}.csv'), index_label='uid')
L += ['', '## Phase 7 pool format (`phase7_pool_{bat,bowl}.csv`)', '',
      '| column | meaning |', '|---|---|', '| uid | player id (Cricsheet identifier or rr<id>) |',
      '| score, score_lo, score_hi | predicted run value per 100 pressure balls, 80% credible interval |',
      '| p_top10 | posterior probability of a top-10 rank among established players |',
      '| tier | established (150+ RR pressure balls) or emerging (40-149) |',
      '| cap_status | IPL 2027 capped/uncapped (5-year rule applied to Indian players) |',
      '| status, team27, buyable | 2027 availability after the 17 Nov 2026 retentions (config/retentions_2027.csv) |',
      '| last_price_cr, pred_price_cr | last auction price (Rs crore, Wikipedia) and price-model estimate for 2027 |',
      '| value_per_cr | (score - replacement level) / predicted price |',
      '| price_known | False = under contract with no auction price on record (retained); excluded from value lists unless uncapped |']
open(res('value/VALUE_REPORT.md'), 'w').write('\n'.join(L))
print('\n'.join(L))
