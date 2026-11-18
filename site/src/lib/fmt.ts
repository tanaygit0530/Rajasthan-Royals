export const f1 = (x: any) => (x === null || x === undefined || Number.isNaN(x) ? '–' : Number(x).toFixed(1))
export const f0 = (x: any) => (x === null || x === undefined || Number.isNaN(x) ? '–' : Math.round(Number(x)).toLocaleString('en-IN'))
export const f2 = (x: any) => (x === null || x === undefined || Number.isNaN(x) ? '–' : Number(x).toFixed(2))
export const pct = (x: any) => (x === null || x === undefined || Number.isNaN(x) ? '–' : `${Math.round(Number(x) * 100)}%`)
export const cr = (x: any) => (x === null || x === undefined || Number.isNaN(x) ? '–' : `₹${Number(x).toFixed(1)} cr`)
export const initials = (n: string) => n.split(/\s+/).filter(Boolean).slice(0, 2).map(s => s[0]).join('').toUpperCase()
export const short = (s: string | null | undefined) => (s || '').replace(' (not on a 2026 IPL roster)', '').replace(' (not in auction)', '').replace(' (traded; not in auction)', ' (traded)')
export const availTone = (s: string | null | undefined) =>
  !s ? 'neutral' : s.startsWith('Not eligible') ? 'risk' : (s.startsWith('In auction pool') || s.startsWith('Open market')) ? 'good' : s.startsWith('Already RR') ? 'royal' : 'neutral'
