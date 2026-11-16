import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen, Target, Users } from 'lucide-react'
import { useData, type Role } from '../lib/data'
import { PlayerCard, Tip } from '../components/ui'

export default function Landing() {
  const { meta, players, rankings } = useData()
  const top = (r: Role) => (rankings.lists[r].open as string[]).slice(0, 10).map(id => players[id])
  return (
    <div>
      <section className="card relative overflow-hidden p-6 sm:p-10">
        <div aria-hidden className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-pink/15 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-24 -left-16 h-72 w-72 rounded-full bg-royal/15 blur-3xl" />
        <div className="relative max-w-3xl">
          <div className="text-xs font-semibold uppercase tracking-widest text-pink">{meta.event}</div>
          <h1 className="mt-2 text-3xl font-extrabold leading-tight sm:text-5xl">{meta.title}</h1>
          <p className="mt-4 text-base text-ink2 sm:text-lg">{meta.pressure_definition}<Tip k="pressureBall" label="pressure ball" /></p>
          <p className="mt-2 text-sm text-ink2">{meta.score_definition}<Tip k="rating" label="Pressure Rating" /></p>
          <div className="mt-6 flex flex-wrap gap-2">
            <Link to="/rankings" className="btn-primary"><Users size={16} aria-hidden />Explore players</Link>
            <Link to="/how-it-works" className="btn-ghost"><BookOpen size={16} aria-hidden />How it works</Link>
            <Link to="/strategy" className="btn-ghost"><Target size={16} aria-hidden />RR recommendations</Link>
          </div>
        </div>
      </section>

      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        {(['bat', 'bowl'] as Role[]).map(r => (
          <section key={r} aria-labelledby={`h-${r}`}>
            <div className="mb-3 flex items-baseline justify-between">
              <h2 id={`h-${r}`} className="text-xl font-bold">Top 10 {r === 'bat' ? 'batters' : 'bowlers'} under pressure</h2>
              <Link to={`/rankings?role=${r}`} className="text-sm text-royal hover:underline">Full ranking <ArrowRight size={14} className="inline" aria-hidden /></Link>
            </div>
            <div className="mb-3 flex items-center gap-3 text-[11px] text-ink2">
              <span>Bar = 80% range<Tip k="interval" label="80% range" /></span><span>P(top 10)<Tip k="ptop10" label="P(top 10)" /></span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">{top(r).map((p, i) => <PlayerCard key={p.id} p={p} role={r} rank={i + 1} />)}</div>
          </section>
        ))}
      </div>
      <p className="mt-4 rounded-xl border border-line bg-surface p-3 text-sm text-ink2"><strong className="text-ink">How sure are we?</strong> {meta.certainty}</p>

      <section className="mt-10" aria-labelledby="h-find">
        <h2 id="h-find" className="mb-4 text-xl font-bold">Three findings that shaped the method</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {meta.findings.map((f: any, i: number) => (
            <div key={i} className="card p-5">
              <div className="num text-3xl font-extrabold text-pink">0{i + 1}</div>
              <h3 className="mt-2 font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm text-ink2">{f.text}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
