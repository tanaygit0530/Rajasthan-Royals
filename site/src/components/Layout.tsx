import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Moon, Sun, Lock } from 'lucide-react'
import { useEffect, useState } from 'react'
import { lock } from '../lib/crypto'
import { useData } from '../lib/data'

const NAV = [['/', 'Overview'], ['/rankings', 'Rankings'], ['/compare', 'Compare'], ['/how-it-works', 'How it works'], ['/strategy', 'RR strategy'], ['/report', 'Report'], ['/deck', 'Presentation']]
export default function Layout() {
  const { meta } = useData()
  const [dark, setDark] = useState(document.documentElement.classList.contains('dark'))
  const loc = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [loc.pathname])
  const toggle = () => { const d = !dark; setDark(d); document.documentElement.classList.toggle('dark', d); try { localStorage.setItem('theme', d ? 'dark' : 'light') } catch {} }
  return (
    <div className="min-h-screen overflow-x-clip">
      <a href="#main" className="skip">Skip to content</a>
      <header className="sticky top-0 z-30 border-b border-line bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 font-bold">
            <span aria-hidden className="grid h-8 w-8 place-items-center rounded-lg bg-royal text-white dark:text-[#0e0f12]">
              <svg viewBox="0 0 32 32" className="h-5 w-5"><path d="M5 23l6-14 5 9 4-6 5 11" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </span>
            <span className="hidden sm:inline">Pressure Scout</span>
          </NavLink>
          <nav aria-label="Main" className="-mx-1 flex flex-1 gap-1 overflow-x-auto">
            {NAV.map(([to, l]) => (
              <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `whitespace-nowrap rounded-lg px-3 py-1.5 text-sm ${isActive ? 'bg-royal/10 font-semibold text-royal' : 'text-ink2 hover:text-ink'}`}>{l}</NavLink>
            ))}
          </nav>
          <button onClick={toggle} className="rounded-lg p-2 text-ink2 hover:text-ink" aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}>{dark ? <Sun size={18} /> : <Moon size={18} />}</button>
          <button onClick={() => { lock(); location.reload() }} className="hidden rounded-lg p-2 text-ink2 hover:text-ink sm:block" aria-label="Lock the site"><Lock size={18} /></button>
        </div>
      </header>
      <main id="main" className="mx-auto max-w-7xl px-4 pb-16 pt-6"><Outlet /></main>
      <footer className="border-t border-line py-6 text-center text-xs text-ink2">
        {meta.event} · analysis generated {meta.generated} · private evaluator preview, not for distribution
      </footer>
    </div>
  )
}
