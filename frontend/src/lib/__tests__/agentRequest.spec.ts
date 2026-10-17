import { describe, expect, it } from 'vitest'

import {
  buildAgentQuestion,
  followUpSuggestions,
  suggestionsFor,
  viewContext,
} from '../agentRequest'
import type { AgentTurnView, AgentViewContext, CitedOpportunity, TurnStatus } from '../agentTypes'
import { parseRadarQuery } from '../radarQuery'

function cited(id: string): CitedOpportunity {
  return { id, topic: `Tema ${id}`, lifecycle: 'accelerating', opportunity_score: 60 }
}

function turn(id: number, status: TurnStatus, citedIds: string[] = []): AgentTurnView {
  return {
    id,
    question: `Pregunta ${id}`,
    status,
    steps: [],
    answer: { text: 'Respuesta', cited: citedIds.map(cited), unknowns: ['Sin casos medidos.'] },
    visibleWords: 1,
    showEnding: true,
    summary: { steps: 1, data_steps: 1, view_steps: 0 },
    failure: null,
  }
}

const RADAR_STATE = {
  selected: null,
  dossierId: null,
  search: null,
  radarQuery: parseRadarQuery({}),
}

describe('buildAgentQuestion', () => {
  it('sends the last four finished questions, oldest first', () => {
    const turns = [1, 2, 3, 4, 5, 6].map((id) => turn(id, 'done'))

    const body = buildAgentQuestion('¿Y por qué ese?', turns, null)

    expect(body.question).toBe('¿Y por qué ese?')
    expect(body.history).toEqual(['Pregunta 3', 'Pregunta 4', 'Pregunta 5', 'Pregunta 6'])
  })

  it('focuses on at most six topics cited in the last finished answer', () => {
    const turns = [
      turn(1, 'done', ['opp_100']),
      turn(2, 'done', ['opp_1', 'opp_2', 'opp_3', 'opp_4', 'opp_5', 'opp_6', 'opp_7']),
    ]

    expect(buildAgentQuestion('¿Y el segundo?', turns, null).focus_ids).toEqual([
      'opp_1',
      'opp_2',
      'opp_3',
      'opp_4',
      'opp_5',
      'opp_6',
    ])
  })

  it('leaves a stopped question out of the conversation', () => {
    const turns = [turn(1, 'done', ['opp_1']), turn(2, 'stopped', ['opp_2'])]

    const body = buildAgentQuestion('¿Y ese?', turns, null)

    expect(body.history).toEqual(['Pregunta 1'])
    expect(body.focus_ids).toEqual(['opp_1'])
  })

  it('sends what the person is looking at', () => {
    const view: AgentViewContext = { screen: 'dossier', opportunity_id: 'opp_1' }

    expect(buildAgentQuestion('Explícame este tema', [], view).view).toEqual(view)
  })
})

describe('viewContext', () => {
  it('sends no filters from a radar left as it is', () => {
    expect(viewContext('radar', RADAR_STATE)).toEqual({ screen: 'radar' })
  })

  it('sends only the radar filters that differ from the default', () => {
    const radarQuery = parseRadarQuery({ lifecycle: 'emerging', confidence: 'high', period: '30d' })

    expect(viewContext('radar', { ...RADAR_STATE, selected: 'opp_1', radarQuery })).toEqual({
      screen: 'radar',
      opportunity_id: 'opp_1',
      filters: { lifecycle: ['emerging'], confidence: 'high' },
    })
  })

  // La API rechaza con 422 un id que no es de oportunidad o una búsqueda de más de 60 caracteres.
  it('leaves out ids the API would reject', () => {
    expect(viewContext('radar', { ...RADAR_STATE, selected: 'not-an-id' })).toEqual({
      screen: 'radar',
    })
    expect(viewContext('dossier', { ...RADAR_STATE, dossierId: '../etc' })).toEqual({
      screen: 'dossier',
    })
  })

  it('cuts a long search to what the API accepts', () => {
    const search = 'agentes '.repeat(20)

    expect(viewContext('explore', { ...RADAR_STATE, search })?.search).toBe(search.slice(0, 60))
  })
})

// D9 del plan fe-radar-agent.
const GENERAL = [
  '¿Qué tema conviene publicar ya y por qué?',
  '¿Qué está acelerando más esta semana?',
  '¿Qué temas ya copiaron todos?',
]
const ON_TOPIC = [
  'Explícame este tema',
  '¿Qué pieza funcionó mejor y por qué?',
  '¿Cómo lo contamos para ejecutivos de LATAM?',
]
const IN_EXPLORE = [
  '¿Qué piezas rinden más frente a su canal?',
  'Busca piezas sobre agentes de IA',
  '¿Qué tema conviene publicar ya y por qué?',
]

describe('suggestionsFor', () => {
  it.each<{ case: string; view: AgentViewContext | null; suggestions: string[] }>([
    { case: 'radar without a topic', view: { screen: 'radar' }, suggestions: GENERAL },
    {
      case: 'radar with a selected topic',
      view: { screen: 'radar', opportunity_id: 'opp_1' },
      suggestions: ON_TOPIC,
    },
    {
      case: 'dossier',
      view: { screen: 'dossier', opportunity_id: 'opp_1' },
      suggestions: ON_TOPIC,
    },
    { case: 'explore', view: { screen: 'explore' }, suggestions: IN_EXPLORE },
  ])('$case', ({ view, suggestions }) => {
    expect(suggestionsFor(view)).toEqual(suggestions)
  })
})

// Con la conversación en marcha la barra ya es alta: solo quedan las que siguen hablando del tema.
describe('followUpSuggestions', () => {
  it.each<{ case: string; view: AgentViewContext | null; suggestions: string[] }>([
    { case: 'radar without a topic', view: { screen: 'radar' }, suggestions: [] },
    {
      case: 'radar with a selected topic',
      view: { screen: 'radar', opportunity_id: 'opp_1' },
      suggestions: ON_TOPIC,
    },
    { case: 'explore', view: { screen: 'explore' }, suggestions: [] },
  ])('$case', ({ view, suggestions }) => {
    expect(followUpSuggestions(view)).toEqual(suggestions)
  })
})
