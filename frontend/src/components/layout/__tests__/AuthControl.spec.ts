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

interface SessionResult {
  data: { session: typeof SESSION | null }
  error: null
}

// Una recarga con sesión: `getSession` tarda en responder y el control no debe invitar a entrar.
function deferSession() {
  let resolve: (value: SessionResult) => void = () => {}
  auth.getSession.mockReturnValue(new Promise<SessionResult>((done) => (resolve = done)))
  return (value: SessionResult) => resolve(value)
}

async function renderControl() {
  const { default: AuthControl } = await import('../AuthControl.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'discover', component: Blank },
      { path: '/login', name: 'login', component: Blank },
    ],
  })
  await router.push('/')
  await router.isReady()
  render(AuthControl, { global: { plugins: [router] } })
  return router
}

async function renderSignedIn() {
  const resolveSession = deferSession()
  auth.signOut.mockResolvedValue({ error: null })
  const router = await renderControl()
  resolveSession({ data: { session: SESSION }, error: null })
  return router
}

// Reka abre el menú con pointerdown o teclado, y lo pinta en un portal sobre `document.body`;
// `screen` consulta todo el body, así que lo encuentra igual.
async function openAccountMenu() {
  const trigger = await screen.findByRole('button', { name: 'Cuenta' })
  trigger.focus()
  await fireEvent.keyDown(trigger, { key: 'Enter' })
}

describe('AuthControl', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.stubEnv('VITE_SUPABASE_URL', 'https://project.supabase.test')
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'anon-key')
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
  })

  it('never offers to sign in while a signed-in session is still loading', async () => {
    const resolveSession = deferSession()
    await renderControl()

    expect(screen.queryByText('Iniciar sesión')).toBeNull()

    resolveSession({ data: { session: SESSION }, error: null })

    expect(await screen.findByRole('button', { name: 'Cuenta' })).toBeTruthy()
    expect(screen.queryByText('Iniciar sesión')).toBeNull()
  })

  it('shows the initial of the email on the account trigger', async () => {
    await renderSignedIn()

    const trigger = await screen.findByRole('button', { name: 'Cuenta' })

    expect(trigger.textContent?.trim()).toBe('A')
  })

  it('shows the email and signs out from the account menu', async () => {
    await renderSignedIn()

    expect(screen.queryByText('ana@example.com')).toBeNull()
    await openAccountMenu()

    expect(await screen.findByText('ana@example.com')).toBeTruthy()
    expect(screen.getByText('Sesión iniciada')).toBeTruthy()
    await fireEvent.click(await screen.findByRole('menuitem', { name: 'Cerrar sesión' }))

    expect(auth.signOut).toHaveBeenCalledOnce()
  })

  it('goes to the login page after signing out when login is required', async () => {
    vi.stubEnv('VITE_AUTH_REQUIRED', 'true')
    const router = await renderSignedIn()

    await openAccountMenu()
    await fireEvent.click(await screen.findByRole('menuitem', { name: 'Cerrar sesión' }))

    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('login'))
  })

  it('offers to sign in once the session resolves empty', async () => {
    const resolveSession = deferSession()
    await renderControl()

    resolveSession({ data: { session: null }, error: null })

    expect(await screen.findByRole('link', { name: 'Iniciar sesión' })).toBeTruthy()
  })
})
