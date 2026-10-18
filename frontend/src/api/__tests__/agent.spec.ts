import { afterEach, describe, expect, it, vi } from 'vitest'

import type { AgentStreamEvent } from '@/lib/agentTypes'

import { AgentRequestError, askAgent } from '../agent'

// Trozo real del stream del 18/10 a través de Vercel (recortado), con el keep-alive de FastAPI.
const AGENT_SAMPLE = [
  'event: step',
  'data: {"id": 1, "kind": "data", "label": "Leyendo las oportunidades", "status": "running"}',
  '',
  ': ping',
  '',
  'event: step',
  'data: {"id": 1, "kind": "data", "label": "Leyendo las oportunidades", "status": "done"}',
  '',
  'event: answer',
  'data: {"text": "El tema que conviene publicar ya es \\"Evaluación y medición de agentes de IA en empresas\\" (Oportunidad 63,9; ↑ +104 % de aceleración).\\n\\nComo alternativa, \\"Control del coste de la IA en empresas\\".", "cited": [{"id": "opp_1552", "topic": "Evaluación y medición de agentes de IA en empresas", "lifecycle": "accelerating", "opportunity_score": 63.9}], "unknowns": ["Ninguna pieza muestra resultados medidos de empresas concretas."]}',
  '',
  'event: done',
  'data: {"steps": 1, "data_steps": 1, "view_steps": 0}',
  '',
  '',
].join('\n')

// La red parte el stream por bytes: un corte puede caer en medio de una tilde o de «↑».
const CHUNK_BYTES = 37

function streamOf(text: string): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(text)
  return new ReadableStream({
    start(controller) {
      for (let start = 0; start < bytes.length; start += CHUNK_BYTES) {
        controller.enqueue(bytes.slice(start, start + CHUNK_BYTES))
      }
      controller.close()
    },
  })
}

function stubFetch(response: Response) {
  const fetchMock = vi.fn(async () => response)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const jsonResponse = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const QUESTION = '¿Qué conviene publicar?'

async function ask(): Promise<AgentStreamEvent[]> {
  const events: AgentStreamEvent[] = []
  await askAgent(
    { question: QUESTION },
    (event) => events.push(event),
    new AbortController().signal,
  )
  return events
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('askAgent', () => {
  it('posts the question and hands the typed events over in order', async () => {
    const fetchMock = stubFetch(
      new Response(streamOf(AGENT_SAMPLE), {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    )

    const events = await ask()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/agent',
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ question: QUESTION }) }),
    )
    expect(events.map((event) => event.type)).toEqual(['step', 'step', 'answer', 'done'])
    expect(events[1]).toEqual({
      type: 'step',
      data: { id: 1, kind: 'data', label: 'Leyendo las oportunidades', status: 'done' },
    })
    const answer = events[2]
    if (answer?.type !== 'answer') throw new Error('the third event must be the answer')
    expect(answer.data.cited.map((cited) => cited.id)).toEqual(['opp_1552'])
    expect(answer.data.text).toContain('↑ +104 % de aceleración')
    expect(events[3]).toEqual({ type: 'done', data: { steps: 1, data_steps: 1, view_steps: 0 } })
  })

  it('raises the API message when the IP quota is used up', async () => {
    const detail = 'Has hecho demasiadas preguntas seguidas. Prueba en unos minutos.'
    stubFetch(jsonResponse(429, { detail }))

    const error = await ask().catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(AgentRequestError)
    expect(error).toMatchObject({ status: 429, message: detail })
  })

  // El campo ya corta la pregunta a 300 caracteres: un 422 suele venir del contexto, no de ella.
  it('explains a rejected question in Spanish without blaming its length', async () => {
    stubFetch(
      jsonResponse(422, {
        detail: [{ type: 'too_long', loc: ['body', 'history'], msg: 'List should have at most 4' }],
      }),
    )

    await expect(ask()).rejects.toThrow(
      'Rad no pudo leer esta pregunta. Prueba a escribirla de nuevo.',
    )
  })
})
