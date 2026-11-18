"""S9: the final submission PDF - compact (~10 pages), visual, every number read from v2_results/.

Builds v2_results/report/final/SupeRR_S2_Final_Report.html (+ .pdf via headless Chrome) with new charts in
v2_results/report/final/img/. Reuses the s19 charts where they already fit.
"""
import json
import shutil
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *

OUT = res('report/final'); IMG = os.path.join(OUT, 'img'); os.makedirs(IMG, exist_ok=True)
rd = lambda p, **k: pd.read_csv(res(p), **k)
ROYAL, PINK, GOOD, RISK, GREY, INK, INK2, LINE = '#254aa5', '#d63384', '#0c8034', '#c43030', '#8a8984', '#111111', '#52514e', '#e4e3de'
plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.edgecolor': '#cfcfca',
                     'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2, 'axes.grid': True, 'grid.color': '#eeeeea',
                     'font.family': 'sans-serif', 'axes.titleweight': 'bold', 'axes.titlesize': 10, 'axes.titlelocation': 'left'})

FR = rd('final_rankings.csv'); BAT = rd('rankings/bat_full_rankings.csv'); BOWL = rd('rankings/bowl_full_rankings.csv')
PD_ = rd('pressure/pressure_definitions.csv'); PCH = json.load(open(res('pressure/chosen_pressure.json')))
WP = rd('models/wp_comparison.csv'); LS = rd('comp_strength/league_strength_2022_26_with_se.csv')
SK = {r: rd(f'models/skill_backtest_{r}_by_fold.csv') for r in ['bat', 'bowl']}
CAL = json.load(open(res('models/interval_calibration.json'))); SENS = rd('models/sensitivity.csv'); FAIR = rd('models/fairness.csv')
GAPS = rd('rr_fit/role_gaps.csv'); SHL = rd('rr_fit/role_shortlists.csv'); VD = rd('rr_fit/selector_verdicts.csv')
SQ = rd('rr_fit/rr_squad_2026.csv'); TEAMS = pd.read_csv(os.path.join(ROOT, 'v2_code', 'config', 'teams_2027.csv'))
VAL = {r: rd(f'value/{r}_uncapped_value_top10.csv') for r in ['bat', 'bowl']}
YB = {r: rd(f'youth/{r}_board_u23.csv') for r in ['bat', 'bowl']}
sk = {r: SK[r][SK[r].wcorr.notna()].groupby('model')[['wcorr', 'noise_ceiling_r']].mean() for r in SK}
KW = PCH['KW_runs_per_wicket']
clear = {r: int((T.head(15).p_top10 >= 0.5).sum()) for r, T in [('bat', BAT), ('bowl', BOWL)]}
gap_b = sk['bat'].loc['M5_eb_overall_plus_gap', 'wcorr'] - sk['bat'].loc['M4_eb_overall', 'wcorr']
gap_w = sk['bowl'].loc['M5_eb_overall_plus_gap', 'wcorr'] - sk['bowl'].loc['M4_eb_overall', 'wcorr']
RRT = TEAMS.set_index('team').loc['Rajasthan Royals']
META7 = json.load(open(w('comp_strength/fit_meta.json')))
XO = rd('models/xoutcome_comparison.csv', index_col=0)
xo_gain = (1 - XO.loc['hgb_separate', 'bat_runs_mse'] / XO.loc['T0_cell_means', 'bat_runs_mse']) * 100
AB = rd('models/ablation_by_fold.csv')

# ---------------- new charts ----------------
def save(fig, name):
    fig.savefig(os.path.join(IMG, name), dpi=200, bbox_inches='tight'); plt.close(fig)


# league strength
L = LS.sort_values('batters_runs_vs_IPL_per100')
fig, ax = plt.subplots(figsize=(6.2, 3.9)); y = np.arange(len(L))
ax.barh(y + 0.2, L.batters_runs_vs_IPL_per100, height=0.38, color=ROYAL, label='Batters (runs per 100 balls vs IPL)')
ax.barh(y - 0.2, L.bowlers_runs_saved_vs_IPL_per100, height=0.38, color=PINK, label='Bowlers (runs saved per 100 balls vs IPL)')
ax.set_yticks(y); ax.set_yticklabels(L.comp); ax.axvline(0, color=INK2, lw=0.8); ax.grid(axis='y', visible=False)
ax.legend(frameon=False, fontsize=7.5, loc='lower center', bbox_to_anchor=(0.45, 1.0), ncol=1); ax.set_title('')
save(fig, 'league.png')

# backtest
NM = {'M2_baseline': 'v1 weighted formula', 'M0_raw_pressure': 'Raw pressure record', 'M3_eb_pressure': 'Shrunk pressure record',
      'M5_eb_overall_plus_gap': 'Overall + pressure gap', 'M4_eb_overall': 'Overall skill (RR data)', 'M6_apm': 'Adjusted skill (all leagues)',
      'M8_bayes': 'Bayesian model'}
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9), sharey=True)
for ax, r, t in zip(axs, ['bat', 'bowl'], ['Batters', 'Bowlers']):
    g = sk[r].reindex(list(NM)); yy = np.arange(len(g))
    cols = [RISK if m == 'M2_baseline' else GOOD if m in ('M4_eb_overall', 'M6_apm', 'M8_bayes') else GREY for m in g.index]
    ax.barh(yy, g.wcorr, color=cols, height=0.6); ax.axvline(0, color=INK2, lw=0.8)
    ax.axvline(g.noise_ceiling_r.iloc[0], color=INK2, ls='--', lw=1); ax.text(g.noise_ceiling_r.iloc[0], len(g) - 0.4, ' best possible', fontsize=7, color=INK2)
    ax.set_yticks(yy); ax.set_yticklabels([NM[m] for m in g.index]); ax.set_title(t); ax.grid(axis='y', visible=False); ax.set_xlim(-0.2, 0.5)
fig.supxlabel('correlation with the NEXT season\'s pressure performance (higher = better prediction)', fontsize=8.5, color=INK2)
save(fig, 'backtest.png')

# RR gaps
G = GAPS.sort_values('gap')
fig, ax = plt.subplots(figsize=(5.0, 3.9)); y = np.arange(len(G))
ax.barh(y + 0.2, G.benchmark_top10_median, height=0.38, color='#c9c8c2', label='League benchmark (median of best 10)')
ax.barh(y - 0.2, G.rr_best_score.fillna(0), height=0.38, color=[RISK if g > 3 else ROYAL for g in G.gap], label="RR's best retained player")
for yi, (n, s) in enumerate(zip(G.rr_best, G.rr_best_score)):
    ax.text(max(s if pd.notna(s) else 0, 0) + 0.5, yi - 0.2, n if isinstance(n, str) else 'none', va='center', fontsize=7.5, color=INK2)
ax.set_yticks(y); ax.set_yticklabels(G.slot); ax.grid(axis='y', visible=False); ax.axvline(0, color=INK2, lw=0.8)
ax.legend(frameon=False, fontsize=8, loc='lower center', bbox_to_anchor=(0.5, 1.0), ncol=2); ax.tick_params(labelsize=8.5)
ax.set_xlim(min(-2, G.rr_best_score.min() - 1), 40)
save(fig, 'rr_gaps.png')

# calibration
fig, ax = plt.subplots(figsize=(3.4, 2.4))
xs = np.arange(2); ax.bar(xs - 0.18, [CAL['bat']['coverage_before'], CAL['bowl']['coverage_before']], 0.34, color=GREY, label='model as fitted')
ax.bar(xs + 0.18, [CAL['bat']['coverage_after'], CAL['bowl']['coverage_after']], 0.34, color=GOOD, label='after calibration')
ax.axhline(0.8, color=INK, ls='--', lw=1); ax.text(1.45, 0.805, 'target 80%', fontsize=7, ha='right')
ax.set_xticks(xs); ax.set_xticklabels(['Batters', 'Bowlers']); ax.set_ylim(0.5, 0.95); ax.set_ylabel('outcomes inside 80% range')
ax.legend(frameon=False, fontsize=7, loc='upper left', ncol=2); ax.grid(axis='x', visible=False); ax.set_title('Honest uncertainty')
save(fig, 'calibration.png')

# submitted lists (auction pool) with 80% ranges
fig, axs = plt.subplots(1, 2, figsize=(7.8, 3.3), gridspec_kw={'wspace': 0.95})
for ax, l, col, t in zip(axs, ['batters_rr_can_buy', 'bowlers_rr_can_buy'], [ROYAL, PINK], ['Batters', 'Bowlers']):
    d = FR[FR.list == l].iloc[::-1]; yy = np.arange(len(d))
    ax.hlines(yy, d.interval_80_lo, d.interval_80_hi, color=col, alpha=0.35, lw=5)
    ax.scatter(d.score_runs_per100_pressure_balls, yy, color=col, s=28, zorder=3, edgecolor='white', linewidth=1)
    ax.axvline(0, color=INK2, lw=0.8); ax.set_yticks(yy); ax.set_yticklabels([f'{int(a)}. {b}' for a, b in zip(d.position, d['name'])], fontsize=8)
    for yi, p_ in zip(yy, d.p_top10): ax.text(d.interval_80_hi.max() + 1.5, yi, f'{p_:.0%}', va='center', fontsize=7, color=INK2)
    ax.set_title(t); ax.grid(axis='y', visible=False); ax.set_xlim(d.interval_80_lo.min() - 2, d.interval_80_hi.max() + 9)
fig.supxlabel('Pressure Rating with 80% range (runs per 100 pressure balls vs expectation; right column = P(top 10 of the auction pool))', fontsize=7.5, color=INK2)
save(fig, 'submitted_intervals.png')

for f in ['1_leverage_by_over.png', '2_batters_top20_intervals.png', '3_bowlers_top20_intervals.png', '4_pressure_vs_normal_batters.png']:
    shutil.copy(res(f'report/charts/{f}'), os.path.join(IMG, f))

# ---------------- html helpers ----------------
f1 = lambda x: '–' if pd.isna(x) else f'{x:.1f}'
pc = lambda x: '–' if pd.isna(x) else f'{x:.0%}'
def short(s):
    s = str(s)
    return (s.replace('In auction pool (released by ', 'Released by ').replace(')', '') if s.startswith('In auction pool') else s.replace(' (not in auction)', '').replace(' (traded; not in auction)', ' (traded)').replace('In auction pool (released by ', 'Auction pool (ex-')
             .replace('Open market (not on a 2026 IPL roster)', 'Open market*').replace('Already RR (retained)', 'RR (retained)'))
def tone(s):
    s = str(s)
    return 'good' if s.startswith(('In auction', 'Open market')) else 'risk' if s.startswith('Not eligible') else 'rr' if s.startswith('Already RR') else 'muted'


def top_table(role, kind='rr_can_buy'):
    t = FR[FR.list == f'{"batters" if role == "bat" else "bowlers"}_{kind}']
    rows = ''.join(f'<tr><td class="n">{int(r.position)}</td><td style="white-space:nowrap"><b>{r.name}</b></td><td class="sm">{r.nation}</td>'
                   f'<td class="n" style="white-space:nowrap"><b>{r.score_runs_per100_pressure_balls:.1f}</b></td><td class="n sm" style="white-space:nowrap">{r.interval_80_lo:.0f} to {r.interval_80_hi:.0f}</td>'
                   f'<td class="n">{pc(r.p_top10)}</td><td class="n">{int(r.pressure_balls)}</td><td><span class="pill {tone(r.status)}">{short(r.status)}</span></td></tr>'
                   for r in t.itertuples())
    return (f'<table class="t"><thead><tr><th>#</th><th>Player</th><th>Country</th><th class="n">Rating</th><th class="n">80% range</th><th class="n">P(top 10)</th>'
            f'<th class="n">Pressure balls</th><th>Available as</th></tr></thead><tbody>{rows}</tbody></table>')


EMB = '<span class="pill muted" style="padding:0 1.2mm">E</span>'
RAB = {'Middle-overs spin': 'Mid-overs spin', 'Middle order (4-5)': 'Middle order', 'Left-handed top-6 bat': 'LH top-6', 'Finisher (6-7)': 'Finisher',
       'Powerplay pace': 'PP pace', 'Death pace': 'Death pace', 'Left-arm bowler': 'Left-arm', 'Wrist spin': 'Wrist spin'}
def av(x):
    x = str(x)
    return 'Open mkt*' if x.startswith('Open market') else x.replace('Released by ', 'ex-')
def rabb(x):
    return ', '.join(RAB.get(r.strip(), r.strip()) for r in str(x).split(',')[:3])


def pool_table(role, n=15):
    t = pd.read_csv(res(f'auction_pool/{role}_auction_pool.csv')).head(n)
    rows = ''.join(f'<tr><td class="n">{int(r.pool_rank)}</td><td style="white-space:nowrap"><b>{r.name}</b>{"<sup>†</sup>" if isinstance(r.evidence_flag, str) and r.evidence_flag else ""} '
                   f'{EMB if r.tier == "emerging" else ""} <span class="sub">{int(r.age) if pd.notna(r.age) else "–"}</span></td>'
                   f'<td class="sm" style="white-space:nowrap">{rabb(r.roles)}</td><td class="n" style="white-space:nowrap"><b>{r.rating:.1f}</b> <span class="sub">{r.low80:.0f} to {r.high80:.0f}</span></td>'
                   f'<td class="sm" style="white-space:nowrap">{av(r.available_as)}</td></tr>' for r in t.itertuples())
    return ('<table class="t sm"><thead><tr><th>#</th><th>Player · age</th><th>Role</th><th class="n">Rating (80%)</th><th>From</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def youth_avail(role, n=8):
    t = pd.read_csv(res(f'auction_pool/{role}_youth_available_u23.csv')).head(n)
    rows = ''.join(f'<tr><td class="n">{int(r.youth_rank)}</td><td><b>{r.name}</b> <span class="sub">{int(r.age)}</span></td><td>{r.label}</td>'
                   f'<td class="n">{r.proj_1:.1f} <span class="sub">{r.proj_1_lo:.0f}–{r.proj_1_hi:.0f}</span></td>'
                   f'<td class="sm" style="white-space:nowrap">{av(r.available_as)}</td></tr>' for r in t.itertuples())
    return ('<table class="t sm"><thead><tr><th>#</th><th>Player · age</th><th>Board</th><th class="n">Projection</th><th>Available as</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def open_ref(role):
    t = FR[FR.list == f'{"batters" if role == "bat" else "bowlers"}_open']
    rows = ''.join(f'<tr><td class="n">{int(r.position)}</td><td style="white-space:nowrap"><b>{r.name}</b></td><td class="n">{r.score_runs_per100_pressure_balls:.1f}</td>'
                   f'<td class="sm"><span class="pill {tone(r.status)}">{short(r.status)}</span></td></tr>' for r in t.itertuples())
    return ('<table class="t sm"><thead><tr><th>#</th><th>' + ('Batter' if role == 'bat' else 'Bowler') + '</th><th class="n">Rating</th><th>IPL 2027</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def buy_table(role):
    t = FR[FR.list == f'{"batters" if role == "bat" else "bowlers"}_rr_can_buy']
    return ''.join(f'<tr><td class="n">{int(r.position)}</td><td><b>{r.name}</b> <span class="sub">{r.nation}</span></td><td class="n">{r.score_runs_per100_pressure_balls:.1f}</td>'
                   f'<td class="n">{int(r.open_rank)}</td><td><span class="pill good">{short(r.status)}</span></td></tr>' for r in t.itertuples())


# requirements map
SEAS = list(range(2019, 2027))
def fold_row(c):
    cells = ''.join(f'<div class="c {"tr" if y <= c else "te" if y == c + 1 else "na"}">{y}</div>' for y in SEAS)
    return f'<div class="fold"><div>Fold: train ≤{c}, test {c + 1}</div>{cells}</div>'
FOLDS = ''.join(fold_row(c) for c in [2022, 2023, 2024, 2025])

REQ = [('Pressure definition', 'Learned <b>leverage index</b>: how much the next ball can swing win probability; top 25% of balls = pressure. 7 definitions compared.', '§2'),
       ('Performance measurement', f'<b>Run value</b> per ball vs the situation\'s expectation (wicket = {KW:.1f} runs); batters and bowlers on one scale; pressure vs usual shown for every player.', '§3'),
       ('Fair comparisons', 'Opposition, venue, era and league strength adjusted (1.6 M public balls); Bayesian shrinkage for small samples; eligibility ≥150 pressure balls, active 2025+.', '§3'),
       ('Evidence for the top 10', 'Ratings with 80% ranges, P(top 10), observed pressure vs normal, biggest pressure moments, scout cards for 60 players, interactive site.', '§4'),
       ('Reliability & limitations', 'Tested on 4 seasons the models never saw; clutch test; calibration; sensitivity; ablation; fairness; full rerun reproduces the lists.', '§5'),
       ('Two ordered top-10 lists', 'Players RR can back at the IPL 2027 auction (p.2) = the Unstop picks; the open ranking of all players (§4) validates the method across the full field.', 'p.2')]
req_html = ''.join(f'<tr><td><b>{a}</b></td><td>{b}</td><td class="n">{c}</td></tr>' for a, b, c in REQ)

STEPS = [('1', 'Win probability', 'every ball, both innings; era, venue, team strength'), ('2', 'Leverage', 'how much the next ball can swing the match'),
         ('3', 'Expected outcome', 'runs & wicket chance for that exact situation'), ('4', 'Run value', 'what the player added vs expectation'),
         ('5', 'Fair comparison', 'opposition, venue, league strength'), ('6', 'Bayesian rating', 'shrink small samples; calibrated 80% range')]
pipe = '<div class="pipe">' + '<div class="arrow">→</div>'.join(f'<div class="step"><div class="sn">{n}</div><b>{h}</b><div class="sub">{t}</div></div>' for n, h, t in STEPS) + '</div>'

wp_chosen = WP[WP.model.eq('logistic')].set_index('innings'); wp_b0 = WP[WP.model.eq('B0_baseline_replica')].set_index('innings')
d1 = PD_.set_index('definition').loc[PCH['chosen']]
pdef = PD_[['definition', 'capture_eff_bat', 'bat_rel_rv', 'bowl_rel_rv']].copy()
pdef_rows = ''.join(f'<tr{" class=hl" if r.definition == PCH["chosen"] else ""}><td>{r.definition.split("_", 1)[1].replace("_", " ")}</td><td class="n">{r.capture_eff_bat:.2f}</td>'
                    f'<td class="n">{r.bat_rel_rv:.2f}</td><td class="n">{r.bowl_rel_rv:.2f}</td></tr>' for r in pdef.itertuples())

sens_b = SENS[SENS.role == 'bat']; sens_w = SENS[SENS.role == 'bowl']
SVN = {'pressure definition D3_baseline_PI': 'Pressure = v1 index (x1.2 knockouts)', 'pressure definition D7_leverage_stakes': 'Pressure weighted by playoff stakes',
       'eligibility 100 pressure balls': 'Eligibility 100 pressure balls', 'eligibility 200 pressure balls': 'Eligibility 200 pressure balls',
       'rank by M6 (APM, all leagues)': 'Rank by adjusted skill only', 'rank incl. pressure-specific effect (theta + delta)': 'Add pressure-specific effect',
       'rank by raw observed pressure run value': 'Rank by raw pressure record'}
def sens_row(v):
    a = sens_b[sens_b.variant == v].top10_kept; b = sens_w[sens_w.variant == v].top10_kept
    return f'<tr><td>{SVN.get(v, v)}</td><td class="n">{int(a.iloc[0]) if len(a) else "–"}/10</td><td class="n">{int(b.iloc[0]) if len(b) else "–"}/10</td></tr>'
SV = ['pressure definition D3_baseline_PI', 'pressure definition D7_leverage_stakes', 'eligibility 100 pressure balls', 'eligibility 200 pressure balls',
      'rank by M6 (APM, all leagues)', 'rank incl. pressure-specific effect (theta + delta)', 'rank by raw observed pressure run value']
sens_html = ''.join(sens_row(v) for v in SV)

plans = []
for sl in GAPS.sort_values('gap', ascending=False).slot.head(5):
    g = SHL[SHL.slot == sl]
    tops = g[g.pick == 'top 3'].head(3); val = g[g.pick == 'value pick'].head(1)
    cells = ''.join(f'<td><b>{r["name"]}</b> <span class="sub">{r.score:.1f}</span></td>' for _, r in tops.iterrows())
    cells += '<td></td>' * (3 - len(tops))
    cells += f'<td>{val["name"].iloc[0]} <span class="sub">{val.score.iloc[0]:.1f}</span></td>' if len(val) else '<td>–</td>'
    gg = GAPS.set_index('slot').loc[sl]
    plans.append(f'<tr><td><b>{sl}</b><div class="sub">gap {gg.gap:.1f}</div></td>{cells}</tr>')
plans_html = ''.join(plans)

vd_pool = VD[VD.status.astype(str).str.startswith(('In auction', 'Open market'))].copy()
vd_pool['o'] = vd_pool.verdict.map({'Priority target': 0, 'Target': 1, 'Medical check first': 2}).fillna(3)
vd_pool = vd_pool.sort_values(['o', 'score'], ascending=[True, False])
ver_html = ''.join(f'<tr><td style="white-space:nowrap"><b>{r.name}</b></td><td><span class="pill {"good" if r.verdict.startswith("Priority") else "risk" if r.verdict.startswith("Medical") else "rr" if r.verdict == "Target" else "muted"}">{r.verdict}</span></td>'
                   f'<td class="sm">{rabb(r.slots)}</td><td class="n">{r.score:.1f}</td><td class="sm">{str(r.main_risks).replace("interval includes below-average", "wide range").replace("in the auction pool - expect competition", "competition expected").replace("2026 fitness reports", "2026 injuries")}</td></tr>' for r in vd_pool.head(6).itertuples())

def small(df, cols, heads):
    return '<table class="t sm"><thead><tr>' + ''.join(f'<th>{h}</th>' for h in heads) + '</tr></thead><tbody>' + ''.join(
        '<tr>' + ''.join(f'<td>{(f"{v:.1f}" if isinstance(v, float) else v)}</td>' for v in r) + '</tr>' for r in df[cols].itertuples(index=False)) + '</tbody></table>'

val_b = small(VAL['bat'].head(5), ['name', 'cap_status', 'score', 'pred_price_cr'], ['Batter', 'Cap', 'Rating', 'Est. price ₹cr'])
val_w = small(VAL['bowl'].head(5), ['name', 'cap_status', 'score', 'pred_price_cr'], ['Bowler', 'Cap', 'Rating', 'Est. price ₹cr'])
for v in (val_b, val_w): pass
yb = small(YB['bat'].head(5), ['name', 'age', 'label', 'proj_1', 'status_2027'], ['Batter', 'Age', 'Board', 'Proj.', 'Status'])
yw = small(YB['bowl'].head(5), ['name', 'age', 'label', 'proj_1', 'status_2027'], ['Bowler', 'Age', 'Board', 'Proj.', 'Status'])
clean = lambda h: h.replace('uncapped (no international)', 'uncapped').replace('uncapped (Indian, last international > 5 years ago)', 'uncapped (5-yr rule)').replace(
    'Open market (not on a 2026 IPL roster)', 'pool (open market)').replace('In auction pool (released by ', 'pool (ex-').replace(' (not in auction)', '').replace('Already RR (retained)', 'RR')
val_b, val_w, yb, yw = map(clean, (val_b, val_w, yb, yw))

n_os = int(SQ.overseas.sum())
pool_teams = TEAMS.sort_values('purse_cr', ascending=False)
purse_html = ''.join(f'<tr{" class=hl" if t.team == "Rajasthan Royals" else ""}><td>{t.team}</td><td class="n">{t.purse_cr:.2f}</td><td class="n">{int(t.slots_left)}</td><td class="n">{int(t.overseas_slots_left)}</td></tr>' for t in pool_teams.itertuples())
CSS = """
@page { size: A4; margin: 13mm 13mm 14mm 13mm; }
* { box-sizing: border-box; }
body { font-family: Inter, 'Helvetica Neue', Arial, sans-serif; color: #111; font-size: 9.6pt; line-height: 1.42; margin: 0; }
h1 { font-size: 23pt; margin: 2mm 0 1mm; letter-spacing: -0.3px; } h2 { font-size: 14pt; margin: 0 0 2mm; color: #111; }
h3 { font-size: 10.5pt; margin: 3mm 0 1.5mm; } p { margin: 1mm 0 2mm; }
.kick { color: #d63384; font-weight: 700; font-size: 7.5pt; letter-spacing: 1.5px; text-transform: uppercase; }
.page { page-break-after: always; } .page.join { page-break-after: auto; margin-bottom: 6mm; } .page:last-child { page-break-after: auto; }
.sub { color: #52514e; font-size: 7.3pt; font-weight: 400; } .sm { font-size: 7.6pt; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; } .grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 3mm; }
.card { border: 1px solid #e4e3de; border-radius: 3mm; padding: 3mm 3.5mm; background: #fff; }
.hero { background: #f4f6fb; border-left: 4px solid #d63384; border-radius: 4mm; padding: 4mm 6mm; margin-bottom: 3mm; } .hero h1 { font-size: 19pt; }
.big { font-size: 20pt; font-weight: 800; color: #254aa5; line-height: 1; } .bigp { color: #d63384; }
.t { width: 100%; border-collapse: collapse; font-size: 8.2pt; } .t th { text-align: left; font-size: 7pt; text-transform: uppercase; color: #52514e; border-bottom: 1.5px solid #cfcfca; padding: 1.2mm 1.5mm; }
.t td { border-bottom: 1px solid #ecebe7; padding: 0.9mm 1.4mm; vertical-align: top; } .t .n, .n { text-align: right; font-variant-numeric: tabular-nums; }
.t tr.hl td { background: #fdf0f6; font-weight: 600; } .t.sm { font-size: 7.4pt; }
.pill { display: inline-block; border-radius: 9px; padding: 0.3mm 2mm; font-size: 6.8pt; border: 1px solid #ddd; white-space: nowrap; }
.pill.good { color: #0c8034; border-color: #9fd3ae; background: #effaf2; } .pill.risk { color: #c43030; border-color: #eab0b0; background: #fdf2f2; }
.pill.rr { color: #254aa5; border-color: #aabce8; background: #eef2fb; } .pill.muted { color: #6b6a66; }
img { width: 100%; display: block; } .note { font-size: 7.6pt; color: #52514e; }
.find { border-left: 3px solid #d63384; padding-left: 3mm; margin-bottom: 2.5mm; } .find b { display: block; font-size: 9.6pt; }
.pipe { display: flex; align-items: stretch; gap: 1.2mm; margin: 2mm 0 3mm; } .step { flex: 1; border: 1px solid #e4e3de; border-radius: 2.5mm; padding: 2mm; background: #fafaf8; font-size: 8pt; }
.sn { width: 5.5mm; height: 5.5mm; border-radius: 50%; background: #254aa5; color: #fff; font-weight: 700; font-size: 7.5pt; text-align: center; line-height: 5.5mm; margin-bottom: 1mm; }
.arrow { align-self: center; color: #d63384; font-weight: 800; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3mm; margin: 3mm 0; } .kpi { border: 1px solid #e4e3de; border-radius: 3mm; padding: 2.5mm 3mm; }
.kpi .v { font-size: 15pt; font-weight: 800; white-space: nowrap; } .kpis.tight .v { font-size: 12.5pt; } .kpi .l { font-size: 7.2pt; color: #52514e; }
.foot { font-size: 7pt; color: #8a8984; margin-top: 2mm; }
.formula { font-family: 'Cambria Math', 'STIX Two Math', Georgia, serif; font-size: 10pt; background: #f6f7fb; border-radius: 2mm; padding: 1.6mm 3mm; margin: 1mm 0 2mm; }
.fold { display: grid; grid-template-columns: 34mm repeat(8, 1fr); gap: 0.8mm; font-size: 7pt; align-items: center; margin: 0.6mm 0; }
.fold div.c { height: 5mm; border-radius: 1mm; text-align: center; line-height: 5mm; color: #fff; }
.tr { background: #254aa5; } .te { background: #d63384; } .na { background: #ecebe7; color: #8a8984 !important; }
.scope li { margin-bottom: 1mm; }

"""
M = sk
AUTHOR = dict(name='Tanay Patil', email='patiltanay569@gmail.com', github='github.com/tanaygit0530')
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>SupeRR Selector S2 – Final Report</title><style>{CSS}</style></head><body>

<section class="page">
  <div class="hero"><div class="kick">SupeRR Selector Season 2 · Round 1 · Rajasthan Royals × Unstop</div>
    <h1>Who should RR back under pressure at the IPL 2027 auction?</h1>
    <p style="font-size:9.8pt;max-width:178mm"><b>Pressure ball</b> = the next delivery can swing the match most (top 25% of balls by expected change in win probability).
    <b>Pressure Rating</b> = runs a player is expected to add per 100 pressure balls next season vs what the situation predicts (wicket = {KW:.1f} runs; 0 = average), from a Bayesian model tested on unseen seasons.
    <b>Only players RR can buy are listed</b>: released on 17 Nov 2026 or not on any IPL roster – none retained by another team, none already at RR.</p></div>
  <h3 style="margin-top:1mm">Top 10 batters RR should back at the 2027 auction</h3>{top_table('bat')}
  <h3>Top 10 bowlers RR should back at the 2027 auction</h3>{top_table('bowl')}
  <p class="note">Eligibility as for all ratings: ≥150 pressure balls in the RR data and active in 2025 or later. P(top 10) = chance of being a genuine top-10 player <i>within the auction pool</i> after uncertainty – the top two or three in each list are the clearest; the rest are near-ties, so role, price and fitness should decide (§6–8).
  * Open-market players were not on a 2026 IPL roster and must register for the auction. The best performers overall – mostly retained by their teams – are shown in §4.</p>
</section>

<section class="page">
  <div class="kick">1 · The brief and our answer</div><h2>What the problem statement asks – and where we answer it</h2>
  <table class="t"><thead><tr><th style="width:30mm">Required</th><th>Our solution</th><th class="n">Where</th></tr></thead><tbody>{req_html}</tbody></table>
  <h3 style="margin-top:4mm">Three findings that shaped the answer</h3>
  <div class="grid3" style="margin-top:1mm">
    <div class="find"><b>"Clutch" does not repeat</b>A player's pressure-minus-usual gap made next-season predictions worse (batters {gap_b:+.3f}, bowlers {gap_w:+.3f} correlation).</div>
    <div class="find"><b>Fair overall skill predicts pressure play</b>r = {M['bat'].loc['M4_eb_overall','wcorr']:.2f} / {M['bowl'].loc['M6_apm','wcorr']:.2f} vs a best-possible {M['bat'].noise_ceiling_r.iloc[0]:.2f} / {M['bowl'].noise_ceiling_r.iloc[0]:.2f}.</div>
    <div class="find"><b>The obvious formula fails</b>A hand-weighted pressure score (our v1) had no out-of-sample signal: r = {M['bat'].loc['M2_baseline','wcorr']:+.2f} / {M['bowl'].loc['M2_baseline','wcorr']:+.2f}.</div>
  </div>
  <h3 style="margin-top:3mm">From ball to rating: the pipeline</h3>{pipe}
  <div class="kpis">
    <div class="kpi"><div class="v">1.67 M</div><div class="l">deliveries modelled (RR pack + 15 public T20 competitions, 2019–26)</div></div>
    <div class="kpi"><div class="v">{len(BAT)} / {len(BOWL)}</div><div class="l">eligible batters / bowlers (≥150 pressure balls, active 2025+)</div></div>
    <div class="kpi"><div class="v">4</div><div class="l">season-ahead test folds (2023–26): every model scored on unseen seasons</div></div>
    <div class="kpi"><div class="v">9</div><div class="l">player-skill models compared, incl. the v1 formula</div></div>
  </div>
  <div class="grid2">
    <div class="card"><h3 style="margin-top:0">Data & rules we followed</h3><p class="sm">RR pack (IPL + T20I + A-team 2022–26) for ratings; Cricsheet (ODC-By) public T20 data only as a prior and for league strength; 99.07% of RR balls linked to public IDs by ball alignment.
      No leakage: every predictive model is trained on earlier seasons and scored on the next. Reputation and news never change a rating – scout notes only flag risks.</p></div>
    <div class="card"><h3 style="margin-top:0">What else we built</h3><p class="sm">Player profiles for 6,748 players (all splits, reconciled to the ball data), 60 scout cards, value & uncapped lists with a price model, a youth board with a backtested development model,
      an RR squad-gap analysis after retentions, and a private interactive website for evaluators. One command (<code>run_all.sh</code>) reproduces everything.</p></div>
  </div>
</section>

<section class="page join">
  <div class="kick">2 · Pressure definition</div><h2>Pressure = balls where the next delivery can swing the match</h2>
  <img src="img/1_leverage_by_over.png" style="width:88%;margin:1mm auto 3mm">
  <div class="grid2">
    <div><p>For every ball we estimate the batting side's <b>win probability</b> (logistic model with run rate, wickets, balls, target, era par, venue and team Elo). <b>Leverage</b> = the expected change in that probability from the next ball, averaged over its possible outcomes (0,1,2,3,4,6,wicket). The top 25% of balls are pressure balls.</p></div>
      <div><p>The chart shows the shape cricket people expect: a chase tightens towards the end (3.5× an average ball in the 20th over), the death overs of the first innings matter, and middle overs are calm. Knockouts and close finishes are captured automatically.</p></div>
  </div>
  <h3>We compared seven definitions (rule fixed in advance: keep leverage unless another is better on both tests)</h3>
  <div class="grid2" style="grid-template-columns:1fr 1fr">
    <table class="t sm"><thead><tr><th>Definition</th><th class="n">Capture×</th><th class="n">Reliab. bat</th><th class="n">Reliab. bowl</th></tr></thead><tbody>{pdef_rows}</tbody></table>
    <div class="card sm"><b>Capture×</b> = share of all win-probability movement that falls on the flagged balls, relative to random (1.0). Leverage captures {d1.capture_eff_bat:.1f}× – twice as much swing per ball as chance.
      <br><br><b>Reliability</b> = how well a player's performance on those balls in one half of his matches matches the other half. Required-rate gap (chases only), wicket stress and the close-game window capture far less of the match swing. The baseline's knockout-weighted index and a playoff-stakes version are near-identical and serve as sensitivity checks.</div>
  </div>
</section>

<section class="page">
  <div class="kick">3 · Performance measurement & fair comparisons</div><h2>Run value: what a player adds beyond what the situation predicts</h2>
  <div class="card" style="margin-bottom:3mm"><b>Per ball:</b> runs scored − expected runs for that exact situation − {KW:.1f} × (dismissal − expected dismissal chance). Bowlers: the mirror image (runs saved + wickets).
    Expected values come from a gradient-boosting model of the situation only (innings, over, wickets, target, required rate, era, venue, team strength – <i>no player information</i>), so openers are not flattered by the powerplay and finishers are not punished for facing yorkers.
    The <b>usual vs pressure</b> comparison the brief asks for is computed for every player (§4).</div>
  <h3>How strong is each league? (IPL = 0; further left = weaker)</h3><img src="img/league.png" style="width:94%;margin:0 auto 3mm">
  <div><h3 style="margin-top:0">Fair across leagues, venues, opponents and eras</h3><div class="grid3">
      <p class="sm">A ridge model of 1.6 M deliveries separates <b>player skill</b> from <b>league</b>, <b>venue</b> and <b>opponent</b> effects, using players who appear in several competitions (match-bootstrap SEs ≈ 0.4–1.2 runs per 100 balls). Full-member T20Is sit close to the IPL; associate T20Is are about {abs(LS.set_index('comp').loc['T20I-Assoc','batters_runs_vs_IPL_per100']):.0f} runs per 100 balls weaker for batters.</p>
      <p class="sm"><b>Small samples:</b> a hierarchical Bayesian model shrinks thin records toward the average; eligibility needs ≥150 pressure balls and an appearance in 2025 or later. <b>Era:</b> IPL par rose from about 162 to 186 since the Impact Player rule; the par term absorbs it.</p>
      <p class="sm"><b>Win-probability model:</b> logistic regression beat tree models on unseen seasons (log-loss {wp_chosen.loc[1,'logloss']:.3f}/{wp_chosen.loc[2,'logloss']:.3f} vs the v1 replica {wp_b0.loc[1,'logloss']:.3f}/{wp_b0.loc[2,'logloss']:.3f}); simpler was better, so it was kept.</p></div></div>
</section>


<section class="page">
  <div class="kick">3b · Models and training logic</div><h2>How the models work – and how we trained them</h2>
  <div class="grid2" style="gap:5mm">
    <div>
      <b>1 · Win probability</b> (batting side, every ball, both innings)
      <div class="formula">WP(s) = σ( β · x(s) ),&nbsp; x = runs needed, balls left, wickets in hand, run rates, era par, venue, team Elo</div>
      <b>2 · Leverage = pressure</b>
      <div class="formula">LI(s) = Σ<sub>k</sub> p<sub>k</sub>(s) · | WP(s after outcome k) − WP(s) |,&nbsp; k ∈ &#123;0,1,2,3,4,6,W&#125;</div>
      <p class="sm">p<sub>k</sub> = chance of each outcome in that exact state (learned outcome model). Top 25% of LI = pressure ball.</p>
    </div>
    <div>
      <b>3 · Run value per ball</b>
      <div class="formula">RV = (runs − E[runs | s]) − {KW:.1f} × (out − P(out | s))</div>
      <b>4 · Player rating (hierarchical Bayes)</b>
      <div class="formula">θ<sub>i</sub> ~ N(a + b·prior<sub>i</sub>, σ<sub>θ</sub>),&nbsp; ȳ<sub>i</sub> ~ N(θ<sub>i</sub> + δ<sub>i</sub>, σ/√n<sub>i</sub>)</div>
      <p class="sm">θ = player's true skill per ball; δ = pressure-specific effect (estimated, but not used to rank – it did not repeat); n = balls. Small samples are pulled towards the average automatically.</p>
    </div>
  </div>
  <h3>The four models, how they were trained and why we kept them</h3>
  <table class="t sm"><thead><tr><th style="width:26mm">Model</th><th>Predicts</th><th>Trained on</th><th>Validation</th><th>Chosen because</th></tr></thead><tbody>
    <tr><td><b>Win probability</b><div class="sub">logistic regression</div></td><td>Batting side wins the match</td><td>All T20s 2019–26 (RR pack + Cricsheet), separate models per innings</td>
        <td>Log-loss / Brier / AUC on the next season (4 folds); 5 families compared</td><td>Best on unseen seasons ({wp_chosen.loc[1,'logloss']:.3f}/{wp_chosen.loc[2,'logloss']:.3f}); tree models over-fit match-level features</td></tr>
    <tr><td><b>Expected outcomes</b><div class="sub">gradient boosting (HGB) + 7-class model</div></td><td>Expected runs, dismissal chance, outcome mix for leverage</td><td>Situation only – no player information</td>
        <td>MSE / log-loss on the next season vs simple cell averages</td><td>{xo_gain:.1f}% better on runs than averages; simpler where no gain</td></tr>
    <tr><td><b>League & venue strength</b><div class="sub">sparse ridge regression</div></td><td>Player, league, venue, opponent effects per ball</td><td>1.6 M deliveries, players who appear in several leagues link the leagues</td>
        <td>Penalty chosen on the 2026 hold-out (runs λ={META7['lam']['runs_bat']:.0f}, wickets λ={META7['lam']['striker_out']:.0f}); 60 match bootstraps for SEs</td><td>Replaces hand-set opposition tiers with measured strength</td></tr>
    <tr><td><b>Player rating</b><div class="sub">Bayesian (NumPyro, NUTS)</div></td><td>Run value per pressure ball next season, with 80% range</td><td>RR-pack balls 2022–26; bowlers get a prior from public leagues only</td>
        <td>Correlation with next-season pressure performance vs 8 alternatives; interval coverage calibrated (×{CAL['bat']['widen']:.2f} / ×{CAL['bowl']['widen']:.2f})</td><td>Within 1 SE of the best predictor and the only one with honest uncertainty</td></tr>
  </tbody></table>
  <h3>Training without leakage: every model is tested on a season it never saw</h3>
  {FOLDS}
  <p class="note"><span style="color:#254aa5">■</span> training seasons &nbsp; <span style="color:#d63384">■</span> test season. Ratings used as features for season c+1 are rebuilt from models trained only on seasons ≤ c. The final ratings are refitted on all seasons.</p>
  <div class="grid3" style="margin-top:2mm">
    <div class="card sm"><b>What we dropped (and why)</b><br>Hand-set weights (no signal), pressure-specific "clutch" term (hurt prediction), age curve (no gain), tree WP models (over-fit). Rule: keep the simpler model unless the complex one wins on unseen seasons.</div>
    <div class="card sm"><b>Fixes found by testing</b><br>Run rate shrunk towards par early in an innings (removed a first-ball swing); a prior that reused the same balls was replaced (intervals had been 3× too narrow); merged venues split by city.</div>
    <div class="card sm"><b>Reproducibility</b><br>Fixed seeds, pinned environment, one command per stage; a clean rerun from raw data reproduces every list except one 0.01-point near-tie.</div>
  </div>
</section>
<section class="page">
  <div class="kick">4 · Evidence for the top 10</div><h2>Ratings with honest uncertainty</h2>
  <img src="img/submitted_intervals.png" style="width:96%;margin:0 auto">
  <h3>The best performers overall (open ranking) – and why they are not on our list</h3>
  <div class="grid2">{open_ref('bat')}{open_ref('bowl')}</div>
  <div class="grid2" style="grid-template-columns:1fr 1.1fr;margin-top:3mm">
    <div><img src="img/4_pressure_vs_normal_batters.png"></div>
    <div><h3 style="margin-top:0">Pressure vs usual performance</h3>
      <p class="sm">Each dot is an eligible batter: observed run value on pressure balls (y) vs normal balls (x). Players above the line did better under pressure. Because that gap did <b>not</b> repeat from one season to the next, the rating relies on skill measured on all balls and shrinks the gap away – the gap is still shown for every player.</p>
      <p class="sm"><b>Behind each name</b>: pressure strike rate / economy, phase splits, matchups, the three matches where he added most win probability (e.g. Bumrah 4-0-20-0 v RCB, +48% win probability), and sourced risk notes – in the 60 scout cards and on the website.</p>
      <p class="sm"><b>Why the open ranking matters:</b> it validates the method on the whole field (its #1, Sooryavanshi, is already RR's – re-derived from the raw ball file: 295 pressure balls, SR ≈ 229). Of the open top 10s, 9 batters and 5 bowlers were retained by other teams, so the auction lists on p.2 are a different, less certain set.</p></div>
  </div>
</section>

<section class="page">
  <div class="kick">5 · Reliability and limitations</div><h2>Tested on seasons the models never saw</h2>
  <img src="img/backtest.png" style="width:92%;margin:0 auto">
  <div class="grid3" style="grid-template-columns:1fr 1.1fr 1fr;margin-top:3mm">
    <div><img src="img/calibration.png"></div>
    <div><h3 style="margin-top:0">Consistency checks</h3><table class="t sm"><thead><tr><th>Variant</th><th class="n">Bat top 10 kept</th><th class="n">Bowl</th></tr></thead><tbody>{sens_html}</tbody></table>
      <p class="note">Ranking by the raw pressure record changes the list most – that is the noise our model removes.</p></div>
    <div class="card sm"><b>Ablation</b>: age curve and the pressure-specific term were dropped (no out-of-sample gain); public-league prior kept for bowlers only.<br><br>
      <b>Fairness</b>: errors for IPL-heavy, T20I-heavy and public-data-heavy players all within ~1 SE of zero.<br><br>
      <b>Reproducible</b>: a clean rerun from raw data reproduces every list; one #10 near-tie (0.01 apart) can swap through sampler noise.</div>
  </div>
  <h3>Limitations</h3>
  <p class="sm">One season of pressure balls is mostly noise, so ranks inside the top 10 are close; fielding, pitch and weather are not in the data; batting hand / bowling type only exist for RR-pack balls; first-innings early overs carry above-average leverage under our WP model (ratings use all balls, so the top 10 is unaffected); auction prices are hard to predict; scout notes are opinion and never change a rating.</p>
</section>

<section class="page">
  <div class="kick">6 · For Rajasthan Royals: after the 17 Nov 2026 retentions</div><h2>Where RR is exposed – and who it can actually buy</h2>
  <h3 style="margin-top:0">RR's best retained player per role vs league benchmark (red = big gap)</h3><img src="img/rr_gaps.png" style="width:74%;margin:0 auto 3mm">
  <div class="grid2" style="grid-template-columns:1fr 1fr">
    <div><div class="kpis tight" style="grid-template-columns:1.4fr 1fr 1fr;margin-top:0">
      <div class="kpi"><div class="v">₹{RRT.purse_cr:.2f} cr</div><div class="l">purse left</div></div><div class="kpi"><div class="v">{int(RRT.slots_left)}</div><div class="l">slots</div></div><div class="kpi"><div class="v">{int(RRT.overseas_slots_left)}</div><div class="l">overseas slots</div></div></div>
      <p class="sm">RR kept {len(SQ)} players incl. Mohammed Shami and M Siddharth (traded in); Hetmyer, Deshpande, Milne, Maphaka and five others were released and Sam Curran went to LSG. The <b>middle order (4–5)</b> is now the biggest gap, then <b>middle-overs spin</b>; opening is RR's strength (Sooryavanshi).</p></div>
      <div><table class="t sm"><thead><tr><th>Team</th><th class="n">Purse ₹cr</th><th class="n">Slots</th><th class="n">OS</th></tr></thead><tbody>{purse_html}</tbody></table></div>
  </div>
  <h3>Auction plan for the biggest gaps (only players in the auction pool)</h3>
  <table class="t"><thead><tr><th>Role</th><th>Plan A</th><th>Plan B</th><th>Plan C</th><th>Value pick (≤ ₹3 cr)</th></tr></thead><tbody>{plans_html}</tbody></table>
</section>

<section class="page">
  <div class="kick">7 · The IPL 2027 auction pool</div><h2>Best players NOT retained by any team</h2>
  <p class="sm">Every rated player who was released on 17 Nov 2026 or is not on any IPL roster – the only players RR can buy. Full lists ({len(pd.read_csv(res('auction_pool/bat_auction_pool.csv')))} batters, {len(pd.read_csv(res('auction_pool/bowl_auction_pool.csv')))} bowlers) in <code>IPL2027_Auction_Pool_Lists.xlsx</code>.
  <b>*</b> open-market players must register for the auction. <b>ex-XXX</b> = released by that team. <b>†</b> record mostly in associate T20Is (weaker opposition) – treat with caution. <b>E</b> = emerging (40–149 pressure balls, wider range).</p>
  <div><h3 style="margin-top:1mm">Batters in the auction pool (top 15)</h3>{pool_table('bat')}</div>
  <div><h3 style="margin-top:2mm">Bowlers in the auction pool (top 15)</h3>{pool_table('bowl')}</div>
</section>

<section class="page">
  <div class="kick">8 · Beyond the top 10</div><h2>Selector verdicts and available youngsters</h2>
  <h3 style="margin-top:1mm">Selector verdicts for the leading auction-pool names</h3>
  <table class="t sm"><thead><tr><th>Player</th><th>Verdict</th><th>Fills</th><th class="n">Rating</th><th>Main risks</th></tr></thead><tbody>{ver_html}</tbody></table>
  <h3 style="margin-top:4mm">Youngsters in the auction pool (aged 23 or under on 1 Apr 2027)</h3>
  <div class="grid2"><div><div class="sub" style="margin-bottom:1mm;font-weight:700">Batters</div>{youth_avail('bat')}</div>
    <div><div class="sub" style="margin-bottom:1mm;font-weight:700">Bowlers</div>{youth_avail('bowl')}</div></div>
  <p class="note">Projection = adjusted skill per 100 balls in all situations (a different scale from the Pressure Rating), next season with 80% range, from a development model backtested on players aged ≤23 in 2021. Small samples: treat as a watch list, not a ranking. Full lists incl. ages 24–26 in the workbook. Minors: cricket data and age only.</p>
</section>

<section class="page">
  <div class="kick">9 · Delivery and future scope</div><h2>Value buys, what we delivered – and where it goes next</h2>
  <h3 style="margin-top:1mm">Value buys in the auction pool (uncapped, or estimated ≤ ₹3 cr)</h3>
  <div class="grid2">{val_b}{val_w}</div>
  <h3>What we delivered</h3>
  <div class="grid3">
    <div class="card sm"><b>Interactive evaluator site</b><br>Private, password-protected and encrypted: rankings with filters, a profile page for 394 players, compare, method explainer, RR strategy and this report.</div>
    <div class="card sm"><b>Reproducible pipeline</b><br>30 stage scripts, one command (<code>run_all.sh</code>), fixed seeds, pinned environment; a clean rerun from raw data reproduces every list (one 0.01 near-tie can swap).</div>
    <div class="card sm"><b>Decision support for the auction</b><br>Scout cards for 60 players, value and youth boards, squad-gap analysis and plan A/B/C per role – refreshed after the 17 Nov retentions; config files make the next refresh a rerun, not a rewrite.</div>
  </div>
  <h3>Future scope: from analysis to a live auction tool</h3>
  <div class="grid2"><ul class="scope sm" style="margin:0;padding-left:5mm">
      <li><b>RR Pressure Scout app</b> – upload any new data pack (CSV, Excel, JSON, Cricsheet); columns are mapped automatically, validated and de-duplicated; player identities checked, never merged silently.</li>
      <li><b>Refresh or retrain on new data</b> – the app decides and explains; a retrained model replaces the current one only if it is at least as good on unseen seasons; drift checks and a model registry.</li>
      <li><b>Auction optimiser</b> – picks the best set of targets within purse, slot and overseas limits, with max bids, plan A/B/C per role, youth-investment and risk sliders, and instant what-ifs.</li></ul>
    <ul class="scope sm" style="margin:0;padding-left:5mm">
      <li><b>Live auction mode</b> – enter each lot; purses and slots of all 10 teams update, RR's targets and max bids re-optimise, alerts when a last option in a role goes.</li>
      <li><b>Better price model</b> – train on the official auction register (base price, set) and show price ranges backtested on past auctions.</li>
      <li><b>Richer data</b> – fielding, ball-tracking and pitch data would sharpen ratings; U19 and state-league scorecards would firm up the youth board.</li></ul></div>
  <div class="grid2" style="margin-top:5mm">
    <div class="card" style="background:#f6f7fb"><h3 style="margin-top:0">Reproduce every number</h3><p class="sm">Install the pinned environment (<code>requirements.txt</code>), place the RR data pack in <code>02_data/</code>, run <code>bash v2_code/run_all.sh</code>. Each stage is one command; the README maps every table and chart in this report to the script and output file that produced it. The data pack is never uploaded or committed.</p></div>
    <div class="card" style="background:#13235a;color:#fff;border:0"><h3 style="margin-top:0;color:#fff">Contact</h3><p style="margin:0;font-size:10pt;line-height:1.7"><b>{AUTHOR['name']}</b><br>{AUTHOR['email']}<br>{AUTHOR['github']}</p><p class="sm" style="color:#d6dbf3;margin-top:2mm">Happy to walk the selection panel through the model, the website or any player in detail.</p></div></div>
  <p class="foot">Sources: RR/Unstop data pack (aggregates only); Cricsheet (ODC-By); Wikipedia (CC BY-SA) auction prices; Wikidata (CC0) ages; IPL 2027 retentions – Willow Sports via Yahoo Sports and rajasthanroyals.com (17 Nov 2026), RVCJ graphic. Full method, code and every table: v2_results/ and the evaluator website.</p>
</section>
</body></html>"""
# ---------------- professional print layout: cover, running header/footer, full A4 pages ----------------
PRINT_CSS = """
@page { size: A4; margin: 0; }
html, body { margin: 0; padding: 0; }
body { font-family: 'Avenir Next', 'Avenir', 'Helvetica Neue', Arial, sans-serif; font-size: 10.2pt; line-height: 1.45; color: #14161c; }
section.page { width: 210mm; height: 297mm; padding: 11mm 15mm 9mm; display: flex; flex-direction: column; overflow: hidden;
               page-break-after: always; break-after: page; margin: 0 !important; }
section.page:last-child { page-break-after: auto; }
.hdr { display: flex; justify-content: space-between; align-items: center; font-size: 7.6pt; color: #6b6a66; letter-spacing: .3px;
       border-bottom: 1.5px solid #254aa5; padding-bottom: 1.8mm; margin-bottom: 4mm; }
.hdr b { color: #254aa5; letter-spacing: .6px; }
.ftr { display: flex; justify-content: space-between; font-size: 7.4pt; color: #6b6a66; border-top: 1px solid #e4e3de; padding-top: 1.8mm; margin-top: 3mm; }
.body { flex: 1; display: flex; flex-direction: column; justify-content: flex-start; min-height: 0; }
.body > h2 { margin-bottom: 3mm; } .body > .grid2, .body > .grid3, .body > table, .body > img { margin-bottom: 2mm; }
h1 { font-size: 24pt; font-weight: 700; } h2 { font-size: 16pt; font-weight: 700; letter-spacing: -.2px; } h3 { font-size: 11.5pt; font-weight: 600; }
.kick { font-size: 8pt; } .t { font-size: 8.9pt; } .t.sm { font-size: 8.2pt; } .sm { font-size: 8.6pt; } .note { font-size: 8.2pt; } .sub { font-size: 7.8pt; }
.t th { font-size: 7.4pt; } .card { padding: 3.5mm 4mm; } .pill { font-size: 7.4pt; }
.formula { font-size: 10.5pt; }
/* cover */
.cover { padding: 0 !important; color: #14161c; background: #fff; }
.cover .in { flex: 1; display: flex; flex-direction: column; justify-content: space-between; padding: 26mm 20mm 0 24mm; border-left: 5mm solid #d63384; }
.cover .tag { font-size: 9pt; letter-spacing: 2.5px; text-transform: uppercase; color: #d63384; font-weight: 600; }
.cover h1 { font-size: 32pt; line-height: 1.12; margin: 6mm 0 5mm; color: #13235a; letter-spacing: -.4px; }
.cover .rule { width: 30mm; height: 1.2mm; background: #d63384; margin: 0 0 6mm; }
.cover .lead { font-size: 12.5pt; max-width: 150mm; color: #52514e; }
.cover .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 4mm; margin-top: 12mm; }
.cover .stat { border-top: 1.2mm solid #254aa5; padding: 3mm 0 0; }
.cover .stat .v { font-size: 20pt; font-weight: 700; color: #13235a; } .cover .stat .l { font-size: 8.4pt; color: #52514e; }
.cover .toc { columns: 2; font-size: 9.8pt; color: #14161c; margin-top: 12mm; border-top: 1px solid #e4e3de; padding-top: 5mm; } .cover .toc div { margin-bottom: 1.8mm; }
.cover .author { display: flex; justify-content: space-between; align-items: flex-end; background: #13235a; color: #fff; margin: 0 -20mm 0 -24mm; padding: 9mm 20mm 10mm 24mm; }
.cover .author .nm { font-size: 16pt; font-weight: 700; } .cover .author .c { font-size: 9.5pt; color: #d6dbf3; line-height: 1.6; }
"""
TOC = ['The answer: players RR should back', 'The brief and our solution', 'Defining pressure', 'Measuring performance fairly',
       'Models and training logic', 'Evidence for the top 10', 'Reliability and limitations', 'RR after the retentions',
       'The IPL 2027 auction pool', 'Selector verdicts and youngsters', 'Value buys and future scope']
COVER = f"""<section class="page cover"><div class="in">
  <div><div class="tag">SupeRR Selector Season 2 · Round 1 · Rajasthan Royals × Unstop</div>
    <h1>The most reliable players<br>under pressure – and whom<br>RR should back at the<br>IPL 2027 auction</h1><div class="rule"></div>
    <div class="lead">A data-driven pressure rating for batters and bowlers, validated on seasons the models never saw, and turned into an auction shortlist after the 17 November 2026 retentions.</div>
    <div class="stats">
      <div class="stat"><div class="v">1.67 M</div><div class="l">deliveries modelled</div></div>
      <div class="stat"><div class="v">{len(BAT) + len(BOWL)}</div><div class="l">players rated (≥150 pressure balls)</div></div>
      <div class="stat"><div class="v">4</div><div class="l">unseen test seasons</div></div>
      <div class="stat"><div class="v">20</div><div class="l">auction picks (10 bat, 10 bowl)</div></div></div>
    <div class="toc">{''.join(f'<div>{i:02d} · {t}</div>' for i, t in enumerate(TOC, 1))}</div></div>
  <div class="author"><div><div style="font-size:8pt;letter-spacing:2px;text-transform:uppercase;color:#ffb8da">Prepared by</div>
      <div class="nm">{AUTHOR['name']}</div><div class="c">{AUTHOR['email']}<br>{AUTHOR['github']}</div></div>
    <div class="c" style="text-align:right">Methodology report<br>18 November 2026</div></div>
</div></section>
"""


def finalize(h):
    h = h.replace('<section class="page join">', '<section class="page">')
    h = h.replace('</style>', PRINT_CSS + '</style>', 1)
    parts = h.split('<section class="page">')
    n = len(parts) - 1
    out = [parts[0].replace('<body>', '<body>' + COVER, 1)]
    for i, part in enumerate(parts[1:], start=2):
        body, _, rest = part.partition('</section>')
        out.append(f'<section class="page"><div class="hdr"><span><b>PRESSURE SCOUT</b> · Most reliable players under pressure</span>'
                   f'<span>SupeRR Selector S2 · Round 1</span></div><div class="body">{body}</div>'
                   f'<div class="ftr"><span>{AUTHOR["name"]} · {AUTHOR["email"]}</span><span>Page {i} of {n + 1}</span></div></section>{rest}')
    return ''.join(out)


html = finalize(html)
path = os.path.join(OUT, 'SupeRR_S2_Final_Report.html')
open(path, 'w').write(html)
chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
pdf = os.path.join(OUT, 'SupeRR_S2_Final_Report.pdf')
subprocess.run([chrome, '--headless', '--disable-gpu', f'--print-to-pdf={pdf}', '--no-pdf-header-footer', '--virtual-time-budget=4000', 'file://' + path], check=True, capture_output=True)
print('written', pdf)
