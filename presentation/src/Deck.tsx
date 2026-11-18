// RR Pressure Scout – interactive presentation. Fixed 1600×900 canvas scaled to the screen, like a slide deck.
// Keys: ← → Space PgUp PgDn Home End · G overview · F full screen. Click the right/left edge or swipe to move.
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import ReactECharts from 'echarts-for-react'
import { ChevronLeft, ChevronRight, LayoutGrid, Maximize2, X } from 'lucide-react'
import DATA from '../private_data/deck.json'

const W = 1600, H = 900
const C = { pink: '#E5197E', pinkSoft: '#FDE7F2', blue: '#1E3FA0', blueSoft: '#E8EDFA', navy: '#0A1B4D', ink: '#121530', mute: '#5B6079', line: '#E6E8F0', green: '#12805C', red: '#C8323C' }
const AUTHOR = { name: 'Tanay Patil', email: 'tanaypatil0530@gmail.com', github: 'github.com/tanaygit0530' }
type Role = 'bat' | 'bowl'
const f1 = (x: any) => (x === null || x === undefined || Number.isNaN(+x) ? '–' : (+x).toFixed(1))
const f0 = (x: any) => (x === null || x === undefined || Number.isNaN(+x) ? '–' : Math.round(+x).toLocaleString('en-IN'))
const pct = (x: any) => (x === null || x === undefined ? '–' : `${Math.round(+x * 100)}%`)
const ini = (n: string) => n.split(/\s+/).slice(0, 2).map(s => s[0]).join('').toUpperCase()
const avail = (s: string | null) => (s || '').startsWith('Open market') ? 'Open market' : (s || '').replace('In auction pool (released by ', 'Released by ').replace(')', '')
const MODEL: Record<string, string> = { M0_raw_pressure: 'Raw pressure record', M1_recency_raw: 'Recent pressure record', M2_baseline: 'Hand-weighted formula (v1)',
  M3_eb_pressure: 'Shrunk pressure record', M4_eb_overall: 'Overall skill (RR data)', M5_eb_overall_plus_gap: 'Overall + "clutch" gap',
  M6_apm: 'Adjusted skill (all leagues)', M7_stack: 'Stacked GBM', M8_bayes: 'Bayesian model (chosen)' }

function EC({ option, h }: { option: any; h: number }) {
  return <ReactECharts option={{ animationDuration: 900, textStyle: { fontFamily: 'Inter', color: C.mute, fontSize: 15 }, ...option }} style={{ height: h, width: '100%' }} notMerge opts={{ renderer: 'svg' }} />
}
const ax = (x: any = {}) => ({ axisLine: { lineStyle: { color: C.line } }, axisLabel: { color: C.mute, fontSize: 15 }, splitLine: { lineStyle: { color: C.line } }, nameTextStyle: { color: C.mute, fontSize: 14 }, ...x })

// ---------- slide chrome ----------
function Frame({ k, t, sub, children, n }: { k: string; t: ReactNode; sub?: ReactNode; children: ReactNode; n: number }) {
  return <div className="relative h-full w-full bg-white px-[88px] pb-[70px] pt-[64px]">
    <div className="absolute left-0 top-0 h-[6px] w-full" style={{ background: C.pink }} />
    <div className="rise text-[18px] font-bold uppercase tracking-[0.22em] text-pink">{k}</div>
    <h2 className="rise mt-2 text-[52px] font-extrabold leading-[1.08] tracking-tight text-blue-deep" style={{ animationDelay: '.05s' }}>{t}</h2>
    {sub ? <p className="rise mt-3 max-w-[1250px] text-[22px] leading-snug text-mute" style={{ animationDelay: '.1s' }}>{sub}</p> : null}
    <div className="rise mt-7" style={{ animationDelay: '.15s' }}>{children}</div>
    <div className="absolute bottom-[26px] left-[88px] right-[88px] flex justify-between text-[14px] text-mute">
      <span><b className="text-blue">PRESSURE SCOUT</b> · SupeRR Selector S2 · Rajasthan Royals</span><span>{AUTHOR.name} · {n}</span></div>
  </div>
}
function Big({ v, l, c = C.blue, d = 0 }: { v: ReactNode; l: string; c?: string; d?: number }) {
  return <div className="card rise p-6" style={{ animationDelay: `${d}s` }}><div className="num font-head text-[54px] font-extrabold leading-none" style={{ color: c }}>{v}</div><div className="mt-2 text-[18px] text-mute">{l}</div></div>
}
function Count({ to, dec = 0, suf = '' }: { to: number; dec?: number; suf?: string }) {
  const [v, setV] = useState(0)
  useEffect(() => { let r = 0; const t0 = performance.now(); const step = (t: number) => { const p = Math.min(1, (t - t0) / 1100); setV(to * (1 - Math.pow(1 - p, 3))); if (p < 1) r = requestAnimationFrame(step) }; r = requestAnimationFrame(step); return () => cancelAnimationFrame(r) }, [to])
  return <>{v.toFixed(dec)}{suf}</>
}
function Face({ id, name, role, photos, size }: { id: string; name: string; role: Role; photos: any; size: number }) {
  const src = photos[id]
  const st = { width: size, height: size, borderRadius: size * 0.22 }
  return src ? <img src={src} alt={name} style={st} className="shrink-0 object-cover object-top shadow-lg" />
    : <div aria-hidden style={{ ...st, fontSize: size * 0.34, background: role === 'bat' ? C.blue : C.pink }} className="grid shrink-0 place-items-center font-head font-extrabold text-white shadow-lg">{ini(name)}</div>
}
function Toggle<T extends string>({ v, set, opts }: { v: T; set: (x: T) => void; opts: [T, string][] }) {
  return <div className="inline-flex gap-1 rounded-full bg-blue-soft p-1" role="tablist">{opts.map(([k, l]) => <button key={k} role="tab" aria-selected={v === k} className={`tab ${v === k ? 'on' : ''}`} onClick={e => { e.stopPropagation(); set(k) }}>{l}</button>)}</div>
}

// ---------- interactive slide bodies ----------
function LeverageSlide({ lev }: { lev: any }) {
  const [m, setM] = useState<'both' | 'setting' | 'chasing'>('both')
  const s = (name: string, data: number[], c: string) => ({ name, type: 'line', data, smooth: true, symbolSize: 9, lineStyle: { width: 5, color: c }, itemStyle: { color: c }, areaStyle: { color: c + '14' } })
  return <div className="grid grid-cols-[1fr_400px] gap-8">
    <div className="card p-5"><div className="mb-2 flex items-center justify-between"><div className="text-[18px] font-semibold">How much the next ball can swing the match, by over</div>
      <Toggle v={m} set={setM} opts={[['both', 'Both'], ['setting', 'Setting'], ['chasing', 'Chasing']]} /></div>
      <EC h={470} option={{ grid: { left: 60, right: 30, top: 50, bottom: 50 }, tooltip: { trigger: 'axis', valueFormatter: (v: number) => `${v.toFixed(2)}× an average ball` },
        legend: { top: 0, right: 10, itemGap: 28, textStyle: { fontSize: 15 } }, xAxis: { type: 'category', data: lev.overs, name: 'Over', nameLocation: 'middle', nameGap: 32, ...ax() }, yAxis: { type: 'value', ...ax() },
        series: [...(m !== 'chasing' ? [s('Setting a total', lev.setting, C.blue)] : []), ...(m !== 'setting' ? [s('Chasing', lev.chasing, C.pink)] : []),
          { type: 'line', data: [], markLine: { silent: true, symbol: 'none', data: [{ yAxis: 1 }], lineStyle: { color: C.mute, type: 'dashed' }, label: { formatter: 'average ball', color: C.mute, fontSize: 14 } } }] }} /></div>
    <div className="flex flex-col gap-4">
      <div className="card p-6"><div className="text-[15px] font-bold uppercase tracking-wider text-pink">Leverage</div><p className="mt-2 text-[19px] leading-snug">Expected change in win probability from the next ball, averaged over its outcomes (0, 1, 2, 3, 4, 6, wicket).</p></div>
      <div className="card p-6"><div className="text-[15px] font-bold uppercase tracking-wider text-pink">Pressure ball</div><p className="mt-2 text-[19px] leading-snug">The top 25% of balls by leverage. A chase's 20th over is <b>3.5×</b> an average ball.</p></div>
      <div className="card bg-blue-soft p-6"><p className="text-[18px] leading-snug">7 definitions compared. Leverage captured <b>≈2×</b> the match swing of a random ball and was kept.</p></div></div></div>
}

function RunValueSlide({ kw }: { kw: number }) {
  const [step, setStep] = useState(0)
  const parts = [['runs', 'What the batter actually scored on the ball', C.blue], ['− E[runs | situation]', 'What an average player scores in exactly this situation (no player info)', C.blue],
    [`− ${kw.toFixed(1)} × (out − P(out))`, 'A wicket costs ≈ 5.6 runs; we charge it relative to the expected dismissal chance', C.pink], ['= run value', 'Positive = added more than the situation predicts. Bowlers: the mirror image.', C.green]]
  return <div>
    <div className="flex items-center justify-center gap-4 rounded-3xl bg-blue-soft px-8 py-10">{parts.map(([t, , c], i) =>
      <button key={i} onClick={e => { e.stopPropagation(); setStep(i) }} className={`rounded-2xl px-6 py-4 font-head text-[38px] font-bold transition ${i <= step ? 'opacity-100' : 'opacity-25'} ${i === step ? 'bg-white shadow-lg' : ''}`} style={{ color: c as string }}>{t}</button>)}</div>
    <div className="mt-6 grid grid-cols-[1fr_1fr] gap-6">
      <div className="card p-8"><div className="text-[15px] font-bold uppercase tracking-wider text-pink">Step {step + 1} of 4 – click the formula</div><p className="mt-3 text-[28px] font-semibold leading-snug text-blue-deep">{parts[step][1]}</p></div>
      <div className="grid grid-cols-1 gap-3 text-[19px]">
        <div className="card p-5">Openers aren't flattered by the powerplay; finishers aren't punished for facing yorkers.</div>
        <div className="card p-5">Averaged over a player's pressure balls → <b>runs added per 100 pressure balls</b>.</div>
        <div className="card p-5">The same scale for batters and bowlers – <b>0 = average</b>.</div></div></div></div>
}

function LeagueSlide({ league }: { league: any[] }) {
  const [r, setR] = useState<Role>('bat')
  const key = r === 'bat' ? 'batters_runs_vs_IPL_per100' : 'bowlers_runs_saved_vs_IPL_per100'
  const L = league.filter(x => x.comp !== 'IPL').sort((a, b) => b[key] - a[key])
  return <div className="grid grid-cols-[1fr_430px] gap-8">
    <div className="card p-5"><div className="mb-1 flex items-center justify-between"><div className="text-[18px] font-semibold">League strength vs IPL (runs per 100 balls; left = weaker)</div>
      <Toggle v={r} set={setR} opts={[['bat', 'Batters'], ['bowl', 'Bowlers']]} /></div>
      <EC h={500} option={{ grid: { left: 150, right: 60, top: 10, bottom: 30 }, tooltip: { trigger: 'axis' }, xAxis: { type: 'value', ...ax() }, yAxis: { type: 'category', inverse: true, data: L.map(x => x.comp), ...ax({ splitLine: { show: false } }) },
        series: [{ type: 'bar', data: L.map(x => +x[key].toFixed(1)), barWidth: 18, itemStyle: { color: r === 'bat' ? C.blue : C.pink, borderRadius: [4, 0, 0, 4] }, label: { show: true, position: 'left', color: C.mute, fontSize: 13 } }] }} /></div>
    <div className="flex flex-col gap-4 text-[19px] leading-snug">
      <div className="card p-6"><b>Measured, not assumed.</b> A ridge model of 1.6 M deliveries separates player skill from league, venue and opponent effects.</div>
      <div className="card p-6"><b>Linked by players</b> who appear in several competitions. Replaces hand-set opposition tiers.</div>
      <div className="card p-6"><b>Small samples</b> are pulled toward the average by a hierarchical Bayesian model. Eligibility: ≥150 pressure balls, active 2025+.</div></div></div>
}

function ModelsSlide({ cal }: { cal: any }) {
  const M = [['Win probability', 'Logistic regression', 'Predicts whether the batting side wins, every ball, both innings.', 'Beat 4 tree/boosting families on next-season log-loss – trees over-fit match-level features, so the simpler model was kept.'],
    ['Expected outcomes', 'Gradient boosting + 7-class model', 'Expected runs, dismissal chance and outcome mix for each situation.', 'Situation only – no player information. The outcome mix feeds the leverage formula.'],
    ['League & venue strength', 'Sparse ridge regression', 'Player, league, venue and opponent effects per ball.', 'Penalty chosen on a 2026 hold-out; 60 match bootstraps give standard errors.'],
    ['Player rating', 'Hierarchical Bayes (NumPyro, NUTS)', 'θᵢ ~ N(a + b·priorᵢ, σθ); ȳᵢ ~ N(θᵢ + δᵢ, σ/√nᵢ)', `Within 1 SE of the best predictor and the only one with honest uncertainty; intervals widened ×${cal.bat.widen} / ×${cal.bowl.widen} after out-of-time checks.`]]
  const [o, setO] = useState(3)
  return <div className="grid grid-cols-[560px_1fr] gap-8">
    <div className="flex flex-col gap-3">{M.map((m, i) => <button key={i} onClick={e => { e.stopPropagation(); setO(i) }}
      className={`card flex items-center gap-5 p-5 text-left transition ${o === i ? 'border-pink ring-4 ring-pink/15' : 'hover:border-blue'}`}>
      <div className={`grid h-14 w-14 shrink-0 place-items-center rounded-2xl font-head text-[24px] font-bold ${o === i ? 'bg-pink text-white' : 'bg-blue-soft text-blue'}`}>{i + 1}</div>
      <div><div className="font-head text-[24px] font-bold text-blue-deep">{m[0]}</div><div className="text-[17px] font-semibold text-pink">{m[1]}</div></div></button>)}</div>
    <div key={o} className="card rise flex flex-col justify-between p-10">
      <div><div className="text-[16px] font-bold uppercase tracking-wider text-pink">Model {o + 1} · {M[o][1]}</div><div className="mt-3 font-head text-[44px] font-extrabold text-blue-deep">{M[o][0]}</div>
        <p className="mt-5 text-[26px] leading-snug">{M[o][2]}</p></div>
      <div className="rounded-2xl bg-white p-6 text-[21px] leading-snug shadow-sm"><b className="text-blue">Why we kept it: </b>{M[o][3]}</div>
      <p className="text-[17px] text-mute">Rule for every model: keep the simpler one unless the complex one wins on seasons it never saw.</p></div></div>
}

function FoldsSlide() {
  const [f, setF] = useState(3); const Y = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
  return <div>
    <div className="card p-8">{[2023, 2024, 2025, 2026].map((t, i) => <button key={t} onClick={e => { e.stopPropagation(); setF(i) }} className={`grid w-full grid-cols-[200px_repeat(8,1fr)] items-center gap-2 rounded-2xl p-2 transition ${f === i ? 'bg-blue-soft' : 'hover:bg-blue-soft/50'}`}>
      <div className="text-left text-[19px] font-semibold text-blue-deep">Fold {i + 1} · test {t}</div>
      {Y.map((y, j) => <div key={y} className="grow rounded-lg py-3 text-center text-[17px] font-semibold" style={{ animationDelay: `${j * 0.04 + i * 0.08}s`, background: y < t ? C.blue : y === t ? C.pink : C.line, color: y <= t ? '#fff' : C.mute }}>{y}</div>)}</button>)}
      <div className="mt-4 flex gap-6 text-[17px] text-mute"><span><span className="mr-2 inline-block h-4 w-4 rounded bg-blue align-middle" />training seasons</span><span><span className="mr-2 inline-block h-4 w-4 rounded bg-pink align-middle" />test season (never seen)</span><span><span className="mr-2 inline-block h-4 w-4 rounded bg-line align-middle" />not used</span></div></div>
    <div className="mt-6 grid grid-cols-3 gap-5 text-[19px] leading-snug">
      <div className="card p-6"><b className="text-pink">Fold {f + 1}:</b> every model is trained on {2019}–{[2022, 2023, 2024, 2025][f]} and scored on {[2023, 2024, 2025, 2026][f]} only.</div>
      <div className="card p-6">Ratings used as features for season c+1 are rebuilt from models trained only on seasons ≤ c – <b>no leakage</b>.</div>
      <div className="card p-6">Fixed seeds, pinned environment, one command per stage: a clean rerun reproduces every list.</div></div></div>
}

function BacktestSlide({ skill, cal }: { skill: any; cal: any }) {
  const [r, setR] = useState<Role>('bat')
  const rows = [...skill[r]].sort((a: any, b: any) => a.wcorr - b.wcorr)
  return <div className="grid grid-cols-[1fr_420px] gap-8">
    <div className="card p-5"><div className="mb-1 flex items-center justify-between"><div className="text-[18px] font-semibold">Correlation with NEXT season's pressure performance · best possible ≈ {rows[0].noise_ceiling_r.toFixed(2)}</div>
      <Toggle v={r} set={setR} opts={[['bat', 'Batters'], ['bowl', 'Bowlers']]} /></div>
      <EC h={500} option={{ grid: { left: 250, right: 70, top: 10, bottom: 30 }, tooltip: { trigger: 'axis' }, xAxis: { type: 'value', ...ax() },
        yAxis: { type: 'category', data: rows.map((x: any) => MODEL[x.model] || x.model), ...ax({ splitLine: { show: false } }) },
        series: [{ type: 'bar', barWidth: 22, data: rows.map((x: any) => ({ value: +x.wcorr.toFixed(3), itemStyle: { color: x.model === 'M8_bayes' ? C.pink : x.wcorr < 0 ? C.red : '#B9BED3', borderRadius: 5 } })),
          label: { show: true, position: 'right', color: C.ink, fontSize: 15 } }] }} /></div>
    <div className="flex flex-col gap-4">
      <Big v={<>{pct(cal[r].coverage_before)} → {pct(cal[r].coverage_after)}</>} l="share of next-season outcomes inside our 80% range, before → after calibration" c={C.pink} />
      <div className="card p-6 text-[19px] leading-snug"><b>The obvious formula fails.</b> A hand-weighted pressure score had no out-of-sample signal.</div>
      <div className="card p-6 text-[19px] leading-snug"><b>"Clutch" doesn't repeat.</b> Adding a player's pressure-minus-normal gap made predictions worse.</div></div></div>
}

function TopTen({ role, D, go, idx }: { role: Role; D: any; go: (k: number) => void; idx: Record<string, number> }) {
  const [by, setBy] = useState<'score' | 'p'>('score')
  const ids: string[] = D.lists[role]
  const rows = ids.map((id, i) => ({ id, rank: i + 1, p: D.players[id], r: D.players[id][role] }))
  const sorted = by === 'score' ? rows : [...rows].sort((a, b) => b.r.p_top10 - a.r.p_top10)
  const c = role === 'bat' ? C.blue : C.pink
  const mx = Math.max(...rows.map(x => by === 'score' ? x.r.score : x.r.p_top10))
  return <div>
    <div className="mb-4 flex items-center justify-between"><div className="text-[18px] text-mute">Click a player to open their slide</div>
      <Toggle v={by} set={setBy} opts={[['score', 'Pressure Rating'], ['p', 'P(top 10)']]} /></div>
    <div className="grid grid-cols-2 gap-x-8 gap-y-3">{sorted.map((x, i) => <button key={x.id} onClick={e => { e.stopPropagation(); go(idx[`${role}-${x.id}`]) }}
      className="card rise flex items-center gap-4 p-3 pr-5 text-left transition hover:-translate-y-0.5 hover:border-pink hover:shadow-xl" style={{ animationDelay: `${i * 0.04}s` }}>
      <div className="w-9 text-right font-head text-[26px] font-extrabold text-mute">{x.rank}</div>
      <Face id={x.id} name={x.p.name} role={role} photos={D.photos} size={64} />
      <div className="min-w-0 flex-1"><div className="truncate font-head text-[22px] font-bold text-blue-deep">{x.p.name}</div>
        <div className="mt-1 h-2.5 w-full overflow-hidden rounded-full bg-line"><div key={by} className="grow h-full rounded-full" style={{ width: `${Math.max(4, ((by === 'score' ? x.r.score : x.r.p_top10) / mx) * 100)}%`, background: c, animationDelay: `${i * 0.05}s` }} /></div>
        <div className="mt-1 truncate text-[15px] text-mute">{x.p.nation} · {avail(x.p.status)}</div></div>
      <div className="text-right"><div className="num font-head text-[30px] font-extrabold" style={{ color: c }}>{by === 'score' ? f1(x.r.score) : pct(x.r.p_top10)}</div>
        <div className="text-[13px] text-mute">{by === 'score' ? `P(top 10) ${pct(x.r.p_top10)}` : `rating ${f1(x.r.score)}`}</div></div></button>)}</div></div>
}

function PlayerSlide({ id, role, rank, D }: { id: string; role: Role; rank: number; D: any }) {
  const p = D.players[id]; const r = p[role]; const pr = D.profiles[id] || {}; const st = pr[role] || {}
  const [tab, setTab] = useState<'pres' | 'phase' | 'moments'>('pres')
  const c = role === 'bat' ? C.blue : C.pink
  const pres = st.pres?.['1'], norm = st.pres?.['0'], car = st.all?.career
  const rows: [string, (x: any) => string, boolean][] = role === 'bat'
    ? [['Strike rate', x => f1(x?.strike_rate), true], ['Average', x => f1(x?.average), true], ['Dot-ball %', x => f1(x?.dot_pct), false], ['Boundary %', x => f1(x?.boundary_pct), true], ['Run value / 100 balls', x => f1(x?.run_value_per100), true]]
    : [['Economy', x => (x?.economy == null ? '–' : (+x.economy).toFixed(2)), false], ['Average', x => f1(x?.average), false], ['Balls per wicket', x => f1(x?.strike_rate), false], ['Dot-ball %', x => f1(x?.dot_pct), true], ['Run value / 100 balls', x => f1(x?.run_value_per100), true]]
  const ph = ['PP', 'Middle', 'Death'].map(k => st.phase?.[k]?.run_value_per100 ?? null)
  const min = -30, max = 45, X = (v: number) => `${((Math.max(min, Math.min(max, v)) - min) / (max - min)) * 100}%`
  const cr = D.credits[id]
  return <div className="relative h-full w-full overflow-hidden bg-white">
    <div className="absolute inset-y-0 left-0 w-[520px]" style={{ background: role === 'bat' ? C.navy : '#9E1458' }} />
    <div className="absolute left-0 top-0 h-[6px] w-full" style={{ background: C.pink }} />
    <div className="absolute left-[64px] top-[70px] w-[392px] text-white">
      <div className="rise text-[17px] font-bold uppercase tracking-[0.2em] text-white/75">{role === 'bat' ? 'Batter' : 'Bowler'} · RR can buy</div>
      <div className="rise mt-1 font-head text-[120px] font-extrabold leading-none text-white/95">#{rank}</div>
      <div className="rise mt-4" style={{ animationDelay: '.08s' }}><Face id={id} name={p.name} role={role} photos={D.photos} size={260} /></div>
      <h2 className="rise mt-6 text-[42px] font-extrabold leading-[1.05]" style={{ animationDelay: '.12s' }}>{p.name}</h2>
      <div className="mt-2 text-[19px] text-white/85">{p.nation}{p.age ? ` · ${p.age} on 1 Apr 2027` : ''}</div>
      <div className="mt-4 flex flex-wrap gap-2">{p.badges.slice(0, 3).map((b: string) => <span key={b} className="pill bg-white/15 text-white">{b}</span>)}</div>
      <div className="mt-3"><span className="pill bg-white text-blue-deep">● {avail(p.status)}{p.status?.startsWith('Open') ? ' – must register' : ''}</span></div>
      {cr ? <div className="mt-4 text-[12px] leading-snug text-white/70">Photo: {cr.author}, {cr.licence}, Wikimedia Commons</div> : null}</div>
    <div className="absolute bottom-[70px] left-[580px] right-[64px] top-[70px] flex flex-col">
      <div className="grid grid-cols-3 gap-4">
        <Big v={<Count to={r.score} dec={1} />} l="Pressure Rating (runs per 100 pressure balls vs expectation)" c={c} />
        <Big v={<Count to={Math.round(r.p_top10 * 100)} suf="%" />} l="chance of a genuine top-10 place in the auction pool" c={C.navy} d={0.05} />
        <Big v={<Count to={r.pressure_balls} />} l="pressure balls in the data" c={C.navy} d={0.1} /></div>
      <div className="card mt-4 px-7 py-5"><div className="flex justify-between text-[17px]"><span className="text-mute">80% range of the rating</span><b>{f0(r.lo)} to {f0(r.hi)}</b></div>
        <div className="relative mt-4 h-8"><div className="absolute inset-x-0 top-1/2 h-[2px] bg-line" /><div className="absolute top-0 h-8 w-[2px] bg-mute/50" style={{ left: X(0) }} />
          <div className="grow absolute top-1/2 h-4 -translate-y-1/2 rounded-full" style={{ left: X(r.lo), width: `calc(${X(r.hi)} - ${X(r.lo)})`, background: c, opacity: 0.25 }} />
          <div className="absolute top-1/2 h-6 w-6 -translate-x-1/2 -translate-y-1/2 rounded-full border-4 border-white shadow" style={{ left: X(r.score), background: c }} /></div>
        <div className="relative h-4 text-[13px] text-mute"><span className="absolute -translate-x-1/2" style={{ left: X(0) }}>0 = average</span></div></div>
      <div className="mt-5 flex items-center justify-between"><Toggle v={tab} set={setTab} opts={[['pres', 'Pressure vs normal'], ['phase', 'By phase'], ['moments', 'Moments & verdict']]} /></div>
      <div key={tab} className="rise mt-4 flex-1">
        {tab === 'pres' ? <table className="w-full text-[20px]"><thead><tr className="text-[15px] uppercase tracking-wider text-mute"><th className="pb-2 text-left font-semibold"></th><th className="pb-2 text-right font-semibold" style={{ color: c }}>Pressure balls</th><th className="pb-2 text-right font-semibold">Normal balls</th><th className="pb-2 text-right font-semibold">Career</th></tr></thead>
          <tbody>{rows.map(([k, g]) => <tr key={k} className="border-t border-line"><td className="py-2.5 text-mute">{k}</td><td className="num py-2.5 text-right font-bold" style={{ color: c }}>{g(pres)}</td><td className="num py-2.5 text-right">{g(norm)}</td><td className="num py-2.5 text-right">{g(car)}</td></tr>)}</tbody></table>
        : tab === 'phase' ? <div className="card p-4"><div className="text-[16px] text-mute">Run value per 100 balls by phase{role === 'bowl' ? ' (runs saved + wickets)' : ''}</div>
          <EC h={250} option={{ grid: { left: 110, right: 70, top: 10, bottom: 30 }, xAxis: { type: 'value', ...ax() }, yAxis: { type: 'category', data: ['Powerplay', 'Middle', 'Death'], ...ax({ splitLine: { show: false } }) }, tooltip: { trigger: 'axis' },
            series: [{ type: 'bar', barWidth: 34, data: ph.map(v => v === null ? null : { value: +v.toFixed(1), itemStyle: { color: v >= 0 ? c : C.red, borderRadius: 6 } }), label: { show: true, position: 'right', fontSize: 16, color: C.ink } }] }} /></div>
        : <div className="grid grid-cols-2 gap-4">
          <div className="card p-5"><div className="text-[14px] font-bold uppercase tracking-wider text-blue">Data · biggest pressure moments</div>
            <ul className="mt-2 space-y-2 text-[16px] leading-snug">{(pr.moments || []).slice(0, 3).map((m: string) => <li key={m}>{m}</li>)}</ul></div>
          <div className="flex flex-col gap-3">
            {p.verdict ? <div className="card p-5"><div className="text-[14px] font-bold uppercase tracking-wider text-blue">Selector verdict</div><div className="mt-1 font-head text-[24px] font-bold text-blue-deep">{p.verdict.verdict}</div>
              <div className="text-[15px] text-mute">Risks: {p.verdict.risks}</div></div> : null}
            <div className="card p-5 text-[16px]"><div className="text-[14px] font-bold uppercase tracking-wider text-blue">Auction</div>{p.price.known && p.price.mid ? <>Est. price <b>₹{f1(p.price.mid)} cr</b> <span className="text-mute">(₹{f1(p.price.lo)}–{f1(p.price.hi)} cr)</span></> : 'No auction price history.'}</div>
            {(pr.notes || []).length ? <div className="rounded-3xl border-2 border-dashed border-pink/40 p-4 text-[14px] leading-snug"><b className="text-pink">Opinion / reporting – never changes the rating: </b>{pr.notes[0].note} <span className="text-mute">({pr.notes[0].source})</span></div> : null}</div></div>}
      </div></div>
    <div className="absolute bottom-[26px] left-[580px] right-[64px] flex justify-between text-[14px] text-mute"><span><b className="text-blue">PRESSURE SCOUT</b> · {role === 'bat' ? 'Batter' : 'Bowler'} {rank} of 10</span><span>{AUTHOR.name}</span></div>
  </div>
}

function CompareSlide({ D }: { D: any }) {
  const all = [...D.lists.bat.map((id: string) => ({ id, role: 'bat' as Role })), ...D.lists.bowl.map((id: string) => ({ id, role: 'bowl' as Role }))]
  const [a, setA] = useState(0); const [b, setB] = useState(10)
  const card = (k: number, set: (n: number) => void, col: string) => { const x = all[k]; const p = D.players[x.id]; const r = p[x.role]; const st = D.profiles[x.id]?.[x.role]
    return <div className="card flex-1 p-6" style={{ borderTop: `8px solid ${col}` }}>
      <select aria-label="Choose player" value={k} onClick={e => e.stopPropagation()} onChange={e => set(+e.target.value)} className="w-full rounded-xl border border-line bg-white px-3 py-2 text-[18px] font-semibold">
        {all.map((y, i) => <option key={y.id + y.role} value={i}>{y.role === 'bat' ? 'Bat' : 'Bowl'} #{(i % 10) + 1} · {D.players[y.id].name}</option>)}</select>
      <div className="mt-5 flex items-center gap-5"><Face id={x.id} name={p.name} role={x.role} photos={D.photos} size={120} />
        <div><div className="font-head text-[30px] font-bold text-blue-deep">{p.name}</div><div className="text-[17px] text-mute">{p.nation} · {avail(p.status)}</div></div></div>
      <div className="mt-5 grid grid-cols-2 gap-3">{[['Pressure Rating', f1(r.score)], ['P(top 10)', pct(r.p_top10)], ['80% range', `${f0(r.lo)} to ${f0(r.hi)}`], ['Pressure balls', f0(r.pressure_balls)],
        [x.role === 'bat' ? 'Pressure SR' : 'Pressure economy', x.role === 'bat' ? f1(st?.pres?.['1']?.strike_rate) : (st?.pres?.['1']?.economy ?? 0).toFixed(2)], ['Est. price', p.price.known && p.price.mid ? `₹${f1(p.price.mid)} cr` : '–']].map(([l, v]) =>
        <div key={l} className="rounded-2xl bg-blue-soft/60 p-4"><div className="text-[14px] text-mute">{l}</div><div className="num font-head text-[28px] font-bold" style={{ color: col }}>{v}</div></div>)}</div></div> }
  const ra = D.players[all[a].id][all[a].role], rb = D.players[all[b].id][all[b].role]
  const overlap = Math.min(ra.hi, rb.hi) > Math.max(ra.lo, rb.lo)
  return <div><div className="flex gap-6">{card(a, setA, C.blue)}{card(b, setB, C.pink)}</div>
    <div className="mt-5 rounded-3xl bg-blue-deep p-6 text-[21px] text-white">{overlap ? <>Their 80% ranges <b className="text-pink-soft">overlap</b> – statistically close. Let role fit, price and fitness decide.</> : <>Their 80% ranges <b>don't overlap</b> – a clear difference on the evidence.</>}</div></div>
}

function GapsSlide({ S }: { S: any }) {
  const G = [...S.gaps].sort((a: any, b: any) => b.gap - a.gap)
  const [sel, setSel] = useState(G[0].slot)
  const rr = S.teams.find((x: any) => x.team === 'Rajasthan Royals')
  const plans = ['A', 'B', 'C', 'Value'].map(pl => S.plans.find((x: any) => x.slot === sel && x.plan === pl)).filter(Boolean)
  return <div className="grid grid-cols-[1fr_520px] gap-8">
    <div className="card p-5"><div className="text-[18px] font-semibold">RR's best retained player vs league benchmark – click a role</div>
      <EC h={470} option={{ grid: { left: 190, right: 40, top: 40, bottom: 40 }, legend: { top: 0, right: 10, itemGap: 28, textStyle: { fontSize: 15 } }, tooltip: { trigger: 'axis' }, xAxis: { type: 'value', ...ax() },
        yAxis: { type: 'category', inverse: true, data: G.map((x: any) => x.slot.replace('Left-handed', 'LH')), ...ax({ splitLine: { show: false } }), triggerEvent: true },
        series: [{ name: 'League benchmark', type: 'bar', barGap: '10%', data: G.map((x: any) => +x.benchmark_top10_median.toFixed(1)), itemStyle: { color: '#C9CEDF', borderRadius: 4 } },
          { name: 'RR best retained', type: 'bar', data: G.map((x: any) => ({ value: +(x.rr_best_score ?? 0).toFixed(1), itemStyle: { color: x.slot === sel ? C.pink : x.gap > 3 ? C.red : C.blue, borderRadius: 4 } })) }] }} />
      <div className="mt-1 flex flex-wrap gap-2">{G.slice(0, 5).map((g: any) => <button key={g.slot} onClick={e => { e.stopPropagation(); setSel(g.slot) }} className={`pill border ${sel === g.slot ? 'border-pink bg-pink text-white' : 'border-line text-blue-deep hover:border-pink'}`}>{g.slot} · gap {f1(g.gap)}</button>)}</div></div>
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-[1.5fr_1fr_1fr] gap-3"><Big v={<span className="text-[40px]">₹{rr.purse_cr}</span>} l="crore purse" c={C.pink} /><Big v={rr.slots_left} l="slots" /><Big v={rr.overseas_slots_left} l="overseas" /></div>
      <div key={sel} className="card rise flex-1 p-6"><div className="text-[15px] font-bold uppercase tracking-wider text-pink">Auction plan · {sel}</div>
        <div className="mt-3 space-y-3">{plans.map((x: any) => <div key={x.plan} className="flex items-center gap-4 rounded-2xl bg-blue-soft/60 p-3">
          <div className={`grid h-12 w-16 place-items-center rounded-xl font-head text-[18px] font-bold ${x.plan === 'Value' ? 'bg-pink text-white' : 'bg-blue text-white'}`}>{x.plan === 'Value' ? '₹' : x.plan}</div>
          <div className="flex-1"><div className="font-head text-[21px] font-bold text-blue-deep">{x.name}</div><div className="text-[14px] text-mute">{avail(x.status)}{x.price ? ` · est. ₹${f1(x.price)} cr` : ''}</div></div>
          <div className="num font-head text-[24px] font-bold text-blue">{f1(x.score)}</div></div>)}</div></div></div></div>
}

// ---------- the deck ----------
export default function Deck() {
  const D: any = DATA
  const [i, setI] = useState(() => Math.max(0, (Number(new URLSearchParams(location.hash.slice(1)).get('s')) || 1) - 1))
  const [dir, setDir] = useState(1); const [grid, setGrid] = useState(false)
  const [scale, setScale] = useState(1); const box = useRef<HTMLDivElement>(null)
  useEffect(() => { const f = () => setScale(Math.min(innerWidth / W, (innerHeight - 56) / H)); f(); addEventListener('resize', f); return () => removeEventListener('resize', f) }, [])

  const { slides, idx } = useMemo(() => {
    if (!D) return { slides: [] as { t: string; g: string; el: (n: number, go: (k: number) => void) => ReactNode }[], idx: {} as Record<string, number> }
    const S: { t: string; g: string; el: (n: number, go: (k: number) => void) => ReactNode }[] = []
    const idx: Record<string, number> = {}
    S.push({ t: 'Title', g: 'Intro', el: () => { const people = [...D.lists.bat.map((id: string) => [id, 'bat']), ...D.lists.bowl.map((id: string) => [id, 'bowl'])] as [string, Role][]
      return <div className="relative h-full w-full overflow-hidden bg-white">
      <div className="absolute left-0 top-0 h-full w-[14px] bg-pink" />
      <div className="absolute left-[110px] top-[96px] w-[900px]">
        <div className="rise text-[19px] font-bold uppercase tracking-[0.22em] text-pink">SupeRR Selector Season 2 · Round 1</div>
        <h1 className="rise mt-6 text-[80px] font-extrabold leading-[1.04] tracking-tight text-blue-deep" style={{ animationDelay: '.08s' }}>The most reliable players under pressure</h1>
        <div className="rise mt-7 h-[5px] w-[120px] bg-pink" style={{ animationDelay: '.12s' }} />
        <p className="rise mt-7 text-[30px] leading-snug text-mute" style={{ animationDelay: '.16s' }}>…and whom Rajasthan Royals should back at the IPL 2027 auction</p></div>
      <div className="absolute right-[90px] top-[110px] w-[470px]">
        {[['bat', 'Top 10 batters'], ['bowl', 'Top 10 bowlers']].map(([r, l], row) => <div key={r} className="rise mb-10" style={{ animationDelay: `${0.2 + row * 0.1}s` }}>
          <div className="mb-3 text-[15px] font-bold uppercase tracking-[0.18em]" style={{ color: r === 'bat' ? C.blue : C.pink }}>{l}</div>
          <div className="flex flex-wrap pl-[26px]">{people.filter(x => x[1] === r).map(([id, role], k) =>
            <div key={id} title={D.players[id].name} className="-ml-[26px] mb-3 rounded-full border-[5px] border-white shadow-md" style={{ zIndex: 20 - k }}>
              {D.photos[id] ? <img src={D.photos[id]} alt={D.players[id].name} className="h-[96px] w-[96px] rounded-full object-cover object-top" />
                : <div className="grid h-[96px] w-[96px] place-items-center rounded-full font-head text-[30px] font-bold text-white" style={{ background: role === 'bat' ? C.blue : C.pink }}>{ini(D.players[id].name)}</div>}</div>)}</div></div>)}</div>
      <div className="absolute bottom-0 left-[14px] right-0 flex h-[170px] items-center justify-between bg-blue-deep px-[96px] text-white">
        <div><div className="text-[14px] uppercase tracking-[0.25em] text-white/60">Presented by</div><div className="mt-1 font-head text-[36px] font-bold">{AUTHOR.name}</div>
          <div className="text-[19px] text-white/80">{AUTHOR.email} · {AUTHOR.github}</div></div>
        <div className="text-right text-[18px] text-white/70">Rajasthan Royals × Unstop<br />Press → or click to begin</div></div></div> } })
    const agendaAt = S.length
    S.push({ t: 'Agenda', g: 'Intro', el: (n, go) => <Frame k="Agenda" t="What we'll cover" n={n}>
      <div className="grid grid-cols-3 gap-5">{[['The question', 'brief'], ['Defining pressure', 'pressure'], ['Fair measurement', 'runvalue'], ['Models & training', 'models'], ['Proof it works', 'backtest'], ['Top 10 batters', 'bat-list'], ['Top 10 bowlers', 'bowl-list'], ['Head-to-head', 'compare'], ['RR auction plan', 'gaps']].map(([l, k], j) =>
        <button key={k} onClick={e => { e.stopPropagation(); go(idx[k]) }} className="card rise flex items-center gap-5 p-6 text-left transition hover:-translate-y-1 hover:border-pink hover:shadow-xl" style={{ animationDelay: `${j * 0.04}s` }}>
          <div className="font-head text-[44px] font-extrabold text-pink/80">{String(j + 1).padStart(2, '0')}</div><div className="font-head text-[26px] font-bold text-blue-deep">{l}</div></button>)}</div></Frame> })
    void agendaAt
    idx.brief = S.length
    S.push({ t: 'The question', g: 'Intro', el: n => <Frame k="The brief" t={<>Who performs when <span className="text-pink">the match is on the line</span>?</>} sub="Identify the most reliable players under pressure whom Rajasthan Royals should back at the IPL 2027 auction – two ordered top-10 lists, with a methodology." n={n}>
      <div className="grid grid-cols-4 gap-5"><Big v={<><Count to={1.67} dec={2} /> M</>} l="deliveries modelled, 15 competitions, 2019–26" /><Big v={<Count to={D.meta.counts.players} />} l="player profiles built" d={.05} />
        <Big v={<Count to={4} />} l="seasons used purely as unseen tests" d={.1} /><Big v={<Count to={20} />} l="auction picks: 10 batters, 10 bowlers" c={C.pink} d={.15} /></div>
      <div className="mt-6 grid grid-cols-3 gap-5 text-[20px] leading-snug">
        <div className="card p-6"><div className="text-[15px] font-bold uppercase tracking-wider text-pink">Pressure ball</div><p className="mt-2">{D.meta.pressure_definition}</p></div>
        <div className="card p-6"><div className="text-[15px] font-bold uppercase tracking-wider text-pink">Pressure Rating</div><p className="mt-2">{D.meta.score_definition}</p></div>
        <div className="card p-6"><div className="text-[15px] font-bold uppercase tracking-wider text-pink">Only players RR can buy</div><p className="mt-2">Released on 17 Nov 2026 or on no IPL roster – none retained elsewhere, none already at RR.</p></div></div></Frame> })
    S.push({ t: 'Three findings', g: 'Intro', el: n => <Frame k="What the data says" t="Three findings that shaped our answer" n={n}>
      <div className="grid grid-cols-3 gap-6">{D.meta.findings.map((f: any, j: number) => <div key={j} className="card rise flex flex-col p-8" style={{ animationDelay: `${j * 0.1}s`, borderTop: `8px solid ${j === 1 ? C.blue : C.pink}` }}>
        <div className="font-head text-[64px] font-extrabold leading-none text-pink/25">0{j + 1}</div><div className="mt-3 font-head text-[28px] font-bold leading-tight text-blue-deep">{f.title}</div><p className="mt-4 text-[19px] leading-snug text-mute">{f.text}</p></div>)}</div>
      <div className="mt-6 rounded-3xl bg-blue-deep p-6 text-[20px] text-white">{D.meta.certainty}</div></Frame> })
    idx.pressure = S.length
    S.push({ t: 'Defining pressure', g: 'Method', el: n => <Frame k="1 · Pressure definition" t="Pressure = balls where the next delivery can swing the match" n={n}><LeverageSlide lev={D.method.leverage} /></Frame> })
    idx.runvalue = S.length
    S.push({ t: 'Run value', g: 'Method', el: n => <Frame k="2 · Performance measurement" t="Run value: what a player adds beyond the situation" n={n}><RunValueSlide kw={D.meta.kw ?? 5.6} /></Frame> })
    S.push({ t: 'Fair comparisons', g: 'Method', el: n => <Frame k="3 · Fair comparisons" t="Fair across leagues, venues, opponents and eras" n={n}><LeagueSlide league={D.method.league} /></Frame> })
    idx.models = S.length
    S.push({ t: 'Models', g: 'Method', el: n => <Frame k="4 · Models" t="Four models – click each to see why we kept it" n={n}><ModelsSlide cal={D.method.calibration} /></Frame> })
    S.push({ t: 'Training', g: 'Method', el: n => <Frame k="5 · Training without leakage" t="Every model is tested on a season it never saw" n={n}><FoldsSlide /></Frame> })
    idx.backtest = S.length
    S.push({ t: 'Backtest', g: 'Method', el: n => <Frame k="6 · Proof it works" t="Overall skill predicts pressure play – 'clutch' doesn't" n={n}><BacktestSlide skill={D.method.skill} cal={D.method.calibration} /></Frame> })
    for (const role of ['bat', 'bowl'] as Role[]) {
      const word = role === 'bat' ? 'batters' : 'bowlers'
      idx[`${role}-list`] = S.length
      S.push({ t: `Top 10 ${word}`, g: role === 'bat' ? 'Batters' : 'Bowlers', el: (n, go) => <Frame k={`The answer · ${word}`} t={<>Top 10 <span className={role === 'bat' ? 'text-blue' : 'text-pink'}>{word}</span> RR should back at the 2027 auction</>} n={n}><TopTen role={role} D={D} go={go} idx={idx} /></Frame> })
      D.lists[role].forEach((id: string, j: number) => { idx[`${role}-${id}`] = S.length
        S.push({ t: D.players[id].name, g: role === 'bat' ? 'Batters' : 'Bowlers', el: () => <PlayerSlide id={id} role={role} rank={j + 1} D={D} /> }) })
    }
    idx.compare = S.length
    S.push({ t: 'Head-to-head', g: 'RR plan', el: n => <Frame k="Interactive" t="Head-to-head: pick any two of our 20" n={n}><CompareSlide D={D} /></Frame> })
    idx.gaps = S.length
    S.push({ t: 'RR gaps & plan', g: 'RR plan', el: n => <Frame k="For Rajasthan Royals" t={<>Where RR is exposed – and <span className="text-pink">who to buy</span></>} n={n}><GapsSlide S={D.strategy} /></Frame> })
    S.push({ t: 'Beyond the top 10', g: 'RR plan', el: n => { const top = (r: Role) => D.lists[r].map((id: string) => D.players[id].name)
      return <Frame k="The IPL 2027 auction pool" t="Beyond the top 10: next best available, and youngsters" n={n}>
        <div className="grid grid-cols-3 gap-6">{(['bat', 'bowl'] as Role[]).map(r => <div key={r} className="card overflow-hidden p-6"><div className="font-head text-[22px] font-bold" style={{ color: r === 'bat' ? C.blue : C.pink }}>Next best {r === 'bat' ? 'batters' : 'bowlers'}</div>
          <table className="mt-3 w-full text-[18px]"><tbody>{D.strategy.pool[r].filter((x: any) => !top(r).includes(x.name)).slice(0, 8).map((x: any) => <tr key={x.name} className="border-t border-line">
            <td className="py-2 text-mute">#{x.pool_rank}</td><td className="py-2 font-semibold">{x.name}{x.tier === 'emerging' ? <span className="ml-2 text-[13px] text-mute">emerging</span> : null}</td><td className="num py-2 text-right font-bold">{f1(x.rating)}</td></tr>)}</tbody></table></div>)}
          <div className="card p-6"><div className="font-head text-[22px] font-bold text-blue-deep">Youngsters in the pool (≤23)</div>
            <table className="mt-3 w-full text-[18px]"><tbody>{[...D.strategy.youth_pool.bat.slice(0, 4), ...D.strategy.youth_pool.bowl.slice(0, 4)].map((x: any) => <tr key={x.name} className="border-t border-line">
              <td className="py-2 font-semibold">{x.name} <span className="text-[14px] text-mute">{x.age}</span></td><td className="py-2 text-right text-[15px] text-pink">{x.label}</td></tr>)}</tbody></table>
            <p className="mt-3 text-[14px] text-mute">Small samples: a watch list, not a ranking. Minors: cricket data and age only.</p></div></div>
        <p className="mt-4 text-[16px] text-mute"># = rank in the whole auction pool, including emerging players (40–149 pressure balls, wider ranges).</p></Frame> } })
    S.push({ t: 'Future scope', g: 'Close', el: n => <Frame k="Future scope" t="From analysis to a live auction tool" n={n}>
      <div className="grid grid-cols-3 gap-5">{[['RR Pressure Scout app', 'Upload any new data pack; columns mapped, validated and de-duplicated; identities checked.'], ['Refresh or retrain', 'A new model replaces the current one only if it wins on unseen seasons; drift checks and a registry.'],
        ['Auction optimiser', 'Best targets within purse, slot and overseas limits – max bids and plan A/B/C per role.'], ['Live auction mode', 'Enter each lot; all 10 purses update and RR\'s targets re-optimise instantly.'],
        ['Better price model', 'Train on the official auction register and backtest price ranges on past auctions.'], ['Richer data', 'Fielding, ball-tracking and pitch data; U19 and state-league scorecards for youth.']].map(([a, b], j) =>
        <div key={a} className="card rise p-7" style={{ animationDelay: `${j * 0.05}s` }}><div className={`mb-4 h-2 w-16 rounded-full ${j % 2 ? 'bg-pink' : 'bg-blue'}`} /><div className="font-head text-[26px] font-bold text-blue-deep">{a}</div><p className="mt-2 text-[19px] leading-snug text-mute">{b}</p></div>)}</div></Frame> })
    S.push({ t: 'Thank you', g: 'Close', el: () => <div className="relative grid h-full w-full grid-cols-[1fr_560px] gap-10 overflow-hidden p-[90px] text-white" style={{ background: C.navy }}>
      <div className="flex flex-col justify-between"><div><div className="rise text-[20px] uppercase tracking-[0.3em] text-pink-soft">Thank you</div><h2 className="rise mt-4 text-[96px] font-extrabold leading-none">Questions?</h2>
        <p className="rise mt-6 max-w-[700px] text-[26px] text-white/85">Happy to walk the selection panel through the model, the data or any player in detail.</p></div>
        <div className="rise"><div className="font-head text-[44px] font-bold">{AUTHOR.name}</div><div className="text-[24px] text-white/85">{AUTHOR.email}</div><div className="text-[24px] text-white/85">{AUTHOR.github}</div></div></div>
      <div className="rise self-center rounded-3xl bg-white p-7 text-[14px] leading-relaxed text-mute"><div className="font-head text-[20px] font-bold text-blue-deep">Sources & photo credits</div>
        <p className="mt-2">RR/Unstop data pack (aggregates only) · Cricsheet (ODC-By) · Wikipedia (CC BY-SA) auction prices · Wikidata (CC0) ages · IPL 2027 retention lists (17 Nov 2026).</p>
        <p className="mt-2">Photos: Wikimedia Commons, free licences only (others shown with initials):</p>
        <ul className="mt-1">{Object.values(D.credits).map((c: any) => <li key={c.name}>{c.name}: <a className="underline" href={c.page} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()}>{c.author}</a>, {c.licence}</li>)}</ul></div></div> })
    return { slides: S, idx }
  }, [D])

  const n = slides.length
  const go = useCallback((k: number) => { setI(cur => { const nx = Math.min(n - 1, Math.max(0, k)); setDir(nx >= cur ? 1 : -1); history.replaceState(null, '', `#s=${nx + 1}`); return nx }) }, [n])
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLSelectElement) return
      if (['ArrowRight', 'PageDown', ' '].includes(e.key)) { e.preventDefault(); go(i + 1) }
      else if (['ArrowLeft', 'PageUp'].includes(e.key)) { e.preventDefault(); go(i - 1) }
      else if (e.key === 'Home') go(0); else if (e.key === 'End') go(n - 1)
      else if (e.key.toLowerCase() === 'g') setGrid(g => !g); else if (e.key === 'Escape') setGrid(false)
      else if (e.key.toLowerCase() === 'f') document.fullscreenElement ? document.exitFullscreen() : box.current?.requestFullscreen?.()
    }
    addEventListener('keydown', h); return () => removeEventListener('keydown', h)
  }, [i, n, go])
  const tx = useRef<number | null>(null)
  if (!D) return <div className="grid h-full place-items-center text-white/80" role="status">Loading presentation…</div>
  const s = slides[i]
  const edge = (e: React.MouseEvent) => { const r = (e.currentTarget as HTMLElement).getBoundingClientRect(); const x = (e.clientX - r.left) / r.width; if (x > 0.88) go(i + 1); else if (x < 0.06) go(i - 1) }
  return <div ref={box} className="flex h-full w-full flex-col bg-blue-deep"
    onTouchStart={e => { tx.current = e.touches[0].clientX }} onTouchEnd={e => { if (tx.current === null) return; const d = e.changedTouches[0].clientX - tx.current; if (Math.abs(d) > 60) go(d < 0 ? i + 1 : i - 1); tx.current = null }}>
    <div className="relative grid flex-1 place-items-center overflow-hidden">
      <div style={{ width: W * scale, height: H * scale }} className="relative overflow-hidden rounded-[6px] shadow-2xl">
        <div style={{ width: W, height: H, transform: `scale(${scale})`, transformOrigin: 'top left' }} onClick={edge} aria-live="polite" aria-label={`Slide ${i + 1} of ${n}: ${s.t}`}>
          <div key={i} className={`h-full w-full ${dir > 0 ? 'fwd' : 'back'}`}>{s.el(i + 1, go)}</div></div></div>
      {innerWidth < innerHeight && innerWidth < 700 ? <div className="absolute bottom-3 rounded-full bg-white/10 px-4 py-1 text-xs text-white/80">Rotate your phone for a bigger view</div> : null}</div>
    <div className="flex h-14 items-center gap-3 px-4 text-white">
      <button onClick={() => go(i - 1)} disabled={i === 0} aria-label="Previous slide" className="grid h-9 w-9 place-items-center rounded-full bg-white/10 hover:bg-white/20 disabled:opacity-30"><ChevronLeft size={20} /></button>
      <div className="flex flex-1 items-center gap-[3px] overflow-hidden">{slides.map((x, k) => <button key={k} title={`${k + 1}. ${x.t}`} aria-label={`Go to slide ${k + 1}: ${x.t}`} onClick={() => go(k)}
        className="h-2 flex-1 rounded-full transition" style={{ background: k === i ? C.pink : k < i ? '#ffffff99' : '#ffffff26' }} />)}</div>
      <div className="num w-16 text-center text-sm text-white/80">{i + 1} / {n}</div>
      <button onClick={() => setGrid(true)} aria-label="All slides (G)" className="grid h-9 w-9 place-items-center rounded-full bg-white/10 hover:bg-white/20"><LayoutGrid size={18} /></button>
      <button onClick={() => document.fullscreenElement ? document.exitFullscreen() : box.current?.requestFullscreen?.()} aria-label="Full screen (F)" className="hidden h-9 w-9 place-items-center rounded-full bg-white/10 hover:bg-white/20 sm:grid"><Maximize2 size={18} /></button>
      <button onClick={() => go(i + 1)} disabled={i === n - 1} aria-label="Next slide" className="grid h-9 w-9 place-items-center rounded-full bg-pink hover:bg-pink-deep disabled:opacity-30"><ChevronRight size={20} /></button></div>
    {grid ? <div className="fixed inset-0 z-50 overflow-y-auto bg-blue-deep/95 p-6 backdrop-blur" role="dialog" aria-label="All slides">
      <div className="mb-4 flex items-center justify-between text-white"><div className="font-head text-2xl font-bold">All slides</div><button onClick={() => setGrid(false)} aria-label="Close" className="grid h-10 w-10 place-items-center rounded-full bg-white/10"><X /></button></div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">{slides.map((x, k) => <button key={k} onClick={() => { go(k); setGrid(false) }}
        className={`rounded-2xl p-4 text-left transition ${k === i ? 'bg-pink text-white' : 'bg-white/10 text-white hover:bg-white/20'}`}>
        <div className="text-[11px] uppercase tracking-widest opacity-70">{k + 1} · {x.g}</div><div className="mt-1 truncate font-semibold">{x.t}</div></button>)}</div></div> : null}
  </div>
}
