import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { json } from './crypto'

export type Rating = { score: number; lo: number; hi: number; p_top10: number; rank: number | null; tier: string;
  pressure_balls: number; obs_pressure: number | null; obs_normal: number | null; role_label: string | null; role_pct: number | null }
export type Player = { id: string; name: string; nation: string; age: number | null; cap: string; status: string | null;
  team27: string | null; badges: string[]; slots: string[]; type_bat: string | null; type_bowl: string | null;
  pace_spin: string | null; bowl_arm: string | null; spin_kind: string | null; bat_hand: string | null;
  bat: Rating | null; bowl: Rating | null;
  price: { known: boolean; mid?: number; lo?: number; hi?: number; last?: number | null; last_year?: number | null; value_per_cr?: number | null };
  youth: null | { role: string; board: string; label: string; rank: number; skill: number; proj_1: number; proj_1_lo: number; proj_1_hi: number; proj_2: number; proj_3: number; balls: number };
  verdict: null | { verdict: string; risks: string; alternative: string; form: string } }
export type Role = 'bat' | 'bowl'
type Core = { meta: any; players: Record<string, Player>; rankings: any; strategy: any; method: any }
const Ctx = createContext<Core | null>(null)

export function DataProvider({ children }: { children: ReactNode }) {
  const [d, setD] = useState<Core | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    Promise.all(['meta.json', 'players.json', 'rankings.json', 'strategy.json', 'method.json'].map(n => json(n)))
      .then(([meta, players, rankings, strategy, method]) => setD({ meta, players, rankings, strategy, method }))
      .catch(e => setErr(String(e)))
  }, [])
  if (err) return <div className="p-8 text-risk">Could not load the data: {err}</div>
  if (!d) return <div className="p-8 text-ink2" role="status">Loading the analysis…</div>
  return <Ctx.Provider value={d}>{children}</Ctx.Provider>
}
export const useData = () => useContext(Ctx)!

let profilesP: Promise<Record<string, any>> | null = null
export function useProfile(id?: string) {
  const [p, setP] = useState<any>(null)
  useEffect(() => {
    if (!id) return
    profilesP = profilesP || json('profiles.json')
    profilesP.then(all => setP(all[id] || {}))
  }, [id])
  return p
}
export function useProfiles() {
  const [p, setP] = useState<Record<string, any> | null>(null)
  useEffect(() => { profilesP = profilesP || json('profiles.json'); profilesP.then(setP) }, [])
  return p
}
