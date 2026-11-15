import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
U = os.environ.get('DATA_DIR') or (os.path.join(HERE, 'data') if os.path.isdir(os.path.join(HERE, 'data')) else os.path.join(HERE, '..', '02_data'))
U = os.path.join(U, '')
OUT = os.path.join(HERE, 'out') + os.sep
os.makedirs(OUT, exist_ok=True)

from ratings import *
from scipy.stats import spearmanr
import json
rows = []
for role in ['bat', 'bowl']:
    base, *_ = run(role, quiet=True)
    top = list(base.index[:10])
    variants = {
        'Pressure = top 33% of balls': dict(thr_q=0.67),
        'Pressure = top 20% of balls': dict(thr_q=0.80),
        'Pressure = top 10% of balls': dict(thr_q=0.90),
        'No recency weighting': dict(recency=False),
        'Equal component weights': dict(Wt={k: 0.2 for k in W}),
        'WPA only': dict(Wt={'x_main': 1.0}),
        'No pressure-vs-baseline delta': dict(Wt={'x_main': 0.4, 'x_rae': 0.25, 'x_surv': 0.15, 'consistency': 0.2}),
        'Eligibility 120 pressure balls': dict(min_p=120),
        'Eligibility 200 pressure balls': dict(min_p=200),
    }
    for nm, kw in variants.items():
        v, *_ = run(role, quiet=True, **kw)
        common = base.index.intersection(v.index)
        rho = spearmanr(base.loc[common, 'rating'], v.loc[common, 'rating']).correlation
        kept = len(set(top) & set(v.index[:10]))
        rows.append(dict(role=role, variant=nm, top10_kept=kept, spearman=round(rho, 3),
                         base_top10_in_variant_top15=len(set(top) & set(v.index[:15]))))
        # rank of each base top10 player under variant
        for p in top:
            rows[-1][NAME.get(p, p)] = int(v.loc[p, 'rank']) if p in v.index else None
pd.DataFrame(rows).to_pickle(OUT + 'sensitivity.pkl')
print(pd.DataFrame(rows)[['role', 'variant', 'top10_kept', 'base_top10_in_variant_top15', 'spearman']].to_string())
