import fixture from '@fixtures/opportunities.json'
import { cleanup, fireEvent, render, screen } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

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

// El fixture se generó contra el schema de Opportunity (opportunities.spec.ts lo vigila).
const OPPORTUNITY = fixture.opportunities.items[0] as Schemas['Opportunity']
const EVIDENCE = (fixture.evidence as Record<string, Schemas['Evidence'][]>)[OPPORTUNITY.id] ?? []

const REQUEST: Schemas['BriefRequest'] = {
  opportunity_id: OPPORTUNITY.id,
  platform: 'linkedin',
  goal: 'educate',
  format: 'carousel',
}

const BRIEF: Schemas['EditorialBrief'] = {
  ...REQUEST,
  topic: 'Evaluación de agentes de IA',
  recommendation: 'publish_now',
  angle: 'Medir un agente es medir un proceso.',
  hook: 'Tu agente no falla: falla cómo lo mides.',
  structure: ['El problema'],
  key_points: [],
  why_it_fits: null,
  evidence: [],
  limitations: [],
  model: 'claude-haiku-5-5',
}

const SUMMARY: Schemas['SavedBriefSummary'] = {
  id: 7,
  ...REQUEST,
  topic: BRIEF.topic,
  created_at: '2026-10-17T19:00:00Z',
}

interface ApiStub {
  savedBriefs?: Schemas['SavedBriefSummary'][]
  postedBrief?: Schemas['EditorialBrief']
}

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } })
}

function respond(request: Request, stub: ApiStub): Response {
  const path = new URL(request.url).pathname
  if (path === '/api/v1/editorial/briefs') return json(stub.savedBriefs ?? [])
  if (path === `/api/v1/editorial/briefs/${SUMMARY.id}` && request.method === 'DELETE') {
    stub.savedBriefs = (stub.savedBriefs ?? []).filter((saved) => saved.id !== SUMMARY.id)
    return new Response(null, { status: 204 })
  }
  if (path === `/api/v1/editorial/briefs/${SUMMARY.id}`) {
    return json({ id: SUMMARY.id, created_at: SUMMARY.created_at, request: REQUEST, brief: BRIEF })
  }
  if (path === '/api/v1/editorial/brief') return json(stub.postedBrief ?? BRIEF)
  if (path === `/api/v1/opportunities/${OPPORTUNITY.id}`) return json(OPPORTUNITY)
  if (path === `/api/v1/opportunities/${OPPORTUNITY.id}/evidence`) return json(EVIDENCE)
  if (path === '/api/v1/opportunities') {
    return json({ ...fixture.opportunities, items: [] })
  }
  return new Response('{}', { status: 404, headers: { 'Content-Type': 'application/json' } })
}

// openapi-fetch guarda `fetch` al crear el cliente: el stub va antes de importar la vista.
function stubApi(stub: ApiStub = {}) {
  const fetchMock = vi.fn<typeof fetch>(async (input) => {
    if (!(input instanceof Request)) throw new Error('openapi-fetch no envió un Request')
    return respond(input, stub)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function requestedPaths(fetchMock: ReturnType<typeof stubApi>): string[] {
  return fetchMock.mock.calls.map(([input]) =>
    input instanceof Request ? new URL(input.url).pathname : '',
  )
}

async function renderCreateAt(url: string) {
  const [{ default: CreateView }, { QueryClient, VueQueryPlugin }] = await Promise.all([
    import('../CreateView.vue'),
    import('@tanstack/vue-query'),
  ])
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'discover', component: Blank },
      { path: '/explore/:id', name: 'dossier', component: Blank },
      { path: '/create', name: 'create', component: CreateView },
      { path: '/login', name: 'login', component: Blank },
    ],
  })
  await router.push(url)
  await router.isReady()
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(CreateView, { global: { plugins: [router, [VueQueryPlugin, { queryClient }]] } })
  return router
}

describe('CreateView · Mis briefs', () => {
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

  it('hides the list and invites to sign in when signed out', async () => {
    const fetchMock = stubApi({ savedBriefs: [SUMMARY] })

    await renderCreateAt('/create')

    const link = await screen.findByRole('link', { name: 'Inicia sesión para guardar tus briefs' })
    expect(link.getAttribute('href')).toBe('/login?redirect=/create')
    expect(screen.queryByText(SUMMARY.topic)).toBeNull()
    expect(requestedPaths(fetchMock)).not.toContain('/api/v1/editorial/briefs')
  })

  it('renders nothing of the history when Supabase is not configured', async () => {
    vi.stubEnv('VITE_SUPABASE_ANON_KEY', '')
    stubApi({ savedBriefs: [SUMMARY] })

    await renderCreateAt('/create')

    expect(await screen.findByText('Todavía no hay temas analizados.')).toBeTruthy()
    expect(screen.queryByRole('region', { name: 'Mis briefs' })).toBeNull()
  })

  describe('signed in', () => {
    beforeEach(() => {
      auth.getSession.mockResolvedValue({ data: { session: SESSION }, error: null })
    })

    it('lists the saved briefs and opens one, keeping it in the URL', async () => {
      stubApi({ savedBriefs: [SUMMARY] })
      const router = await renderCreateAt('/create')

      const item = await screen.findByRole('link', { name: /Evaluación de agentes de IA/ })
      expect(item.textContent).toContain('Carrusel · LinkedIn · 17/10')
      await fireEvent.click(item)

      await vi.waitFor(() => expect(router.currentRoute.value.query.brief).toBe('7'))
      expect(await screen.findByText(`«${BRIEF.hook}»`)).toBeTruthy()
      expect(screen.getByText('Brief guardado el 17/10, 19:00 UTC')).toBeTruthy()
    })

    it('deletes a saved brief and closes it when it was open', async () => {
      const fetchMock = stubApi({ savedBriefs: [SUMMARY] })
      const router = await renderCreateAt(`/create?brief=${SUMMARY.id}`)

      await fireEvent.click(
        await screen.findByRole('button', { name: `Borrar el brief «${SUMMARY.topic}»` }),
      )

      expect(await screen.findByText('Todavía no has creado briefs.')).toBeTruthy()
      await vi.waitFor(() => expect(router.currentRoute.value.query.brief).toBeUndefined())
      const deletions = fetchMock.mock.calls.filter(
        ([input]) => input instanceof Request && input.method === 'DELETE',
      )
      expect(deletions).toHaveLength(1)
    })

    it('says there are no briefs yet when the list is empty', async () => {
      stubApi({ savedBriefs: [] })

      await renderCreateAt('/create')

      expect(await screen.findByText('Todavía no has creado briefs.')).toBeTruthy()
    })

    it('marks a new brief as saved when the API returns its id', async () => {
      const fetchMock = stubApi({ savedBriefs: [], postedBrief: { ...BRIEF, id: 12 } })

      await renderCreateAt(
        `/create?opportunity=${OPPORTUNITY.id}&platform=linkedin&goal=educate&format=carousel`,
      )

      expect(await screen.findByText('Guardado en Mis briefs')).toBeTruthy()
      // La lista se pide otra vez para que el brief nuevo aparezca sin recargar.
      await vi.waitFor(() =>
        expect(
          requestedPaths(fetchMock).filter((path) => path === '/api/v1/editorial/briefs'),
        ).toHaveLength(2),
      )
    })

    it('does not mark the brief as saved without an id', async () => {
      stubApi({ savedBriefs: [], postedBrief: { ...BRIEF, id: null } })

      await renderCreateAt(
        `/create?opportunity=${OPPORTUNITY.id}&platform=linkedin&goal=educate&format=carousel`,
      )

      expect(await screen.findByText(`«${BRIEF.hook}»`)).toBeTruthy()
      expect(screen.queryByText('Guardado en Mis briefs')).toBeNull()
    })
  })
})
