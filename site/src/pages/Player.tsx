import { Link, useParams } from 'react-router-dom'
import { ExternalLink, AlertTriangle, Zap } from 'lucide-react'
import { useData, useProfile, type Player, type Role } from '../lib/data'
import { Avatar, Chip, PCell, RatingBar, Status, Tip, Section } from '../components/ui'
import Chart, { axis, alpha } from '../components/Chart'
import { cr, f0, f1, pct } from '../lib/fmt'

const PH = ['PP', 'Middle', 'Death']
const PHN: Record<string, string> = { PP: 'Powerplay (1-6)', Middle: 'Middle (7-15)', Death: 'Death (16-20)' }

function batRows(d: any) {
  const rows: [string, any][] = [['Career T20 (2019-26)', d.all?.career]]
  for (const [k, v] of Object.entries(d.comp2 || {})) rows.push([k, v])
  rows.push(['Last 12 months', d.recent?.last_12_months])
  for (const p of PH) rows.push([PHN[p], d.phase?.[p]])
  rows.push(['Setting a total', d.setting?.setting], ['Chasing', d.setting?.chasing], ['Pressure balls', d.pres?.['1']], ['Normal balls', d.pres?.['0']])
  return rows.filter(r => r[1])
}

function BatCard({ d }: { d: any }) {
  return (
    <div className="card overflow-x-auto"><table className="tbl w-full min-w-[720px] text-sm">
      <thead><tr><th>Split</th>{['Inns', 'Runs', 'Balls', 'Avg', 'SR', '50s', '100s', 'HS', 'Bdry %', 'Dot %', 'Run value/100'].map(h => <th key={h} className="text-right">{h}{h === 'Run value/100' && <Tip k="runValue" label="run value" />}</th>)}</tr></thead>
      <tbody>{batRows(d).map(([n, v]) => <tr key={n}><td className="font-medium">{n}</td>
        {[v.innings, v.runs, v.balls].map((x, i) => <td key={i} className="num text-right">{f0(x)}</td>)}
        <td className="num text-right">{f1(v.average)}</td><td className="num text-right font-semibold">{f1(v.strike_rate)}</td>
        <td className="num text-right">{f0(v.fifties)}</td><td className="num text-right">{f0(v.hundreds)}</td><td className="num text-right">{f0(v.highest)}</td>
        <td className="num text-right">{f1(v.boundary_pct)}</td><td className="num text-right">{f1(v.dot_pct)}</td><td className="num text-right">{f1(v.run_value_per100)}</td></tr>)}</tbody>
    </table></div>)
}
function bowlRows(d: any) {
  const rows: [string, any][] = [['Career T20 (2019-26)', d.all?.career]]
  for (const [k, v] of Object.entries(d.comp2 || {})) rows.push([k, v])
  rows.push(['Last 12 months', d.recent?.last_12_months])
  for (const p of PH) rows.push([PHN[p], d.phase?.[p]])
  rows.push(['vs left-hand bats', d.bat_hand?.LHB], ['vs right-hand bats', d.bat_hand?.RHB], ['Pressure balls', d.pres?.['1']], ['Normal balls', d.pres?.['0']])
  return rows.filter(r => r[1])
}
function BowlCard({ d }: { d: any }) {
  return (
    <div className="card overflow-x-auto"><table className="tbl w-full min-w-[720px] text-sm">
      <thead><tr><th>Split</th>{['Overs', 'Wkts', 'Econ', 'Avg', 'SR', 'Dot %', 'Bdry %', '3w', '4w+', 'Extras', 'Run value/100'].map(h => <th key={h} className="text-right">{h}{h === 'Run value/100' && <Tip k="runValue" label="run value" />}</th>)}</tr></thead>
      <tbody>{bowlRows(d).map(([n, v]) => <tr key={n}><td className="font-medium">{n}</td>
        <td className="num text-right">{v.balls ? `${Math.floor(v.balls / 6)}.${v.balls % 6}` : '–'}</td><td className="num text-right">{f0(v.wickets)}</td>
        <td className="num text-right font-semibold">{v.economy?.toFixed?.(2) ?? '–'}</td><td className="num text-right">{f1(v.average)}</td><td className="num text-right">{f1(v.strike_rate)}</td>
        <td className="num text-right">{f1(v.dot_pct)}</td><td className="num text-right">{f1(v.boundary_pct)}</td><td className="num text-right">{f0(v.three_w)}</td>
        <td className="num text-right">{f0(v.four_w_plus)}</td><td className="num text-right">{v.wides !== undefined ? f0((v.wides || 0) + (v.no_balls || 0)) : '–'}</td>
        <td className="num text-right">{f1(v.run_value_per100)}</td></tr>)}</tbody>
    </table></div>)
}

function PhaseChart({ d, role }: { d: any; role: Role }) {
  const m = role === 'bat' ? 'strike_rate' : 'economy'
  return <Chart label={`Phase profile: ${role === 'bat' ? 'strike rate' : 'economy'} and run value by phase`} height={260} option={(t: any) => ({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: PH.map(p => PHN[p]), ...axis(t) },
    yAxis: [{ type: 'value', ...axis(t) }, { type: 'value', ...axis(t, { splitLine: { show: false } }) }],
    series: [
      { name: role === 'bat' ? 'Strike rate' : 'Economy', type: 'bar', barMaxWidth: 36, itemStyle: { color: role === 'bat' ? t.bat : t.bowl, borderRadius: [4, 4, 0, 0] }, data: PH.map(p => d.phase?.[p]?.[m] ?? null) },
      { name: 'Run value / 100 balls', type: 'line', yAxisIndex: 1, symbolSize: 8, lineStyle: { width: 2, color: t.ink }, itemStyle: { color: t.ink }, data: PH.map(p => d.phase?.[p]?.run_value_per100 ?? null) }] })} />
}

const abbr = (s: string) => s.replace('Right-arm', 'RA').replace('Left-arm', 'LA').replace('medium-fast', 'med-fast').replace('fast-medium', 'fast-med').replace('Slow left-arm orthodox', 'SLA orthodox').replace('offbreak', 'off-spin').replace('Leg-Break', 'leg-spin')
function MatchupHeat({ d, role }: { d: any; role: Role }) {
  const src = role === 'bat' ? d.bowl_type || {} : d.bat_hand || {}
  const rows = Object.entries(src).filter(([, v]: any) => (v.balls || 0) >= 30).sort((a: any, b: any) => b[1].balls - a[1].balls)
  if (!rows.length) return <p className="text-sm text-ink2">Not enough RR-pack balls with bowling-type / batting-hand data for a matchup view.</p>
  const cols = role === 'bat' ? ['strike_rate', 'run_value_per100', 'dot_pct', 'boundary_pct'] : ['economy', 'run_value_per100', 'dot_pct', 'strike_rate']
  const names: Record<string, string> = { strike_rate: role === 'bat' ? 'Strike rate' : 'Balls/wkt', run_value_per100: 'Run value/100', dot_pct: 'Dot %', boundary_pct: 'Boundary %', economy: 'Economy' }
  const rv = rows.map(([, v]: any) => v.run_value_per100 ?? 0)
  const lim = Math.max(10, ...rv.map(Math.abs))
  return <Chart label={`Matchup heatmap vs ${role === 'bat' ? 'bowling types' : 'batting hands'}`} height={Math.max(160, 40 + rows.length * 30)} option={(t: any) => ({
    grid: { left: t.compact ? 112 : 170, right: 10, top: 30, bottom: 10, containLabel: false },
    tooltip: { formatter: (p: any) => `${rows[p.value[1]][0]} · ${names[cols[p.value[0]]]}: ${(rows[p.value[1]][1] as any)[cols[p.value[0]]]?.toFixed?.(1)} (${(rows[p.value[1]][1] as any).balls} balls)` },
    xAxis: { type: 'category', position: 'top', data: cols.map(c => names[c]), ...axis(t), splitLine: { show: false } },
    yAxis: { type: 'category', data: rows.map(r => `${t.compact ? abbr(r[0]) : r[0]} (${(r[1] as any).balls})`), inverse: true, ...axis(t), splitLine: { show: false } },
    visualMap: { show: false, min: -lim, max: lim, dimension: 3, inRange: { color: [alpha(t.risk, 0.35), t.surface, alpha(t.good, 0.35)] } },
    series: [{ type: 'heatmap', label: { show: true, color: t.ink, formatter: (p: any) => p.value[2] === null ? '–' : Number(p.value[2]).toFixed(1) },
      itemStyle: { borderColor: t.surface, borderWidth: 2 },
      data: rows.flatMap(([, v]: any, y) => cols.map((c, x) => [x, y, v[c] ?? null, v.run_value_per100 ?? 0])) }] })} />
}

function FormChart({ d, role }: { d: any; role: Role }) {
  const s = Object.entries(d.season || {}).sort((a, b) => Number(a[0]) - Number(b[0])).filter(([, v]: any) => (v.balls || 0) >= 30)
  if (s.length < 2) return <p className="text-sm text-ink2">Not enough seasons for a trend.</p>
  const m = role === 'bat' ? 'strike_rate' : 'economy'
  return <Chart label="Form trend by season" height={240} option={(t: any) => ({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: s.map(x => x[0]), ...axis(t) },
    yAxis: [{ type: 'value', ...axis(t) }, { type: 'value', ...axis(t, { splitLine: { show: false } }) }],
    series: [{ name: 'Run value / 100 balls', type: 'line', symbolSize: 8, lineStyle: { width: 2.5, color: role === 'bat' ? t.bat : t.bowl }, itemStyle: { color: role === 'bat' ? t.bat : t.bowl }, data: s.map(([, v]: any) => v.run_value_per100) },
      { name: role === 'bat' ? 'Strike rate' : 'Economy', type: 'line', yAxisIndex: 1, symbolSize: 6, lineStyle: { width: 1.5, type: 'dashed', color: t.ink2 }, itemStyle: { color: t.ink2 }, data: s.map(([, v]: any) => v[m]) },
      { type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: t.line }, data: [{ yAxis: 0 }] }, data: [] }] })} />
}

function RolePanel({ p, role, prof }: { p: Player; role: Role; prof: any }) {
  const r = p[role]; const d = prof?.[role]
  if (!r && !d) return null
  return (
    <Section title={role === 'bat' ? 'Batting' : 'Bowling'} kicker={role === 'bat' ? 'With the bat' : 'With the ball'}>
      {r && <div className="grid gap-4 md:grid-cols-3">
        <div className="card p-5 md:col-span-2">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div><div className="text-xs font-semibold uppercase tracking-wide text-ink2">Pressure Rating<Tip k="rating" label="Pressure Rating" /></div>
              <div className="num text-4xl font-extrabold">{f1(r.score)}</div></div>
            <div className="text-right text-sm"><div>Rank <strong className="num">{r.rank ?? '–'}</strong> {r.tier === 'emerging' && <Chip tone="warn">emerging tier</Chip>}</div>
              <div>P(top 10) <PCell p={r.p_top10} /><Tip k="ptop10" label="P(top 10)" /></div></div>
          </div>
          <div className="mt-4"><RatingBar r={r} role={role} /></div>
          <div className="num mt-1 flex justify-between text-xs text-ink2"><span>80% range {f1(r.lo)} to {f1(r.hi)}<Tip k="interval" label="80% range" /></span><span>{f0(r.pressure_balls)} pressure balls<Tip k="pressureBalls" label="pressure balls" /></span></div>
        </div>
        <div className="card p-5">
          <div className="text-xs font-semibold uppercase tracking-wide text-ink2">Pressure vs normal (observed)<Tip k="obsGap" label="pressure vs normal" /></div>
          {[['Pressure balls', r.obs_pressure], ['Normal balls', r.obs_normal]].map(([l, v]: any) => (
            <div key={l} className="mt-3"><div className="flex justify-between text-sm"><span>{l}</span><span className="num font-semibold">{f1(v)}</span></div>
              <div className="mt-1 h-2 rounded-full bg-line"><div className={`h-2 rounded-full ${role === 'bat' ? 'bg-[rgb(var(--bat))]' : 'bg-[rgb(var(--bowl))]'}`} style={{ width: `${Math.max(2, Math.min(100, ((v ?? 0) + 30) / 1))}%` }} /></div></div>))}
          <p className="mt-3 text-xs text-ink2">Run value per 100 balls, RR pack 2022-26. The gap is context, not part of the rating.</p>
        </div>
      </div>}
      {d && <>
        <div className="mt-4">{role === 'bat' ? <BatCard d={d} /> : <BowlCard d={d} />}</div>
        <div className="mt-4 grid gap-4 lg:grid-cols-3 [&>*]:min-w-0">
          <div className="card p-4"><h3 className="mb-1 text-sm font-semibold">Phase profile</h3><PhaseChart d={d} role={role} /></div>
          <div className="card p-4"><h3 className="mb-1 text-sm font-semibold">Matchups {role === 'bat' ? 'vs bowling types' : 'vs batting hand'}</h3><MatchupHeat d={d} role={role} />
            <p className="mt-1 text-[11px] text-ink2">{role === 'bat' ? 'Spin-vs-pace differences are repeatable in our tests; finer splits are noisier.' : 'Left/right splits proved mostly noise in our tests; treat as descriptive.'}</p></div>
          <div className="card p-4"><h3 className="mb-1 text-sm font-semibold">Form trend</h3><FormChart d={d} role={role} /></div>
        </div>
      </>}
    </Section>)
}

export default function PlayerPage() {
  const { id } = useParams(); const { players, strategy } = useData(); const prof = useProfile(id)
  const p = id ? players[id] : undefined
  if (!p) return <div className="py-16 text-center text-ink2">Player not found. <Link className="text-royal underline" to="/rankings">Back to rankings</Link></div>
  const mainRole: Role = p.bowl && (!p.bat || (p.bowl.rank ?? 999) < (p.bat.rank ?? 999)) ? 'bowl' : 'bat'
  return (
    <div>
      <div className="card p-5 sm:p-6">
        <div className="flex flex-wrap items-start gap-4">
          <Avatar name={p.name} role={mainRole} />
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-extrabold sm:text-3xl">{p.name}</h1>
            <div className="mt-1 text-sm text-ink2">{p.nation}{p.age ? ` · age ${p.age} on 1 Apr 2027` : ''} · {p.cap}{p.team27 ? ` · ${p.team27}` : ''}</div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              <Status s={p.status} />{p.badges.map(b => <Chip key={b}>{b}</Chip>)}
              {p.type_bat && <Chip tone="royal">{p.type_bat}</Chip>}{p.type_bowl && <Chip tone="pink">{p.type_bowl}</Chip>}
              {p.slots.map(s => <Chip key={s}>{s}</Chip>)}
            </div>
          </div>
          <div className="w-full text-sm sm:w-auto sm:text-right">
            <div className="text-xs font-semibold uppercase tracking-wide text-ink2">Est. 2027 price<Tip k="price" label="price range" /></div>
            <div className="num text-lg font-bold">{p.price.known ? `${cr(p.price.lo)} – ${cr(p.price.hi)}` : 'not estimable'}</div>
            <div className="text-xs text-ink2">{p.price.known ? `middle ${cr(p.price.mid)}` : 'retained / no auction record'}{p.price.last ? ` · last sold ${cr(p.price.last)} (${p.price.last_year})` : ''}</div>
            {p.verdict && <div className="mt-2"><Chip tone={p.verdict.verdict.startsWith('Priority') ? 'good' : p.verdict.verdict.startsWith('Medical') ? 'risk' : 'royal'}>RR verdict: {p.verdict.verdict}</Chip></div>}
          </div>
        </div>
      </div>

      {p.youth && <Section title="Youth projection" kicker="Development">
        <div className="card p-5"><div className="flex flex-wrap items-center gap-3"><Chip tone={p.youth.label === 'Buy now' ? 'good' : 'royal'}>{p.youth.label}</Chip>
          <span className="text-sm text-ink2">Board rank {p.youth.rank} ({p.youth.board}) · {f0(p.youth.balls)} balls<Tip k="youth" label="youth board" /></span></div>
          <div className="mt-3 grid grid-cols-3 gap-3 text-center">{[['Next season', p.youth.proj_1], ['In 2 seasons', p.youth.proj_2], ['In 3 seasons', p.youth.proj_3]].map(([l, v]: any) =>
            <div key={l} className="rounded-xl bg-page p-3"><div className="text-xs text-ink2">{l}</div><div className="num text-xl font-bold">{f1(v)}</div></div>)}</div>
          <p className="mt-2 text-xs text-ink2">Adjusted skill per 100 balls (all situations). Next-season 80% range {f1(p.youth.proj_1_lo)} to {f1(p.youth.proj_1_hi)}. Projections use a model backtested on players aged 23 or under in 2021.</p></div>
      </Section>}

      {!prof && <p className="mt-6 text-sm text-ink2" role="status">Loading profile…</p>}
      {([mainRole, mainRole === 'bat' ? 'bowl' : 'bat'] as Role[]).map((r, i) => {
        const balls = prof?.[r]?.all?.career?.balls ?? 0
        if (i === 1 && !p[r] && balls < 200) return balls > 0 ? <p key={r} className="mt-8 text-sm text-ink2">{r === 'bat' ? 'Batting' : 'Bowling'}: limited data ({f0(balls)} balls) – not rated and not shown in detail.</p> : null
        return <RolePanel key={r} p={p} role={r} prof={prof} />
      })}

      {prof && <div className="mt-10 grid gap-4 lg:grid-cols-2 [&>*]:min-w-0">
        <div className="card p-5"><h2 className="flex items-center gap-2 font-bold"><Zap size={16} className="text-pink" aria-hidden />Biggest pressure performances</h2>
          {Object.entries(prof.moments || {}).flatMap(([r, ms]: any) => ms.map((m: string, i: number) => <p key={r + i} className="mt-3 text-sm"><Chip tone={r === 'bat' ? 'royal' : 'pink'}>{r === 'bat' ? 'bat' : 'ball'}</Chip> {m}</p>))}
          {!Object.values(prof.moments || {}).flat().length && <p className="mt-3 text-sm text-ink2">No RR-pack innings with 6+ pressure balls.</p>}
          <p className="mt-3 text-[11px] text-ink2">From the RR data pack: matches where this player added the most win probability.</p></div>
        <div className="card p-5"><h2 className="flex items-center gap-2 font-bold"><AlertTriangle size={16} className="text-warn" aria-hidden />Risk flags</h2>
          <ul className="mt-2 space-y-1 text-sm">{(prof.flags || []).map((f: string) => <li key={f} className="flex gap-2"><span aria-hidden className="text-warn">▲</span>{f}</li>)}</ul>
          {!prof.flags?.length && <p className="mt-2 text-sm text-ink2">None flagged.</p>}
          {p.verdict && <p className="mt-3 text-sm"><strong>Risks noted by the selector view:</strong> {p.verdict.risks}. <strong>If unavailable:</strong> {p.verdict.alternative}.</p>}</div>
        <div className="card p-5"><h2 className="font-bold">RR fit</h2>
          {prof.rr_fit?.length ? <div className="overflow-x-auto"><table className="tbl mt-2 w-full min-w-[420px] text-sm"><thead><tr><th>Role</th><th className="text-right">RR's best now</th><th className="text-right">League benchmark</th><th className="text-right">Gap<Tip k="gap" label="gap" /></th></tr></thead>
            <tbody>{prof.rr_fit.map((f: any) => <tr key={f.slot}><td>{f.slot}</td><td className="text-right">{f.rr_best || '—'} <span className="num text-ink2">{f1(f.rr_best_score)}</span></td><td className="num text-right">{f1(f.benchmark)}</td>
              <td className={`num text-right font-semibold ${f.gap > 3 ? 'text-risk' : f.gap < 0 ? 'text-good' : ''}`}>{f1(f.gap)}</td></tr>)}</tbody></table></div>
            : <p className="mt-2 text-sm text-ink2">No mapped role slot.</p>}
          <Link to="/strategy" className="mt-3 inline-block text-sm text-royal hover:underline">See RR strategy →</Link></div>
        <div className="card p-5"><h2 className="font-bold">Scout notes <Chip tone="warn">opinion · sourced</Chip></h2>
          {(prof.notes || []).map((n: any, i: number) => <p key={i} className="mt-3 text-sm"><span className="text-ink2">[{n.type}]</span> {n.note}{' '}
            <a className="inline-flex items-center gap-0.5 text-royal hover:underline" href={n.url} target="_blank" rel="noreferrer noopener">{n.source}<ExternalLink size={12} aria-hidden /></a></p>)}
          {!prof.notes?.length && <p className="mt-2 text-sm text-ink2">No public reporting was reviewed for this player.</p>}
          <p className="mt-3 text-[11px] text-ink2">Public reporting checked 15–16 Nov 2026. Used only to explain results or flag risks – never to change a rating.</p></div>
      </div>}
    </div>)
}
