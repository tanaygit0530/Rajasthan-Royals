"""S6: the six report charts (static PNG, light mode, validated palette: blue #2a78d6, orange #eb6834, aqua #1baf7a).
Outputs: v2_results/report/charts/*.png
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *
import skill as K

BLUE, ORANGE, AQUA, GRAY = '#2a78d6', '#eb6834', '#1baf7a', '#8a8984'
INK, INK2, SURF = '#0b0b0b', '#52514e', '#fcfcfb'
plt.rcParams.update({'figure.facecolor': SURF, 'axes.facecolor': SURF, 'axes.edgecolor': '#d6d5d0', 'axes.labelcolor': INK2,
                     'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK, 'font.size': 10, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#ecebe7', 'grid.linewidth': 0.8,
                     'axes.titleweight': 'bold', 'axes.titlesize': 12, 'axes.titlelocation': 'left'})
OUT = res('report/charts'); os.makedirs(OUT, exist_ok=True)

# 1. leverage by over
V = pd.read_parquet(w('values/ball_values_final.parquet'), columns=['source', 'season', 'legal', 'innings', 'seq', 'li_norm', 'match_id'])
B = pd.read_parquet(w('unified/balls.parquet'), columns=['over'])
V['over'] = B.over.values[pd.read_parquet(w('values/ball_values_final.parquet'), columns=['row']).row.values]
r = V[V.source.eq('RR') & V.legal & V.season.between(2022, 2026)]
lv = r.groupby(['innings', 'over']).li_norm.mean().unstack(0)
fig, ax = plt.subplots(figsize=(7.5, 4))
for inn, c, lab in [(1, BLUE, 'Setting a total'), (2, ORANGE, 'Chasing')]:
    ax.plot(lv.index, lv[inn], color=c, lw=2, marker='o', ms=4)
    ax.text(20.3, lv[inn].iloc[-1], lab, color=INK2, va='center')
ax.axhline(1, color=GRAY, lw=1, ls='--'); ax.text(0.6, 1.04, 'average ball = 1.0', color=INK2, fontsize=9)
ax.set_xlabel('Over'); ax.set_ylabel('Leverage index (mean)'); ax.set_xlim(0.5, 22.5); ax.set_xticks(range(1, 21))
ax.set_title('How much the next ball can swing the match, by over (RR pack, 2022-26)')
fig.tight_layout(); fig.savefig(f'{OUT}/1_leverage_by_over.png', dpi=180); plt.close(fig)

# 2-3. top-20 with intervals
for role, fn, title in [('bat', '2_batters_top20_intervals.png', 'Batters'), ('bowl', '3_bowlers_top20_intervals.png', 'Bowlers')]:
    T = pd.read_csv(res(f'rankings/{role}_full_rankings.csv')).head(20).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.5, 6.2))
    y = np.arange(len(T))
    c = np.where(T['rank'] <= 10, BLUE, GRAY)
    ax.hlines(y, T.score_lo, T.score_hi, color=c, lw=2)
    ax.scatter(T.score, y, color=c, s=40, zorder=3, edgecolor=SURF, linewidth=1.5)
    ax.set_yticks(y); ax.set_yticklabels([f'{int(a)}. {b}' for a, b in zip(T['rank'], T['name'])])
    for yi, (s, p) in enumerate(zip(T.score_hi, T.p_top10)):
        ax.text(s + 0.6, yi, f'P(top 10) {p:.0%}', va='center', fontsize=8, color=INK2)
    ax.set_xlabel('Pressure Reliability Score (runs per 100 pressure balls above expectation), 80% interval')
    ax.set_title(f'{title}: top 20 with uncertainty (top 10 in blue)'); ax.grid(axis='y', visible=False)
    fig.tight_layout(); fig.savefig(f'{OUT}/{fn}', dpi=180); plt.close(fig)

# 4. pressure vs normal (observed) - the gap does not predict next season
T = pd.read_csv(res('rankings/bat_full_rankings.csv'))
fig, ax = plt.subplots(figsize=(7, 5.2))
top = T['rank'] <= 10
ax.scatter(T.obs_normal_rv100[~top], T.obs_pressure_rv100[~top], color=GRAY, s=22, alpha=0.8, edgecolor=SURF, linewidth=1)
ax.scatter(T.obs_normal_rv100[top], T.obs_pressure_rv100[top], color=BLUE, s=36, edgecolor=SURF, linewidth=1.5, zorder=3)
for _, r_ in T[top].iterrows():
    ax.annotate(r_['name'].split()[-1], (r_.obs_normal_rv100, r_.obs_pressure_rv100), xytext=(4, 3), textcoords='offset points', fontsize=8, color=INK2)
lim = [min(T.obs_normal_rv100.min(), T.obs_pressure_rv100.min()) - 3, max(T.obs_normal_rv100.max(), T.obs_pressure_rv100.max()) + 3]
ax.plot(lim, lim, color=GRAY, ls='--', lw=1); ax.text(lim[1] - 2, lim[1] - 6, 'same in both', color=INK2, fontsize=8, ha='right')
ax.set_xlabel('Run value per 100 balls, normal situations'); ax.set_ylabel('Run value per 100 balls, pressure situations')
ax.set_title('Batters: pressure vs normal performance (eligible players)')
fig.tight_layout(); fig.savefig(f'{OUT}/4_pressure_vs_normal_batters.png', dpi=180); plt.close(fig)

# 5. WP calibration (chase), chosen vs baseline replica
cal = pd.read_csv(res('models/wp_calibration.csv'))
fig, axs = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
for ax, inn in zip(axs, [1, 2]):
    for m, c, lab in [('logistic', BLUE, 'v2 (logistic + era/venue/Elo)'), ('B0_baseline_replica', ORANGE, 'baseline replica')]:
        d = cal[(cal.innings == inn) & (cal.model == m)]
        ax.plot(d.mean_pred, d.obs, color=c, marker='o', ms=5, lw=2, label=lab)
    ax.plot([0, 1], [0, 1], color=GRAY, ls='--', lw=1)
    ax.set_title('First innings' if inn == 1 else 'Chase'); ax.set_xlabel('Predicted win probability')
axs[0].set_ylabel('Observed win rate'); axs[0].legend(frameon=False, fontsize=8, loc='upper left')
fig.suptitle('Win-probability calibration, season-ahead test folds (RR pack 2023-26)', x=0.02, ha='left', fontweight='bold')
fig.tight_layout(); fig.savefig(f'{OUT}/5_wp_calibration.png', dpi=180); plt.close(fig)

# 6. backtest: next-season prediction by model vs noise ceiling
fig, axs = plt.subplots(1, 2, figsize=(10, 4.4), sharex=True)
NM = {'M2_baseline': 'Baseline formula (M2)', 'M0_raw_pressure': 'Raw pressure record (M0)', 'M3_eb_pressure': 'Shrunk pressure record (M3)',
      'M5_eb_overall_plus_gap': 'Overall + pressure gap (M5)', 'M4_eb_overall': 'Overall skill, RR (M4)', 'M6_apm': 'Adjusted skill, all leagues (M6)',
      'M8_bayes': 'Bayes incl. pressure effect (M8)'}
for ax, role, title in zip(axs, ['bat', 'bowl'], ['Batters', 'Bowlers']):
    R = pd.read_csv(res(f'models/skill_backtest_{role}_by_fold.csv'))
    g = R[R.model.isin(NM)].groupby('model').wcorr.agg(['mean', 'std']).reindex(list(NM))
    ceil = R.noise_ceiling_r.mean()
    y = np.arange(len(g))
    cols = [ORANGE if m == 'M2_baseline' else BLUE if m in ('M4_eb_overall', 'M6_apm') else GRAY for m in g.index]
    ax.barh(y, g['mean'], color=cols, height=0.6)
    ax.errorbar(g['mean'], y, xerr=g['std'] / 2, fmt='none', ecolor=INK2, lw=1, capsize=2)
    ax.axvline(ceil, color=INK2, ls='--', lw=1); ax.text(ceil, len(g) - 0.4, f' noise ceiling {ceil:.2f}', fontsize=8, color=INK2)
    ax.axvline(0, color='#bdbcb6', lw=1)
    ax.set_yticks(y); ax.set_yticklabels([NM[m] for m in g.index] if role == 'bat' else []); ax.set_title(title); ax.grid(axis='y', visible=False)
    ax.set_xlabel('Correlation with next-season pressure run value')
fig.suptitle('Which models predict next season\'s pressure performance? (4 season-ahead folds, +-1 SE)', x=0.02, ha='left', fontweight='bold')
fig.tight_layout(); fig.savefig(f'{OUT}/6_backtest_models.png', dpi=180); plt.close(fig)
print('charts written to', OUT)
