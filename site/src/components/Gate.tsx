import { useEffect, useState, type ReactNode } from 'react'
import { resume, unlock } from '../lib/crypto'
export default function Gate({ children }: { children: ReactNode }) {
  const [ok, setOk] = useState<boolean | null>(null)
  const [pw, setPw] = useState(''); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  useEffect(() => { resume().then(setOk) }, [])
  if (ok === null) return <div className="p-8 text-ink2" role="status">Loading…</div>
  if (ok) return <>{children}</>
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr('')
    const good = await unlock(pw); setBusy(false)
    if (good) setOk(true); else setErr('That password did not work. Please check it and try again.')
  }
  return (
    <div className="grid min-h-screen place-items-center px-4">
      <form onSubmit={submit} className="card w-full max-w-sm p-6" aria-labelledby="gate-title">
        <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-pink">Private evaluator preview</div>
        <h1 id="gate-title" className="text-2xl font-bold">Pressure Scout</h1>
        <p className="mt-2 text-sm text-ink2">SupeRR Selector Season 2 · Round 1 submission. Enter the password you were given.</p>
        <label htmlFor="pw" className="mt-5 block text-sm font-medium">Password</label>
        <input id="pw" type="password" autoFocus autoComplete="current-password" value={pw} onChange={e => setPw(e.target.value)}
          className="mt-1 w-full rounded-xl border border-line bg-page px-3 py-2 outline-none focus:border-royal" />
        {err && <p role="alert" className="mt-2 text-sm text-risk">{err}</p>}
        <button className="btn-primary mt-4 w-full justify-center" disabled={busy || !pw}>{busy ? 'Unlocking…' : 'Open'}</button>
        <p className="mt-4 text-[11px] text-ink2">All data on this site is encrypted and only decrypted in your browser after unlocking.</p>
      </form>
    </div>
  )
}
