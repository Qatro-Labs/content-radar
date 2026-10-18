import type {
  ActionEvent,
  AgentStreamEvent,
  AnswerEvent,
  DoneEvent,
  ErrorEvent,
  StepEvent,
  StepKind,
} from './agentTypes'

// D7 del plan fe-radar-agent: el backend emite `running`, `done` y `action` de un mismo paso con
// milisegundos de diferencia. El front guarda los eventos en un búfer y una cola los reproduce de
// uno en uno, al ritmo de la presencia.

export interface PlayableStep {
  id: number
  kind: StepKind
  label: string
  status: 'done' | 'failed'
  action: ActionEvent | null
}

export type Playable =
  | { type: 'step'; step: PlayableStep }
  | { type: 'answer'; answer: AnswerEvent }
  | { type: 'error'; error: ErrorEvent }
  | { type: 'done'; summary: DoneEvent }

interface StepGroup {
  id: number
  steps: StepEvent[]
  action: ActionEvent | null
  events: AgentStreamEvent[]
}

type ClosingEvent = Exclude<AgentStreamEvent, { type: 'step' | 'action' }>

type Entry = { type: 'step'; group: StepGroup } | { type: 'closing'; event: ClosingEvent }

function stepIdOf(event: AgentStreamEvent & { type: 'step' | 'action' }): number {
  return event.type === 'step' ? event.data.id : event.data.step_id
}

function addToGroup(group: StepGroup, event: AgentStreamEvent & { type: 'step' | 'action' }) {
  group.events.push(event)
  if (event.type === 'step') group.steps.push(event.data)
  else group.action = event.data
}

// Agrupa los eventos de cada paso en el orden en que llegó el primero de ellos.
function groupEntries(buffer: readonly AgentStreamEvent[]): Entry[] {
  const entries: Entry[] = []
  const groups = new Map<number, StepGroup>()
  for (const event of buffer) {
    if (event.type !== 'step' && event.type !== 'action') {
      entries.push({ type: 'closing', event })
      continue
    }
    const id = stepIdOf(event)
    const group = groups.get(id) ?? { id, steps: [], action: null, events: [] }
    if (!groups.has(id)) {
      groups.set(id, group)
      entries.push({ type: 'step', group })
    }
    addToGroup(group, event)
  }
  return entries
}

// Un paso de vista que terminó bien espera su `action`, salvo que ya haya llegado algo detrás:
// entonces no la trae. Un paso que sigue en curso bloquea todo lo que viene detrás.
function isStepReady(group: StepGroup, hasLaterEvent: boolean): boolean {
  const last = group.steps.at(-1)
  if (last === undefined || last.status === 'running') return false
  if (last.status === 'failed' || last.kind === 'data') return true
  return group.action !== null || hasLaterEvent
}

// La etiqueta es la del último evento `step`: en vivo pasa de «Revisando una oportunidad» a
// «Revisando «X»». Un paso que nunca terminó (stream cerrado) no se pinta como hecho (regla 3).
function toPlayableStep(group: StepGroup): PlayableStep | null {
  const last = group.steps.at(-1)
  if (last === undefined) return null
  const status = last.status === 'done' ? 'done' : 'failed'
  return { id: group.id, kind: last.kind, label: last.label, status, action: group.action }
}

function toPlayable(entry: Entry): Playable | null {
  if (entry.type === 'step') {
    const step = toPlayableStep(entry.group)
    return step === null ? null : { type: 'step', step }
  }
  const { event } = entry
  if (event.type === 'answer') return { type: 'answer', answer: event.data }
  if (event.type === 'error') return { type: 'error', error: event.data }
  return { type: 'done', summary: event.data }
}

function eventsOf(entry: Entry): AgentStreamEvent[] {
  return entry.type === 'step' ? entry.group.events : [entry.event]
}

// Lo que ya se puede reproducir, en orden, y el resto del búfer. Con el stream cerrado sale todo.
export function takePlayable(
  buffer: readonly AgentStreamEvent[],
  streamEnded: boolean,
): { ready: Playable[]; rest: AgentStreamEvent[] } {
  const entries = groupEntries(buffer)
  const ready: Playable[] = []
  let taken = 0
  for (const [index, entry] of entries.entries()) {
    const hasLaterEvent = index < entries.length - 1
    const isReady =
      streamEnded || entry.type === 'closing' || isStepReady(entry.group, hasLaterEvent)
    if (!isReady) break
    const playable = toPlayable(entry)
    if (playable !== null) ready.push(playable)
    taken += 1
  }
  return { ready, rest: entries.slice(taken).flatMap(eventsOf) }
}
