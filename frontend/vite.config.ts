import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Open the system default browser on `npm run dev` (instead of VS Code's built-in one).
  server: { open: true },
})
