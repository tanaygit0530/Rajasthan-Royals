// Encrypts every file in private_data/ into public/enc/<name>.bin (gzip -> AES-256-GCM).
// Key = PBKDF2-SHA256(password, random salt, 250k iterations). The password comes from SITE_PASSWORD or .env.local
// and is never written to the output. Only these encrypted blobs are shipped with the site.
import { readFileSync, writeFileSync, mkdirSync, readdirSync, existsSync, rmSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
import { webcrypto as crypto } from 'node:crypto'
let pw = process.env.SITE_PASSWORD
if (!pw && existsSync('.env.local')) {
  const m = readFileSync('.env.local', 'utf8').match(/^SITE_PASSWORD=(.*)$/m); if (m) pw = m[1].trim()
}
if (!pw) { console.error('Set SITE_PASSWORD (env) or put SITE_PASSWORD=... in site/.env.local'); process.exit(1) }
const ITER = 250000
const salt = crypto.getRandomValues(new Uint8Array(16))
const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey'])
const key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt, iterations: ITER, hash: 'SHA-256' }, base,
  { name: 'AES-GCM', length: 256 }, false, ['encrypt'])
const enc = async (buf) => { const iv = crypto.getRandomValues(new Uint8Array(12))
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, buf))
  const out = new Uint8Array(12 + ct.length); out.set(iv); out.set(ct, 12); return out }
if (existsSync('public/enc')) rmSync('public/enc', { recursive: true })
mkdirSync('public/enc', { recursive: true })
const files = readdirSync('private_data')
for (const f of files) {
  const raw = readFileSync(`private_data/${f}`)
  writeFileSync(`public/enc/${f}.bin`, await enc(gzipSync(raw, { level: 9 })))
}
const check = await enc(gzipSync(Buffer.from('unlocked')))
writeFileSync('public/enc/key.json', JSON.stringify({ salt: Buffer.from(salt).toString('base64'), iterations: ITER,
  check: Buffer.from(check).toString('base64'), files }))
console.log(`encrypted ${files.length} files into public/enc`)
