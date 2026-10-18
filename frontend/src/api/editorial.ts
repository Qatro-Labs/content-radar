import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'

import { useAuth } from '@/composables/useAuth'

import { api, type Schemas } from './client'
import { USING_FIXTURES } from './opportunities'

type BriefRequest = Schemas['BriefRequest']
type EditorialBrief = Schemas['EditorialBrief']
type SavedBrief = Schemas['SavedBrief']
type SavedBriefSummary = Schemas['SavedBriefSummary']

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
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: postBrief,
    retry: false,
    // Con sesión la API lo guarda y devuelve su id: «Mis briefs» lo enseña sin recargar.
    onSuccess: (brief) => {
      if (brief.id != null) void queryClient.invalidateQueries({ queryKey: SAVED_BRIEFS_KEY })
    },
  })
}

// Los briefs guardados son de quien inició sesión: la clave lleva su correo para que otra cuenta
// no vea la lista de la anterior desde la caché.
const SAVED_BRIEFS_KEY = ['saved-briefs'] as const

async function fetchSavedBriefs(): Promise<SavedBriefSummary[]> {
  const { data, error } = await api.GET('/api/v1/editorial/briefs')
  if (error !== undefined || data === undefined) throw new Error('GET /editorial/briefs falló')
  return data
}

// Un brief de otra cuenta o borrado da 404: la vista lo dice en lugar de reintentar.
async function fetchSavedBrief(id: number): Promise<SavedBrief | null> {
  const { data, error, response } = await api.GET('/api/v1/editorial/briefs/{brief_id}', {
    params: { path: { brief_id: id } },
  })
  if (response.status === BRIEF_NOT_FOUND) return null
  if (error !== undefined || data === undefined) throw new Error('GET /editorial/briefs/{id} falló')
  return data
}

export function useSavedBriefs() {
  const { email, isSignedIn } = useAuth()
  return useQuery({
    queryKey: computed(() => [...SAVED_BRIEFS_KEY, email.value]),
    queryFn: fetchSavedBriefs,
    enabled: isSignedIn,
  })
}

export function useSavedBrief(id: MaybeRefOrGetter<number>) {
  const { email, isSignedIn } = useAuth()
  return useQuery({
    queryKey: computed(() => [...SAVED_BRIEFS_KEY, email.value, toValue(id)]),
    queryFn: () => fetchSavedBrief(toValue(id)),
    enabled: isSignedIn,
  })
}

async function deleteSavedBrief(id: number): Promise<void> {
  const { response } = await api.DELETE('/api/v1/editorial/briefs/{brief_id}', {
    params: { path: { brief_id: id } },
  })
  // Si ya no estaba, el resultado es el mismo: deja de aparecer en la lista.
  if (!response.ok && response.status !== BRIEF_NOT_FOUND) {
    throw new Error('DELETE /editorial/briefs/{id} falló')
  }
}

export function useDeleteSavedBrief() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteSavedBrief,
    retry: false,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: SAVED_BRIEFS_KEY }),
  })
}
