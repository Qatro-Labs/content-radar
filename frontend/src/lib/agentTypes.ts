import type { components } from '@/types/api'

type Schemas = components['schemas']

export type StepEvent = Schemas['StepEvent']
export type ActionEvent = Schemas['ActionEvent']
export type AnswerEvent = Schemas['AnswerEvent']
export type ErrorEvent = Schemas['ErrorEvent']
export type DoneEvent = Schemas['DoneEvent']
export type RadarPatch = Schemas['RadarPatch']
export type Navigation = Schemas['Navigation']
export type AgentQuestion = Schemas['AgentQuestion']
export type AgentViewContext = Schemas['AgentViewContext']
export type AgentScreen = Schemas['AgentScreen']
export type DossierSection = Schemas['DossierSection']
export type CitedOpportunity = Schemas['CitedOpportunity']
export type StepKind = Schemas['StepKind']

// Un evento del stream SSE de `POST /api/v1/agent`: el nombre del evento decide el tipo de `data`.
export type AgentStreamEvent =
  | { type: 'step'; data: StepEvent }
  | { type: 'action'; data: ActionEvent }
  | { type: 'answer'; data: AnswerEvent }
  | { type: 'error'; data: ErrorEvent }
  | { type: 'done'; data: DoneEvent }

export type AgentStatus = 'idle' | 'running' | 'answering'
export type TurnStatus = 'running' | 'answering' | 'done' | 'stopped' | 'failed'
export type StepStatus = 'running' | 'done' | 'failed'

export interface AgentStepView {
  id: number
  kind: StepKind
  label: string
  status: StepStatus
}

// Lo que la barra pinta de cada pregunta de la conversación.
export interface AgentTurnView {
  id: number
  question: string
  status: TurnStatus
  steps: AgentStepView[]
  answer: AnswerEvent | null
  // Palabras de `answer.text` ya mostradas (DESIGN.md §7: la respuesta aparece palabra a palabra).
  visibleWords: number
  // «Citadas» y los enlaces: solo cuando la respuesta ya está entera.
  showEnding: boolean
  summary: DoneEvent | null
  // Mensaje en español, listo para pintar.
  failure: string | null
}

export type TargetKind = 'control' | 'block' | 'point'

// `anchor` es el valor de `data-agent` del elemento al que va la presencia.
export interface AgentTarget {
  anchor: string
  kind: TargetKind
}

// Coordenadas relativas a `[data-agent-root]` (DESIGN.md §7: capa absoluta sobre la raíz).
export interface RingBox {
  x: number
  y: number
  width: number
  height: number
  radius: number
}

export interface PresenceView {
  visible: boolean
  x: number
  y: number
  label: string
  ring: RingBox | null
  // Salta sin viajar: primera aparición o movimiento reducido.
  instant: boolean
  // Cambia en cada pulsación: la onda se monta con esta `key`.
  tapCount: number
  // Cerca del borde derecho el rótulo va a la izquierda del punto.
  labelOnLeft: boolean
}
