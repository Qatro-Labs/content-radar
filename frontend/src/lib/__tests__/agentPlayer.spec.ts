import { describe, expect, it } from 'vitest'

import { takePlayable } from '../agentPlayer'
import type { AgentStreamEvent, StepKind, StepStatus } from '../agentTypes'

const READING = 'Leyendo las oportunidades'

function step(id: number, kind: StepKind, status: StepStatus, label = READING): AgentStreamEvent {
  return { type: 'step', data: { id, kind, label, status } }
}

const PATCH = { lifecycle: ['accelerating' as const] }
const action = (stepId: number): AgentStreamEvent => ({
  type: 'action',
  data: { step_id: stepId, patch: PATCH },
})
const ANSWER: AgentStreamEvent = {
  type: 'answer',
  data: { text: 'Conviene publicar ya.', cited: [], unknowns: ['Sin casos medidos.'] },
}
const DONE: AgentStreamEvent = { type: 'done', data: { steps: 1, data_steps: 1, view_steps: 0 } }

describe('takePlayable', () => {
  it('plays a data step once it is done', () => {
    const { ready, rest } = takePlayable(
      [step(1, 'data', 'running'), step(1, 'data', 'done')],
      false,
    )

    expect(ready).toEqual([
      { type: 'step', step: { id: 1, kind: 'data', label: READING, status: 'done', action: null } },
    ])
    expect(rest).toEqual([])
  })

  it('waits for the action of a view step, or for any later event', () => {
    const viewDone = [step(1, 'view', 'running'), step(1, 'view', 'done')]

    expect(takePlayable(viewDone, false)).toEqual({ ready: [], rest: viewDone })

    const withAction = takePlayable([...viewDone, action(1)], false)
    expect(withAction.ready).toEqual([
      {
        type: 'step',
        step: { id: 1, kind: 'view', label: READING, status: 'done', action: action(1).data },
      },
    ])

    const nextStep = step(2, 'data', 'running')
    const withLaterEvent = takePlayable([...viewDone, nextStep], false)
    expect(withLaterEvent.ready).toEqual([
      { type: 'step', step: { id: 1, kind: 'view', label: READING, status: 'done', action: null } },
    ])
    expect(withLaterEvent.rest).toEqual([nextStep])
  })

  it('plays a failed view step without an action', () => {
    const { ready } = takePlayable([step(1, 'view', 'running'), step(1, 'view', 'failed')], false)

    expect(ready).toEqual([
      {
        type: 'step',
        step: { id: 1, kind: 'view', label: READING, status: 'failed', action: null },
      },
    ])
  })

  it('labels the step with its last step event', () => {
    const { ready } = takePlayable(
      [
        step(1, 'data', 'running', 'Revisando una oportunidad'),
        step(1, 'data', 'done', 'Revisando «Agentes de IA»'),
      ],
      false,
    )

    expect(ready).toMatchObject([{ step: { label: 'Revisando «Agentes de IA»' } }])
  })

  it('holds the answer back while an earlier step is still running', () => {
    const buffer = [step(1, 'data', 'running'), ANSWER]

    expect(takePlayable(buffer, false)).toEqual({ ready: [], rest: buffer })

    const { ready } = takePlayable(
      [step(1, 'data', 'running'), step(1, 'data', 'done'), ANSWER],
      false,
    )
    expect(ready.map((playable) => playable.type)).toEqual(['step', 'answer'])
  })

  it('lets everything out when the stream ends', () => {
    const { ready, rest } = takePlayable(
      [step(1, 'view', 'running'), step(1, 'view', 'done'), step(2, 'data', 'running'), DONE],
      true,
    )

    expect(ready).toEqual([
      { type: 'step', step: { id: 1, kind: 'view', label: READING, status: 'done', action: null } },
      // Nunca llegó a terminar: no se pinta como hecho (regla 3).
      {
        type: 'step',
        step: { id: 2, kind: 'data', label: READING, status: 'failed', action: null },
      },
      { type: 'done', summary: DONE.data },
    ])
    expect(rest).toEqual([])
  })
})
