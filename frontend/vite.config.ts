import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

const API_DEV_TARGET = process.env.API_DEV_TARGET ?? 'http://localhost:8000'
const REPO_ROOT = fileURLToPath(new URL('..', import.meta.url))

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@fixtures': fileURLToPath(new URL('../data/fixtures', import.meta.url)),
    },
  },
  server: {
    // Los fixtures viven fuera de frontend/ (data/fixtures, compartidos con el backend) y Vite
    // solo sirve su propio workspace: sin esto, el JSON de `@fixtures` da 403 en desarrollo.
    fs: {
      allow: [REPO_ROOT],
    },
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
