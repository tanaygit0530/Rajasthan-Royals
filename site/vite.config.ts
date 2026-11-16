import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// base './' so the built site works from any host path; only public/enc (encrypted) data is shipped
export default defineConfig({ plugins: [react()], base: './', build: { chunkSizeWarningLimit: 1500 } })
