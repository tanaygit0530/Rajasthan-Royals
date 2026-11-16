import { useEffect, useState } from 'react'
import { Download } from 'lucide-react'
import { file, json } from '../lib/crypto'
export default function Report() {
  const [url, setUrl] = useState<string | null>(null); const [src, setSrc] = useState<any>(null)
  useEffect(() => { let u = ''; file('report.pdf').then(b => { u = URL.createObjectURL(new Blob([b], { type: 'application/pdf' })); setUrl(u) }); json('sources.json').then(setSrc); return () => { if (u) URL.revokeObjectURL(u) } }, [])
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3"><div><h1 className="text-2xl font-bold sm:text-3xl">Methodology report</h1>
        <p className="mt-1 text-sm text-ink2">The full written submission, with every number generated from the same outputs as this site.</p></div>
        {url && <a href={url} download="SupeRR_S2_Pressure_Methodology_Report.pdf" className="btn-primary"><Download size={16} aria-hidden />Download PDF</a>}</div>
      <div className="card mt-4 overflow-hidden">{url ? <object data={url} type="application/pdf" className="h-[78vh] w-full" aria-label="Methodology report PDF">
        <p className="p-6 text-sm">Your browser cannot show the PDF inline. <a className="text-royal underline" href={url} download="SupeRR_S2_Pressure_Methodology_Report.pdf">Download it</a>.</p></object>
        : <p className="p-6 text-ink2" role="status">Decrypting the report…</p>}</div>
      <section className="mt-8"><h2 className="text-xl font-bold">Data sources and licences</h2>
        <ul className="card mt-3 divide-y divide-line">{src?.licences.map((l: any) => <li key={l.name} className="flex flex-wrap justify-between gap-2 p-4 text-sm"><span className="font-semibold">{l.url ? <a className="text-royal hover:underline" href={l.url} target="_blank" rel="noreferrer noopener">{l.name}</a> : l.name}</span><span className="text-ink2">{l.licence}</span></li>)}</ul>
        <p className="mt-3 text-xs text-ink2">No raw ball-by-ball data or data-pack files are included in this site – only aggregated results.</p></section>
    </div>)
}
