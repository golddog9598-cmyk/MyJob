import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'node:path'

export default defineConfig(({ mode }) => ({
  plugins: [vue()],
  base: mode === 'production' ? '/static/app/' : '/',
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'https://127.0.0.1:8010',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'wss://127.0.0.1:8010',
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
  build: {
    outDir: resolve(__dirname, '../static/app'),
    emptyOutDir: true,
    assetsDir: 'assets',
    cssCodeSplit: true,
  },
}))
