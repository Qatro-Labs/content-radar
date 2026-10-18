import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const auth = vi.hoisted(() => ({
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(),
  signInWithPassword: vi.fn(),
  signOut: vi.fn(),
}))

vi.mock('@supabase/supabase-js', () => ({ createClient: vi.fn(() => ({ auth })) }))
// El Radar real arrastra ECharts y la API: aquí solo importa a dónde lleva la navegación.
vi.mock('@/views/DiscoverView.vue', () => ({ default: { render: () => null } }))
vi.mock('@/views/LoginView.vue', () => ({ default: { render: () => null } }))

async function loadRouter() {
  const { router } = await import('../index')
  return router
}

describe('auth guard', () => {
  beforeEach(() => {
    vi.resetModules()
    auth.getSession.mockResolvedValue({ data: { session: null }, error: null })
    vi.stubEnv('VITE_SUPABASE_URL', 'https://project.supabase.test')
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'anon-key')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('sends a visitor without a session to the login when the login is required', async () => {
    vi.stubEnv('VITE_AUTH_REQUIRED', 'true')
    const router = await loadRouter()

    await router.push('/?period=24h')

    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/?period=24h')
  })

  it('lets a signed-in visitor through when the login is required', async () => {
    vi.stubEnv('VITE_AUTH_REQUIRED', 'true')
    auth.getSession.mockResolvedValue({
      data: { session: { access_token: 'token', user: { email: 'ana@example.com' } } },
      error: null,
    })
    const router = await loadRouter()

    await router.push('/')

    expect(router.currentRoute.value.name).toBe('discover')
  })

  it('does not redirect when the login is optional', async () => {
    vi.stubEnv('VITE_AUTH_REQUIRED', '')
    const router = await loadRouter()

    await router.push('/')

    expect(router.currentRoute.value.name).toBe('discover')
  })

  it('does not redirect when the login is required but Supabase is not configured', async () => {
    vi.stubEnv('VITE_AUTH_REQUIRED', 'true')
    vi.stubEnv('VITE_SUPABASE_URL', '')
    const router = await loadRouter()

    await router.push('/')

    expect(router.currentRoute.value.name).toBe('discover')
  })
})
