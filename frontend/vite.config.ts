import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // amazon-cognito-identity-js expects a Node-style `global`; browsers only have `globalThis`.
  define: { global: 'globalThis' },
})
