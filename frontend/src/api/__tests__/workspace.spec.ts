import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createApp, type App } from 'vue'

import type { components } from '@/types/api'

type Schemas = components['schemas']

const auth = vi.hoisted(() => ({
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(),
  signInWithPassword: vi.fn(),
  signOut: vi.fn(),
}))

vi.mock('@supabase/supabase-js', () => ({ createClient: vi.fn(() => ({ auth })) }))

const API_BASE = 'http://api.test'
const CONFLICT_DETAIL =
  'Alguien del equipo guardó cambios mientras editabas. Recarga para ver la última versión.'

const PROFILE = {
  profile: { brand_name: '30X' },
  version: 3,
  updated_at: '2026-11-27T10:00:00Z',
  can_edit: true,
} as unknown as Schemas['ProfileRead']

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function stubFetch(putStatus: number) {
  const fetchMock = vi.fn<typeof fetch>(async (input) => {
    if (!(input instanceof Request)) throw new Error('openapi-fetch no envió un Request')
    const path = new URL(input.url).pathname
    if (path === '/api/v1/profile' && input.method === 'PUT') {
      return putStatus === 409 ? json({ detail: CONFLICT_DETAIL }, 409) : json(PROFILE)
    }
    if (path === '/api/v1/profile') return json(PROFILE)
    if (path === '/api/v1/workspace') {
      const signedIn = input.headers.get('Authorization') !== null
      return json({ slug: '30x', name: '30X', public_demo: true, role: signedIn ? 'member' : null })
    }
    return json({}, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function countOf(fetchMock: ReturnType<typeof stubFetch>, method: string): number {
  return fetchMock.mock.calls.filter(
    ([input]) => input instanceof Request && input.method === method,
  ).length
}

let app: App | null = null

function setup<T>(use: () => T): T {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  let result!: T
  app = createApp({
    setup() {
      result = use()
      return () => null
    },
  })
  app.use(VueQueryPlugin, { queryClient })
  app.mount(document.createElement('div'))
  return result
}

describe('workspace api', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.stubEnv('VITE_API_BASE_URL', API_BASE)
  })

  afterEach(() => {
    app?.unmount()
    app = null
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('saving the profile invalidates the profile query', async () => {
    const fetchMock = stubFetch(200)
    const { useProfile, useSaveProfile } = await import('../workspace')
    const result = setup(() => ({ profile: useProfile(), save: useSaveProfile() }))
    await vi.waitFor(() => expect(result.profile.data.value?.version).toBe(3))
    expect(countOf(fetchMock, 'GET')).toBe(1)

    await result.save.mutateAsync({ profile: PROFILE.profile, expected_version: 3 })

    await vi.waitFor(() => expect(countOf(fetchMock, 'GET')).toBe(2))
    expect(result.save.conflict.value).toBe(false)
  })

  it('a 409 on save is reported as a conflict and not retried', async () => {
    const fetchMock = stubFetch(409)
    const { useSaveProfile } = await import('../workspace')
    const save = setup(() => useSaveProfile())

    await save.mutateAsync({ profile: PROFILE.profile, expected_version: 1 }).catch(() => undefined)

    await vi.waitFor(() => expect(save.conflict.value).toBe(true))
    expect(countOf(fetchMock, 'PUT')).toBe(1)
    expect(save.error.value?.message).toBe(CONFLICT_DETAIL)
  })

  it('refetches the workspace role when the account changes', async () => {
    vi.stubEnv('VITE_SUPABASE_URL', 'https://project.supabase.test')
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'anon-key')
    const session = { access_token: 'token', user: { email: 'ana@example.com' } }
    auth.getSession.mockResolvedValue({ data: { session: null }, error: null })
    auth.signInWithPassword.mockImplementation(async () => {
      auth.getSession.mockResolvedValue({ data: { session }, error: null })
      return { data: { session }, error: null }
    })
    stubFetch(200)
    const { useWorkspace } = await import('../workspace')
    const { useAuth } = await import('@/composables/useAuth')
    const result = setup(() => ({ workspace: useWorkspace(), auth: useAuth() }))
    await vi.waitFor(() => expect(result.workspace.data.value?.role).toBeNull())

    await result.auth.signIn('ana@example.com', 'secret')

    await vi.waitFor(() => expect(result.workspace.data.value?.role).toBe('member'))
  })

  it('canEdit is true only for owners and members', async () => {
    const { canEdit } = await import('../workspace')
    const base = { slug: '30x', name: '30X', public_demo: true }
    expect(canEdit(undefined)).toBe(false)
    expect(canEdit({ ...base, role: null })).toBe(false)
    expect(canEdit({ ...base, role: 'member' })).toBe(true)
    expect(canEdit({ ...base, role: 'owner' })).toBe(true)
  })
})
