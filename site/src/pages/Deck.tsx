// Interactive web "presentation": the whole report as slides, plus one slide per submitted player.
// Keyboard: ← → / Space / PageUp-Down, Home/End, G = overview grid, F = full screen. Swipe on touch screens.
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Grid3x3, Maximize2, X } from 'lucide-react'
import Chart, { axis, alpha } from '../components/Chart'
import { useData, useProfiles, type Player, type Role } from '../lib/data'
import { json } from '../lib/crypto'
import { f1, f0, pct, initials } from '../lib/fmt'

const AUTHOR = { name: 'Tanay Patil', email: 'tanaypatil0530@gmail.com', github: 'github.com/tanaygit0530' }
type Photos = { photos: Record<string, string>; credits: Record<string, any> }
type Slide = { id: string; title: string; group: string; body: ReactNode }

const MODEL = { M0_raw_pressure: 'Raw pressure record', M1_recency_raw: 'Recent pressure record', M2_baseline: 'v1 weighted formula',
  M3_eb_pressure: 'Shrunk pressure record', M4_eb_overall: 'Overall skill (RR data)', M5_eb_overall_plus_gap: 'Overall + pressure gap',
  M6_apm: 'Adjusted skill (all leagues)', M7_stack: 'Stacked GBM', M8_bayes: 'Bayesian model (chosen)' } as Record<string, string>
const avail = (s: string | null | undefined) => (s || '').startsWith('Open market') ? 'Open market – must register' :
  (s || '').replace('In auction pool (released by ', 'Released by ').replace(')', '')

// ---------- small building blocks ----------
function Kicker({ children }: { children: ReactNode }) {
  return <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-pink sm:text-xs">{children}</div>
}
function H({ k, t, sub }: { k: string; t: string; sub?: string }) {
  return <header className="mb-4 sm:mb-6"><Kicker>{k}</Kicker>
    <h2 className="mt-1 text-2xl font-extrabold leading-tight tracking-tight sm:text-4xl">{t}</h2>
    {sub ? <p className="mt-2 max-w-3xl text-sm text-ink2 sm:text-base">{sub}</p> : null}</header>
}
function Stat({ v, l, tone }: { v: ReactNode; l: string; tone?: string }) {
  return <div className="card p-3 sm:p-4"><div className={`num text-2xl font-extrabold sm:text-3xl ${tone || ''}`}>{v}</div>
    <div className="mt-1 text-xs text-ink2 sm:text-sm">{l}</div></div>
}
function Face({ p, role, photos, size = 'lg' }: { p: Player; role: Role; photos?: Photos | null; size?: 'lg' | 'sm' }) {
  const src = photos?.photos[p.id]
  const cls = size === 'lg' ? 'h-40 w-40 sm:h-56 sm:w-56 rounded-3xl text-5xl' : 'h-10 w-10 rounded-xl text-sm'
  if (src) return <img src={src} alt={`${p.name}`} className={`${cls} shrink-0 object-cover object-top shadow-lg ring-1 ring-line`} />
  return <div aria-hidden className={`${cls} grid shrink-0 place-items-center font-extrabold text-white shadow-lg`}
    style={{ background: role === 'bat' ? 'linear-gradient(140deg,#13235a,#254aa5)' : 'linear-gradient(140deg,#7a2a7a,#d63384)' }}>{initials(p.name)}</div>
}
function Range({ score, lo, hi, role, min = -30, max = 45 }: { score: number; lo: number; hi: number; role: Role; min?: number; max?: number }) {
  const x = (v: number) => `${((Math.max(min, Math.min(max, v)) - min) / (max - min)) * 100}%`
  const c = role === 'bat' ? 'rgb(var(--bat))' : 'rgb(var(--bowl))'
  return <div className="relative mt-3 h-8" role="img" aria-label={`Rating ${f1(score)}, 80% range ${f0(lo)} to ${f0(hi)}`}>
    <div className="absolute inset-x-0 top-1/2 h-px bg-line" />
    <div className="absolute top-1/2 h-px w-px" style={{ left: x(0) }}><div className="absolute -top-3 h-6 w-px bg-ink2/60" /></div>
    <div className="absolute top-1/2 h-2.5 -translate-y-1/2 rounded-full" style={{ left: x(lo), width: `calc(${x(hi)} - ${x(lo)})`, background: c, opacity: 0.28 }} />
    <div className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-surface" style={{ left: x(score), background: c }} />
    <div className="absolute -bottom-3 text-[10px] text-ink2" style={{ left: x(0) }}>0 = average</div>
  </div>
}

// ---------- player slide ----------
function PlayerSlide({ p, role, rank, prof, photos }: { p: Player; role: Role; rank: number; prof: any; photos: Photos | null }) {
  const r = role === 'bat' ? p.bat! : p.bowl!
  const pr = prof?.[role]
  const car = pr?.all?.career, pres = pr?.pres?.['1'], norm = pr?.pres?.['0']
  const rows: [string, (x: any) => string][] = role === 'bat'
    ? [['Strike rate', x => f1(x?.strike_rate)], ['Average', x => f1(x?.average)], ['Dot-ball %', x => f1(x?.dot_pct)], ['Boundary %', x => f1(x?.boundary_pct)], ['Run value /100', x => f1(x?.run_value_per100)]]
    : [['Economy', x => (x?.economy ?? null) === null ? '–' : Number(x.economy).toFixed(2)], ['Average', x => f1(x?.average)], ['Balls / wicket', x => f1(x?.strike_rate)], ['Dot-ball %', x => f1(x?.dot_pct)], ['Run value /100', x => f1(x?.run_value_per100)]]
  const ph = ['PP', 'Middle', 'Death'].map(k => pr?.phase?.[k]?.run_value_per100 ?? null)
  const moments: string[] = (prof?.moments?.[role] || []).slice(0, 2)
  const notes: any[] = (prof?.notes || []).slice(0, 2)
  const tone = role === 'bat' ? 'text-[rgb(var(--bat))]' : 'text-[rgb(var(--bowl))]'
  const credit = photos?.credits?.[p.id]
  return <div className="grid gap-5 lg:grid-cols-[minmax(0,15rem)_1fr_minmax(0,19rem)] lg:gap-7">
    <div className="flex flex-col items-center gap-3 text-center lg:items-start lg:text-left">
      <div className="relative"><Face p={p} role={role} photos={photos} />
        <div className={`absolute -right-3 -top-3 grid h-12 w-12 place-items-center rounded-full bg-surface text-lg font-extrabold shadow ring-1 ring-line ${tone}`}>#{rank}</div></div>
      <div><h2 className="text-2xl font-extrabold leading-tight sm:text-3xl">{p.name}</h2>
        <div className="text-sm text-ink2">{p.nation}{p.age ? ` · ${p.age} on 1 Apr 2027` : ''} · {p.cap}</div></div>
      <div className="flex flex-wrap justify-center gap-1.5 lg:justify-start">{p.badges.slice(0, 4).map(b => <span key={b} className="chip">{b}</span>)}</div>
      <span className="chip border-good/40 text-good">● {avail(p.status)}</span>
      {credit?.photo ? <div className="text-[10px] leading-snug text-ink2">Photo: {credit.author}, {credit.licence}, via Wikimedia Commons</div> : null}
    </div>
    <div className="min-w-0">
      <Kicker>{role === 'bat' ? 'Batter' : 'Bowler'} #{rank} of 10 · RR can buy</Kicker>
      <div className="mt-2 grid grid-cols-3 gap-2 sm:gap-3">
        <Stat v={<span className={tone}>{f1(r.score)}</span>} l="Pressure Rating (runs / 100 pressure balls)" />
        <Stat v={pct(r.p_top10)} l="P(top 10 in the auction pool)" />
        <Stat v={f0(r.pressure_balls)} l="pressure balls in the data" />
      </div>
      <div className="mt-3 card p-3 sm:p-4"><div className="text-xs text-ink2">80% range of the rating: <b className="text-ink">{f0(r.lo)} to {f0(r.hi)}</b></div><Range score={r.score} lo={r.lo} hi={r.hi} role={role} /><div className="h-3" /></div>
      <div className="mt-3 overflow-x-auto"><table className="tbl w-full text-sm">
        <thead><tr><th></th><th className="text-right">Pressure balls</th><th className="text-right">Normal balls</th><th className="hidden text-right sm:table-cell">Career</th></tr></thead>
        <tbody>{rows.map(([k, g]) => <tr key={k}><td className="text-ink2">{k}</td><td className="num text-right font-semibold">{g(pres)}</td><td className="num text-right">{g(norm)}</td><td className="num hidden text-right sm:table-cell">{g(car)}</td></tr>)}</tbody></table></div>
      <div className="mt-3"><div className="text-xs font-semibold text-ink2">Run value per 100 balls by phase {role === 'bowl' ? '(runs saved + wickets)' : ''}</div>
        <Chart label={`${p.name} run value by phase`} height={120} option={(t: any) => ({ grid: { left: 8, right: 24, top: 6, bottom: 4, containLabel: true }, legend: { show: false },
          xAxis: { type: 'value', ...axis(t) }, yAxis: { type: 'category', data: ['Powerplay', 'Middle', 'Death'], ...axis(t, { splitLine: { show: false } }) },
          series: [{ type: 'bar', data: ph.map(v => v === null ? null : Math.round(v * 10) / 10), barWidth: 12, itemStyle: { color: role === 'bat' ? t.bat : t.bowl, borderRadius: 4 },
            label: { show: true, position: 'right', color: t.ink2, fontSize: 11 } }] })} /></div>
    </div>
    <div className="space-y-3">
      <div className="card p-3 sm:p-4"><div className="text-xs font-bold uppercase tracking-wide text-royal">Data · biggest pressure moments</div>
        <ul className="mt-2 space-y-2 text-sm">{moments.length ? moments.map(m => <li key={m} className="leading-snug">{m}</li>) : <li className="text-ink2">No standout match in the data.</li>}</ul></div>
      {p.verdict ? <div className="card p-3 sm:p-4"><div className="text-xs font-bold uppercase tracking-wide text-royal">Selector verdict</div>
        <div className="mt-1 text-lg font-bold">{p.verdict.verdict}</div><div className="text-sm text-ink2">Risks: {p.verdict.risks}</div>
        {p.verdict.alternative ? <div className="text-sm text-ink2">If outbid: {p.verdict.alternative}</div> : null}</div> : null}
      <div className="card p-3 sm:p-4"><div className="text-xs font-bold uppercase tracking-wide text-royal">Auction</div>
        <div className="mt-1 text-sm">{p.price.known && p.price.mid ? <>Estimated price <b>₹{f1(p.price.mid)} cr</b> <span className="text-ink2">(range ₹{f1(p.price.lo)}–{f1(p.price.hi)} cr)</span></> : 'No auction price history – no estimate shown.'}</div>
        {p.price.last ? <div className="text-xs text-ink2">Last IPL fee ₹{f1(p.price.last)} cr ({p.price.last_year})</div> : null}</div>
      {notes.length ? <div className="rounded-2xl border border-dashed border-warn/50 p-3 sm:p-4"><div className="text-xs font-bold uppercase tracking-wide text-warn">Opinion / reporting – never changes the rating</div>
        <ul className="mt-1 space-y-1.5 text-xs leading-snug">{notes.map((n, i) => <li key={i}>{n.note} <span className="text-ink2">({n.source})</span></li>)}</ul></div> : null}
    </div>
  </div>
}

function ListSlide({ ids, role, players, photos }: { ids: string[]; role: Role; players: Record<string, Player>; photos: Photos | null }) {
  return <div className="grid gap-2 sm:grid-cols-2">{ids.map((id, i) => { const p = players[id]; const r = role === 'bat' ? p.bat! : p.bowl!
    return <div key={id} className="card flex items-center gap-3 p-2.5 sm:p-3">
      <div className="w-6 text-right text-lg font-extrabold text-ink2">{i + 1}</div><Face p={p} role={role} photos={photos} size="sm" />
      <div className="min-w-0 flex-1"><div className="truncate font-bold">{p.name}</div><div className="truncate text-xs text-ink2">{p.nation} · {avail(p.status)}</div></div>
      <div className="text-right"><div className={`num text-lg font-extrabold ${role === 'bat' ? 'text-[rgb(var(--bat))]' : 'text-[rgb(var(--bowl))]'}`}>{f1(r.score)}</div>
        <div className="num text-[11px] text-ink2">P(top 10) {pct(r.p_top10)}</div></div></div> })}</div>
}

// ---------- the deck ----------
export default function Deck() {
  const { meta, players, rankings, strategy, method } = useData()
  const profiles = useProfiles()
  const [photos, setPhotos] = useState<Photos | null>(null)
  useEffect(() => { json<Photos>('photos.json').then(setPhotos).catch(() => setPhotos({ photos: {}, credits: {} })) }, [])
  const top = (r: Role) => (rankings.lists[r].buy as string[]).slice(0, 10)
  const cal = method.calibration
  const lev = method.leverage

  const slides: Slide[] = useMemo(() => {
    const S: Slide[] = []
    S.push({ id: 'title', group: 'Intro', title: 'Title', body:
      <div className="flex min-h-[60vh] flex-col justify-between gap-8 rounded-3xl p-6 text-white sm:p-12" style={{ background: 'linear-gradient(150deg,#13235a 0%,#254aa5 55%,#7a2a7a 100%)' }}>
        <div><div className="text-xs font-semibold uppercase tracking-[0.25em] text-[#ffb8da]">SupeRR Selector Season 2 · Round 1 · Rajasthan Royals × Unstop</div>
          <h1 className="mt-4 max-w-4xl text-3xl font-extrabold leading-[1.08] tracking-tight sm:text-6xl">The most reliable players under pressure – and whom RR should back at the IPL 2027 auction</h1>
          <p className="mt-4 max-w-2xl text-base text-[#e6e9f7] sm:text-lg">A data-driven pressure rating, validated on seasons the models never saw, turned into an auction shortlist after the 17 Nov 2026 retentions.</p></div>
        <div className="flex flex-wrap items-end justify-between gap-4 border-t border-white/30 pt-5">
          <div><div className="text-[11px] uppercase tracking-[0.2em] text-[#ffb8da]">Presented by</div><div className="text-2xl font-bold">{AUTHOR.name}</div>
            <div className="text-sm text-[#e6e9f7]">{AUTHOR.email} · {AUTHOR.github}</div></div>
          <div className="text-sm text-[#e6e9f7]">Use ← → or swipe · G for overview</div></div></div> })
    S.push({ id: 'brief', group: 'Intro', title: 'The brief', body: <>
      <H k="The brief and our answer" t="Who performs when the match is on the line?" sub="Identify the most reliable players under pressure whom Rajasthan Royals should back at the IPL 2027 auction – two ordered top-10 lists with a methodology." />
      <div className="grid gap-3 sm:grid-cols-4"><Stat v="1.67 M" l={`deliveries modelled (${meta.counts.competitions} competitions, ${meta.counts.seasons})`} /><Stat v={meta.counts.players} l="player profiles" /><Stat v="4" l="unseen test seasons" /><Stat v="20" l="auction picks (10 bat, 10 bowl)" /></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="card p-4"><Kicker>Pressure ball</Kicker><p className="mt-1 text-sm">{meta.pressure_definition}</p></div>
        <div className="card p-4"><Kicker>Pressure Rating</Kicker><p className="mt-1 text-sm">{meta.score_definition}</p></div>
        <div className="card p-4"><Kicker>Only players RR can buy</Kicker><p className="mt-1 text-sm">Released on 17 Nov 2026 or not on any IPL roster – none retained by another team, none already at RR.</p></div></div></> })
    S.push({ id: 'findings', group: 'Intro', title: 'Three findings', body: <>
      <H k="What the data says" t="Three findings that shaped the answer" />
      <div className="grid gap-4 sm:grid-cols-3">{meta.findings.map((f: any, i: number) => <div key={i} className="card border-l-4 border-l-pink p-5">
        <div className="text-4xl font-extrabold text-pink/70">0{i + 1}</div><div className="mt-2 text-lg font-bold leading-snug">{f.title}</div><p className="mt-2 text-sm text-ink2">{f.text}</p></div>)}</div>
      <p className="mt-4 text-sm text-ink2">{meta.certainty}</p></> })
    S.push({ id: 'pressure', group: 'Method', title: 'Defining pressure', body: <>
      <H k="1 · Pressure definition" t="Pressure = balls where the next delivery can swing the match" sub="Leverage = expected change in win probability from the next ball, averaged over its possible outcomes. Top 25% of balls = pressure. Seven definitions compared; leverage captured about twice as much match swing per ball as chance." />
      <div className="card p-3"><Chart label="Leverage by over" height={300} option={(t: any) => ({ xAxis: { type: 'category', data: lev.overs, name: 'Over', nameLocation: 'middle', nameGap: 26, ...axis(t) },
        yAxis: { type: 'value', name: 'Leverage (1 = average ball)', ...axis(t) }, tooltip: { trigger: 'axis' },
        series: [{ name: 'Setting a total', type: 'line', data: lev.setting, smooth: true, symbolSize: 6, lineStyle: { width: 3, color: t.bat }, itemStyle: { color: t.bat } },
          { name: 'Chasing', type: 'line', data: lev.chasing, smooth: true, symbolSize: 6, lineStyle: { width: 3, color: t.bowl }, itemStyle: { color: t.bowl },
            markLine: { silent: true, symbol: 'none', data: [{ yAxis: 1 }], lineStyle: { color: t.ink2, type: 'dashed' }, label: { formatter: 'average ball', color: t.ink2 } } }] })} /></div></> })
    S.push({ id: 'measure', group: 'Method', title: 'Measuring fairly', body: <>
      <H k="2 · Performance measurement & fair comparisons" t="Run value: what a player adds beyond what the situation predicts" />
      <div className="card bg-page p-4 text-center font-serif text-base sm:text-xl">RV = (runs − E[runs | situation]) − {meta.kw?.toFixed?.(1) ?? '5.6'} × (out − P(out | situation))</div>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <div className="card p-3"><div className="px-1 text-sm font-semibold">League strength vs IPL (runs per 100 balls; left = weaker)</div>
          <Chart label="League strength" height={300} option={(t: any) => { const L = [...method.league].filter((x: any) => x.comp !== 'IPL').sort((a: any, b: any) => b.batters_runs_vs_IPL_per100 - a.batters_runs_vs_IPL_per100)
            return { grid: { left: 8, right: 16, top: 8, bottom: 30, containLabel: true }, tooltip: { trigger: 'axis' }, xAxis: { type: 'value', ...axis(t) }, yAxis: { type: 'category', inverse: true, data: L.map((x: any) => x.comp), ...axis(t, { splitLine: { show: false } }) },
              series: [{ name: 'Batters', type: 'bar', data: L.map((x: any) => +x.batters_runs_vs_IPL_per100.toFixed(1)), itemStyle: { color: t.bat } },
                { name: 'Bowlers', type: 'bar', data: L.map((x: any) => +x.bowlers_runs_saved_vs_IPL_per100.toFixed(1)), itemStyle: { color: t.bowl } }] } }} /></div>
        <div className="space-y-3 text-sm">
          <div className="card p-4"><b>Situation-only expectations.</b> Expected runs and wicket chance come from a model of the situation only – no player information – so openers aren't flattered by the powerplay and finishers aren't punished for facing yorkers.</div>
          <div className="card p-4"><b>Fair across leagues, venues, opponents, eras.</b> A ridge model of 1.6 M deliveries separates player skill from league, venue and opponent effects, linked by players who appear in several competitions.</div>
          <div className="card p-4"><b>Small samples.</b> A hierarchical Bayesian model pulls thin records toward the average; eligibility needs ≥150 pressure balls and an appearance in 2025 or later.</div></div></div></> })
    S.push({ id: 'models', group: 'Method', title: 'Models & training', body: <>
      <H k="3 · Models and training logic" t="Four models – each kept only if it won on unseen seasons" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[
        ['Win probability', 'Logistic regression', 'Beat 4 tree/boosting families on next-season log-loss; trees over-fit match features.'],
        ['Expected outcomes', 'Gradient boosting + 7-class model', 'Expected runs, dismissal chance and the outcome mix that drives leverage. Situation only.'],
        ['League & venue strength', 'Sparse ridge regression', 'Replaces hand-set opposition tiers; 60 match bootstraps for standard errors.'],
        ['Player rating', 'Hierarchical Bayes (NumPyro, NUTS)', `θᵢ ~ N(a + b·priorᵢ, σθ); intervals calibrated out-of-time (×${cal.bat.widen} / ×${cal.bowl.widen}).`]].map(([a, b, c]) =>
        <div key={a} className="card p-4"><div className="text-lg font-bold">{a}</div><div className="text-sm font-semibold text-royal">{b}</div><p className="mt-2 text-sm text-ink2">{c}</p></div>)}</div>
      <div className="mt-5 card p-4"><div className="mb-2 text-sm font-semibold">No leakage: train on earlier seasons, test on the next one</div>
        <div className="space-y-1.5">{[2023, 2024, 2025, 2026].map(test => <div key={test} className="grid grid-cols-[7rem_repeat(8,1fr)] items-center gap-1 text-[11px]">
          <div className="text-ink2">test {test}</div>{[2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026].map(y => <div key={y}
            className={`rounded py-1 text-center ${y < test ? 'bg-royal text-white' : y === test ? 'bg-pink text-white' : 'bg-line text-ink2'}`}>{y}</div>)}</div>)}</div></div></> })
    S.push({ id: 'backtest', group: 'Method', title: 'Backtest', body: <>
      <H k="4 · Reliability" t="Tested on seasons the models never saw" sub="Correlation with the NEXT season's pressure performance. The obvious hand-weighted formula fails; fair overall skill wins; the 'clutch gap' makes predictions worse." />
      <div className="grid gap-4 lg:grid-cols-2">{(['bat', 'bowl'] as Role[]).map(r => { const rows = [...method.skill[r]].sort((a: any, b: any) => a.wcorr - b.wcorr)
        return <div key={r} className="card p-3"><div className="px-1 text-sm font-semibold">{r === 'bat' ? 'Batters' : 'Bowlers'} · best possible r ≈ {rows[0].noise_ceiling_r.toFixed(2)}</div>
          <Chart label={`${r} backtest`} height={300} option={(t: any) => ({ grid: { left: 8, right: 30, top: 8, bottom: 8, containLabel: true }, legend: { show: false },
            xAxis: { type: 'value', ...axis(t) }, yAxis: { type: 'category', data: rows.map((x: any) => MODEL[x.model] || x.model), ...axis(t, { splitLine: { show: false } }) },
            series: [{ type: 'bar', data: rows.map((x: any) => ({ value: +x.wcorr.toFixed(3), itemStyle: { color: x.model === 'M8_bayes' ? t.good : x.wcorr < 0 ? t.risk : alpha(t.ink2, 0.5), borderRadius: 3 } })),
              label: { show: true, position: 'right', color: t.ink2, fontSize: 11 } }] })} /></div> })}</div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2"><Stat v={`${pct(cal.bat.coverage_before)} → ${pct(cal.bat.coverage_after)}`} l="batters: share of outcomes inside the 80% range, before → after calibration" />
        <Stat v={`${pct(cal.bowl.coverage_before)} → ${pct(cal.bowl.coverage_after)}`} l="bowlers: same check – the ranges are honest" /></div></> })
    for (const role of ['bat', 'bowl'] as Role[]) {
      const ids = top(role)
      S.push({ id: `${role}-list`, group: role === 'bat' ? 'Batters' : 'Bowlers', title: `Top 10 ${role === 'bat' ? 'batters' : 'bowlers'}`, body: <>
        <H k={`The answer · ${role === 'bat' ? 'batters' : 'bowlers'}`} t={`Top 10 ${role === 'bat' ? 'batters' : 'bowlers'} RR should back at the 2027 auction`} sub="Pressure Rating (runs per 100 pressure balls vs expectation) and the chance of being a genuine top-10 player within the auction pool. Beyond the top two or three, ranks are near-ties – role, price and fitness decide." />
        <ListSlide ids={ids} role={role} players={players} photos={photos} /></> })
      ids.forEach((id, i) => S.push({ id: `${role}-${i + 1}`, group: role === 'bat' ? 'Batters' : 'Bowlers', title: players[id].name,
        body: <PlayerSlide p={players[id]} role={role} rank={i + 1} prof={profiles?.[id]} photos={photos} /> }))
    }
    S.push({ id: 'rr', group: 'RR plan', title: 'RR after retentions', body: <>
      <H k="For Rajasthan Royals" t="Where RR is exposed after the 17 Nov retentions" />
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="card p-3"><div className="px-1 text-sm font-semibold">RR's best retained player vs league benchmark, per role</div>
          <Chart label="RR role gaps" height={330} option={(t: any) => { const G = [...strategy.gaps].sort((a: any, b: any) => a.gap - b.gap)
            return { grid: { left: 20, right: 16, top: 8, bottom: 30, containLabel: true }, tooltip: { trigger: 'axis' }, xAxis: { type: 'value', ...axis(t) },
              yAxis: { type: 'category', data: G.map((x: any) => x.slot.replace('Left-handed', 'LH')), ...axis(t, { splitLine: { show: false } }) },
              series: [{ name: 'League benchmark', type: 'bar', data: G.map((x: any) => +x.benchmark_top10_median.toFixed(1)), itemStyle: { color: alpha(t.ink2, 0.35) } },
                { name: 'RR best retained', type: 'bar', data: G.map((x: any) => ({ value: +(x.rr_best_score ?? 0).toFixed(1), itemStyle: { color: x.gap > 3 ? t.risk : t.bat } })) }] } }} /></div>
        <div className="space-y-3">{(() => { const rr = strategy.teams.find((x: any) => x.team === 'Rajasthan Royals')
          return <div className="grid grid-cols-3 gap-2"><Stat v={`₹${rr.purse_cr}`} l="crore purse left" /><Stat v={rr.slots_left} l="slots" /><Stat v={rr.overseas_slots_left} l="overseas slots" /></div> })()}
          <div className="card p-4 text-sm">RR kept {strategy.squad.length} players. The <b>middle order (4–5)</b> is now the biggest gap, then <b>middle-overs spin</b>; opening is RR's strength ({strategy.gaps.find((g: any) => g.slot === 'Opener')?.rr_best}).</div>
          <div className="card overflow-hidden"><table className="tbl w-full text-sm"><thead><tr><th>Team</th><th className="text-right">Purse ₹cr</th><th className="text-right">Slots</th></tr></thead>
            <tbody>{[...strategy.teams].sort((a: any, b: any) => b.purse_cr - a.purse_cr).slice(0, 6).map((x: any) => <tr key={x.team} className={x.team === 'Rajasthan Royals' ? 'bg-pink/10 font-semibold' : ''}>
              <td>{x.team}</td><td className="num text-right">{Number(x.purse_cr).toFixed(2)}</td><td className="num text-right">{x.slots_left}</td></tr>)}</tbody></table></div></div></div></> })
    S.push({ id: 'plan', group: 'RR plan', title: 'Auction plan', body: <>
      <H k="Auction plan" t="Plan A / B / C for the biggest gaps – auction-pool players only" />
      <div className="overflow-x-auto card"><table className="tbl w-full text-sm"><thead><tr><th>Role (gap)</th><th>Plan A</th><th>Plan B</th><th>Plan C</th><th>Value pick</th></tr></thead>
        <tbody>{[...strategy.gaps].sort((a: any, b: any) => b.gap - a.gap).slice(0, 5).map((g: any) => { const by = (pl: string) => strategy.plans.find((x: any) => x.slot === g.slot && x.plan === pl)
          return <tr key={g.slot}><td><b>{g.slot}</b><div className="text-xs text-ink2">gap {f1(g.gap)}</div></td>{['A', 'B', 'C', 'Value'].map(pl => { const x = by(pl)
            return <td key={pl}>{x ? <><b>{x.name}</b> <span className="num text-xs text-ink2">{f1(x.score)}</span><div className="text-[11px] text-ink2">{avail(x.status)}</div></> : '–'}</td> })}</tr> })}</tbody></table></div>
      <p className="mt-3 text-sm text-ink2">Plans use only players in the auction pool; the value pick is the best option at an estimated ≤ ₹3 cr.</p></> })
    S.push({ id: 'pool', group: 'RR plan', title: 'Auction pool', body: <>
      <H k="The IPL 2027 auction pool" t="Beyond the top 10: next best available, and youngsters" />
      <div className="grid gap-4 lg:grid-cols-3">{(['bat', 'bowl'] as Role[]).map(r => <div key={r} className="card overflow-hidden"><div className="px-3 pt-3 text-sm font-semibold">Next best {r === 'bat' ? 'batters' : 'bowlers'} (not in our top 10)</div>
        <table className="tbl w-full text-sm"><tbody>{strategy.pool[r].filter((x: any) => !top(r).some(id => players[id].name === x.name)).slice(0, 8).map((x: any) => <tr key={x.name}><td className="num text-ink2">#{x.pool_rank}</td><td><b>{x.name}</b> <span className="text-xs text-ink2">{x.tier === 'emerging' ? 'emerging' : ''}</span></td><td className="num text-right">{f1(x.rating)}</td></tr>)}</tbody></table></div>)}
        <div className="card overflow-hidden"><div className="px-3 pt-3 text-sm font-semibold">Youngsters in the pool (≤23)</div>
          <table className="tbl w-full text-sm"><tbody>{[...strategy.youth_pool.bat.slice(0, 4), ...strategy.youth_pool.bowl.slice(0, 4)].map((x: any) => <tr key={x.name}><td><b>{x.name}</b> <span className="text-xs text-ink2">{x.age}</span></td><td className="text-xs">{x.label}</td></tr>)}</tbody></table>
          <p className="p-3 text-xs text-ink2"># = rank in the whole auction pool, including emerging players (40–149 pressure balls, wider ranges). Development projections on a different scale; small samples – a watch list, not a ranking. Minors: cricket data and age only.</p></div></div></> })
    S.push({ id: 'future', group: 'Close', title: 'Future scope', body: <>
      <H k="Future scope" t="From analysis to a live auction tool" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{[
        ['RR Pressure Scout app', 'Upload any new data pack; columns mapped, validated and de-duplicated; identities checked, never merged silently.'],
        ['Refresh or retrain', 'A retrained model replaces the current one only if it is at least as good on unseen seasons; drift checks and a model registry.'],
        ['Auction optimiser', 'Best set of targets within purse, slot and overseas limits, with max bids and plan A/B/C per role.'],
        ['Live auction mode', 'Enter each lot; purses and slots of all 10 teams update and RR\'s targets re-optimise instantly.'],
        ['Better price model', 'Train on the official auction register (base price, set), with price ranges backtested on past auctions.'],
        ['Richer data', 'Fielding, ball-tracking and pitch data; U19 and state-league scorecards to firm up the youth board.']].map(([a, b]) =>
        <div key={a} className="card p-4"><div className="font-bold">{a}</div><p className="mt-1 text-sm text-ink2">{b}</p></div>)}</div></> })
    S.push({ id: 'close', group: 'Close', title: 'Thank you', body:
      <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <div className="flex flex-col justify-between gap-6 rounded-3xl p-6 text-white sm:p-10" style={{ background: 'linear-gradient(150deg,#13235a 0%,#254aa5 55%,#7a2a7a 100%)' }}>
          <div><div className="text-xs uppercase tracking-[0.25em] text-[#ffb8da]">Thank you</div><h2 className="mt-3 text-3xl font-extrabold sm:text-5xl">Questions welcome</h2>
            <p className="mt-3 text-[#e6e9f7]">Happy to walk the selection panel through the model, the website or any player in detail.</p></div>
          <div><div className="text-2xl font-bold">{AUTHOR.name}</div><div className="text-[#e6e9f7]">{AUTHOR.email}</div><div className="text-[#e6e9f7]">{AUTHOR.github}</div></div></div>
        <div className="card p-4 text-xs leading-relaxed text-ink2"><div className="mb-2 text-sm font-bold text-ink">Sources and photo credits</div>
          <p>Ratings: RR/Unstop data pack (aggregates only); Cricsheet (ODC-By); Wikipedia (CC BY-SA) auction prices; Wikidata (CC0) ages; IPL 2027 retention lists (17 Nov 2026).</p>
          <p className="mt-2">Photos from Wikimedia Commons under free licences (players without a freely licensed photo are shown with initials):</p>
          <ul className="mt-1 space-y-0.5">{photos ? Object.values(photos.credits).filter((c: any) => c.photo).map((c: any) =>
            <li key={c.name}>{c.name}: <a className="underline" href={c.page} target="_blank" rel="noreferrer">{c.author}</a>, {c.licence}</li>) : <li>loading…</li>}</ul>
          <p className="mt-3"><Link className="text-royal underline" to="/">Open the full evaluator site</Link> · <Link className="text-royal underline" to="/report">Report (PDF)</Link></p></div></div> })
    return S
  }, [meta, players, rankings, strategy, method, profiles, photos])

  const [sp, setSp] = useSearchParams()
  const n = slides.length
  const i = Math.min(n - 1, Math.max(0, (Number(sp.get('s')) || 1) - 1))
  const go = useCallback((k: number) => setSp({ s: String(Math.min(n, Math.max(1, k + 1))) }, { replace: true }), [n, setSp])
  const [grid, setGrid] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return
      if (['ArrowRight', 'PageDown', ' '].includes(e.key)) { e.preventDefault(); go(i + 1) }
      else if (['ArrowLeft', 'PageUp'].includes(e.key)) { e.preventDefault(); go(i - 1) }
      else if (e.key === 'Home') go(0); else if (e.key === 'End') go(n - 1)
      else if (e.key.toLowerCase() === 'g') setGrid(g => !g)
      else if (e.key === 'Escape') setGrid(false)
      else if (e.key.toLowerCase() === 'f') document.fullscreenElement ? document.exitFullscreen() : box.current?.requestFullscreen?.()
    }
    window.addEventListener('keydown', h); return () => window.removeEventListener('keydown', h)
  }, [i, n, go])
  const touch = useRef<number | null>(null)
  useEffect(() => { box.current?.querySelector('main')?.scrollTo({ top: 0 }) }, [i])
  const s = slides[i]

  return <div ref={box} className="fixed inset-0 z-30 flex flex-col bg-page text-ink"
    onTouchStart={e => { touch.current = e.touches[0].clientX }}
    onTouchEnd={e => { if (touch.current === null) return; const dx = e.changedTouches[0].clientX - touch.current; if (Math.abs(dx) > 60) go(dx < 0 ? i + 1 : i - 1); touch.current = null }}>
    <div className="h-1 w-full bg-line"><div className="h-1 bg-gradient-to-r from-royal to-pink transition-all" style={{ width: `${((i + 1) / n) * 100}%` }} /></div>
    <div className="flex items-center justify-between gap-2 border-b border-line px-3 py-2 text-xs text-ink2 sm:px-6">
      <Link to="/" className="font-bold text-royal">PRESSURE SCOUT</Link>
      <div className="truncate">{s.group} · {s.title}</div>
      <div className="flex items-center gap-1">
        <button className="btn-ghost !px-2 !py-1" onClick={() => setGrid(g => !g)} aria-label="Slide overview (G)"><Grid3x3 size={16} /></button>
        <button className="btn-ghost hidden !px-2 !py-1 sm:inline-flex" onClick={() => document.fullscreenElement ? document.exitFullscreen() : box.current?.requestFullscreen?.()} aria-label="Full screen (F)"><Maximize2 size={16} /></button></div></div>
    <main className="flex-1 overflow-y-auto" aria-live="polite">
      <div key={s.id} className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-8 sm:py-8 animate-[fadein_.25s_ease-out]">{s.body}</div></main>
    <div className="flex items-center justify-between gap-3 border-t border-line px-3 py-2 sm:px-6">
      <button className="btn-ghost" onClick={() => go(i - 1)} disabled={i === 0} aria-label="Previous slide"><ChevronLeft size={18} /><span className="hidden sm:inline">Previous</span></button>
      <div className="num text-sm text-ink2">{i + 1} / {n}</div>
      <button className="btn-primary" onClick={() => go(i + 1)} disabled={i === n - 1} aria-label="Next slide"><span className="hidden sm:inline">Next</span><ChevronRight size={18} /></button></div>
    {grid ? <div className="absolute inset-0 z-40 overflow-y-auto bg-page/95 p-4 backdrop-blur sm:p-8" role="dialog" aria-label="Slide overview">
      <div className="mb-4 flex items-center justify-between"><div className="text-lg font-bold">All slides</div><button className="btn-ghost" onClick={() => setGrid(false)} aria-label="Close overview"><X size={16} /></button></div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">{slides.map((x, k) => <button key={x.id} onClick={() => { go(k); setGrid(false) }}
        className={`card p-3 text-left transition hover:border-royal ${k === i ? 'border-royal ring-2 ring-royal/30' : ''}`}>
        <div className="text-[10px] uppercase tracking-wide text-pink">{k + 1} · {x.group}</div><div className="mt-1 truncate text-sm font-semibold">{x.title}</div></button>)}</div></div> : null}
  </div>
}

