import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const auth = vi.hoisted(() => ({
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(),
  signInWithPassword: vi.fn(),
  signOut: vi.fn(),
}))

vi.mock('@supabase/supabase-js', () => ({ createClient: vi.fn(() => ({ auth })) }))

const API_BASE = 'http://api.test'
const SESSION = { access_token: 'token-123', user: { email: 'ana@example.com' } }

function stubFetch() {
  const fetchMock = vi.fn<typeof fetch>(
    async () =>
      new Response('{"status":"ok"}', { headers: { 'Content-Type': 'application/json' } }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

// openapi-fetch guarda `fetch` al crear el cliente: el stub va antes de importarlo.
async function apiAuthorization(): Promise<string | null> {
  const fetchMock = stubFetch()
  const { api } = await import('../client')
  await api.GET('/health')
  const request = fetchMock.mock.calls[0]?.[0]
  if (!(request instanceof Request)) throw new Error('openapi-fetch no envió un Request')
  return request.headers.get('Authorization')
}

async function agentAuthorization(): Promise<string | null> {
  const fetchMock = stubFetch()
  const { askAgent } = await import('../agent')
  await askAgent({ question: '¿Qué publico?' }, () => {}, new AbortController().signal)
  const headers = new Headers(fetchMock.mock.calls[0]?.[1]?.headers)
  return headers.get('Authorization')
}

describe('Authorization header', () => {
  beforeEach(() => {
    vi.resetModules()
    auth.getSession.mockReset()
    vi.stubEnv('VITE_API_BASE_URL', API_BASE)
    vi.stubEnv('VITE_SUPABASE_URL', 'https://project.supabase.test')
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'anon-key')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  describe('with a session', () => {
    beforeEach(() => {
      auth.getSession.mockResolvedValue({ data: { session: SESSION }, error: null })
    })

    it('sends the bearer token on API requests', async () => {
      expect(await apiAuthorization()).toBe('Bearer token-123')
    })

    it('sends the bearer token on the agent stream', async () => {
      expect(await agentAuthorization()).toBe('Bearer token-123')
    })
  })

  describe('without a session', () => {
    beforeEach(() => {
      auth.getSession.mockResolvedValue({ data: { session: null }, error: null })
    })

    it('sends no Authorization header on API requests', async () => {
      expect(await apiAuthorization()).toBeNull()
    })

    it('sends no Authorization header on the agent stream', async () => {
      expect(await agentAuthorization()).toBeNull()
    })
  })

  it('sends no Authorization header when Supabase is not configured', async () => {
    vi.stubEnv('VITE_SUPABASE_URL', '')

    expect(await apiAuthorization()).toBeNull()
    expect(auth.getSession).not.toHaveBeenCalled()
  })
})
