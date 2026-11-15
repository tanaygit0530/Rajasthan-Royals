import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
U = os.environ.get('DATA_DIR') or (os.path.join(HERE, 'data') if os.path.isdir(os.path.join(HERE, 'data')) else os.path.join(HERE, '..', '02_data'))
U = os.path.join(U, '')
OUT = os.path.join(HERE, 'out') + os.sep
os.makedirs(OUT, exist_ok=True)

import pandas as pd, numpy as np
mp=pd.read_csv(U+'competition_team_player_mapping.csv'); c=pd.read_csv(U+'competitions.csv')
mp=mp.merge(c[['comp_id','match_format','season']],on='comp_id')
ipl_teams={'Chennai Super Kings','Mumbai Indians','Rajasthan Royals','Punjab Kings','Royal Challengers Bengaluru','Delhi Capitals','Kolkata Knight Riders','Sunrisers Hyderabad','Gujarat Titans','Lucknow Super Giants'}
intl=mp[(mp.match_format=='T20I')|(mp.comp_id.isin([2670,3289]))]
nat=intl.groupby('player_id').team_name.agg(lambda s:s.value_counts().index[0]).str.replace(' A$','',regex=True)
ipl26=mp[mp.comp_id==3298].drop_duplicates('player_id').set_index('player_id').team_name
# 2027 trades confirmed (as of 11 Nov 2026)
TRADES={'Kuldeep Yadav':'Lucknow Super Giants','Rishabh Pant':'Delhi Capitals','T Natarajan':'Sunrisers Hyderabad',
        'Liam Livingstone':'Chennai Super Kings','Jack Edwards':'Chennai Super Kings','Khaleel Ahmed':'Sunrisers Hyderabad',
        'Nathan Ellis':'Sunrisers Hyderabad','Hardik Pandya':'Punjab Kings','Arshdeep Singh':'Mumbai Indians'}
ABBR={'Chennai Super Kings':'CSK','Mumbai Indians':'MI','Rajasthan Royals':'RR','Punjab Kings':'PBKS','Royal Challengers Bengaluru':'RCB',
      'Delhi Capitals':'DC','Kolkata Knight Riders':'KKR','Sunrisers Hyderabad':'SRH','Gujarat Titans':'GT','Lucknow Super Giants':'LSG'}
def status(r):
    team=TRADES.get(r['name'], r['ipl26'])
    if r['nation']=='Pakistan': return team,'Not eligible (Pakistan national)'
    if r['name']=='Harry Brook': return None,'Not eligible (IPL ban through 2027)'
    if r['name']=='Andre Russell': return None,'Not eligible (retired from IPL)'
    if team=='Rajasthan Royals': return team,'Already RR'
    if isinstance(team,str): return team,f'Under contract ({ABBR[team]}); only if released 17 Nov'
    return None,'Open market (not on a 2026 IPL roster)'
for role in ['bat','bowl']:
    t=pd.read_pickle(OUT+f'{role}_table.pkl')
    t['nation']=t.index.map(nat).fillna('India')
    t.loc[t.name.eq('Sunil Narine'),'nation']='West Indies'
    t[['team27','status']]=t.apply(lambda r: pd.Series(status(r)),axis=1)
    t['buyable']=~t.status.str.startswith(('Already','Not eligible'))
    t['open_market']=t.status.str.startswith('Open')
    b=t[t.buyable].copy(); b['buy_rank']=range(1,len(b)+1); t=t.join(b[['buy_rank']])
    t.to_pickle(OUT+f'{role}_final.pkl')
    cols=['rank','name','nation','status','p_balls','p_matches','rating','rating_lo','rating_hi','rank_lo','rank_hi','p_top10']
    pass #; 
    print(role.upper()); print(t[t.buyable][[c for c in ['buy_rank','rank','name','status','p_top10'] if c in t.columns]].head(14).to_string())

# ---- export readable ranking tables ----
for role in ['bat', 'bowl']:
    t = pd.read_pickle(OUT + f'{role}_final.pkl')
    cols = ['rank', 'name', 'nation', 'team27', 'status', 'buy_rank', 'p_balls', 'p_matches', 'rating',
            'x_main', 'x_rae', 'x_surv', 'consistency', 'delta'] + \
           [c for c in ['rating_lo', 'rating_hi', 'p_top10', 'rank_lo', 'rank_hi'] if c in t.columns]
    t[cols].round(3).to_csv(OUT + f'{role}_pressure_rankings.csv', index_label='player_id')
    print(f'saved {OUT}{role}_pressure_rankings.csv')
