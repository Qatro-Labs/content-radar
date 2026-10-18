import { useMutation } from '@tanstack/vue-query'

import { api, type Schemas } from './client'
import { USING_FIXTURES } from './opportunities'

type BriefRequest = Schemas['BriefRequest']
type EditorialBrief = Schemas['EditorialBrief']

// 404 tema fuera del análisis servido · 409 sin evidencia segura · 429 cupo · 502 falló el LLM ·
// 503 sin LLM. La API explica cada uno en `detail`, ya en español y para mostrar tal cual.
export const BRIEF_NOT_FOUND = 404
const FALLBACK_MESSAGE = 'No se pudo generar el brief.'
const NETWORK_MESSAGE = 'No se pudo conectar con la API.'
const FIXTURES_MESSAGE = 'Con datos de ejemplo no se generan briefs: hace falta la API.'
// Sin respuesta HTTP (red caída o CORS) no hay código que mostrar.
export const NO_RESPONSE = 0

export class BriefError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

// Un 422 trae `detail` como lista de errores de validación: ese no se muestra.
function detailOf(body: unknown): string | null {
  if (typeof body !== 'object' || body === null || !('detail' in body)) return null
  return typeof body.detail === 'string' ? body.detail : null
}

async function postBrief(request: BriefRequest): Promise<EditorialBrief> {
  if (USING_FIXTURES) throw new BriefError(NO_RESPONSE, FIXTURES_MESSAGE)
  let result
  try {
    result = await api.POST('/api/v1/editorial/brief', { body: request })
  } catch {
    throw new BriefError(NO_RESPONSE, NETWORK_MESSAGE)
  }
  const { data, error, response } = result
  if (data !== undefined) return data
  throw new BriefError(response.status, detailOf(error) ?? FALLBACK_MESSAGE)
}

// Un POST, pero idempotente: la API cachea por ejecución y petición, así que repetirlo no vuelve a
// llamar al LLM. Sin reintentos automáticos: un 429 o un 502 se enseñan y decide la persona.
export function useBrief() {
  return useMutation({ mutationFn: postBrief, retry: false })
}
