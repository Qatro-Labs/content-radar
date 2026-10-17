import type {
  AgentQuestion,
  AgentScreen,
  AgentTurnView,
  AgentViewContext,
  RadarPatch,
} from './agentTypes'
import { DEFAULT_RANKING_SORT, type RadarQuery } from './radarQuery'

// D2 del plan fe-radar-agent: la conversación viaja como las preguntas anteriores y los temas que
// citó la última respuesta, nunca como las respuestas del modelo. Los mismos límites que
// `MAX_HISTORY` y `MAX_FOCUS_IDS` de backend/app/schemas/agent.py: con más, la API responde 422.
const MAX_HISTORY = 4
const MAX_FOCUS_IDS = 6
// La URL la puede escribir cualquiera: lo que la API rechazaría (422) no se manda. Los mismos
// `OPPORTUNITY_ID_PATTERN` (backend/app/schemas/opportunity.py) y `MAX_SEARCH_CHARS`
// (backend/app/schemas/agent.py).
const OPPORTUNITY_ID = /^opp_[A-Za-z0-9_]{1,64}$/
const MAX_SEARCH_CHARS = 60

function validOpportunityId(id: string | null): string | null {
  return id !== null && OPPORTUNITY_ID.test(id) ? id : null
}

// D10: ningún cliente MCP de asistente está probado todavía (docs/mcp.md), así que el enlace lleva
// a la guía de conexión en lugar de prometer uno concreto.
export const MCP_DOCS_URL = 'https://github.com/Qatro-Labs/content-radar/blob/main/docs/mcp.md'

// Un turno detenido o fallido no cuenta: su respuesta no llegó entera.
function finishedTurns(turns: readonly AgentTurnView[]): AgentTurnView[] {
  return turns.filter((turn) => turn.status === 'done')
}

export function buildAgentQuestion(
  question: string,
  turns: readonly AgentTurnView[],
  view: AgentViewContext | null,
): AgentQuestion {
  const finished = finishedTurns(turns)
  const history = finished.slice(-MAX_HISTORY).map((turn) => turn.question)
  const lastCited = finished.at(-1)?.answer?.cited ?? []
  const focusIds = lastCited.slice(0, MAX_FOCUS_IDS).map((cited) => cited.id)
  return { question, history, focus_ids: focusIds, view }
}

export interface ViewState {
  selected: string | null
  // Id de `/explore/:id`.
  dossierId: string | null
  // `?q=` de Explorar.
  search: string | null
  radarQuery: RadarQuery
}

// Solo lo que la persona cambió respecto al Radar por defecto; la selección va en `opportunity_id`
// y el periodo no es un filtro del agente.
function changedFilters(query: RadarQuery): RadarPatch | null {
  const filters: RadarPatch = {}
  if (query.lifecycle.length > 0) filters.lifecycle = query.lifecycle
  if (query.recommendation !== null) filters.recommendation = query.recommendation
  if (query.confidence !== null) filters.confidence = query.confidence
  if (query.topic !== null) filters.topic = query.topic
  if (query.gap) filters.gap = query.gap
  if (query.sort !== DEFAULT_RANKING_SORT) filters.sort = query.sort
  if (query.highlight.length > 0) filters.highlight = query.highlight
  return Object.keys(filters).length > 0 ? filters : null
}

function radarContext({ selected, radarQuery }: ViewState): AgentViewContext {
  const context: AgentViewContext = { screen: 'radar' }
  const opportunityId = validOpportunityId(selected)
  if (opportunityId) context.opportunity_id = opportunityId
  const filters = changedFilters(radarQuery)
  if (filters !== null) context.filters = filters
  return context
}

export function viewContext(screen: AgentScreen | null, state: ViewState): AgentViewContext | null {
  if (screen === 'radar') return radarContext(state)
  if (screen === 'dossier') {
    const opportunityId = validOpportunityId(state.dossierId)
    return opportunityId ? { screen, opportunity_id: opportunityId } : { screen }
  }
  if (screen === 'explore') {
    const search = state.search?.slice(0, MAX_SEARCH_CHARS)
    return search ? { screen, search } : { screen }
  }
  return null
}

// D9: preguntas que funcionan con los datos reales del 18/10.
const PUBLISH_NOW_QUESTION = '¿Qué tema conviene publicar ya y por qué?'
const GENERAL_SUGGESTIONS = [
  PUBLISH_NOW_QUESTION,
  '¿Qué está acelerando más esta semana?',
  '¿Qué temas ya copiaron todos?',
]
const TOPIC_SUGGESTIONS = [
  'Explícame este tema',
  '¿Qué pieza funcionó mejor y por qué?',
  '¿Cómo lo contamos para ejecutivos de LATAM?',
]
const EXPLORE_SUGGESTIONS = [
  '¿Qué piezas rinden más frente a su canal?',
  'Busca piezas sobre agentes de IA',
  PUBLISH_NOW_QUESTION,
]

function hasTopic(view: AgentViewContext | null): boolean {
  return view?.screen === 'dossier' || Boolean(view?.opportunity_id)
}

// Con la conversación en marcha la barra ya es alta: solo quedan las que siguen hablando del tema.
export function followUpSuggestions(view: AgentViewContext | null): string[] {
  return view?.screen !== 'explore' && hasTopic(view) ? TOPIC_SUGGESTIONS : []
}

export function suggestionsFor(view: AgentViewContext | null): string[] {
  if (view?.screen === 'explore') return EXPLORE_SUGGESTIONS
  if (hasTopic(view)) return TOPIC_SUGGESTIONS
  return GENERAL_SUGGESTIONS
}
