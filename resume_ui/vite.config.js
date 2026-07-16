import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const rootDir = dirname(fileURLToPath(import.meta.url))

export default defineConfig(({ mode }) => ({
  root: rootDir,
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
    outDir: resolve(rootDir, '../static/app'),
    emptyOutDir: true,
    assetsDir: 'assets',
    cssCodeSplit: true,
  },
}))
