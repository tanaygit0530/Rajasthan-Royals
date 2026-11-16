import { useMemo, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { X } from 'lucide-react'
import { useData, useProfiles, type Role } from '../lib/data'
import { Avatar, PCell, RatingBar, Status, Tip } from '../components/ui'
import Chart, { axis } from '../components/Chart'
import { cr, f0, f1 } from '../lib/fmt'

export default function Compare() {
  const { players, rankings } = useData(); const profs = useProfiles()
  const [sp, setSp] = useSearchParams()
  const init = (sp.get('ids') || [...rankings.lists.bat.open.slice(0, 2), ...rankings.lists.bowl.open.slice(0, 1)].join(',')).split(',').filter(i => players[i])
  const [ids, setIds] = useState<string[]>(init.slice(0, 4)); const [q, setQ] = useState('')
  const upd = (n: string[]) => { setIds(n); setSp({ ids: n.join(',') }, { replace: true }) }
  const sugg = useMemo(() => q.length < 2 ? [] : Object.values(players).filter(p => p.name.toLowerCase().includes(q.toLowerCase()) && !ids.includes(p.id)).slice(0, 8), [q, ids, players])
  const ps = ids.map(i => players[i])
  const role = (id: string): Role => { const p = players[id]; return p.bowl && (!p.bat || (p.bowl.rank ?? 999) < (p.bat.rank ?? 999)) ? 'bowl' : 'bat' }
  const prof = (id: string) => profs?.[id]?.[role(id)]
  const rowsBat = [['Strike rate', 'strike_rate'], ['Average', 'average'], ['Boundary %', 'boundary_pct'], ['Dot %', 'dot_pct'], ['Run value / 100', 'run_value_per100']]
  const rowsBowl = [['Economy', 'economy'], ['Average', 'average'], ['Balls per wicket', 'strike_rate'], ['Dot %', 'dot_pct'], ['Run value / 100', 'run_value_per100']]
  return (
    <div>
      <h1 className="text-2xl font-bold sm:text-3xl">Compare players</h1>
      <p className="mt-1 text-sm text-ink2">Pick 2–4 players. Each is shown in his main role (the one with the better rank).</p>
      <div className="relative mt-4 max-w-md">
        <label htmlFor="cmp" className="sr-only">Add a player</label>
        <input id="cmp" disabled={ids.length >= 4} placeholder={ids.length >= 4 ? 'Maximum 4 players' : 'Type a name to add…'} value={q} onChange={e => setQ(e.target.value)}
          className="w-full rounded-xl border border-line bg-surface px-3 py-2" role="combobox" aria-expanded={sugg.length > 0} aria-controls="cmp-list" />
        {sugg.length > 0 && <ul id="cmp-list" role="listbox" className="card absolute z-20 mt-1 w-full p-1">{sugg.map(p =>
          <li key={p.id}><button role="option" aria-selected={false} className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-page" onClick={() => { upd([...ids, p.id]); setQ('') }}>{p.name} <span className="text-ink2">· {p.nation}</span></button></li>)}</ul>}
      </div>
      {ps.length === 0 && <p className="mt-8 text-ink2">Add players to compare.</p>}
      {ps.length > 0 && <>
        <div className={`mt-6 grid gap-4 sm:grid-cols-2 ${ps.length > 2 ? 'xl:grid-cols-4' : ''}`}>
          {ps.map(p => { const r = role(p.id); const rt = p[r]; return (
            <div key={p.id} className="card p-4">
              <div className="flex items-start gap-3"><Avatar name={p.name} role={r} /><div className="min-w-0 flex-1"><Link to={`/player/${p.id}`} className="font-semibold hover:text-royal">{p.name}</Link>
                <div className="text-xs text-ink2">{p.nation} · {r === 'bat' ? 'batting' : 'bowling'}</div></div>
                <button aria-label={`Remove ${p.name}`} onClick={() => upd(ids.filter(i => i !== p.id))} className="text-ink2 hover:text-risk"><X size={16} /></button></div>
              {rt && <><div className="num mt-3 text-3xl font-extrabold">{f1(rt.score)}</div><RatingBar r={rt} role={r} compact />
                <div className="mt-1 flex justify-between text-xs text-ink2"><span className="num">{f1(rt.lo)} to {f1(rt.hi)}</span><span>P(top 10) <PCell p={rt.p_top10} /></span></div></>}
              <div className="mt-3"><Status s={p.status} /></div>
              <dl className="mt-3 grid grid-cols-2 gap-y-1 text-sm">
                <dt className="text-ink2">Age</dt><dd className="num text-right">{p.age ?? '–'}</dd>
                <dt className="text-ink2">Pressure balls</dt><dd className="num text-right">{f0(rt?.pressure_balls)}</dd>
                <dt className="text-ink2">Price<Tip k="price" label="price" /></dt><dd className="num text-right">{p.price.known ? `${cr(p.price.mid)}` : 'n/a'}</dd>
                <dt className="text-ink2">Roles</dt><dd className="text-right text-xs">{p.slots.join(', ') || '–'}</dd>
                {(r === 'bat' ? rowsBat : rowsBowl).map(([l, k]) => <><dt key={l} className="text-ink2">{l}</dt><dd key={l + 'v'} className="num text-right">{f1(prof(p.id)?.all?.career?.[k])}</dd></>)}
              </dl>
            </div>)})}
        </div>
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <div className="card p-4"><h2 className="text-sm font-semibold">Pressure Rating with 80% range<Tip k="interval" label="80% range" /></h2>
            <Chart label="Ratings with 80% ranges" height={80 + ps.length * 46} option={(t: any) => ({
              grid: { left: t.compact ? 100 : 140, right: 16, top: 10, bottom: 30, containLabel: false }, tooltip: {},
              xAxis: { type: 'value', ...axis(t) }, yAxis: { type: 'category', inverse: true, data: ps.map(p => p.name), ...axis(t), splitLine: { show: false } },
              series: [{ type: 'custom', renderItem: (_: any, api: any) => { const y = api.coord([0, api.value(0)])[1]; const a = api.coord([api.value(1), 0])[0]; const b = api.coord([api.value(2), 0])[0];
                return { type: 'rect', shape: { x: a, y: y - 4, width: b - a, height: 8, r: 4 }, style: { fill: t.line } } }, data: ps.map((p, i) => [i, p[role(p.id)]?.lo, p[role(p.id)]?.hi]) },
                { type: 'scatter', symbolSize: 14, itemStyle: { color: (x: any) => role(ps[x.dataIndex].id) === 'bat' ? t.bat : t.bowl }, data: ps.map((p, i) => [p[role(p.id)]?.score, i]) }] })} /></div>
          <div className="card p-4"><h2 className="text-sm font-semibold">Run value per 100 balls by phase<Tip k="runValue" label="run value" /></h2>
            {profs ? <Chart label="Run value by phase per player" height={260} option={(t: any) => ({
              tooltip: { trigger: 'axis' },
              xAxis: { type: 'category', data: ['Powerplay', 'Middle', 'Death'], ...axis(t) }, yAxis: { type: 'value', ...axis(t) },
              series: ps.map((p, i) => ({ name: p.name, type: 'bar', barMaxWidth: 22, itemStyle: { borderRadius: [3, 3, 0, 0], color: [t.bat, t.bowl, t.good, t.ink2][i] },
                data: ['PP', 'Middle', 'Death'].map(ph => prof(p.id)?.phase?.[ph]?.run_value_per100 ?? null) })) })} /> : <p className="text-sm text-ink2">Loading…</p>}
          </div>
        </div>
      </>}
    </div>)
}
