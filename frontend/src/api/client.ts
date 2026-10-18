import createClient, { type Middleware } from 'openapi-fetch'

import { authorizationHeaders } from '@/lib/supabase'
import type { components, paths } from '@/types/api'

export type Schemas = components['schemas']

// Vacío en desarrollo: las rutas ya empiezan por /api y Vite hace de proxy (vite.config.ts).
// El stream del agente (agent.ts) usa la misma base con `fetch`.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

const authMiddleware: Middleware = {
  async onRequest({ request }) {
    for (const [name, value] of Object.entries(await authorizationHeaders())) {
      request.headers.set(name, value)
    }
    return request
  },
}

export const api = createClient<paths>({ baseUrl: API_BASE_URL })
api.use(authMiddleware)
