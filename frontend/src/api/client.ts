import createClient from 'openapi-fetch'

import type { components, paths } from '@/types/api'

export type Schemas = components['schemas']

// Vacío en desarrollo: las rutas ya empiezan por /api y Vite hace de proxy (vite.config.ts).
// El stream del agente (agent.ts) usa la misma base con `fetch`.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export const api = createClient<paths>({ baseUrl: API_BASE_URL })
