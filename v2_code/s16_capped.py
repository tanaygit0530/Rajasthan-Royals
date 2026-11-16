"""S5B(i): capped / uncapped status for the IPL 2027 auction.

IPL rule used: a player is 'capped' if he has played international cricket (Test, ODI or T20I); an Indian player
becomes 'uncapped' again if his last international match was 5 or more years before the auction season
(cut-off used: last international before 1 Jan 2022 -> uncapped for 2027; the exact auction date is not yet announced).
Sources: Cricsheet registries of every men's Test, ODI and T20I match (all years, ODC-By) + RR-pack T20I and full-member
appearances 2022-26 (covers Afghanistan, which Cricsheet's T20I archive lacks).
Output: v2_work/value/capped.parquet; v2_results/value/capped_status_check.csv
"""
import io
import csv
import zipfile
from common import *

rows = []
for key in ['t20s', 'odis', 'tests']:
    with zipfile.ZipFile(os.path.join(PUB, 'zips', f'{key}_male_csv2.zip')) as z:
        for n in z.namelist():
            if not n.endswith('_info.csv'):
                continue
            date, ttype, reg, plays = None, None, {}, []
            for r in csv.reader(io.StringIO(z.read(n).decode('utf-8'))):
                if len(r) < 3 or r[0] != 'info':
                    continue
                if r[1] == 'date' and date is None: date = r[2]
                elif r[1] == 'team_type': ttype = r[2]
                elif r[1] == 'registry' and r[2] == 'people' and len(r) >= 5: reg[r[3]] = r[4]
                elif r[1] == 'player' and len(r) >= 4: plays.append((r[2], r[3]))
            if ttype not in (None, 'international'):
                continue
            for team, name in plays:
                if name in reg:
                    rows.append((reg[name], team, date.replace('/', '-'), key))
I = pd.DataFrame(rows, columns=['uid', 'team', 'date', 'fmt'])
I['date'] = pd.to_datetime(I.date)
# RR pack internationals (T20I), mapped to uid
b = rr('playing_eleven.csv'); m = rr('matches.csv').merge(rr('competitions.csv')[['comp_id', 'match_format']], on='comp_id')
t = rr('teams.csv').drop_duplicates('team_id').set_index('team_id').team_name
b = b[b.is_played.astype(str).str.lower().eq('true')].merge(m[['match_id', 'match_date', 'match_format']], on='match_id')
b = b[b.match_format.eq('T20I')]
idm = pd.read_csv(res('idmap/idmap.csv')); U = idm[idm.method.str.match(r'^(A_|B1_|B2_)')].set_index('pid').cs.to_dict()
R = pd.DataFrame({'uid': b.player_id.map(lambda p: U.get(p, f'rr{int(p)}')), 'team': b.team_id.map(t),
                  'date': pd.to_datetime(b.match_date), 'fmt': 'rr_t20i'})
I = pd.concat([I, R], ignore_index=True)
FULL = {'India', 'Australia', 'England', 'South Africa', 'New Zealand', 'Pakistan', 'Sri Lanka', 'West Indies',
        'Afghanistan', 'Bangladesh', 'Zimbabwe', 'Ireland'}
g = I.groupby('uid')
# intl_matches counts distinct dates: the same match can appear in both Cricsheet and the RR pack
C = pd.DataFrame({'intl_matches': g.date.nunique(), 'first_intl': g.date.min(), 'last_intl': g.date.max(),
                  'intl_team': g.team.agg(lambda s: s.value_counts().index[0]),
                  'formats': g.fmt.agg(lambda s: ','.join(sorted(set(s))))})
C['played_for_india'] = C.index.isin(I[I.team.eq('India')].uid).astype(bool)
P = pd.read_parquet(w('unified/players.parquet')).set_index('uid')
C = C.reindex(P.index.union(C.index))
C['intl_matches'] = C.intl_matches.fillna(0).astype(int)
CUT = pd.Timestamp('2022-01-01')
C['capped_2027'] = np.where(C.intl_matches.eq(0), False,
                            np.where(C.played_for_india.astype('boolean').fillna(False).astype(bool) & (C.last_intl < CUT), False, True))
C['status_2027'] = np.select([C.intl_matches.eq(0), C.played_for_india.astype('boolean').fillna(False).astype(bool) & (C.last_intl < CUT)],
                             ['uncapped (no international)', 'uncapped (Indian, last international > 5 years ago)'], 'capped')
C['name'] = P.name.reindex(C.index)
# country for sport (Wikidata P1532, CC0; generic query, cached) - used only for IPL eligibility of players with no
# international record (e.g. uncapped Pakistan players in the PSL)
import json, urllib.parse, urllib.request
WD = os.path.join(PUB, 'wikidata_country.csv')
if not os.path.exists(WD):
    # country for sport (P1532) preferred, else country of citizenship (P27)
    q = ('SELECT ?cid ?cl WHERE { ?p wdt:P2697 ?cid . { ?p wdt:P1532 ?c } UNION { ?p wdt:P27 ?c } . '
         '?c rdfs:label ?cl . FILTER(LANG(?cl) = "en") }')
    url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'})
    js = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'cricket-analytics-research-script/1.0'}), timeout=300))
    pd.DataFrame([(r['cid']['value'], r['cl']['value']) for r in js['results']['bindings']], columns=['cid', 'country']).to_csv(WD, index=False)
    with open(os.path.join(PUB, 'SOURCES.md'), 'a') as f:
        f.write(f'\n- Wikidata SPARQL (CC0): ESPNcricinfo ID (P2697) -> country for sport (P1532) / citizenship (P27). Accessed {pd.Timestamp.now(tz="UTC"):%Y-%m-%d}. Used only for IPL eligibility.\n')
wd = pd.read_csv(WD, dtype=str)
wd['country'] = wd.country.replace({'India national cricket team': 'India', 'British India': 'India', 'Dominion of Pakistan': 'Pakistan',
                                    'United Kingdom': 'England', "People's Republic of China": 'China'})
wd = wd.drop_duplicates('cid').set_index('cid').country
kc = P.key_cricinfo.reindex(C.index)
C['wd_country'] = [wd.get(str(int(k))) if pd.notna(k) else None for k in kc]
B_ = pd.read_parquet(w('unified/balls.parquet'), columns=['batter', 'bowler', 'comp'])
indian_dom = set(B_[B_.comp.isin(['IPL', 'SMAT'])].batter) | set(B_[B_.comp.isin(['IPL', 'SMAT'])].bowler)
C['nationality'] = C.intl_team.str.replace(' A$', '', regex=True).fillna(C.wd_country.replace({'India national cricket team': 'India'}))
# manual, cited nationality for shortlisted players with no international or Wikidata record (youth reads, 16 Nov 2026)
MAN = res('youth/manual_nationality.csv')
if os.path.exists(MAN):
    mn = pd.read_csv(MAN).set_index('name').nationality
    nm_clean = C.name.str.replace(r' \(\d+\)$', '', regex=True)
    fill = nm_clean.map(mn)
    C['nationality'] = C.nationality.fillna(fill)
C['nationality'] = C.nationality.fillna(pd.Series(np.where(C.index.isin(indian_dom), 'India', 'unknown'), index=C.index))
os.makedirs(w('value'), exist_ok=True); os.makedirs(res('value'), exist_ok=True)
C.index.name = 'uid'
C.reset_index().to_parquet(w('value/capped.parquet'), index=False)
# check list: well-known recent cases
chk = C[C.name.isin(['MS Dhoni', 'Vaibhav Sooryavanshi', 'Priyansh Arya', 'Abhishek Sharma', 'Ashutosh Sharma',
                     'Shashank Singh', 'Riyan Parag', 'Prabhsimran Singh', 'Ayush Mhatre', 'Jos Buttler', 'Vipraj Nigam'])]
chk[['name', 'intl_matches', 'last_intl', 'played_for_india', 'status_2027']].to_csv(res('value/capped_status_check.csv'))
print(chk[['name', 'intl_matches', 'last_intl', 'played_for_india', 'status_2027']].to_string())
print(C.status_2027.value_counts())
