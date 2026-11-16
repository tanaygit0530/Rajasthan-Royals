import { Link } from 'react-router-dom'
import { useData } from '../lib/data'
import Chart from '../components/Chart'
import { Chip, Section, Tip } from '../components/ui'
import { f1, pct } from '../lib/fmt'

const VT: Record<string, string> = { 'Priority target': 'good', Target: 'royal', 'Value / back-up option': 'neutral', 'Medical check first': 'risk', 'Core - already RR': 'pink', 'Not eligible': 'risk' }
export default function Strategy() {
  const { strategy: s, players } = useData()
  const gaps = [...s.gaps].sort((a: any, b: any) => b.gap - a.gap)
  const slots = Array.from(new Set(s.plans.map((p: any) => p.slot))) as string[]
  const order = ['Priority target', 'Target', 'Value / back-up option', 'Medical check first', 'Core - already RR', 'Not eligible']
  const plink = (id: string | undefined, name: string) => id && players[id] ? <Link className="font-semibold hover:text-royal" to={`/player/${id}`}>{name}</Link> : <span className="font-semibold">{name}</span>
  return (
    <div>
      <div className="text-xs font-semibold uppercase tracking-widest text-pink">From ranking to selection</div>
      <h1 className="text-3xl font-extrabold sm:text-4xl">What Rajasthan Royals should do</h1>
      <p className="mt-3 max-w-3xl text-ink2">We placed every rated player into a role and compared RR's best current player in each role (2026 roster, all assumed retained) with the league benchmark – the median of the ten best eligible players in that role.<Tip k="gap" label="gap" /></p>

      <Section title="Where RR is strong and where it is exposed" kicker="Pressure gaps by role">
        <div className="card p-4"><Chart label="RR pressure gaps by role" height={80 + gaps.length * 34} option={(t: any) => {
          const cols = ['RR best now', 'League benchmark', 'Gap']
          const lim = Math.max(...gaps.map((g: any) => Math.abs(g.gap)))
          return { grid: { left: 170, right: 20, top: 34, bottom: 10, containLabel: false },
            tooltip: { formatter: (p: any) => `${gaps[p.value[1]].slot} · ${cols[p.value[0]]}: ${Number(p.value[2]).toFixed(1)}${p.value[0] === 0 ? ` (${gaps[p.value[1]].rr_best || 'none'})` : ''}` },
            xAxis: { type: 'category', position: 'top', data: cols, axisLabel: { color: t.ink2 }, axisLine: { show: false }, axisTick: { show: false } },
            yAxis: { type: 'category', inverse: true, data: gaps.map((g: any) => g.slot), axisLabel: { color: t.ink }, axisLine: { show: false }, axisTick: { show: false } },
            visualMap: { show: false, min: -lim, max: lim, dimension: 3, inRange: { color: [t.good, t.surface, t.risk] } },
            series: [{ type: 'heatmap', itemStyle: { borderColor: t.surface, borderWidth: 3 }, label: { show: true, color: t.ink, formatter: (p: any) => p.value[2] === null ? '–' : Number(p.value[2]).toFixed(1) },
              data: gaps.flatMap((g: any, y: number) => [[0, y, g.rr_best_score, 0], [1, y, g.benchmark_top10_median, 0], [2, y, g.gap, g.gap]]) }] } }} />
          <p className="mt-2 text-xs text-ink2">Gap column: red = RR below the league benchmark, green = RR above it. Ratings in runs per 100 pressure balls.</p></div>
      </Section>

      <Section title="Targets by role: plan A, B, C and a value pick" kicker="Shortlists">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{slots.map(sl => {
          const g = gaps.find((x: any) => x.slot === sl)
          return <div key={sl} className="card p-4">
            <div className="flex items-baseline justify-between"><h3 className="font-semibold">{sl}</h3>{g && <span className={`num text-xs ${g.gap > 3 ? 'text-risk' : 'text-ink2'}`}>gap {f1(g.gap)}</span>}</div>
            <ol className="mt-2 space-y-2 text-sm">{s.plans.filter((p: any) => p.slot === sl).map((p: any) => (
              <li key={p.plan + p.name} className="flex items-center gap-2"><span className={`grid h-6 w-12 shrink-0 place-items-center rounded-md text-[11px] font-bold ${p.plan === 'Value' ? 'bg-good/15 text-good' : 'bg-royal/10 text-royal'}`}>{p.plan === 'Value' ? 'Value' : `Plan ${p.plan}`}</span>
                <span className="min-w-0 flex-1 truncate">{plink(p.id, p.name)}</span><span className="num font-semibold">{f1(p.score)}</span><span className="num w-10 text-right text-xs text-ink2">{pct(p.p_top10)}</span></li>))}</ol>
          </div> })}</div>
      </Section>

      <Section title="Selector verdicts" kicker="Rationale per player">
        <div className="space-y-6">{order.map(v => { const rows = s.verdicts.filter((x: any) => x.verdict === v); if (!rows.length) return null
          return <div key={v}><h3 className="mb-2 flex items-center gap-2 font-semibold"><Chip tone={VT[v]}>{v}</Chip><span className="text-sm text-ink2">{rows.length}</span></h3>
            <div className="grid gap-3 md:grid-cols-2">{rows.map((x: any) => (
              <div key={x.name} className="card p-4 text-sm"><div className="flex items-baseline justify-between gap-2">{plink(x.id, x.name)}<span className="num font-semibold">{f1(x.score)} <span className="text-xs font-normal text-ink2">({x.interval})</span></span></div>
                <p className="mt-1 text-ink2">Fills: {x.slots}. P(top 10) {pct(x.p_top10)} · form {x.form_trend}.</p>
                <p className="mt-1"><span className="text-ink2">Risks:</span> {x.main_risks}. <span className="text-ink2">If unavailable:</span> {x.alternative}.</p></div>))}</div></div> })}</div>
        <p className="mt-3 text-xs text-ink2">Decision support, not a replacement for judgement. Fitness reports are used only as risk flags, never to change a rating.</p>
      </Section>

      <Section title="Value buys and youth picks" kicker="Beyond the top 10">
        <div className="grid gap-4 lg:grid-cols-2">
          {(['bat', 'bowl'] as const).map(r => <div key={r} className="card p-4"><h3 className="font-semibold">Value & uncapped – {r === 'bat' ? 'batters' : 'bowlers'}<Tip k="valuePerCr" label="value per crore" /></h3>
            <ol className="mt-2 space-y-1.5 text-sm">{s.value[r].slice(0, 6).map((x: any) => <li key={x.uid} className="flex justify-between gap-2"><span className="min-w-0 truncate">{plink(x.uid, x.name)} <span className="text-xs text-ink2">· {x.cap_status.startsWith('uncapped') ? 'uncapped' : 'capped'} · {x.tier.split(' ')[0]}</span></span><span className="num">{f1(x.score)}</span></li>)}</ol></div>)}
          {(['bat', 'bowl'] as const).map(r => <div key={r + 'y'} className="card p-4"><h3 className="font-semibold">Youth board – {r === 'bat' ? 'batters' : 'bowlers'} (≤23)<Tip k="youth" label="youth board" /></h3>
            <ol className="mt-2 space-y-1.5 text-sm">{s.youth[r].slice(0, 6).map((x: any) => <li key={x.uid} className="flex justify-between gap-2"><span className="min-w-0 truncate">{plink(x.uid, x.name)} <span className="text-xs text-ink2">· {x.age} · {x.status_2027?.startsWith('Already') ? 'already RR' : x.label}</span></span><span className="num">{f1(x.proj_1)}</span></li>)}</ol></div>)}
        </div>
      </Section>
    </div>)
}
