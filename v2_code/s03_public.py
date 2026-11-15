"""S2.2: parse Cricsheet csv2 archives (men's T20, 2019+) into one ball table + match table.

Output (v2_work/public/):
  cs_balls.parquet  - one row per delivery, Cricsheet person identifiers for striker/non-striker/bowler/dismissed
  cs_matches.parquet - one row per match: comp, date, teams, toss, winner, target, method, innings totals
"""
import io, zipfile, glob
from common import *

MIN_DATE = '2019-01-01'
COMP = {'ipl': 'IPL', 't20s': 'T20I', 'it20s': 'Unofficial T20I', 'bbl': 'BBL', 'psl': 'PSL', 'cpl': 'CPL',
        'sat': 'SA20', 'ilt': 'ILT20', 'mlc': 'MLC', 'ntb': 'T20 Blast', 'sma': 'SMAT', 'ssm': 'Super Smash',
        'bpl': 'BPL', 'lpl': 'LPL', 'ctc': 'CSA T20 Challenge'}
BALL_COLS = ['match_id', 'innings', 'ball', 'batting_team', 'bowling_team', 'striker', 'non_striker', 'bowler',
             'runs_off_bat', 'extras', 'wides', 'noballs', 'byes', 'legbyes', 'penalty', 'wicket_type',
             'player_dismissed', 'other_wicket_type', 'other_player_dismissed']


def parse_info(txt):
    d = {'teams': [], 'reg': {}}
    for row in csv_rows(txt):
        if len(row) < 3 or row[0] != 'info':
            continue
        k = row[1]
        if k == 'team': d['teams'].append(row[2])
        elif k == 'registry' and row[2] == 'people': d['reg'][row[3]] = row[4]
        elif k in ('target_runs', 'target_overs'): d[k] = row[3] if len(row) > 3 else row[2]
        elif k in ('winner_runs', 'winner_wickets', 'outcome', 'method', 'eliminator'): d[k] = row[2]
        elif k not in ('player', 'umpire', 'reserve_umpire', 'tv_umpire', 'match_referee', 'player_of_match'):
            d.setdefault(k, row[2])
    return d


def csv_rows(txt):
    import csv
    return csv.reader(io.StringIO(txt))


matches, balls = [], []
for zp in sorted(glob.glob(os.path.join(PUB, 'zips', '*_male_csv2.zip'))):
    key = os.path.basename(zp).split('_male')[0]
    z = zipfile.ZipFile(zp)
    files = [n for n in z.namelist() if n.endswith('_info.csv')]
    n_kept = 0
    for fn in files:
        info = parse_info(z.read(fn).decode('utf-8'))
        date = info.get('date', '').replace('/', '-')
        if date < MIN_DATE or info.get('match_type') not in ('T20', 'IT20') or info.get('gender') != 'male':
            continue
        if str(info.get('balls_per_over', '6')) != '6':
            continue
        mid = fn.replace('_info.csv', '')
        bf = mid + '.csv'
        if bf not in z.namelist():
            continue
        d = pd.read_csv(io.BytesIO(z.read(bf)), dtype={'match_id': str, 'season': str}, low_memory=False)
        d = d[[c for c in BALL_COLS if c in d.columns]].copy()
        reg = info['reg']
        for c in ['striker', 'non_striker', 'bowler', 'player_dismissed', 'other_player_dismissed']:
            if c in d:
                d[c + '_cs'] = d[c].map(reg)
        d['match_id'] = f'{key}_{mid}'
        balls.append(d)
        matches.append(dict(match_id=f'{key}_{mid}', comp_key=key, comp=COMP[key], event=info.get('event'),
                            date=date, season=int(date[:4]), match_type=info.get('match_type'),
                            team1=info['teams'][0] if info['teams'] else None,
                            team2=info['teams'][1] if len(info['teams']) > 1 else None,
                            venue=info.get('venue'), city=info.get('city'), toss_winner=info.get('toss_winner'),
                            toss_decision=info.get('toss_decision'), winner=info.get('winner'),
                            outcome=info.get('outcome'), method=info.get('method'),
                            target_runs=info.get('target_runs'), target_overs=info.get('target_overs'),
                            overs=info.get('overs'), n_registry=len(reg)))
        n_kept += 1
    print(f'{key:6s} {COMP[key]:20s} kept {n_kept:5d} of {len(files):5d} matches')

B = pd.concat(balls, ignore_index=True)
M = pd.DataFrame(matches)
num = ['runs_off_bat', 'extras', 'wides', 'noballs', 'byes', 'legbyes', 'penalty']
B[num] = B[num].fillna(0).astype(int)
B['over'] = B.ball.astype(str).str.split('.').str[0].astype(int) + 1
B['seq'] = B.groupby(['match_id', 'innings']).cumcount()
tot = B.assign(t=B.runs_off_bat + B.extras).groupby(['match_id', 'innings']).t.sum().unstack()
M['inn1_total'] = M.match_id.map(tot.get(1)); M['inn2_total'] = M.match_id.map(tot.get(2))
for c in ['target_runs', 'target_overs']:
    M[c] = pd.to_numeric(M[c], errors='coerce')
os.makedirs(w('public'), exist_ok=True)
B.to_parquet(w('public/cs_balls.parquet'), index=False)
M.to_parquet(w('public/cs_matches.parquet'), index=False)
print('balls', len(B), 'matches', len(M))
print(M.pivot_table(index='comp', columns='season', values='match_id', aggfunc='count', fill_value=0).to_string())
unk = B[['striker_cs', 'bowler_cs']].isna().mean()
print('share of balls with no registry id:', unk.round(4).to_dict())
