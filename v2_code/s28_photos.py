"""S11: photos for the 20 submitted players (web deck). Public, freely licensed images only.

Route: ESPNcricinfo id (Cricsheet people.csv) -> Wikidata item (P2697) -> image (P18) on Wikimedia Commons, else the
English Wikipedia lead image restricted to free licences (pilicense=free) ->
Commons licence metadata. Only CC0 / public domain / CC BY / CC BY-SA files are kept; each is credited (author, licence,
file page) on the deck's credits slide. Players without a usable image get an initials avatar in the deck.
Cricket-only: no other personal data is requested. Outputs: site/private_data/photos.json (git-ignored;
encrypted with the rest of the site data) and v2_results/deck/photo_credits.json.
"""
from common import *
import base64, json, re, time, urllib.parse, urllib.request

SITE = os.path.join(ROOT, 'site', 'private_data'); os.makedirs(SITE, exist_ok=True)
PHOTOS = {}
CRED = res('deck'); os.makedirs(CRED, exist_ok=True)
UA = {'User-Agent': 'SupeRR-S2-deck/1.0 (research use; contact via repository)'}
OK = re.compile(r'^(CC0|Public domain|PD|CC BY(-SA)? \d)', re.I)


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except Exception as e:  # rate limits: back off
            if k == tries - 1: raise
            time.sleep(10 * (k + 1))


FR = pd.read_csv(res('final_rankings.csv'))
pick = FR[FR.list.isin(['batters_rr_can_buy', 'bowlers_rr_can_buy'])][['uid', 'name']].drop_duplicates('uid')
P = pd.read_parquet(w('unified/players.parquet')).set_index('uid')
pick['cid'] = [str(int(P.key_cricinfo.get(u))) if pd.notna(P.key_cricinfo.get(u)) else None for u in pick.uid]
cids = ' '.join(f'"{c}"' for c in pick.cid.dropna())
q = f'SELECT ?cid ?img WHERE {{ VALUES ?cid {{ {cids} }} ?p wdt:P2697 ?cid . ?p wdt:P18 ?img . }}'
rows = json.loads(get('https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'})))['results']['bindings']
img = {}
for r in rows:
    img.setdefault(r['cid']['value'], urllib.parse.unquote(r['img']['value'].rsplit('/', 1)[1]))

def wiki_image(name):
    # fallback: English Wikipedia lead image, free licences only (pilicense=free), trying common disambiguations
    for t in (name, f'{name} (cricketer)'):
        d = json.loads(get('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(dict(
            action='query', titles=t, prop='pageimages|categories', piprop='name', pilicense='free', redirects=1,
            cllimit='max', format='json'))))
        pg = next(iter(d['query']['pages'].values()))
        cats = ' '.join(c['title'] for c in pg.get('categories', [])).lower()
        # must be a cricketer's page and the file name must carry the player's surname (guards against namesakes)
        if pg.get('pageimage') and 'cricketers' in cats \
                and name.split()[-1].lower() in pg['pageimage'].lower():
            return pg['pageimage']
    return None


credits = {}
for u, name, cid in pick.itertuples(index=False):
    f = img.get(cid) or wiki_image(name)
    if not f:
        credits[u] = dict(name=name, photo=False, reason='no freely licensed image on Wikidata or Wikipedia'); continue
    api = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(dict(
        action='query', titles=f'File:{f}', prop='imageinfo', iiprop='url|extmetadata', iiurlwidth=480, format='json'))
    ii = next(iter(json.loads(get(api))['query']['pages'].values()))['imageinfo'][0]
    md = ii['extmetadata']; lic = md.get('LicenseShortName', {}).get('value', '')
    artist = re.sub('<[^>]+>', '', md.get('Artist', {}).get('value', 'unknown')).strip()
    if not OK.match(lic):
        credits[u] = dict(name=name, photo=False, reason=f'licence not accepted: {lic}'); continue
    PHOTOS[u] = 'data:image/jpeg;base64,' + base64.b64encode(get(ii['thumburl'])).decode()
    credits[u] = dict(name=name, photo=True, file=f, author=artist[:120], licence=lic,
                      page=ii['descriptionurl'], accessed=pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d'))
    time.sleep(1.5)
json.dump(credits, open(os.path.join(CRED, 'photo_credits.json'), 'w'), indent=1)
json.dump(dict(photos=PHOTOS, credits=credits), open(os.path.join(SITE, 'photos.json'), 'w'))
print(sum(c['photo'] for c in credits.values()), 'of', len(credits), 'players with a freely licensed photo')
for c in credits.values():
    print(f"  {c['name']:24s} {'OK ' + c['licence'] if c['photo'] else '-- ' + c['reason']}")
