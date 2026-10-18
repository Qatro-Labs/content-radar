import type { AgentQuestion, AgentStreamEvent } from '@/lib/agentTypes'
import { createSseParser, type SseMessage } from '@/lib/sse'
import { authorizationHeaders } from '@/lib/supabase'

import { API_BASE_URL } from './client'

// `fetch` y no `openapi-fetch` (D12 del plan fe-radar-agent): `openapi-fetch` captura `fetch` al
// crear el cliente y no aporta nada a un stream. Los tipos siguen saliendo de src/types/api.ts.
const AGENT_PATH = '/api/v1/agent'

const AGENT_EVENTS = [
  'step',
  'action',
  'answer',
  'error',
  'done',
] as const satisfies readonly AgentStreamEvent['type'][]

const HTTP_UNPROCESSABLE = 422
// El 422 de FastAPI trae la lista de errores de Pydantic, en inglés. No se culpa a la longitud:
// el campo ya la corta, así que el rechazo suele venir del contexto que manda el navegador.
const INVALID_QUESTION_MESSAGE = 'Rad no pudo leer esta pregunta. Prueba a escribirla de nuevo.'
const NO_RESPONSE_MESSAGE = 'El asistente no respondió.'

// La API rechazó la pregunta antes de abrir el stream (429 y 503 traen su mensaje en español).
export class AgentRequestError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'AgentRequestError'
    this.status = status
  }
}

async function readDetail(response: Response): Promise<unknown> {
  try {
    const body: unknown = await response.json()
    return typeof body === 'object' && body !== null && 'detail' in body ? body.detail : null
  } catch {
    // Un proxy puede responder con HTML: no hay `detail` que mostrar.
    return null
  }
}

async function requestError(response: Response): Promise<AgentRequestError> {
  if (response.status === HTTP_UNPROCESSABLE) {
    return new AgentRequestError(response.status, INVALID_QUESTION_MESSAGE)
  }
  const detail = await readDetail(response)
  const message = typeof detail === 'string' ? detail : NO_RESPONSE_MESSAGE
  return new AgentRequestError(response.status, message)
}

function toStreamEvent({ event, data }: SseMessage): AgentStreamEvent | null {
  const type = AGENT_EVENTS.find((name) => name === event)
  if (type === undefined) return null
  // El backend serializa cada evento con su modelo del contrato (AgentEvent en src/types/api.ts).
  return { type, data: JSON.parse(data) } as AgentStreamEvent
}

async function readStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: AgentStreamEvent) => void,
): Promise<void> {
  const parser = createSseParser((message) => {
    const event = toStreamEvent(message)
    if (event !== null) onEvent(event)
  })
  const reader = body.getReader()
  // `stream: true`: un trozo puede cortar un carácter de varios bytes («á», «↑») por la mitad.
  const decoder = new TextDecoder()
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    parser.push(decoder.decode(value, { stream: true }))
  }
  parser.push(decoder.decode())
  parser.end()
}

// Resuelve cuando el stream se cierra; un `AbortError` de `signal` se propaga tal cual.
export async function askAgent(
  body: AgentQuestion,
  onEvent: (event: AgentStreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${AGENT_PATH}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(await authorizationHeaders()),
    },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok) throw await requestError(response)
  if (response.body === null) return
  await readStream(response.body, onEvent)
}
