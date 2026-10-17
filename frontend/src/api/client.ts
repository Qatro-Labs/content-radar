import createClient from 'openapi-fetch'

import type { components, paths } from '@/types/api'

export type Schemas = components['schemas']

// Vacío en desarrollo: las rutas ya empiezan por /api y Vite hace de proxy (vite.config.ts).
export const api = createClient<paths>({ baseUrl: import.meta.env.VITE_API_BASE_URL ?? '' })
