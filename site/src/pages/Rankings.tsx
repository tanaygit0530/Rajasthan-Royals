import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Download } from 'lucide-react'
import { useData, type Player, type Role } from '../lib/data'
import { Avatar, PCell, RatingBar, Status, Tip, downloadCsv } from '../components/ui'
import { cr, f0, f1 } from '../lib/fmt'

const LISTS = [['open', 'Open ranking'], ['buy', 'RR can buy'], ['value', 'Value & uncapped'], ['youth', 'Youth (≤23)']] as const
type L = typeof LISTS[number][0]

export default function Rankings() {
  const { players, rankings } = useData()
  const [sp, setSp] = useSearchParams()
  const role = (sp.get('role') as Role) || 'bat'
  const list = (sp.get('list') as L) || 'open'
  const set = (k: string, v: string) => { const n = new URLSearchParams(sp); n.set(k, v); setSp(n, { replace: true }) }
  const [slot, setSlot] = useState(''); const [hand, setHand] = useState(''); const [style, setStyle] = useState('')
  const [nat, setNat] = useState(''); const [cap, setCap] = useState(''); const [avail, setAvail] = useState(''); const [q, setQ] = useState('')
  const nav = useNavigate()
  const ids: string[] = rankings.lists[role][list]
  const base = ids.map(id => players[id]).filter(Boolean) as Player[]
  const rows = useMemo(() => base.filter(p =>
    (!slot || p.slots.includes(slot)) && (!hand || p.bat_hand === hand) &&
    (!style || (style === 'Pace' || style === 'Spin' ? p.pace_spin === style : style === 'Left-arm' ? p.bowl_arm === 'Left' : style === 'Right-arm' ? p.bowl_arm === 'Right' : style === 'Wrist spin' ? p.spin_kind === 'wrist' : p.spin_kind === 'finger')) &&
    (!nat || (nat === 'India' ? p.nation === 'India' : p.nation !== 'India')) &&
    (!cap || (cap === 'capped' ? p.cap === 'capped' : p.cap !== 'capped')) &&
    (!avail || (p.status || '').startsWith(avail)) && (!q || p.name.toLowerCase().includes(q.toLowerCase()))
  ), [base, slot, hand, style, nat, cap, avail, q])
  const slots = Array.from(new Set(base.flatMap(p => p.slots))).sort()
  const sel = 'rounded-lg border border-line bg-surface px-2 py-1.5 text-sm'
  const score = (p: Player) => list === 'youth' && p.youth ? { score: p.youth.proj_1, lo: p.youth.proj_1_lo, hi: p.youth.proj_1_hi } : p[role]
  const lim = list === 'youth' ? { min: -40, max: 140 } : { min: -40, max: 70 }
  const exportRows = () => downloadCsv(`${role}_${list}.csv`, rows.map((p, i) => { const r = score(p)!; return {
    position: i + 1, player: p.name, nation: p.nation, age: p.age, rating: r?.score, low80: r?.lo, high80: r?.hi,
    p_top10: p[role]?.p_top10, pressure_balls: p[role]?.pressure_balls, status: p.status } }))
  return (
    <div>
      <h1 className="text-2xl font-bold sm:text-3xl">Rankings</h1>
      <p className="mt-1 text-sm text-ink2">Click any player for the full profile. Ratings carry an 80% range<Tip k="interval" label="80% range" />.</p>
      <div className="mt-5 flex flex-wrap items-center gap-2">
        <div role="tablist" aria-label="Role" className="flex rounded-xl border border-line bg-surface p-1">
          {(['bat', 'bowl'] as Role[]).map(r => <button key={r} role="tab" aria-selected={role === r} onClick={() => set('role', r)}
            className={`rounded-lg px-4 py-1.5 text-sm font-semibold ${role === r ? 'bg-royal text-white dark:text-[#0e0f12]' : 'text-ink2'}`}>{r === 'bat' ? 'Batters' : 'Bowlers'}</button>)}
        </div>
        <div role="tablist" aria-label="List" className="flex flex-wrap rounded-xl border border-line bg-surface p-1">
          {LISTS.map(([k, l]) => <button key={k} role="tab" aria-selected={list === k} onClick={() => set('list', k)}
            className={`rounded-lg px-3 py-1.5 text-sm ${list === k ? 'bg-pink/15 font-semibold text-pink' : 'text-ink2'}`}>{l}</button>)}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2" aria-label="Filters">
        <input aria-label="Search players" placeholder="Search name" value={q} onChange={e => setQ(e.target.value)} className={sel} />
        <select aria-label="Role slot" className={sel} value={slot} onChange={e => setSlot(e.target.value)}><option value="">All roles</option>{slots.map(s => <option key={s}>{s}</option>)}</select>
        <select aria-label="Batting hand" className={sel} value={hand} onChange={e => setHand(e.target.value)}><option value="">Any batting hand</option><option value="RHB">Right-hand bat</option><option value="LHB">Left-hand bat</option></select>
        <select aria-label="Bowling type" className={sel} value={style} onChange={e => setStyle(e.target.value)}><option value="">Any bowling type</option>{['Pace', 'Spin', 'Left-arm', 'Right-arm', 'Wrist spin', 'Finger spin'].map(s => <option key={s}>{s}</option>)}</select>
        <select aria-label="Nationality" className={sel} value={nat} onChange={e => setNat(e.target.value)}><option value="">Indian & overseas</option><option value="India">Indian</option><option value="overseas">Overseas</option></select>
        <select aria-label="Capped status" className={sel} value={cap} onChange={e => setCap(e.target.value)}><option value="">Capped & uncapped</option><option value="capped">Capped</option><option value="uncapped">Uncapped</option></select>
        <select aria-label="Availability" className={sel} value={avail} onChange={e => setAvail(e.target.value)}><option value="">Any availability</option><option value="Open market">Open market</option><option value="Under contract">Under contract</option><option value="Already RR">Already RR</option><option value="Not eligible">Not eligible</option></select>
        <button onClick={exportRows} className="btn-ghost py-1.5"><Download size={14} aria-hidden />CSV</button>
      </div>
      <div className="card mt-4 overflow-x-auto">
        <table className="tbl w-full min-w-[760px] text-sm">
          <caption className="sr-only">{role === 'bat' ? 'Batters' : 'Bowlers'} – {LISTS.find(l => l[0] === list)![1]}</caption>
          <thead><tr>
            <th className="w-10">#</th><th>Player</th>
            <th className="text-right">{list === 'youth' ? 'Projected' : 'Rating'}<Tip k={list === 'youth' ? 'youth' : 'rating'} label="rating" /></th>
            <th className="w-[30%]">80% range<Tip k="interval" label="80% range" /></th>
            <th className="text-right">P(top 10)<Tip k="ptop10" label="P(top 10)" /></th>
            <th className="text-right">{list === 'value' ? <>Price<Tip k="price" label="price" /></> : <>Pressure balls<Tip k="pressureBalls" label="pressure balls" /></>}</th>
            <th>Status<Tip k="status" label="status" /></th>
          </tr></thead>
          <tbody>
            {rows.map((p, i) => { const r = score(p); return (
              <tr key={p.id} tabIndex={0} onClick={() => nav(`/player/${p.id}`)} onKeyDown={e => e.key === 'Enter' && nav(`/player/${p.id}`)}
                className="cursor-pointer hover:bg-page focus:bg-page">
                <td className="num text-ink2">{i + 1}</td>
                <td><div className="flex items-center gap-3"><Avatar name={p.name} role={role} />
                  <div className="min-w-0"><div className="font-semibold">{p.name}</div>
                    <div className="text-xs text-ink2">{p.nation}{p.age ? ` · ${p.age}` : ''} · {p.slots.filter(s => role === 'bat' ? !/pace|spin|bowler/i.test(s) : /pace|spin|bowler/i.test(s)).join(', ') || '–'}
                      {list === 'youth' && p.youth ? ` · ${p.youth.label}` : ''}</div></div></div></td>
                <td className="num text-right text-base font-bold">{f1(r?.score)}</td>
                <td>{r && <RatingBar r={r} role={role} compact {...lim} />}<div className="num mt-0.5 text-[11px] text-ink2">{f1(r?.lo)} to {f1(r?.hi)}</div></td>
                <td className="text-right">{p[role] ? <PCell p={p[role]!.p_top10} /> : '–'}</td>
                <td className="num text-right">{list === 'value' ? (p.price.known ? `${cr(p.price.mid)}` : 'n/a') : f0(p[role]?.pressure_balls ?? p.youth?.balls)}</td>
                <td><Status s={p.status} /></td>
              </tr>) })}
            {!rows.length && <tr><td colSpan={7} className="py-10 text-center text-ink2">No players match these filters.</td></tr>}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-ink2">{rows.length} players. {list === 'youth' ? 'Youth projections are adjusted skill per 100 balls in all situations (not only pressure), so they are on a different scale.' : ''}</p>
    </div>
  )
}
