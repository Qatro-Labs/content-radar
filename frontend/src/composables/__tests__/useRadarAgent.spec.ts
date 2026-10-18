import { render } from '@testing-library/vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { AgentRequestError, askAgent } from '@/api/agent'
import { AGENT_TIMING } from '@/lib/agentMotion'
import type { AgentStreamEvent, Navigation, RadarPatch } from '@/lib/agentTypes'
import { RouteName } from '@/router'

import { useRadarAgent } from '../useRadarAgent'

vi.mock('@/api/agent', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/agent')>()
  return { ...actual, askAgent: vi.fn() }
})

// Las marcas que la página real pone en el Radar, la navegación y el expediente (D8). En jsdom
// todas miden 0: no se comprueban coordenadas, sí el orden.
const ANCHORS = [
  'composer',
  'radar',
  'ranking',
  'filter-lc-accelerating',
  'nav-radar',
  'nav-explore',
  'dossier-score',
  'pieces',
]

const Empty = { render: () => null }

async function mountAgent(url = '/') {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: RouteName.Discover, component: Empty },
      { path: '/explore', name: RouteName.Explore, component: Empty },
      { path: '/explore/:id', name: RouteName.Dossier, component: Empty },
    ],
  })
  let agent!: ReturnType<typeof useRadarAgent>
  const Probe = defineComponent({
    setup() {
      agent = useRadarAgent()
      return () =>
        h(
          'div',
          { 'data-agent-root': '' },
          ANCHORS.map((anchor) => h('div', { key: anchor, 'data-agent': anchor })),
        )
    },
  })
  await router.push(url)
  await router.isReady()
  const { unmount } = render(Probe, { global: { plugins: [router] } })
  return { agent, router, unmount }
}

const step = (id: number, status: 'running' | 'done', kind: 'data' | 'view' = 'view') =>
  ({ type: 'step', data: { id, kind, label: 'Pulsando «Acelerando»', status } }) as const

const patchAction = (patch: RadarPatch): AgentStreamEvent => ({
  type: 'action',
  data: { step_id: 1, patch },
})

const navigateAction = (navigate: Navigation): AgentStreamEvent => ({
  type: 'action',
  data: { step_id: 1, navigate },
})

const ANSWER_TEXT = 'Conviene publicar «Agentes» ya.'
const ANSWER_WORDS = 4

function answer(citedIds: string[] = []): AgentStreamEvent {
  return {
    type: 'answer',
    data: {
      text: ANSWER_TEXT,
      cited: citedIds.map((id) => ({
        id,
        topic: 'Agentes de IA',
        lifecycle: 'accelerating',
        opportunity_score: 64,
      })),
      unknowns: ['Sin casos medidos.'],
    },
  }
}

const DONE: AgentStreamEvent = { type: 'done', data: { steps: 1, data_steps: 0, view_steps: 1 } }

// El stream entero llega de golpe, como en la prueba en vivo: el ritmo lo pone el front (D7).
function streams(script: AgentStreamEvent[]) {
  vi.mocked(askAgent).mockImplementationOnce(async (_body, onEvent) => {
    script.forEach(onEvent)
  })
}

const settle = () => vi.advanceTimersByTimeAsync(0)

let unmountAgent: (() => void) | null = null

async function setUp(url = '/') {
  const mounted = await mountAgent(url)
  unmountAgent = mounted.unmount
  return mounted
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined)
})

afterEach(() => {
  // El estado del agente es compartido: sin desmontar, la siguiente prueba heredaría la conversación.
  unmountAgent?.()
  unmountAgent = null
  vi.mocked(askAgent).mockReset()
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('useRadarAgent', () => {
  it('applies a view step only once the presence has reached its target', async () => {
    const { agent, router } = await setUp()
    streams([
      step(1, 'running'),
      step(1, 'done'),
      patchAction({ lifecycle: ['accelerating'] }),
      answer(),
      DONE,
    ])

    void agent.ask('¿Qué acelera?')
    await settle()
    await vi.advanceTimersByTimeAsync(AGENT_TIMING.travelMs - 1)

    expect(router.currentRoute.value.query.lifecycle).toBeUndefined()

    await vi.advanceTimersByTimeAsync(1)

    expect(router.currentRoute.value.query.lifecycle).toBe('accelerating')
  })

  it('writes the answer word by word after the last step, then shows the ending', async () => {
    const { agent } = await setUp()
    streams([
      step(1, 'running'),
      step(1, 'done'),
      patchAction({ lifecycle: ['accelerating'] }),
      answer(),
      DONE,
    ])

    void agent.ask('¿Qué acelera?')
    await settle()
    await vi.advanceTimersByTimeAsync(AGENT_TIMING.stepMs - 1)

    const turn = () => agent.turns.value[0]!
    expect(turn().visibleWords).toBe(0)

    await vi.advanceTimersByTimeAsync(1 + ANSWER_WORDS * AGENT_TIMING.wordMs)

    expect(turn().visibleWords).toBe(ANSWER_WORDS)
    expect(turn().showEnding).toBe(true)
  })

  // Con la barra reducida al ojo, una respuesta que llega se avisa hasta que se abre la barra.
  it('flags an answer that finished while minimized until the bar opens', async () => {
    const { agent } = await setUp()
    streams([step(1, 'running'), step(1, 'done'), answer(), DONE])

    agent.minimize()
    void agent.ask('¿Qué acelera?')
    await settle()
    await vi.advanceTimersByTimeAsync(
      AGENT_TIMING.stepMs + (ANSWER_WORDS + 1) * AGENT_TIMING.wordMs,
    )

    expect(agent.isMinimized.value).toBe(true)
    expect(agent.hasUnread.value).toBe(true)

    agent.expand()

    expect(agent.isMinimized.value).toBe(false)
    expect(agent.hasUnread.value).toBe(false)
  })

  it('drops the pending action on stop and hides the presence', async () => {
    const { agent, router } = await setUp()
    streams([
      step(1, 'running'),
      step(1, 'done'),
      patchAction({ lifecycle: ['accelerating'] }),
      answer(),
      DONE,
    ])

    void agent.ask('¿Qué acelera?')
    await settle()
    await vi.advanceTimersByTimeAsync(AGENT_TIMING.travelMs / 2)
    agent.stop()
    await vi.advanceTimersByTimeAsync(AGENT_TIMING.stepMs * 2)

    expect(router.currentRoute.value.query).toEqual({})
    expect(agent.turns.value[0]?.status).toBe('stopped')
    expect(agent.turns.value[0]?.steps.map((s) => s.status)).toEqual(['failed'])
    expect(agent.presence.value.visible).toBe(false)
    expect(agent.status.value).toBe('idle')
  })

  it('shows the API message when the question is rejected', async () => {
    const { agent } = await setUp()
    const message = 'Has hecho demasiadas preguntas seguidas. Prueba en unos minutos.'
    vi.mocked(askAgent).mockRejectedValueOnce(new AgentRequestError(429, message))

    await agent.ask('¿Qué acelera?')
    await settle()

    expect(agent.turns.value[0]).toMatchObject({ status: 'failed', failure: message })
    expect(agent.status.value).toBe('idle')
  })

  it('sends the previous question and its cited topics with a follow-up', async () => {
    const { agent } = await setUp()
    streams([step(1, 'running', 'data'), step(1, 'done', 'data'), answer(['opp_1']), DONE])
    void agent.ask('¿Qué conviene publicar?')
    await vi.runAllTimersAsync()
    streams([answer(), DONE])

    void agent.ask('¿Y por qué ese?')
    await settle()

    expect(vi.mocked(askAgent).mock.lastCall?.[0]).toMatchObject({
      question: '¿Y por qué ese?',
      history: ['¿Qué conviene publicar?'],
      focus_ids: ['opp_1'],
    })
  })

  it('opens the dossier the agent navigates to without stopping itself', async () => {
    const { agent, router } = await setUp()
    streams([
      step(1, 'running'),
      step(1, 'done'),
      navigateAction({ screen: 'dossier', opportunity_id: 'opp_1' }),
      answer(['opp_1']),
      DONE,
    ])

    void agent.ask('Explícame este tema')
    await vi.runAllTimersAsync()

    expect(router.currentRoute.value.path).toBe('/explore/opp_1')
    expect(agent.turns.value[0]?.status).toBe('done')
  })

  it('stops when the person changes screen while the agent works', async () => {
    const { agent, router } = await setUp()
    streams([step(1, 'running', 'data'), step(1, 'done', 'data'), answer(), DONE])

    void agent.ask('¿Qué acelera?')
    await settle()
    await router.push('/explore')

    expect(agent.turns.value[0]?.status).toBe('stopped')
    expect(agent.status.value).toBe('idle')
    expect(vi.mocked(askAgent).mock.lastCall?.[2].aborted).toBe(true)
  })
})
