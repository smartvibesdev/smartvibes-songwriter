import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

/**
 * Local preview only: adds a /__preview-login page that pretends you are signed in, so the
 * app can be tried against the sample-data API (backend/dev_server.py) without AWS. It is
 * only active in the dev server, and only when VITE_API_URL points at localhost. It is
 * never part of a production build.
 */
function previewLogin(): Plugin {
  const fakeSession = "JSON.stringify({ idToken: 'local-preview', expiresAt: Date.now() + 86400000 })"

  return {
    name: 'preview-login',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/__preview-login', (_request, response) => {
        response.setHeader('Content-Type', 'text/html')
        response.end(`<script>localStorage.setItem('sv_oauth_tokens', ${fakeSession}); location.replace('/')</script>`)
      })
    },
  }
}

const usesLocalApi = process.env.VITE_API_URL?.startsWith('http://localhost') ?? false

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), ...(usesLocalApi ? [previewLogin()] : [])],
  // amazon-cognito-identity-js expects a Node-style `global`; browsers only have `globalThis`.
  define: { global: 'globalThis' },
})
