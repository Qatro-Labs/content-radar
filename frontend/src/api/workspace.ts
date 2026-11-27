import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed } from 'vue'

import { api, type Schemas } from './client'

type WorkspaceRead = Schemas['WorkspaceRead']
type ProfileRead = Schemas['ProfileRead']
type ProfileUpdate = Schemas['ProfileUpdate']

export const PROFILE_KEY = ['profile'] as const
const WORKSPACE_KEY = ['workspace'] as const

export const PROFILE_CONFLICT = 409
const SAVE_FALLBACK_MESSAGE = 'No se pudo guardar el perfil.'

export class ProfileSaveError extends Error {
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

async function fetchWorkspace(): Promise<WorkspaceRead> {
  const { data, error } = await api.GET('/api/v1/workspace')
  if (error !== undefined || data === undefined) throw new Error('GET /workspace falló')
  return data
}

async function fetchProfile(): Promise<ProfileRead> {
  const { data, error } = await api.GET('/api/v1/profile')
  if (error !== undefined || data === undefined) throw new Error('GET /profile falló')
  return data
}

async function putProfile(update: ProfileUpdate): Promise<ProfileRead> {
  const { data, error, response } = await api.PUT('/api/v1/profile', { body: update })
  if (data !== undefined) return data
  throw new ProfileSaveError(response.status, detailOf(error) ?? SAVE_FALLBACK_MESSAGE)
}

export function useWorkspace() {
  return useQuery({ queryKey: WORKSPACE_KEY, queryFn: fetchWorkspace })
}

export function useProfile() {
  return useQuery({ queryKey: PROFILE_KEY, queryFn: fetchProfile })
}

// Sin reintentos: un 409 significa que alguien guardó antes, y repetir el mismo PUT lo pisaría.
export function useSaveProfile() {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: putProfile,
    retry: false,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROFILE_KEY }),
  })
  const conflict = computed(
    () =>
      mutation.error.value instanceof ProfileSaveError &&
      mutation.error.value.status === PROFILE_CONFLICT,
  )
  return { ...mutation, conflict }
}

export function canEdit(workspace: WorkspaceRead | undefined): boolean {
  return workspace?.role === 'owner' || workspace?.role === 'member'
}
