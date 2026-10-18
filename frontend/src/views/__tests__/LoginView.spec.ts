import { cleanup, fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

const supabaseJs = vi.hoisted(() => {
  const auth = {
    getSession: vi.fn(),
    onAuthStateChange: vi.fn(),
    signInWithPassword: vi.fn(),
    signOut: vi.fn(),
  }
  return { auth, createClient: vi.fn(() => ({ auth })) }
})

vi.mock('@supabase/supabase-js', () => ({ createClient: supabaseJs.createClient }))

const { auth } = supabaseJs
const SESSION = { access_token: 'token', user: { email: 'ana@example.com' } }
const Blank = { render: () => null }

async function renderLoginAt(url: string, { guarded = false } = {}) {
  const { default: LoginView } = await import('../LoginView.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'discover', component: Blank },
      { path: '/explore/:id', name: 'dossier', component: Blank },
      { path: '/login', name: 'login', component: LoginView },
    ],
  })
  if (guarded) {
    const { hasSession } = await import('@/composables/useAuth')
    const { createAuthGuard } = await import('@/router/authGuard')
    router.beforeEach(createAuthGuard(hasSession))
  }
  await router.push(url)
  await router.isReady()
  render(LoginView, { global: { plugins: [router] } })
  return router
}

async function submitCredentials() {
  await fireEvent.update(screen.getByLabelText('Correo'), 'ana@example.com')
  await fireEvent.update(screen.getByLabelText('Contraseña'), 'secreta')
  await fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
}

describe('LoginView', () => {
  beforeEach(() => {
    vi.resetModules()
    supabaseJs.createClient.mockClear()
    auth.getSession.mockResolvedValue({ data: { session: null }, error: null })
    vi.stubEnv('VITE_SUPABASE_URL', 'https://project.supabase.test')
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'anon-key')
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
  })

  it('shows the error and stays on the login when the credentials are rejected', async () => {
    auth.signInWithPassword.mockResolvedValue({
      data: { session: null, user: null },
      error: { code: 'invalid_credentials', message: 'Invalid login credentials' },
    })
    const router = await renderLoginAt('/login')

    await submitCredentials()

    expect(await screen.findByRole('alert')).toHaveProperty(
      'textContent',
      expect.stringContaining('Correo o contraseña incorrectos.'),
    )
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('goes to the redirect target after signing in', async () => {
    auth.signInWithPassword.mockResolvedValue({
      data: { session: SESSION, user: SESSION.user },
      error: null,
    })
    const router = await renderLoginAt('/login?redirect=/explore/opp_001')

    await submitCredentials()

    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/explore/opp_001'))
    expect(auth.signInWithPassword).toHaveBeenCalledWith({
      email: 'ana@example.com',
      password: 'secreta',
    })
  })

  // Regresión: el guard recordaba la sesión de la primera carga (ninguna) y devolvía al login.
  it('passes the auth guard right after signing in', async () => {
    auth.signInWithPassword.mockResolvedValue({
      data: { session: SESSION, user: SESSION.user },
      error: null,
    })
    const router = await renderLoginAt('/login?redirect=/explore/opp_001', { guarded: true })

    await submitCredentials()

    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/explore/opp_001'))
  })

  it('sends back to the login after signing out', async () => {
    auth.getSession.mockResolvedValue({ data: { session: SESSION }, error: null })
    auth.signOut.mockResolvedValue({ error: null })
    const router = await renderLoginAt('/login', { guarded: true })
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('discover'))

    const { useAuth } = await import('@/composables/useAuth')
    await useAuth().signOut()
    await router.push('/explore/opp_001')

    expect(router.currentRoute.value.name).toBe('login')
  })

  it('goes to the Radar when the redirect points outside the app', async () => {
    auth.signInWithPassword.mockResolvedValue({
      data: { session: SESSION, user: SESSION.user },
      error: null,
    })
    const router = await renderLoginAt('/login?redirect=//evil.example')

    await submitCredentials()

    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('discover'))
  })

  it('goes to the Radar after signing in without a redirect', async () => {
    auth.signInWithPassword.mockResolvedValue({
      data: { session: SESSION, user: SESSION.user },
      error: null,
    })
    const router = await renderLoginAt('/login')

    await submitCredentials()

    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('discover'))
  })

  it('sends a signed-in visitor straight to the Radar without showing the form', async () => {
    let resolveSession: (value: unknown) => void = () => {}
    auth.getSession.mockReturnValue(new Promise((done) => (resolveSession = done)))
    const router = await renderLoginAt('/login')

    expect(screen.queryByRole('heading', { name: 'Iniciar sesión' })).toBeNull()
    expect(screen.queryByLabelText('Correo')).toBeNull()

    resolveSession({ data: { session: SESSION }, error: null })

    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('discover'))
    expect(screen.queryByLabelText('Correo')).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Sesión iniciada' })).toBeNull()
  })

  it('sends a signed-in visitor to the redirect target', async () => {
    auth.getSession.mockResolvedValue({ data: { session: SESSION }, error: null })
    const router = await renderLoginAt('/login?redirect=/explore/opp_001')

    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/explore/opp_001'))
  })

  it('says the login is not configured and creates no Supabase client without its env vars', async () => {
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', '')

    await renderLoginAt('/login')

    expect(screen.getByRole('heading', { name: 'Login no configurado' })).toBeTruthy()
    expect(screen.queryByLabelText('Correo')).toBeNull()
    expect(supabaseJs.createClient).not.toHaveBeenCalled()
  })
})
