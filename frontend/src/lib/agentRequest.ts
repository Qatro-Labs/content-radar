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
  if (selected) context.opportunity_id = selected
  const filters = changedFilters(radarQuery)
  if (filters !== null) context.filters = filters
  return context
}

export function viewContext(screen: AgentScreen | null, state: ViewState): AgentViewContext | null {
  if (screen === 'radar') return radarContext(state)
  if (screen === 'dossier') {
    return state.dossierId ? { screen, opportunity_id: state.dossierId } : { screen }
  }
  if (screen === 'explore') return state.search ? { screen, search: state.search } : { screen }
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

export function suggestionsFor(view: AgentViewContext | null): string[] {
  if (view?.screen === 'explore') return EXPLORE_SUGGESTIONS
  if (view?.screen === 'dossier' || view?.opportunity_id) return TOPIC_SUGGESTIONS
  return GENERAL_SUGGESTIONS
}
