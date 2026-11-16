import ReactECharts from 'echarts-for-react'
import { useEffect, useState } from 'react'
// Reads the CSS colour tokens so charts follow light/dark mode.
function tokens() {
  const s = getComputedStyle(document.documentElement)
  const c = (v: string) => `rgb(${s.getPropertyValue(v).trim().split(' ').join(',')})`
  return { ink: c('--ink'), ink2: c('--ink2'), line: c('--line'), bat: c('--bat'), bowl: c('--bowl'), good: c('--good'), risk: c('--risk'), surface: c('--surface') }
}
export function useTokens() {
  const [t, setT] = useState(tokens())
  useEffect(() => { const o = new MutationObserver(() => setT(tokens())); o.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] }); return () => o.disconnect() }, [])
  return t
}
export const alpha = (c: string, a: number) => c.replace('rgb(', 'rgba(').replace(')', `,${a})`)
export default function Chart({ option, height = 300, label }: { option: any; height?: number; label: string }) {
  const t: any = { ...useTokens(), compact: typeof window !== 'undefined' && window.innerWidth < 640 }
  const base = {
    textStyle: { color: t.ink2, fontFamily: 'Inter, system-ui, sans-serif' }, backgroundColor: 'transparent',
    grid: { left: 12, right: 16, top: 24, bottom: 44, containLabel: true },
    legend: { bottom: 0, itemWidth: 14, itemHeight: 8, textStyle: { color: t.ink2, fontSize: 11 } },
    tooltip: { backgroundColor: t.surface, borderColor: t.line, textStyle: { color: t.ink } },
  }
  return <div role="img" aria-label={label}><ReactECharts option={{ ...base, ...option(t) }} style={{ height }} notMerge lazyUpdate opts={{ renderer: 'svg' }} /></div>
}
export const axis = (t: any, extra: any = {}) => ({ axisLine: { lineStyle: { color: t.line } }, axisLabel: { color: t.ink2 }, splitLine: { lineStyle: { color: t.line, opacity: 0.6 } }, nameTextStyle: { color: t.ink2 }, ...extra })
