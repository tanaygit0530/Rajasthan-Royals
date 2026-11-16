// Client-side decryption of the encrypted data bundle (AES-256-GCM, key from PBKDF2-SHA256 of the shared password).
const b64 = (s: string) => Uint8Array.from(atob(s), c => c.charCodeAt(0))
let KEY: CryptoKey | null = null
let META: { salt: string; iterations: number; check: string; files: string[] } | null = null
const cache = new Map<string, Promise<ArrayBuffer>>()

async function gunzip(buf: ArrayBuffer): Promise<ArrayBuffer> {
  const ds = new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))
  return await new Response(ds).arrayBuffer()
}
async function decrypt(bytes: Uint8Array): Promise<ArrayBuffer> {
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: bytes.slice(0, 12) }, KEY!, bytes.slice(12))
  return gunzip(pt)
}
async function loadMeta() {
  if (!META) META = await (await fetch('./enc/key.json', { cache: 'no-store' })).json()
  return META!
}
export async function unlock(password: string): Promise<boolean> {
  const m = await loadMeta()
  const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveKey'])
  const k = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: b64(m.salt), iterations: m.iterations, hash: 'SHA-256' },
    base, { name: 'AES-GCM', length: 256 }, true, ['decrypt'])
  KEY = k
  try {
    const t = new TextDecoder().decode(await decrypt(b64(m.check)))
    if (t !== 'unlocked') throw new Error('bad')
    try { sessionStorage.setItem('k', JSON.stringify(await crypto.subtle.exportKey('jwk', k))) } catch {}
    return true
  } catch { KEY = null; return false }
}
export async function resume(): Promise<boolean> {
  try {
    const j = sessionStorage.getItem('k'); if (!j) return false
    KEY = await crypto.subtle.importKey('jwk', JSON.parse(j), { name: 'AES-GCM' }, true, ['decrypt'])
    const m = await loadMeta()
    return new TextDecoder().decode(await decrypt(b64(m.check))) === 'unlocked'
  } catch { KEY = null; return false }
}
export function lock() { KEY = null; cache.clear(); try { sessionStorage.removeItem('k') } catch {} }
export function file(name: string): Promise<ArrayBuffer> {
  if (!cache.has(name)) cache.set(name, fetch(`./enc/${name}.bin`).then(r => r.arrayBuffer()).then(b => decrypt(new Uint8Array(b))))
  return cache.get(name)!
}
export async function json<T = any>(name: string): Promise<T> {
  return JSON.parse(new TextDecoder().decode(await file(name)))
}
