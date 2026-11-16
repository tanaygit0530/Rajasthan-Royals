import { useId, useState, type ReactNode } from 'react'
import { Info } from 'lucide-react'
import { G } from '../lib/glossary'
import { availTone, f1, initials, pct, short } from '../lib/fmt'
import type { Player, Role } from '../lib/data'
import { Link } from 'react-router-dom'

export function Tip({ k, text, label }: { k?: string; text?: string; label?: string }) {
  const id = useId(); const [open, setOpen] = useState(false)
  const t = text ?? (k ? G[k] : '')
  return (
    <span className="relative inline-flex align-middle">
      <button type="button" aria-describedby={id} aria-label={label ? `What is ${label}?` : 'Explanation'}
        className="ml-1 text-ink2 hover:text-royal" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} onClick={() => setOpen(o => !o)}>
        <Info size={14} aria-hidden />
      </button>
      {open ? <span id={id} role="tooltip"
        className="absolute left-1/2 top-6 z-40 w-64 max-w-[78vw] -translate-x-1/2 rounded-xl border border-line bg-surface p-3 text-left text-xs font-normal normal-case tracking-normal text-ink shadow-lg">
        {t}
      </span> : <span id={id} className="sr-only">{t}</span>}
    </span>
  )
}

export function Chip({ children, tone = 'neutral', title }: { children: ReactNode; tone?: string; title?: string }) {
  const c = { good: 'border-good/40 text-good', risk: 'border-risk/40 text-risk', royal: 'border-royal/40 text-royal',
    pink: 'border-pink/40 text-pink', warn: 'border-warn/40 text-warn', neutral: '' }[tone] || ''
  return <span className={`chip ${c}`} title={title}>{children}</span>
}

export function Status({ s }: { s: string | null | undefined }) {
  const tone = availTone(s)
  const icon = tone === 'risk' ? '✕' : tone === 'good' ? '●' : tone === 'royal' ? '★' : '○'
  return <Chip tone={tone} title={s || ''}><span aria-hidden>{icon}</span>{short(s) || 'unknown'}</Chip>
}

export function Avatar({ name, role }: { name: string; role: Role }) {
  return <div aria-hidden className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl text-sm font-bold text-white ${role === 'bat' ? 'bg-[rgb(var(--bat))]' : 'bg-[rgb(var(--bowl))]'} dark:text-[#0e0f12]`}>{initials(name)}</div>
}

/** rating with 80% interval on a shared scale */
export function RatingBar({ r, min = -20, max = 70, role, compact }: { r: { score: number; lo: number; hi: number }; min?: number; max?: number; role: Role; compact?: boolean }) {
  const x = (v: number) => `${((Math.max(min, Math.min(max, v)) - min) / (max - min)) * 100}%`
  const col = role === 'bat' ? 'bg-[rgb(var(--bat))]' : 'bg-[rgb(var(--bowl))]'
  return (
    <div className={`relative w-full ${compact ? 'h-3' : 'h-4'}`} role="img"
      aria-label={`Rating ${f1(r.score)}, 80% range ${f1(r.lo)} to ${f1(r.hi)}`}>
      <div className="absolute inset-y-1/2 left-0 right-0 h-px bg-line" />
      <div className="absolute top-0 bottom-0 w-px bg-ink2/50" style={{ left: x(0) }} title="0 = average" />
      <div className={`absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full ${col} opacity-30`} style={{ left: x(r.lo), width: `calc(${x(r.hi)} - ${x(r.lo)})` }} />
      <div className={`absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface ${col}`} style={{ left: x(r.score) }} />
    </div>
  )
}

export function PCell({ p }: { p: number }) {
  const tone = p >= 0.5 ? 'text-good' : p >= 0.2 ? 'text-ink' : 'text-ink2'
  return <span className={`num font-semibold ${tone}`}>{pct(p)}</span>
}

export function PlayerCard({ p, role, rank }: { p: Player; role: Role; rank: number }) {
  const r = p[role]!
  return (
    <Link to={`/player/${p.id}`} className="card group flex flex-col gap-3 p-4 transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start gap-3">
        <div className="num w-5 shrink-0 pt-0.5 text-right text-sm font-bold text-ink2">{rank}</div>
        <Avatar name={p.name} role={role} />
        <div className="min-w-0 flex-1">
          <div className="font-semibold leading-snug group-hover:text-royal">{p.name}</div>
          <div className="truncate text-xs text-ink2">{p.nation} · {(role === 'bat' ? p.type_bat : p.type_bowl) || r.role_label || ''}</div>
        </div>
      </div>
      <div className="flex items-end justify-between gap-2">
        <div className="num text-2xl font-bold leading-none">{f1(r.score)}<span className="ml-1 text-xs font-normal text-ink2">rating</span></div>
        <div className="text-right text-xs text-ink2">P(top 10) <PCell p={r.p_top10} /></div>
      </div>
      <RatingBar r={r} role={role} compact />
      <div className="flex flex-wrap gap-1"><Status s={p.status} /></div>
    </Link>
  )
}

export function Section({ title, kicker, children, id, right }: { title: string; kicker?: string; children: ReactNode; id?: string; right?: ReactNode }) {
  return (
    <section id={id} className="mt-10">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>{kicker && <div className="text-xs font-semibold uppercase tracking-widest text-pink">{kicker}</div>}
          <h2 className="text-xl font-bold sm:text-2xl">{title}</h2></div>{right}
      </div>
      {children}
    </section>
  )
}

export function Details({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <details className="card mt-3 p-4 [&_summary]:cursor-pointer">
      <summary className="text-sm font-semibold text-royal">{summary}</summary>
      <div className="mt-3 text-sm text-ink2">{children}</div>
    </details>
  )
}

export function DataTable({ cols, rows }: { cols: { k: string; h: ReactNode; f?: (r: any) => ReactNode; num?: boolean }[]; rows: any[] }) {
  return (
    <div className="overflow-x-auto"><table className="tbl w-full text-sm">
      <thead><tr>{cols.map(c => <th key={c.k} className={c.num ? 'text-right' : ''}>{c.h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i}>{cols.map(c => <td key={c.k} className={c.num ? 'num text-right' : ''}>{c.f ? c.f(r) : r[c.k] ?? '–'}</td>)}</tr>)}</tbody>
    </table></div>
  )
}

export function downloadCsv(name: string, rows: any[]) {
  if (!rows.length) return
  const cols = Object.keys(rows[0])
  const esc = (v: any) => { const s = v === null || v === undefined ? '' : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s }
  const csv = [cols.join(','), ...rows.map(r => cols.map(c => esc(r[c])).join(','))].join('\n')
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); a.download = name; a.click()
}
