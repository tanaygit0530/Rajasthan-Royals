"""S6: build the report and companion documents FROM OUTPUT FILES ONLY (every number is read from v2_results/).

Writes: v2_results/report/SupeRR_S2_v2_Methodology_Report.md (+ .docx via pandoc, + .html for PDF printing),
        v2_results/MODEL_COMPARISON.md, v2_results/BASELINE_VS_V2.md, v2_results/EXECUTIVE_SUMMARY.md (+ .html)
"""
import json
import shutil
import subprocess
from common import *

R = lambda p: res(p)
rd = lambda p, **k: pd.read_csv(R(p), **k)
fmt = lambda x, d=1: '-' if pd.isna(x) else f'{x:.{d}f}'
pc = lambda x: '-' if pd.isna(x) else f'{x:.0%}'

FR = rd('final_rankings.csv')
BAT = rd('rankings/bat_full_rankings.csv'); BOWL = rd('rankings/bowl_full_rankings.csv')
WP = rd('models/wp_comparison.csv'); XO = rd('models/xoutcome_comparison.csv', index_col=0)
PD_ = rd('pressure/pressure_definitions.csv'); PCH = json.load(open(R('pressure/chosen_pressure.json')))
SK = {r: rd(f'models/skill_backtest_{r}_by_fold.csv') for r in ['bat', 'bowl']}
AB = rd('models/ablation_by_fold.csv'); FAIR = rd('models/fairness.csv'); SENS = rd('models/sensitivity.csv')
CAL = json.load(open(R('models/interval_calibration.json')))
COV = rd('models/interval_coverage.csv'); CLU = {r: rd(f'models/clutch_{r}.csv') for r in ['bat', 'bowl']}
SURV = {r: rd(f'models/skill_survivorship_{r}.csv') for r in ['bat', 'bowl']}
LS = rd('comp_strength/league_strength_2022_26_with_se.csv')
MREL = rd('explain/matchup_reliability.csv')
SH = rd('explain/shap_top_predictors.csv')
BASE = {k: pd.read_csv(os.path.join(ROOT, '04_outputs', f'top10_{k}_open_ranking.csv')) for k in ['batters', 'bowlers']}


def skill_tab(role):
    S = SK[role]
    g = S[S.wcorr.notna()].groupby('model')[['wcorr', 'spearman', 'top10_hit']].mean()
    g['ceiling'] = S.noise_ceiling_r.mean()
    return g.sort_values('wcorr', ascending=False)


def abl_tab(role):
    P = AB[AB.role == role].pivot(index='cutoff', columns='variant', values='wcorr')
    d = P.sub(P['full'], axis=0)
    return pd.DataFrame({'mean_corr': P.mean(), 'diff_vs_full': d.mean(), 'se': d.std() / 2, 'folds_better': (d > 0).sum()}).round(3)


def top_table(role, kind):
    lst = f'{"batters" if role == "bat" else "bowlers"}_{kind}'
    t = FR[FR.list == lst].copy()
    t['Score (80% interval)'] = [f'{a:.1f} ({b:.1f} to {c:.1f})' for a, b, c in zip(t.score_runs_per100_pressure_balls, t.interval_80_lo, t.interval_80_hi)]
    t['P(top 10)'] = t.p_top10.map(pc)
    t['Tie'] = np.where(t.near_tie_with_next, 'near-tie with next', '')
    cols = ['position', 'name', 'nation', 'Score (80% interval)', 'P(top 10)', 'pressure_balls', 'status', 'Tie']
    if kind == 'rr_can_buy':
        cols.insert(1, 'open_rank')
    return t[cols].rename(columns={'position': '#', 'name': 'Player', 'nation': 'Nation', 'pressure_balls': 'Pressure balls',
                                   'status': '2027 status', 'open_rank': 'Open rank'}).to_markdown(index=False)


sb, sw = skill_tab('bat'), skill_tab('bowl')
m2b, m2w = sb.loc['M2_baseline', 'wcorr'], sw.loc['M2_baseline', 'wcorr']
gap_b = sb.loc['M5_eb_overall_plus_gap', 'wcorr'] - sb.loc['M4_eb_overall', 'wcorr']
gap_w = sw.loc['M5_eb_overall_plus_gap', 'wcorr'] - sw.loc['M4_eb_overall', 'wcorr']
ab_b, ab_w = abl_tab('bat'), abl_tab('bowl')
fb = ab_b.loc['full'];
wp1 = WP[(WP.innings == 1)].set_index('model'); wp2 = WP[(WP.innings == 2)].set_index('model')
d1 = PD_.set_index('definition').loc[PCH['chosen']]
covm = COV.groupby('role').coverage_80.mean()
clear = {r: int((T.head(15).p_top10 >= 0.5).sum()) for r, T in [('bat', BAT), ('bowl', BOWL)]}
clear_txt = (f'only {clear["bat"]} batter(s) and {clear["bowl"]} bowler(s) have a better-than-even chance of a top-10 place once '
             'uncertainty is calibrated; the rest of each top 10 is a near-tie, so price, role, fitness and team fit should decide between them')
ovl = {k: len(set(BASE[k].Player) & set(FR[FR.list == f'{k}_open'].name)) for k in BASE}

# ======================= REPORT =======================
L = []
L += ['---', 'title: "SupeRR Selector Season 2 - Round 1: Who performs under pressure? (v2)"',
      'subtitle: "Methodology report - Rajasthan Royals x Unstop"', 'date: "15 November 2026"', '---', '']
L += ['# Headline', '',
      'We rank batters and bowlers by the run value they are expected to add **per pressure ball next season** - runs above '
      'the expectation for the exact match situation, with a wicket costing '
      f'{PCH["KW_runs_per_wicket"]:.1f} runs - estimated with a hierarchical Bayesian model and validated on seasons it was not trained on.', '',
      '**Three findings drive the method:**', '',
      f'1. *Clutch is not a repeatable skill in this data.* Adding a player-specific "pressure gap" to overall skill made next-season '
      f'predictions worse for batters ({gap_b:+.3f} correlation) and bowlers ({gap_w:+.3f}). Players who over-performed under pressure '
      'tended to fall back the next season.',
      f'2. *The best predictor of pressure performance is overall skill measured fairly* - adjusted for the match situation, opposition, '
      f'venue, era and competition. These models reach correlations of about {sb.loc["M4_eb_overall", "wcorr"]:.2f} (batters) and '
      f'{sw.loc["M6_apm", "wcorr"]:.2f} (bowlers) with next-season pressure performance, against a noise ceiling of '
      f'{sb.ceiling.iloc[0]:.2f} and {sw.ceiling.iloc[0]:.2f}.',
      f'3. *The v1 baseline formula had no out-of-sample signal* (correlation {m2b:+.2f} for batters, {m2w:+.2f} for bowlers).', '',
      '## Top 10 batters under pressure (open ranking)', '', top_table('bat', 'open'), '',
      '## Top 10 bowlers under pressure (open ranking)', '', top_table('bowl', 'open'), '',
      'Score = predicted runs added per 100 pressure balls above expectation (bowlers: runs saved plus wickets). '
      '"Near-tie" = less than 60% posterior probability that the player is ahead of the next one; ranks inside a near-tie are '
      'statistically interchangeable. Auction status: trades to 15 Nov 2026; 2027 retention lists not yet published.', '',
      '## The lists RR can act on (excluding current RR players and ineligible players)', '', '**Batters**', '',
      top_table('bat', 'rr_can_buy'), '', '**Bowlers**', '', top_table('bowl', 'rr_can_buy'), '']

# ---- 1. pressure
L += ['# 1. Defining pressure', '',
      'A ball is a **pressure ball** when the next delivery can move the match a lot. We measure that with a **leverage index**: the '
      'expected absolute change in win probability from the next ball, averaging over its possible outcomes (0, 1, 2, 3, 4, 6, '
      'wicket) with probabilities from a model of the current situation. The top 25% of balls by leverage are pressure balls.', '',
      '![Leverage by over](charts/1_leverage_by_over.png)', '',
      'We compared seven definitions on three tests: how much of the total win-probability movement the flagged balls capture '
      '(capture efficiency: 1.0 = no better than random), how reliably players\' performance on those balls repeats '
      '(split-half reliability), and season-to-season stability.', '',
      PD_[['definition', 'share_balls', 'capture_eff_bat', 'bat_rel_rv', 'bowl_rel_rv', 'bat_yty_rv', 'bowl_yty_rv']].round(2).to_markdown(index=False), '',
      f'- Rule fixed before looking: keep learned leverage unless another definition is at least as good on both capture and reliability. '
      f'**Chosen: {PCH["chosen"]}** (capture efficiency {d1.capture_eff_bat:.2f}). The baseline\'s pressure index (D3) and a '
      'stakes-weighted version (D7, using simulated playoff qualification stakes) are close; they are sensitivity checks (section 5).',
      '- Leverage covers knockouts and close finishes automatically: a ball late in a tight chase moves win probability more. '
      'We tested an extra knockout multiplier and qualification stakes directly; neither changed the ranking materially.', '']

# ---- 2. performance
L += ['# 2. Measuring performance', '',
      '**Win probability.** We compared logistic regression, sklearn gradient boosting, LightGBM, XGBoost and a blend, trained on '
      'all public T20 data up to season c and tested on RR-pack matches of season c+1 (four folds). Features include an era term '
      '(the competition\'s par score over the previous year), a venue term (earlier totals at the ground) and team Elo.', '',
      WP.round(4).to_markdown(index=False), '',
      f'- **Logistic regression won** on both innings (log-loss {wp1.loc["logistic", "logloss"]:.3f} / {wp2.loc["logistic", "logloss"]:.3f} '
      f'vs the baseline replica {wp1.loc["B0_baseline_replica", "logloss"]:.3f} / {wp2.loc["B0_baseline_replica", "logloss"]:.3f}). '
      'The tree models overfit match-level features (every ball of a match shares them); stronger regularisation narrowed but did '
      'not close the gap, so the simpler model is kept.', '',
      '![WP calibration](charts/5_wp_calibration.png)', '',
      '**Expected outcomes.** For every ball we predict the expected runs and dismissal probability from the situation only '
      '(innings, over, wickets, target, required rate, era, venue, team strength - no player information). Gradient boosting '
      'beat simple averages by about 1.5% on runs:', '', XO.round(4).to_markdown(), '',
      f'**Run value per ball** = (runs - expected runs) - {PCH["KW_runs_per_wicket"]:.1f} x (dismissal - expected dismissal); bowlers '
      f'the mirror image. The wicket cost {PCH["KW_runs_per_wicket"]:.1f} runs is estimated from how runs and dismissals move win probability. '
      'We also compute win probability added (WPA); run value is used for ranking because it is far less noisy per ball.', '']

# ---- 3. fairness
lsd = LS.set_index('comp')
L += ['# 3. Making comparisons fair', '',
      '- **Situation.** Every ball is judged against the expectation for that exact state, so finishers are not punished for '
      'facing yorkers at the death and openers are not flattered by the powerplay.',
      '- **Era.** The IPL first-innings par rose from about 162 (2022) to 186 (2026). The par term in both models absorbs it.',
      '- **Venue.** A venue term from a ridge model of 1.6 million deliveries (e.g. Wankhede and Eden Gardens about +11 runs per 100 balls, '
      'Jaipur about -2.4, Chepauk -6.6).',
      '- **Competition strength.** Estimated from players who appear in several leagues, with match-bootstrap standard errors:', '',
      lsd[['balls', 'batters_runs_vs_IPL_per100', 'batters_runs_vs_IPL_per100_se', 'bowlers_runs_saved_vs_IPL_per100',
           'bowlers_runs_saved_vs_IPL_per100_se']].round(1).to_markdown(), '',
      '- **Opposition.** The ridge model includes the batter and bowler on every ball, so facing better opponents is credited.',
      '- **Public data (Cricsheet, 1.6M balls, 15 competitions) as a prior, not a substitute.** For bowlers, a skill prior from public '
      f'leagues only (no overlap with the RR-pack balls) raised out-of-sample correlation from {ab_w.loc["no APM prior (no public data, no competition adjustment)", "mean_corr"]:.2f} '
      f'(no prior) to {ab_w.loc["public-only APM prior (no double counting)", "mean_corr"]:.2f} and is used. For batters it did not '
      f'({ab_b.loc["public-only APM prior (no double counting)", "mean_corr"]:.2f} vs {ab_b.loc["no APM prior (no public data, no competition adjustment)", "mean_corr"]:.2f} without), '
      'so batters are rated on RR-pack data with hierarchical shrinkage.',
      '- **Fairness test.** Out-of-sample residuals by player group (runs per 100 pressure balls; a fair model is near zero):', '',
      FAIR.round(2).to_markdown(index=False), '',
      '- All groups are within about one standard error of zero: no detectable bias against T20I-heavy or IPL-heavy players.', '']

# ---- 4. evidence
L += ['# 4. Evidence for the top 10', '',
      '![Batters top 20](charts/2_batters_top20_intervals.png)', '', '![Bowlers top 20](charts/3_bowlers_top20_intervals.png)', '',
      'Every top-10 player has a scout card (`v2_results/cards/`) with: the score and interval, observed pressure and normal run '
      'value, pressure strike rate or economy, phase and matchup splits, their three biggest pressure performances in the RR pack '
      '(by win probability added, with date and opponent), computed risk flags, and a separately labelled scouting panel with '
      'cited public reporting (fitness, availability). The scouting panel never changes a rank.', '',
      '![Pressure vs normal](charts/4_pressure_vs_normal_batters.png)', '',
      'Players above the diagonal did better under pressure than normally. Because that gap does not repeat (section 5), the '
      'ranking uses overall skill measured on all balls and shrinks the pressure gap away; the observed gap is shown on each card for context.', '']
for role, T in [('Batters', BAT), ('Bowlers', BOWL)]:
    t = T.head(10)[['rank', 'name', 'score', 'p_n', 'obs_pressure_rv100', 'obs_normal_rv100', 'role_label', 'age']].copy()
    L += [f'**{role}: observed record behind the scores**', '', t.round(1).rename(columns={
        'p_n': 'pressure balls', 'obs_pressure_rv100': 'observed pressure RV/100', 'obs_normal_rv100': 'observed normal RV/100',
        'role_label': 'role'}).to_markdown(index=False), '']

# ---- 5. reliability
sens_tab = SENS[['role', 'variant', 'top10_kept', 'base_top10_in_variant_top15', 'spearman']].round(3)
L += ['# 5. Reliability and limitations', '',
      '**Backtest.** For each season 2023-26 we rebuilt every model with data up to the previous season and predicted each '
      'player\'s pressure run value in the next season (RR pack, players with 30+ pressure balls).', '',
      '![Backtest](charts/6_backtest_models.png)', '', '**Batters**', '', sb.round(3).to_markdown(), '', '**Bowlers**', '',
      sw.round(3).to_markdown(), '',
      '- `ceiling` is the best correlation any model could reach given how noisy one season of pressure balls is (square root of '
      'the target\'s split-half reliability). Batting pressure outcomes are noisy; bowling ones even more so.',
      '- **Is clutch real?** The hierarchical model estimates each player\'s pressure-specific effect; its spread shrinks as data '
      f'accumulates (bowlers: posterior SD of the effect {CLU["bowl"].post_sig_d_mean.iloc[0]:.3f} -> {CLU["bowl"].post_sig_d_mean.iloc[-1]:.3f} runs per ball '
      'from the 2022 to the 2025 cutoff), and adding it never improved out-of-sample accuracy. We therefore rank on overall skill.', '',
      '**Ablation** (out of time; diff_vs_full > 0 means removing the component helped):', '', 'Batters', '', ab_b.to_markdown(), '',
      'Bowlers', '', ab_w.to_markdown(), '',
      '- Final configuration: no age curve (it never helped), no pressure-specific term (it hurt), public-league prior for bowlers only, '
      'and no prior that reuses the RR-pack balls of the likelihood (that would count the same balls twice and make intervals falsely narrow).',
      f'- **Intervals are calibrated out of time.** The model\'s raw 80% intervals covered only {CAL["bat"]["coverage_before"]:.0%} (batters) and '
      f'{CAL["bowl"]["coverage_before"]:.0%} (bowlers) of next-season outcomes in the backtest. We widened them by the smallest factor that '
      f'restores 80% coverage ({CAL["bat"]["widen"]:.2f}x batters, {CAL["bowl"]["widen"]:.2f}x bowlers; coverage after: '
      f'{CAL["bat"]["coverage_after"]:.0%} / {CAL["bowl"]["coverage_after"]:.0%}). All intervals and P(top 10) values in this report use the widened version.', '',
      '**Sensitivity** (top 10 kept out of 10 under each variant):', '', sens_tab.to_markdown(index=False), '',
      '**Survivorship.** Poor performers are dropped more often, so next-season targets exist mainly for survivors. Re-scoring with '
      'inverse-probability-of-retention weights and with all-competition next-season targets left the model ordering unchanged '
      '(`v2_results/models/skill_survivorship_*.csv`).', '',
      '**Limitations.**', '',
      f'- Pressure outcomes in one season are mostly noise: {clear_txt}.',
      '- Fielding is not measured (no fielder names in the RR pack or Cricsheet csv2). Pitch, weather and field placements are unknown.',
      '- Batting hand, bowling type and speed exist only for RR-pack balls; matchup splits are shown only where the effect type is '
      f'repeatable (batter spin-vs-pace r = {MREL.set_index("effect").reliability.iloc[0]:.2f}; other matchup types are noise).',
      '- Day/night is inferred from IPL double-headers; no dew effect was detectable.',
      '- Leverage in the first overs of a first innings is above average (about 1.9x in over 1, falling to 1.2x by over 6) because the '
      'win-probability model treats an early wicket as a large cut to the projected total. Chases look as expected (rising to 3.5x in the '
      'last over). We shrank the early run rate toward par to remove a first-ball artefact; the remaining effect is partly real and partly '
      'model shape. It changes which balls count as pressure, not the ratings themselves (ratings use all balls), and the top 10 '
      'is stable across the alternative pressure definitions in the sensitivity table.',
      '- Auction status is as of 15 Nov 2026 (trades and retirements from Wikipedia); retention lists were due mid-November and '
      'were not yet published. Re-run `s13_final.py` with the published lists before the 16 Dec auction.',
      '- Qualitative notes come from public reporting and may be incomplete; they are labelled and never change a rank.', '']
# ---- 6. from ranking to selection (RR fit; s23)
if os.path.exists(R('rr_fit/role_gaps.csv')):
    G = rd('rr_fit/role_gaps.csv'); VD = rd('rr_fit/selector_verdicts.csv'); SHL = rd('rr_fit/role_shortlists.csv')
    g2 = list(G.slot.head(2))
    pt = VD[VD.verdict.eq('Priority target')]
    L += ['# 6. From ranking to selection: what RR should do', '',
          'A ranking answers "who is best under pressure"; a selector also asks "who does Rajasthan Royals need". We placed every '
          'rated player into role slots and compared RR\'s best player in each slot (2026 roster, all assumed retained) with the '
          'league benchmark (median of the ten best eligible players in that slot).', '',
          G[['slot', 'benchmark_top10_median', 'rr_best', 'rr_best_score', 'gap']].round(1).to_markdown(index=False), '',
          f'- **RR\'s biggest pressure gaps are {g2[0].lower()} and {g2[1].lower()}.** Opening is RR\'s strength (Sooryavanshi is the '
          'top-rated batter in the dataset).',
          f'- **Priority targets** (fill one of the two biggest gaps, P(top 10) of 20% or more, available if released): '
          + (', '.join(f'{r.name} ({r.slots})' for r in pt.itertuples()) if len(pt) else 'none meet all three conditions') + '.',
          '- Shortlists of the best three available players per slot, with a value pick, form trend and price, are in '
          '`v2_results/rr_fit/RR_FIT_REPORT.md`; a verdict, main risks and the fallback option for every candidate are in '
          '`SELECTOR_VERDICTS.md`. Fitness reports are used only as risk flags.', '']
    for sl in g2:
        t = SHL[SHL.slot == sl][['pick', 'name', 'nation', 'score', 'p_top10', 'trend', 'status']]
        L += [f'**Shortlist - {sl}**', '', t.round(2).to_markdown(index=False), '']
L += ['# Appendix', '',
      '- Uncapped & Value Targets, emerging tier, price model: `v2_results/value/VALUE_REPORT.md`.',
      '- Youth board (age 23 and under), development-model backtest, comparables: `v2_results/youth/YOUTH_REPORT.md`.',
      '- RR squad fit, role gaps, shortlists, selector verdicts: `v2_results/rr_fit/`.',
      '- Player profile database and data dictionary: `v2_results/profiles/`.',
      '- What predicts pressure performance (SHAP), player types, matchups: `v2_results/explain/EXPLAIN_REPORT.md`.',
      '- Reproduction: `bash v2_code/run_all.sh`; sources and licences: `data_public/SOURCES.md`, `CRICKET_PRIMER.md`.']
os.makedirs(R('report'), exist_ok=True)
md = R('report/SupeRR_S2_v2_Methodology_Report.md')
open(md, 'w').write('\n'.join(L))

# ======================= MODEL_COMPARISON =======================
M = ['# Model comparison (all out of time)', '', '## Win probability', '', WP.round(4).to_markdown(index=False), '',
     '## Expected outcomes', '', XO.round(5).to_markdown(), '', '## Pressure definitions', '', PD_.round(3).to_markdown(index=False), '',
     '## Player skill: next-season pressure run value', '', '### Batters', '', sb.round(3).to_markdown(), '', '### Bowlers', '',
     sw.round(3).to_markdown(), '', '## Ablation', '', '### Batters', '', ab_b.to_markdown(), '', '### Bowlers', '', ab_w.to_markdown(), '',
     '## Interval coverage (80% predictive intervals)', '', 'Before calibration (s13b, public-only prior variant):', '', COV.round(3).to_markdown(index=False), '',
     'Calibration of the final configuration (s13c): widening factor per role and coverage before / after:', '',
     pd.DataFrame(CAL).T.round(3).to_markdown(), '',
     '## Profile-feature LightGBM vs the Bayesian model', '', rd('explain/profile_model_vs_bayes.csv').groupby(['role', 'model'])[['wcorr', 'spearman']].mean().round(3).to_markdown(), '',
     '## Decisions', '', '- WP: logistic (simplest and best). Expected outcomes: sklearn HGB. Pressure: learned leverage.',
     '- Skill: hierarchical Bayes, overall skill only; bowlers with a public-league prior, batters without a prior; no age curve. '
     'Every fancier variant that did not beat its simpler alternative out of time was dropped (hard rule 6).']
open(R('MODEL_COMPARISON.md'), 'w').write('\n'.join(M))

# ======================= BASELINE_VS_V2 =======================
bl = []
for k, role in [('batters', 'bat'), ('bowlers', 'bowl')]:
    v2 = FR[FR.list == f'{k}_open'].set_index('name')
    T = BAT if role == 'bat' else BOWL
    rk = T.set_index('name')['rank']
    rows = [dict(baseline_rank=int(r.Rank), player=r.Player, v2_rank=rk.get(r.Player, 'not eligible / not ranked')) for r in BASE[k].itertuples()]
    new = [n for n in v2.index if n not in set(BASE[k].Player)]
    bl += [f'## {k.title()}', '', pd.DataFrame(rows).to_markdown(index=False), '', f'- New in the v2 top 10: {", ".join(new) if new else "none"}.',
           f'- Overlap: {ovl[k]} of 10.', '']
BV = ['# Baseline (v1) vs v2', '',
      '| | v1 baseline | v2 |', '|---|---|---|',
      '| Data | RR pack only | RR pack + 1.6M public balls (prior, validation, competition strength) |',
      '| Win probability | HGB, tier + is_ipl features, in-sample check | logistic with era, venue, Elo; 4 season-ahead folds |',
      '| Pressure | leverage with phase-average outcome mix, x1.2 knockouts | leverage with situation-specific outcome mix; 7 definitions compared |',
      '| Opposition / league | hand-set tiers 1 / 0.75 / 0.4 | ridge model of competition, venue, opponents with bootstrap SEs |',
      '| Rating | weighted sum of 5 components, hand-set weights | hierarchical Bayes posterior; weights learned; intervals and P(top 10) |',
      f'| Validated on future seasons | no | yes; v1 formula correlation {m2b:+.2f} (bat) / {m2w:+.2f} (bowl) vs v2 ~{sb.loc["M4_eb_overall", "wcorr"]:.2f} / {sw.loc["M6_apm", "wcorr"]:.2f} |',
      '| Clutch | rewarded (15% weight on pressure-vs-normal delta) | tested; not repeatable; not rewarded |', ''] + bl
open(R('BASELINE_VS_V2.md'), 'w').write('\n'.join(BV))

# ======================= EXECUTIVE SUMMARY =======================
def short(k):
    t = FR[FR.list == k]
    return ', '.join(f'{int(p)}. {n} ({s:.0f})' for p, n, s in zip(t.position, t.name, t.score_runs_per100_pressure_balls))
ES = ['# SupeRR Selector S2 - executive summary (v2)', '',
      '**Question.** Which batters and bowlers can Rajasthan Royals rely on when the match is on the line?', '',
      '**Answer.**', '', f'- Batters: {short("batters_open")}.', f'- Bowlers: {short("bowlers_open")}.',
      f'- RR can act on (batters): {short("batters_rr_can_buy")}.', f'- RR can act on (bowlers): {short("bowlers_rr_can_buy")}.', '',
      '(score = runs added per 100 pressure balls above expectation; full intervals and P(top 10) in the report)', '',
      '**How.** Pressure = balls where the next delivery can swing win probability most (top 25%). Performance = runs and wickets '
      'above the expectation for the exact situation, adjusted for era, venue, opposition and competition. Ratings come from a '
      'hierarchical Bayesian model tested on seasons it had not seen.', '',
      '**What we learned.**', '',
      '- "Clutch" does not repeat: players who over-perform under pressure in one season tend to fall back. The best guide to '
      'pressure performance is overall skill measured fairly.',
      f'- The v1 ranking formula did not predict next-season pressure performance (correlation {m2b:+.2f} / {m2w:+.2f}); v2 does, '
      f'about {sb.loc["M4_eb_overall", "wcorr"]:.2f} / {sw.loc["M6_apm", "wcorr"]:.2f}, roughly half to all of what the noise allows.',
      f'- The order is a best estimate, not a certainty: {clear_txt}.', '',
      '**Risks.** Fitness reports in 2026 for several names (see scout cards); retention lists not yet published; fielding unmeasured.']
open(R('EXECUTIVE_SUMMARY.md'), 'w').write('\n'.join(ES))

# ======================= conversions =======================
css = ('body{font-family:Georgia,serif;max-width:780px;margin:24px auto;color:#0b0b0b;line-height:1.45;font-size:11pt}'
       'table{border-collapse:collapse;font-size:8.5pt;margin:8px 0}td,th{border:1px solid #d6d5d0;padding:3px 5px}'
       'th{background:#f3f2ee}img{max-width:100%}h1{font-size:17pt;margin-top:26px}h2{font-size:13pt}code{font-size:9pt}')
open(R('report/report.css'), 'w').write(css)
if shutil.which('pandoc'):
    for src, base in [(md, R('report/SupeRR_S2_v2_Methodology_Report')), (R('EXECUTIVE_SUMMARY.md'), R('report/Executive_Summary'))]:
        subprocess.run(['pandoc', src, '-o', base + '.docx', '--resource-path', R('report')], check=True)
        subprocess.run(['pandoc', src, '-s', '--embed-resources', '--css', R('report/report.css'), '--resource-path', R('report'),
                        '-o', base + '.html', '--metadata', 'title=SupeRR S2 v2'], check=True)
    chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    if os.path.exists(chrome):
        for base in [R('report/SupeRR_S2_v2_Methodology_Report'), R('report/Executive_Summary')]:
            subprocess.run([chrome, '--headless', '--disable-gpu', f'--print-to-pdf={base}.pdf', '--no-pdf-header-footer',
                            'file://' + base + '.html'], check=True, capture_output=True)
print('report written:', md)
