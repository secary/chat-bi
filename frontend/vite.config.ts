import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const proxyTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/chat': proxyTarget,
      '/health': proxyTarget,
      '/upload': proxyTarget,
      '/sessions': proxyTarget,
      '/dashboard': proxyTarget,
      '/admin': proxyTarget,
    },
  },
})
