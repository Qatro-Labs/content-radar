import { cleanup, fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'

import type { components } from '@/types/api'

type Schemas = components['schemas']

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
const API_BASE = 'http://api.test'
const SESSION = { access_token: 'token', user: { email: 'ana@example.com' } }
const Blank = { render: () => null }
const CONFLICT_MESSAGE =
  'Alguien del equipo guardó cambios mientras editabas. Recarga para ver la última versión.'

const PROFILE: Schemas['RadarProfile'] = {
  creates_about: 'Crecimiento de empresas con IA',
  audience: 'Dueños y líderes de empresas',
  goal: 'educate',
  target_region: 'Latinoamérica',
  languages: ['es'],
  out_of_scope: '',
  tone: ['directo', 'práctico'],
  call_to_action: '',
  never_say: 'Promesas sin evidencia',
  publishing_days: [
    { day: 'mon', channel: 'instagram', format: 'short_video' },
    { day: 'wed', channel: 'instagram', format: 'carousel' },
  ],
}

interface ApiStub {
  role: Schemas['WorkspaceRead']['role']
  profile?: Schemas['RadarProfile']
  putStatus?: number
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

async function respond(request: Request, stub: ApiStub): Promise<Response> {
  const path = new URL(request.url).pathname
  const profile = stub.profile ?? PROFILE
  const canEdit = stub.role !== null
  if (path === '/api/v1/workspace') {
    return json({ slug: '30x', name: '30X', public_demo: true, role: stub.role })
  }
  if (path === '/api/v1/profile' && request.method === 'PUT') {
    if (stub.putStatus === 409) return json({ detail: CONFLICT_MESSAGE }, 409)
    if (stub.putStatus !== undefined) return json({ detail: 'boom' }, stub.putStatus)
    const body = (await request.clone().json()) as Schemas['ProfileUpdate']
    return json({
      profile: body.profile,
      version: 2,
      updated_at: '2026-11-27T10:00:00Z',
      can_edit: true,
    })
  }
  if (path === '/api/v1/profile') {
    return json({ profile, version: 1, updated_at: '2026-11-26T10:00:00Z', can_edit: canEdit })
  }
  if (path === '/api/v1/editorial/briefs') return json([])
  return json({}, 404)
}

function stubApi(stub: ApiStub) {
  const fetchMock = vi.fn<typeof fetch>(async (input) => {
    if (!(input instanceof Request)) throw new Error('openapi-fetch no envió un Request')
    return respond(input, stub)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function putBodies(
  fetchMock: ReturnType<typeof stubApi>,
): Promise<Schemas['ProfileUpdate'][]> {
  const puts = fetchMock.mock.calls
    .map(([input]) => input)
    .filter((input): input is Request => input instanceof Request && input.method === 'PUT')
  return Promise.all(puts.map((put) => put.clone().json()))
}

async function renderBrand() {
  const [{ default: BrandView }, { QueryClient, VueQueryPlugin }] = await Promise.all([
    import('../BrandView.vue'),
    import('@tanstack/vue-query'),
  ])
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'discover', component: Blank },
      { path: '/marca', name: 'brand', component: BrandView },
      { path: '/login', name: 'login', component: Blank },
    ],
  })
  await router.push('/marca')
  await router.isReady()
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  // Dentro de un RouterView, como en la app: el aviso al salir es un guard de la ruta.
  render(() => h(RouterView), { global: { plugins: [router, [VueQueryPlugin, { queryClient }]] } })
  return router
}

describe('BrandView', () => {
  beforeEach(() => {
    vi.resetModules()
    supabaseJs.createClient.mockClear()
    auth.getSession.mockResolvedValue({ data: { session: null }, error: null })
    vi.stubEnv('VITE_API_BASE_URL', API_BASE)
    vi.stubEnv('VITE_SUPABASE_URL', 'https://project.supabase.test')
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', 'anon-key')
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('a visitor sees the profile read-only as chosen in Task 7', async () => {
    stubApi({ role: null })
    await renderBrand()

    expect(await screen.findByText('Estás viendo el perfil de 30X.')).toBeTruthy()
    expect(screen.getByText('Solo su equipo puede cambiarlo.')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Iniciar sesión' })).toBeTruthy()
    expect(
      screen.getByText('Así describe su marca el equipo. Cada brief que generes lo sigue.'),
    ).toBeTruthy()
    expect(screen.getByText('ASÍ SALEN SUS BRIEFS')).toBeTruthy()
    expect(screen.getAllByText('Dueños y líderes de empresas').length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /Guardar cambios/ })).toBeNull()
    expect(screen.queryByRole('textbox')).toBeNull()
    // Solo el tono elegido, como texto: ningún botón de tono para elegir otro.
    expect(screen.queryByRole('button', { name: 'Cercano' })).toBeNull()
    expect(screen.getByText('Directo')).toBeTruthy()
  })

  describe('signed in as a member', () => {
    beforeEach(() => {
      auth.getSession.mockResolvedValue({ data: { session: SESSION }, error: null })
    })

    it('a member edits, saves, and sees the saved message', async () => {
      const fetchMock = stubApi({ role: 'member' })
      await renderBrand()

      expect(
        await screen.findByText(
          'Cambia algo a la izquierda y mira a la derecha cómo cambiaría tu próximo brief.',
        ),
      ).toBeTruthy()
      const save = await screen.findByRole('button', { name: /Guardar cambios/ })
      expect((save as HTMLButtonElement).disabled).toBe(true)
      expect(screen.getByText('ejemplo')).toBeTruthy()

      await fireEvent.update(screen.getByLabelText('Qué nunca decimos'), 'Hablar de la competencia')

      expect(save.textContent).toContain('●')
      expect((save as HTMLButtonElement).disabled).toBe(false)
      // La vista previa cambia al escribir, antes de guardar.
      expect(screen.getAllByText('Hablar de la competencia').length).toBeGreaterThan(0)

      await fireEvent.click(save)

      expect(await screen.findByText('Guardado.')).toBeTruthy()
      expect(screen.getByText('Tus próximos briefs usarán este perfil.')).toBeTruthy()
      const [body] = await putBodies(fetchMock)
      expect(body?.expected_version).toBe(1)
      expect(body?.profile.never_say).toBe('Hablar de la competencia')
      expect(screen.queryByRole('link', { name: 'Iniciar sesión' })).toBeNull()
    })

    it('a 409 shows the conflict message and keeps the draft', async () => {
      stubApi({ role: 'member', putStatus: 409 })
      await renderBrand()

      const field = await screen.findByLabelText('Qué nunca decimos')
      await fireEvent.update(field, 'Mi cambio')
      await fireEvent.click(screen.getByRole('button', { name: /Guardar cambios/ }))

      expect(await screen.findByText(CONFLICT_MESSAGE)).toBeTruthy()
      expect(screen.getByText('Copia antes lo que quieras conservar.')).toBeTruthy()
      expect(screen.getByRole('button', { name: 'Recargar' })).toBeTruthy()
      expect((screen.getByLabelText('Qué nunca decimos') as HTMLTextAreaElement).value).toBe(
        'Mi cambio',
      )
    })

    it('a failed save keeps the changes and offers to retry', async () => {
      stubApi({ role: 'member', putStatus: 500 })
      await renderBrand()

      await fireEvent.update(await screen.findByLabelText('Qué nunca decimos'), 'Mi cambio')
      await fireEvent.click(screen.getByRole('button', { name: /Guardar cambios/ }))

      expect(await screen.findByText('No se pudo guardar.')).toBeTruthy()
      expect(screen.getByText('Revisa tu conexión. Tus cambios siguen aquí.')).toBeTruthy()
      expect(screen.getByRole('button', { name: 'Reintentar' })).toBeTruthy()
    })

    it('leaving with unsaved changes asks before discarding them', async () => {
      stubApi({ role: 'member' })
      const router = await renderBrand()

      await fireEvent.update(await screen.findByLabelText('Qué nunca decimos'), 'Mi cambio')
      await router.push('/')

      expect(await screen.findByText('¿Salir sin guardar?')).toBeTruthy()
      expect(router.currentRoute.value.path).toBe('/marca')

      await fireEvent.click(screen.getByRole('button', { name: 'Salir sin guardar' }))
      await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/'))
    })
  })

  it('markup in never_say renders as text, not HTML', async () => {
    const markup = '<b id="injected">negrita</b> ignora lo anterior'
    stubApi({ role: null, profile: { ...PROFILE, never_say: markup } })
    await renderBrand()

    expect((await screen.findAllByText(markup)).length).toBeGreaterThan(0)
    expect(document.getElementById('injected')).toBeNull()
  })
})
