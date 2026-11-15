"""S2.7: date of birth for age-curve modelling (used ONLY to compute age; no other personal data is fetched or kept).

Source: Wikidata (CC0), SPARQL query for every item with an ESPNcricinfo player ID (P2697) and a date of birth (P569).
The query is generic (all cricketers) - nothing from the RR pack is sent. Joined to players via Cricsheet's
key_cricinfo. Raw download cached in data_public/wikidata_dob.csv (re-run with --refresh to re-download).
Output: v2_work/unified/players.parquet gains `dob`; v2_results/context/dob_coverage.csv
"""
import sys
import json
import urllib.parse
import urllib.request
from common import *

RAW = os.path.join(PUB, 'wikidata_dob.csv')
if '--refresh' in sys.argv or not os.path.exists(RAW):
    q = 'SELECT ?cid ?dob WHERE { ?p wdt:P2697 ?cid . ?p wdt:P569 ?dob . }'
    url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'})
    req = urllib.request.Request(url, headers={'User-Agent': 'cricket-analytics-research-script/1.0 (python urllib)'})
    js = json.load(urllib.request.urlopen(req, timeout=300))
    d = pd.DataFrame([(r['cid']['value'], r['dob']['value'][:10]) for r in js['results']['bindings']], columns=['cid', 'dob'])
    d.to_csv(RAW, index=False)
    with open(os.path.join(PUB, 'SOURCES.md'), 'a') as f:
        f.write(f'\n- Wikidata SPARQL (CC0): ESPNcricinfo ID (P2697) -> date of birth (P569), {len(d)} rows. '
                f'https://query.wikidata.org/ accessed {pd.Timestamp.now(tz="UTC"):%Y-%m-%d}. Used only to compute age.\n')
D = pd.read_csv(RAW, dtype=str)
D = D[D.cid.str.fullmatch(r'\d+')]
# a few items carry two DOB statements (precision variants) - keep the earliest full date, flag conflicts
D['dob'] = pd.to_datetime(D.dob, errors='coerce')
conf = D.groupby('cid').dob.nunique()
D = D.sort_values('dob').drop_duplicates('cid').set_index('cid').dob

P = pd.read_parquet(w('unified/players.parquet'))
P['dob'] = P.key_cricinfo.map(lambda k: D.get(str(int(k))) if pd.notna(k) else pd.NaT)
P['dob_conflict'] = P.key_cricinfo.map(lambda k: conf.get(str(int(k)), 0) > 1 if pd.notna(k) else False)
P.to_parquet(w('unified/players.parquet'), index=False)

# coverage weighted by balls in the data (who actually matters)
B = pd.read_parquet(w('unified/balls.parquet'), columns=['batter', 'bowler', 'source', 'comp'])
vol = pd.concat([B[['batter', 'source', 'comp']].rename(columns={'batter': 'uid'}),
                 B[['bowler', 'source', 'comp']].rename(columns={'bowler': 'uid'})])
vol = vol.merge(P[['uid', 'dob']], on='uid', how='left')
cov = vol.groupby(['source', 'comp']).apply(lambda d: pd.Series({'balls': len(d), 'share_with_dob': d.dob.notna().mean(),
                                                                 'players': d.uid.nunique(),
                                                                 'players_with_dob': d[d.dob.notna()].uid.nunique()}),
                                            include_groups=False)
os.makedirs(res('context'), exist_ok=True)
cov.round(3).to_csv(res('context/dob_coverage.csv'))
print('wikidata rows', len(D), '| players with dob', P.dob.notna().sum(), 'of', len(P))
print(cov.round(3).to_string())
