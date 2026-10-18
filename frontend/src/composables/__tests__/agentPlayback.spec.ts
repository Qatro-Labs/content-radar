import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { AgentStreamEvent, AgentTurnView } from '@/lib/agentTypes'

import { createAgentPlayback, type PlaybackHost } from '../agentPlayback'

function newTurn(): AgentTurnView {
  return {
    id: 1,
    question: 'Explícame este tema',
    status: 'running',
    steps: [],
    answer: null,
    visibleWords: 0,
    showEnding: false,
    summary: null,
    failure: null,
  }
}

function hostWith(performStep: PlaybackHost['performStep']): PlaybackHost {
  return {
    turn: newTurn(),
    signal: new AbortController().signal,
    isReducedMotion: () => true,
    performStep,
    onAnswerStart: vi.fn(),
    onAnswerShown: vi.fn(),
    onFinish: vi.fn(),
  }
}

const openDossier = (id: number): AgentStreamEvent[] => [
  { type: 'step', data: { id, kind: 'view', label: 'Abriendo un expediente', status: 'running' } },
  { type: 'step', data: { id, kind: 'view', label: 'Abriendo «Agentes»', status: 'done' } },
  {
    type: 'action',
    data: { step_id: id, navigate: { screen: 'dossier', opportunity_id: 'opp_1' } },
  },
]

const ANSWER: AgentStreamEvent = {
  type: 'answer',
  data: { text: 'Agentes acelera.', cited: [], unknowns: ['Sin casos medidos.'] },
}
const DONE: AgentStreamEvent = { type: 'done', data: { steps: 2, data_steps: 0, view_steps: 2 } }

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('createAgentPlayback', () => {
  // P. ej. no carga el chunk de la ruta a la que va el paso: sin esto el turno seguía «en curso».
  it('fails the turn when a step cannot be played in the page', async () => {
    const performStep = vi.fn().mockRejectedValue(new Error('Failed to fetch dynamic import'))
    const host = hostWith(performStep)
    const playback = createAgentPlayback(host)

    for (const event of openDossier(1)) playback.push(event)
    await vi.runAllTimersAsync()
    for (const event of [...openDossier(2), ANSWER, DONE]) playback.push(event)
    playback.end()
    await vi.runAllTimersAsync()

    expect(host.turn.status).toBe('failed')
    expect(host.turn.failure).toBe(
      'Rad no pudo terminar este paso. Lo que ya cambió en la vista se queda.',
    )
    expect(host.turn.steps.map((step) => step.status)).toEqual(['failed'])
    expect(host.turn.answer).toBeNull()
    expect(performStep).toHaveBeenCalledTimes(1)
    expect(host.onFinish).toHaveBeenCalledTimes(1)
  })
})
