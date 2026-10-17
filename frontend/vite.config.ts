import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

const API_DEV_TARGET = process.env.API_DEV_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // Mismo origen en desarrollo: el navegador no necesita CORS hacia la API local.
    proxy: {
      '/api': API_DEV_TARGET,
      '/health': API_DEV_TARGET,
    },
  },
  test: {
    environment: 'jsdom',
  },
})
