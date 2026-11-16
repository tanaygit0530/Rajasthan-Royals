"""Shared RR-fit rules (role slots). Used by s23_rr_fit.py and the evaluator-site exporter (s25)."""
import pandas as pd
from common import *

ID = pd.read_parquet(w('profiles/player_identity.parquet')).set_index('uid')


def slots(uid):
    i = ID.loc[uid] if uid in ID.index else None
    out = []
    if i is None:
        return out
    bp = i.bat_pos_median
    if pd.notna(bp) and (i.bat_balls_all or 0) >= 200:
        out.append('Opener' if bp <= 2.5 else 'No.3' if bp <= 3.5 else 'Middle order (4-5)' if bp <= 5.5 else 'Finisher (6-7)' if bp <= 7.5 else None)
        if i.bat_hand == 'LHB' and bp <= 6.5:
            out.append('Left-handed top-6 bat')
    if (i.bowl_balls_all or 0) >= 300 and not i.part_timer:
        if i.pace_spin == 'Pace':
            if (i.pp_share or 0) >= 0.30: out.append('Powerplay pace')
            if (i.death_share or 0) >= 0.25: out.append('Death pace')
            if i.bowl_arm == 'Left': out.append('Left-arm bowler')
        elif i.pace_spin == 'Spin':
            if (i.mid_share or 0) >= 0.45: out.append('Middle-overs spin')
            if i.spin_kind == 'wrist': out.append('Wrist spin')
            if i.bowl_arm == 'Left': out.append('Left-arm bowler')
    return [s for s in out if s]


BAT_SLOTS = ['Opener', 'No.3', 'Middle order (4-5)', 'Finisher (6-7)', 'Left-handed top-6 bat']
BOWL_SLOTS = ['Powerplay pace', 'Death pace', 'Middle-overs spin', 'Wrist spin', 'Left-arm bowler']
