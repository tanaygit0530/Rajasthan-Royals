"""S12: data bundle for the standalone presentation (presentation/private_data/deck.json, git-ignored, encrypted at build).
Subset of the evaluator-site export (s25) + photos (s28): only aggregated outputs for the 20 picks and the method/RR slides.
No ball-by-ball rows, no data-pack files."""
from common import *
import json
SITE = os.path.join(ROOT, 'site', 'private_data'); OUT = os.path.join(ROOT, 'presentation', 'private_data'); os.makedirs(OUT, exist_ok=True)
L = lambda n: json.load(open(os.path.join(SITE, n)))
meta, players, rankings, strategy, method, profiles, photos = map(L, ['meta.json', 'players.json', 'rankings.json', 'strategy.json', 'method.json', 'profiles.json', 'photos.json'])
lists = {r: rankings['lists'][r]['buy'][:10] for r in ['bat', 'bowl']}
ids = lists['bat'] + lists['bowl']
keep_prof = lambda p, r: {r: {k: p.get(r, {}).get(k) for k in ['all', 'pres', 'phase', 'setting']}, 'moments': p.get('moments', {}).get(r, [])[:3],
                          'notes': p.get('notes', [])[:3], 'flags': p.get('flags', [])}
deck = dict(
    meta={k: meta[k] for k in ['pressure_definition', 'score_definition', 'findings', 'certainty', 'counts', 'calibration', 'kw']},
    lists=lists, players={u: players[u] for u in ids},
    profiles={u: keep_prof(profiles.get(u, {}), 'bat' if u in lists['bat'] else 'bowl') for u in ids},
    method={k: method[k] for k in ['leverage', 'skill', 'league', 'calibration', 'sensitivity']},
    strategy={k: strategy[k] for k in ['gaps', 'plans', 'teams', 'pool', 'youth_pool']} | {'squad_n': len(strategy['squad'])},
    photos={u: photos['photos'][u] for u in ids if u in photos['photos']},
    credits={u: c for u, c in photos['credits'].items() if c.get('photo')})
json.dump(deck, open(os.path.join(OUT, 'deck.json'), 'w'), separators=(',', ':'), allow_nan=False)
print('deck.json', round(os.path.getsize(os.path.join(OUT, 'deck.json')) / 1e6, 2), 'MB')
