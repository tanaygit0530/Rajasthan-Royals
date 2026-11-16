import { useData } from '../lib/data'
import Chart, { axis } from '../components/Chart'
import { Details, Section, DataTable, Tip } from '../components/ui'
import { f1, f2, pct } from '../lib/fmt'

const MNAME: Record<string, string> = { M0_raw_pressure: 'Raw pressure record', M1_recency_raw: 'Recent pressure record', M2_baseline: 'v1 weighted formula (5 components)',
  M3_eb_pressure: 'Shrunk pressure record', M4_eb_overall: 'Overall skill (RR pack)', M5_eb_overall_plus_gap: 'Overall skill + pressure gap', M6_apm: 'Adjusted skill, all leagues',
  M7_stack: 'Stacked model', M8_bayes: 'Bayesian, incl. pressure effect', 'zero (league average)': 'Everyone average' }

export default function How() {
  const { method: m, meta } = useData()
  const steps = [
    ['1', 'Win probability', 'For every ball we estimate each team\'s chance of winning from the score, wickets, balls left, target, era, venue and team strength.'],
    ['2', 'Pressure', 'Leverage = how much the next ball can move that probability. The top 25% of balls are pressure balls.'],
    ['3', 'Expected outcome', 'For the exact situation we predict expected runs and wicket chance – no player information.'],
    ['4', 'Run value', `Each ball: runs above expectation, minus ${f1(meta.kw)} runs per extra dismissal (bowlers: the reverse).`],
    ['5', 'Fair comparison', 'Adjust for opposition, venue and league strength using 1.6 million public deliveries.'],
    ['6', 'Rating', 'A Bayesian model combines the evidence, shrinks small samples, and gives an honest range, calibrated on past seasons.'],
  ]
  const sk = (r: string) => (m.skill[r] as any[]).filter(x => MNAME[x.model]).sort((a, b) => b.wcorr - a.wcorr)
  return (
    <div className="mx-auto max-w-4xl">
      <div className="text-xs font-semibold uppercase tracking-widest text-pink">Method</div>
      <h1 className="text-3xl font-extrabold sm:text-4xl">How it works</h1>
      <p className="mt-3 text-ink2">Plain language first. Open “technical details” under any section for the evidence.</p>

      <Section title="What counts as pressure" kicker="Step 1–2">
        <p className="text-sm text-ink2">{meta.pressure_definition} The chart shows how much the next ball matters on average in each over (1.0 = an average ball).<Tip k="leverage" label="leverage" /></p>
        <div className="card mt-3 p-4"><Chart label="Leverage by over, setting vs chasing" height={300} option={(t: any) => ({
          tooltip: { trigger: 'axis', valueFormatter: (v: number) => v?.toFixed(2) },
          xAxis: { type: 'category', name: 'Over', nameLocation: 'middle', nameGap: 28, data: m.leverage.overs, ...axis(t) }, yAxis: { type: 'value', ...axis(t) },
          series: [{ name: 'Setting a total', type: 'line', symbolSize: 6, lineStyle: { width: 2.5, color: t.bat }, itemStyle: { color: t.bat }, data: m.leverage.setting },
            { name: 'Chasing', type: 'line', symbolSize: 6, lineStyle: { width: 2.5, color: t.bowl }, itemStyle: { color: t.bowl }, data: m.leverage.chasing,
              markLine: { silent: true, symbol: 'none', label: { formatter: 'average', position: 'insideStartTop', color: t.ink2 }, lineStyle: { color: t.ink2, type: 'dashed' }, data: [{ yAxis: 1 }] } }] })} /></div>
        <Details summary="Technical details: seven pressure definitions compared">
          <DataTable rows={m.pressure_defs} cols={[{ k: 'definition', h: 'Definition' }, { k: 'capture_eff_bat', h: 'Capture', num: true, f: r => f2(r.capture_eff_bat) },
            { k: 'bat_rel_rv', h: 'Reliability (bat)', num: true, f: r => f2(r.bat_rel_rv) }, { k: 'bowl_rel_rv', h: 'Reliability (bowl)', num: true, f: r => f2(r.bowl_rel_rv) }]} />
          <p className="mt-2">Capture = share of win-probability movement on flagged balls relative to random (1.0). Rule fixed in advance: keep learned leverage unless another definition is better on both. Chosen: {m.chosen_pressure.chosen}.</p>
        </Details>
      </Section>

      <Section title="From ball to rating" kicker="The pipeline">
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{steps.map(([n, h, t]) => (
          <li key={n} className="card relative p-4"><div className="num absolute right-4 top-3 text-3xl font-extrabold text-line">{n}</div>
            <h3 className="font-semibold">{h}</h3><p className="mt-1 text-sm text-ink2">{t}</p></li>))}</ol>
        <div className="card mt-4 p-4 text-sm text-ink2"><strong className="text-ink">Why not a weighted formula?</strong> Our first version (v1) scored players with five hand-weighted components
          (win-probability added, runs above expectation, survival, consistency, pressure-vs-normal gap). When we tested it on seasons it had not seen, it predicted nothing
          (see the chart below), so v2 replaced the weights with a model that learns from data and is tested out of sample.</div>
        <Details summary="Technical details: win-probability models compared">
          <DataTable rows={m.wp} cols={[{ k: 'innings', h: 'Innings' }, { k: 'model', h: 'Model' }, { k: 'logloss', h: 'Log-loss', num: true, f: r => r.logloss.toFixed(3) },
            { k: 'brier', h: 'Brier', num: true, f: r => r.brier.toFixed(3) }, { k: 'auc', h: 'AUC', num: true, f: r => r.auc.toFixed(3) }]} />
          <p className="mt-2">Trained on all seasons before each test season; tested on the next (four folds). Logistic regression won; tree models over-fitted match-level features.</p>
        </Details>
      </Section>

      <Section title="Making comparisons fair" kicker="Step 5">
        <p className="text-sm text-ink2">A run in the IPL is harder to score than a run in a weaker league. We measure league strength from players who appear in several competitions. Bars show runs per 100 balls below the IPL (IPL = 0).</p>
        <div className="card mt-3 p-4"><Chart label="League strength vs IPL" height={420} option={(t: any) => {
          const L = [...m.league].sort((a: any, b: any) => a.batters_runs_vs_IPL_per100 - b.batters_runs_vs_IPL_per100)
          return { grid: { left: t.compact ? 104 : 130, right: 16, top: 10, bottom: 50, containLabel: false }, tooltip: { trigger: 'axis' },
            xAxis: { type: 'value', ...axis(t) }, yAxis: { type: 'category', data: L.map((x: any) => x.comp), ...axis(t), splitLine: { show: false } },
            series: [{ name: 'Batters', type: 'bar', barMaxWidth: 10, itemStyle: { color: t.bat }, data: L.map((x: any) => x.batters_runs_vs_IPL_per100) },
              { name: 'Bowlers', type: 'bar', barMaxWidth: 10, itemStyle: { color: t.bowl }, data: L.map((x: any) => x.bowlers_runs_saved_vs_IPL_per100) }] } }} /></div>
        <Details summary="Technical details: fairness test">
          <DataTable rows={m.fairness} cols={[{ k: 'role', h: 'Role' }, { k: 'group', h: 'Group' }, { k: 'players_total', h: 'Players', num: true }, { k: 'mean_resid_per100', h: 'Mean error', num: true, f: r => f1(r.mean_resid_per100) }, { k: 'se', h: '± SE', num: true, f: r => f1(r.se) }]} />
          <p className="mt-2">Out-of-sample errors by player group (runs per 100 pressure balls). All groups are within about one standard error of zero: no detectable bias against IPL-heavy or T20I-heavy players.</p>
        </Details>
      </Section>

      <Section title="Does it work? Tested on seasons it never saw" kicker="Reliability">
        <p className="text-sm text-ink2">For each season 2023–26 we rebuilt everything with earlier data only and predicted each player's pressure performance in the next season.</p>
        <div className="grid gap-4 md:grid-cols-2">{(['bat', 'bowl'] as const).map(r => (
          <div key={r} className="card p-4"><h3 className="text-sm font-semibold">{r === 'bat' ? 'Batters' : 'Bowlers'}</h3>
            <Chart label={`Backtest correlation by model, ${r}`} height={320} option={(t: any) => { const S = sk(r).reverse(); const ceil = S[0]?.noise_ceiling_r; return {
              grid: { left: t.compact ? 128 : 200, right: 16, top: 26, bottom: 24, containLabel: false }, tooltip: { valueFormatter: (v: number) => v?.toFixed(3) },
              xAxis: { type: 'value', min: -0.2, max: 0.5, ...axis(t) }, yAxis: { type: 'category', data: S.map((x: any) => MNAME[x.model]), ...axis(t), splitLine: { show: false }, axisLabel: { color: t.ink2, width: t.compact ? 120 : 190, overflow: 'break', fontSize: t.compact ? 10 : 12 } },
              series: [{ type: 'bar', barMaxWidth: 14, data: S.map((x: any) => ({ value: x.wcorr, itemStyle: { color: x.model === 'M2_baseline' ? t.risk : ['M4_eb_overall', 'M6_apm', 'M8_bayes'].includes(x.model) ? t.good : t.ink2, borderRadius: 3 } })),
                markLine: { silent: true, symbol: 'none', label: { formatter: `ceiling ${ceil?.toFixed(2)}`, color: t.ink2, position: 'end', rotate: 0 }, lineStyle: { color: t.ink2, type: 'dashed' }, data: [{ xAxis: ceil }] } }] } }} /></div>))}</div>
        <div className="card mt-4 p-4 text-sm"><strong>Is “clutch” real?</strong> <span className="text-ink2">{meta.findings[0].text}</span></div>
        <div className="card mt-3 p-4 text-sm"><strong>Honest ranges.</strong> <span className="text-ink2">The model's own 80% ranges were too narrow: they covered {pct(meta.calibration.bat.coverage_before)} (batters) and {pct(meta.calibration.bowl.coverage_before)} (bowlers) of what happened next season. We widened them ×{f2(meta.calibration.bat.widen)} and ×{f2(meta.calibration.bowl.widen)} so they now cover {pct(meta.calibration.bat.coverage_after)} and {pct(meta.calibration.bowl.coverage_after)}. {meta.certainty}</span></div>
        <Details summary="Technical details: ablation (what each component adds) and sensitivity">
          {(['bat', 'bowl'] as const).map(r => <div key={r} className="mb-4"><div className="font-semibold text-ink">{r === 'bat' ? 'Batters' : 'Bowlers'}</div>
            <DataTable rows={m.ablation[r]} cols={[{ k: 'variant', h: 'Variant' }, { k: 'mean', h: 'Correlation', num: true, f: x => f2(x.mean) }, { k: 'diff', h: 'vs full', num: true, f: x => (x.diff >= 0 ? '+' : '') + x.diff.toFixed(3) }, { k: 'se', h: '± SE', num: true, f: x => x.se.toFixed(3) }]} /></div>)}
          <DataTable rows={m.sensitivity} cols={[{ k: 'role', h: 'Role' }, { k: 'variant', h: 'Variant' }, { k: 'top10_kept', h: 'Top 10 kept', num: true }, { k: 'spearman', h: 'Rank corr.', num: true, f: x => f2(x.spearman) }]} />
        </Details>
      </Section>

      <Section title="Limitations" kicker="What this cannot tell you">
        <ul className="card list-disc space-y-2 p-5 pl-9 text-sm text-ink2">
          <li>One season of pressure balls is mostly noise; most ranks inside the top 10 are statistical near-ties.</li>
          <li>Fielding is not measured (no fielder names in the data). Pitch, weather and field placements are unknown.</li>
          <li>Batting hand, bowling type and speed exist only for RR-pack balls; finer matchup splits are noisy.</li>
          <li>Availability uses trades and retirements to 15 Nov 2026; 2027 retention lists were not yet published.</li>
          <li>Auction prices are hard to predict, so price ranges are wide.</li>
          <li>Scout notes are opinion from public reporting and never change a rating.</li>
        </ul>
      </Section>
    </div>)
}
