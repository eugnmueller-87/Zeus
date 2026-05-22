import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  esbuild: { loader: 'jsx', include: /src\/.*\.[jt]sx?$/ },
  optimizeDeps: { esbuildOptions: { loader: { '.js': 'jsx' } } },
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8081',
      '/ws': { target: 'ws://localhost:8081', ws: true },
    },
  },
})
