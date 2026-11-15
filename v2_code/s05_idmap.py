"""S2.3: (a) find RR-pack matches that also exist in Cricsheet (for dedupe), and
(b) map RR player_id -> Cricsheet person identifier.

Method A (primary) - ball alignment: in matches present in both sources, align deliveries over by over and
   vote (RR striker_id -> Cricsheet striker id), same for bowler and non-striker.
Method B (fallback) - name matching against the Cricsheet register (names.csv aliases), restricted to people who
   appear in the public T20 ball data, for RR players with no overlapping match.
Outputs: v2_work/public/match_overlap.parquet, v2_results/idmap/idmap.csv, idmap_report.md, idmap_top200_check.csv
"""
from common import *
from rapidfuzz import fuzz, process

# ---------------- RR side ----------------
b = rr('ball_by_ball.csv'); b = b[b.innings.isin([1, 2])]
m = rr('matches.csv')
b['total'] = b.runs + b.extras1_runs + b.extras_2_runs
tot = b.groupby(['match_id', 'innings']).total.sum().unstack()
R = m[['match_id', 'match_date', 'home_team', 'away_team']].copy()
R['inn1'] = R.match_id.map(tot.get(1)); R['inn2'] = R.match_id.map(tot.get(2))
R = R[R.inn1.notna()]
R['date'] = pd.to_datetime(R.match_date)

# ---------------- Cricsheet side ----------------
CB = pd.read_parquet(w('public/cs_balls.parquet'))
CM = pd.read_parquet(w('public/cs_matches.parquet'))
CM = CM[CM.season >= 2021].copy()
CM['date'] = pd.to_datetime(CM.date)

# ---------------- (a) match pairing: date +-1 day and both innings totals equal ----------------
cand = R.merge(CM[['match_id', 'date', 'inn1_total', 'inn2_total', 'comp', 'team1', 'team2']].rename(
    columns={'match_id': 'cs_match', 'date': 'cs_date'}), left_on=['inn1', 'inn2'], right_on=['inn1_total', 'inn2_total'])
cand = cand[(cand.cs_date - cand.date).abs().dt.days <= 1]
# keep 1:1 pairs; if several, prefer exact date
cand['dd'] = (cand.cs_date - cand.date).abs().dt.days
cand = cand.sort_values(['match_id', 'dd']).drop_duplicates('match_id').drop_duplicates('cs_match')
# no-result / abandoned matches with no second innings
nr = R[R.inn2.isna()]
print(f'RR matches with balls: {len(R) + 0}; paired with Cricsheet: {len(cand)}')

# ---------------- (b) ball alignment ----------------
b = b.sort_values(['match_id', 'innings', 'innings_ball_num'])
b['pos'] = b.groupby(['match_id', 'innings', 'overid']).cumcount()
CB['pos'] = CB.groupby(['match_id', 'innings', 'over']).cumcount()
cbx = CB[CB.match_id.isin(cand.cs_match)][['match_id', 'innings', 'over', 'pos', 'striker_cs', 'non_striker_cs', 'bowler_cs',
                                             'runs_off_bat', 'striker', 'bowler']]
bx = b[b.match_id.isin(cand.match_id)].merge(cand[['match_id', 'cs_match']], on='match_id')
A = bx.merge(cbx, left_on=['cs_match', 'innings', 'overid', 'pos'], right_on=['match_id', 'innings', 'over', 'pos'],
             suffixes=('', '_cs'))
A['runs_agree'] = A.runs == A.runs_off_bat
agree = A.groupby('match_id').runs_agree.mean()
good = agree[agree >= 0.9].index                                  # discard badly aligned matches
A = A[A.match_id.isin(good)]
print(f'aligned balls {len(A):,}; matches with >=90% run agreement {len(good)} of {agree.size}; '
      f'median agreement {agree.median():.3f}')

votes = pd.concat([A[['striker_id', 'striker_cs']].set_axis(['pid', 'cs'], axis=1),
                   A[['bowler_id', 'bowler_cs']].set_axis(['pid', 'cs'], axis=1),
                   A[['non_striker_id', 'non_striker_cs']].set_axis(['pid', 'cs'], axis=1)]).dropna()
vc = votes.value_counts().rename('votes').reset_index()
tot_v = vc.groupby('pid').votes.transform('sum')
vc['share'] = vc.votes / tot_v
best = vc.sort_values(['pid', 'votes'], ascending=[True, False]).drop_duplicates('pid')
best['method'] = 'A_ball_alignment'

# ---------------- names ----------------
names = pd.concat([b[['striker_id', 'striker_name']].set_axis(['pid', 'name'], axis=1),
                   b[['bowler_id', 'bowler_name']].set_axis(['pid', 'name'], axis=1),
                   b[['non_striker_id', 'non_striker_name']].set_axis(['pid', 'name'], axis=1)]).drop_duplicates('pid').set_index('pid').name
people = pd.read_csv(os.path.join(PUB, 'people.csv'))
alias = pd.read_csv(os.path.join(PUB, 'names.csv'))
CSNAME = people.set_index('identifier').unique_name

# ---------------- (c) fallback name matching ----------------
in_cs = set(CB.striker_cs.dropna()) | set(CB.bowler_cs.dropna()) | set(CB.non_striker_cs.dropna())
# NB: Cricsheet's t20s archive contains no Afghanistan matches (0 of 3,649) - Afghan players can only be found
# through franchise leagues, so they rely on this fallback.
al = pd.concat([alias.rename(columns={'name': 'n'}), people[['identifier', 'name']].rename(columns={'name': 'n'}),
                people[['identifier', 'unique_name']].rename(columns={'unique_name': 'n'})]).drop_duplicates()


def norm(s):
    s = str(s).lower().replace('.', ' ').replace('-', ' ')
    s = ''.join(ch for ch in s if ch.isalpha() or ch == ' ')
    return ' '.join(s.split())


def init_key(s):
    t = norm(s).split()
    return f'{t[0][0]} {t[-1]}' if len(t) >= 2 else None


def initials_compatible(rr_name, cs_name):
    """'Nimesh Vimukthi' ~ 'N Vimukthi' (initials form) or 'Mahfuzur Rabby' ~ 'Mahfuzur Rahman Rabby' (same first
    name). Rejects 'Mohammad Saleem Safi' ~ 'Mansoor Safi' (different full first name)."""
    r, c = norm(rr_name).split(), str(cs_name).replace('.', ' ').split()
    if len(c) < 2 or len(r) < 2:
        return False
    if all(tok.isupper() and len(tok) <= 4 for tok in c[:-1]):        # initials form, e.g. 'VS Halambage'
        return c[0][0].lower() == r[0][0]
    return c[0].lower() == r[0]


al['key'] = al.n.map(norm)
al['ikey'] = al.n.map(init_key)
# uniqueness is judged on the WHOLE register (all formats, all eras), matching only to people in the T20 ball data
full_ids = al.groupby('key').identifier.unique()
init_ids = al.groupby('ikey').identifier.unique()
alc = al[al.identifier.isin(in_cs)].reset_index(drop=True)
keys = alc.key.tolist()
used = set(best.cs)
rows = []
for pid in sorted(set(names.index) - set(best.pid)):
    nm = names[pid]; k = norm(nm); ik = init_key(nm)
    hits = process.extract(k, keys, scorer=fuzz.token_sort_ratio, limit=8)
    ids = pd.DataFrame([(alc.identifier.iloc[i], sc) for _, sc, i in hits], columns=['cs', 'score']) \
        .groupby('cs').score.max().sort_values(ascending=False)
    top = ids.index[0] if len(ids) else None
    sc1 = ids.iloc[0] if len(ids) else 0
    sc2 = ids.iloc[1] if len(ids) > 1 else 0
    cs, meth = None, 'unmatched'
    ex = full_ids.get(k, [])
    ii = init_ids.get(ik, []) if ik else []
    if len(ex) == 1 and ex[0] in in_cs and ex[0] not in used:
        cs, meth = ex[0], 'B1_exact_unique'
    elif len(ex) > 1:
        meth = 'unmatched_ambiguous_name'
    elif len(ii) == 1 and ii[0] in in_cs and ii[0] not in used and initials_compatible(nm, CSNAME.get(ii[0], '')):
        cs, meth = ii[0], 'B2_initial_surname_unique'
    elif top is not None and sc1 >= 92 and sc1 - sc2 >= 5 and top not in used:
        meth = 'unmatched_fuzzy_candidate'   # recorded in `cand` for manual review; NOT used for modelling
    rows.append(dict(pid=pid, cs=cs, votes=0, share=np.nan, score=sc1, runner_up=sc2, method=meth, cand=top,
                     n_exact=len(ex), n_initial=len(ii)))
fb = pd.DataFrame(rows)

idm = pd.concat([best.assign(score=np.nan), fb], ignore_index=True)
idm['rr_name'] = idm.pid.map(names)
idm['cs_name'] = idm.cs.map(CSNAME)
idm['cand_name'] = idm.cand.map(CSNAME) if 'cand' in idm else None
# usage volume in RR data (balls faced + bowled) to prioritise checks
vol = pd.concat([b.striker_id, b.bowler_id]).value_counts()
idm['rr_balls'] = idm.pid.map(vol).fillna(0).astype(int)
idm['name_sim'] = [fuzz.token_sort_ratio(str(a), str(c)) if isinstance(c, str) else np.nan for a, c in zip(idm.rr_name, idm.cs_name)]
# one-to-one check
dup_cs = idm[idm.cs.notna()].cs.duplicated(keep=False)
idm['cs_shared'] = False; idm.loc[idm.cs.notna(), 'cs_shared'] = dup_cs.values
idm = idm.sort_values('rr_balls', ascending=False)
idm[['pid', 'rr_name', 'cs', 'cs_name', 'method', 'votes', 'share', 'score', 'name_sim', 'rr_balls', 'cs_shared', 'cand', 'cand_name']] \
    .to_csv(res('idmap/idmap.csv'), index=False)
idm.head(200)[['pid', 'rr_name', 'cs', 'cs_name', 'method', 'votes', 'share', 'name_sim', 'rr_balls']] \
    .to_csv(res('idmap/idmap_top200_check.csv'), index=False)
cand[['match_id', 'cs_match', 'comp', 'date', 'inn1', 'inn2']].assign(aligned=cand.match_id.isin(good)) \
    .to_parquet(w('public/match_overlap.parquet'), index=False)

# ---------------- report ----------------
n = len(idm)
by = idm.method.str.split('_').str[0].value_counts(); byf = idm.method.value_counts()
L = ['# Player identity map: RR pack -> Cricsheet', '',
     f'- RR players: {n}. By method: {byf.to_dict()}. '
     f'Unmatched total: {by.get("unmatched", 0)} ({by.get("unmatched", 0) / n:.1%}).',
     f'- Share of RR balls (faced + bowled) covered by a mapped player: '
     f'{idm[~idm.method.str.startswith("unmatched")].rr_balls.sum() / idm.rr_balls.sum():.2%}.',
     f'- RR matches paired with a Cricsheet match: {len(cand)} of {len(R)}; well aligned (>=90% runs agree): {len(good)}.',
     f'- Ball-alignment vote share: median {best.share.median():.3f}, players below 0.9: {(best.share < 0.9).sum()}.',
     f'- Cricsheet ids used by more than one RR id: {int(idm.cs_shared.sum())}.', '',
     '## Unmatched players by RR balls (top 30)', '',
     idm[idm.method.str.startswith('unmatched')].head(30)[['pid', 'rr_name', 'rr_balls', 'cand_name', 'score']].to_markdown(index=False), '',
     '## Lowest name similarity among ball-aligned top-200 (manual check list)', '',
     idm.head(200).sort_values('name_sim').head(25)[['pid', 'rr_name', 'cs_name', 'votes', 'share', 'name_sim', 'rr_balls']].to_markdown(index=False)]
open(res('idmap/idmap_report.md'), 'w').write('\n'.join(L))
print('\n'.join(L))
