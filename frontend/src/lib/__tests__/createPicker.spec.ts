import { describe, expect, it } from 'vitest'

import fixture from '@fixtures/opportunities.json'
import type { components } from '@/types/api'

import {
  buildTopicList,
  COLLAPSED_TOPICS,
  featuredNote,
  featuredSummary,
  featuredTiles,
  morePiecesLine,
  splitByPublishNow,
} from '../createPicker'

type Schemas = components['schemas']
type Opportunity = Schemas['Opportunity']
type OpportunityList = Schemas['OpportunityList']
type Recommendation = Schemas['Recommendation']

// TS lee los enums del JSON como `string`; el fixture cumple el contrato `OpportunityList`.
const base = (fixture.opportunities as OpportunityList).items[0]!

function topic(id: string, name: string, recommendation: Recommendation = 'find_angle') {
  return { ...base, id, topic: name, recommendation } satisfies Opportunity
}

function manyTopics(count: number): Opportunity[] {
  return Array.from({ length: count }, (_, index) => topic(`opp_${index}`, `Tema ${index}`))
}

describe('splitByPublishNow', () => {
  it('separates «Publicar ya» from the rest, both in ranking order', () => {
    const items = [
      topic('opp_a', 'Agentes', 'find_angle'),
      topic('opp_b', 'Coste de la IA', 'publish_now'),
      topic('opp_c', 'Modelos abiertos', 'wait_for_case'),
      topic('opp_d', 'Copilotos', 'publish_now'),
    ]

    const { featured, others } = splitByPublishNow(items)

    expect(featured.map((t) => t.id)).toEqual(['opp_b', 'opp_d'])
    expect(others.map((t) => t.id)).toEqual(['opp_a', 'opp_c'])
  })
})

describe('featuredNote', () => {
  it('says when the topic is the only one in «Publicar ya»', () => {
    expect(featuredNote(1)).toBe('El único tema en «Publicar ya» esta semana')
    expect(featuredNote(3)).toBe('3 temas en «Publicar ya»')
  })
})

describe('featuredSummary', () => {
  it('falls back to the recommendation rule and never invents text', () => {
    expect(featuredSummary({ why_it_matters: 'Importa.', recommendation_reason: 'Regla.' })).toBe(
      'Importa.',
    )
    expect(featuredSummary({ why_it_matters: '  ', recommendation_reason: 'Regla.' })).toBe(
      'Regla.',
    )
    expect(featuredSummary({ why_it_matters: '', recommendation_reason: null })).toBeNull()
  })
})

describe('featuredTiles', () => {
  it('shows score, acceleration with its evidence type, and independent sources', () => {
    const opportunity: Opportunity = {
      ...base,
      opportunity_score: 58.4,
      acceleration: 0.69,
      growth_status: 'observed',
      source_count: 7,
    }

    expect(featuredTiles(opportunity).map(({ label, value }) => [label, value])).toEqual([
      ['Oportunidad de 100', '58'],
      ['Aceleración · Observado', '↑ +69 %'],
      ['Fuentes independientes', '7'],
    ])
  })

  it('writes a missing score as «no disponible», never 0', () => {
    const [score] = featuredTiles({ ...base, opportunity_score: null })

    expect(score).toEqual({
      label: 'Oportunidad',
      value: 'no disponible',
      isMissing: true,
      isNegative: false,
    })
  })
})

describe('morePiecesLine', () => {
  it('counts the pieces that are not shown', () => {
    expect(morePiecesLine(7, 3)).toBe('y 4 piezas más del tema')
    expect(morePiecesLine(4, 3)).toBe('y 1 pieza más del tema')
    expect(morePiecesLine(3, 3)).toBeNull()
  })

  it('says «al menos» when the API cap is full', () => {
    expect(morePiecesLine(25, 3)).toBe('y al menos 22 piezas más del tema')
  })
})

describe('buildTopicList', () => {
  it(`shows the first ${COLLAPSED_TOPICS} topics and offers the rest`, () => {
    const topics = manyTopics(COLLAPSED_TOPICS + 5)

    const view = buildTopicList({ topics, hasFeatured: true, text: '', expanded: false })

    expect(view.title).toBe('O escribe de otro tema')
    expect(view.rows.map((t) => t.id)).toEqual(topics.slice(0, COLLAPSED_TOPICS).map((t) => t.id))
    expect(view.expandLabel).toBe('Ver los 12 temas')
    expect(view.countLine).toBe(
      '12 temas más, ordenados por oportunidad. Cualquiera sirve: Rad avisa si conviene esperar.',
    )
  })

  it('shows every topic once expanded, without the button', () => {
    const topics = manyTopics(COLLAPSED_TOPICS + 5)

    const view = buildTopicList({ topics, hasFeatured: true, text: '', expanded: true })

    expect(view.rows).toHaveLength(COLLAPSED_TOPICS + 5)
    expect(view.expandLabel).toBeNull()
  })

  it('has no button when every topic already fits', () => {
    const view = buildTopicList({
      topics: manyTopics(COLLAPSED_TOPICS),
      hasFeatured: true,
      text: '',
      expanded: false,
    })

    expect(view.rows).toHaveLength(COLLAPSED_TOPICS)
    expect(view.expandLabel).toBeNull()
  })

  it('says so when no topic is in «Publicar ya», instead of promoting one', () => {
    const view = buildTopicList({
      topics: manyTopics(3),
      hasFeatured: false,
      text: '',
      expanded: false,
    })

    expect(view.title).toBe('Todos los temas')
    expect(view.countLine).toBe(
      'Ningún tema está en «Publicar ya» esta semana: estos son todos, por oportunidad.',
    )
  })

  it('filters by topic ignoring case and accents, showing every match', () => {
    const topics = [
      ...manyTopics(COLLAPSED_TOPICS + 2).map((t, index) => ({ ...t, topic: `Agentes ${index}` })),
      topic('opp_latam', 'Rezago de América Latina ante la IA'),
      topic('opp_coste', 'Control del coste de la IA'),
    ]

    const agents = buildTopicList({ topics, hasFeatured: true, text: ' AGÉNTES ', expanded: false })
    const latam = buildTopicList({ topics, hasFeatured: true, text: 'américa', expanded: false })

    expect(agents.rows).toHaveLength(COLLAPSED_TOPICS + 2)
    expect(agents.expandLabel).toBeNull()
    expect(agents.countLine).toBe('9 de 11 temas')
    expect(latam.rows.map((t) => t.id)).toEqual(['opp_latam'])
  })

  it('reports no matches only when a query found nothing', () => {
    const topics = manyTopics(3)

    expect(
      buildTopicList({ topics, hasFeatured: true, text: 'blockchain', expanded: false }),
    ).toMatchObject({ rows: [], noMatches: true, countLine: '0 de 3 temas' })
    expect(buildTopicList({ topics, hasFeatured: true, text: '', expanded: false }).noMatches).toBe(
      false,
    )
  })
})
