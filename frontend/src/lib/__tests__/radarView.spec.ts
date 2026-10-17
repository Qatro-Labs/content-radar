import { describe, expect, it } from 'vitest'

import fixture from '@fixtures/opportunities.json'
import type { components } from '@/types/api'

import type { RadarQuery } from '../radarQuery'
import {
  buildRadarView,
  counterPatch,
  describeStageUnknowns,
  describeWeekPicks,
  radarHeadline,
  radarSubline,
} from '../radarView'

type Schemas = components['schemas']
type Opportunity = Schemas['Opportunity']
type OpportunityList = Schemas['OpportunityList']

// TS lee los enums del JSON como `string`; el fixture cumple el contrato `OpportunityList`.
const list = fixture.opportunities as OpportunityList

function query(patch: Partial<RadarQuery> = {}): RadarQuery {
  return {
    period: '7d',
    lifecycle: [],
    confidence: null,
    topic: null,
    selected: null,
    highlight: [],
    gap: false,
    sort: 'opportunity',
    recommendation: null,
    ...patch,
  }
}

const ids = (items: { id: string }[]) => items.map((item) => item.id)

// Los contadores del fixture: opp_001 acelera y es «Publicar ya», opp_002 emerge, opp_005 no
// tiene etapa.
const FIXTURE_COUNTS = { publishNow: 1, accelerating: 1, emerging: 1, unknown: 1 }

describe('buildRadarView', () => {
  it('ranks every item in API order and leaves topics without fit out of the radar', () => {
    const view = buildRadarView(list, query())

    expect(view.total).toBe(5)
    expect(ids(view.ranked)).toEqual(['opp_001', 'opp_002', 'opp_003', 'opp_004', 'opp_005'])
    expect(view.ranked.map((item) => item.rank)).toEqual([1, 2, 3, 4, 5])
    expect(ids(view.visible)).toEqual(ids(view.ranked))
    expect(view.isFiltered).toBe(false)
    expect(ids(view.plotted)).toEqual(['opp_001', 'opp_002', 'opp_003', 'opp_004'])
    expect(view.unevaluatedCount).toBe(1)
    expect(view.dimmedIds).toEqual(new Set())
    expect(view.counts).toEqual(FIXTURE_COUNTS)
    expect(view.activeCounter).toBeNull()
  })

  it('keeps the selected stages with their global rank and dims the rest of the radar', () => {
    const view = buildRadarView(
      list,
      query({ lifecycle: ['peaking', 'saturated'], selected: 'opp_003' }),
    )

    expect(ids(view.visible)).toEqual(['opp_003', 'opp_004'])
    expect(view.visible.map((item) => item.rank)).toEqual([3, 4])
    expect(view.isFiltered).toBe(true)
    expect(view.dimmedIds).toEqual(new Set(['opp_001', 'opp_002']))
  })

  it('keeps only the topics to publish now and counts every topic, not the filtered ones', () => {
    const view = buildRadarView(list, query({ recommendation: 'publish_now' }))

    expect(ids(view.visible)).toEqual(['opp_001'])
    expect(view.isFiltered).toBe(true)
    expect(view.counts).toEqual(FIXTURE_COUNTS)
    expect(view.activeCounter).toBe('publish_now')
  })

  it('keeps only the topics with a LATAM gap when the gap filter is on', () => {
    const view = buildRadarView(list, query({ gap: true }))

    expect(ids(view.visible)).toEqual(['opp_001'])
    expect(view.isFiltered).toBe(true)
  })

  it('sorts the ranking by acceleration without changing the rank', () => {
    const view = buildRadarView(list, query({ sort: 'acceleration' }))

    expect(ids(view.visible)).toEqual(['opp_005', 'opp_001', 'opp_002', 'opp_003', 'opp_004'])
    expect(view.visible.map((item) => item.rank)).toEqual([5, 1, 2, 3, 4])
  })

  it('breaks acceleration ties by rank', () => {
    const tied = {
      ...list,
      items: list.items.map((item) => ({ ...item, acceleration: 0 })),
    }

    const view = buildRadarView(tied, query({ sort: 'acceleration' }))

    expect(view.visible.map((item) => item.rank)).toEqual([1, 2, 3, 4, 5])
  })

  it.each([
    { case: 'a valid id selects that topic', selected: 'opp_003', rank: 3 },
    { case: 'an unknown id selects nothing', selected: 'opp_999', rank: undefined },
    { case: 'no id selects nothing', selected: null, rank: undefined },
  ])('selection: $case', ({ selected, rank }) => {
    expect(buildRadarView(list, query({ selected })).selected?.rank).toBe(rank)
  })

  it('never dims the selected topic, even when the filters leave it out', () => {
    const view = buildRadarView(list, query({ lifecycle: ['saturated'], selected: 'opp_001' }))

    expect(view.dimmedIds).toEqual(new Set(['opp_002', 'opp_003']))
  })

  it('dims what is not highlighted when there is a highlight', () => {
    const view = buildRadarView(
      list,
      query({ highlight: ['opp_002', 'opp_003'], selected: 'opp_002' }),
    )

    expect(view.dimmedIds).toEqual(new Set(['opp_001', 'opp_004']))
  })

  it('picks the topics to publish now for the week, in rank order', () => {
    const view = buildRadarView(list, query({ lifecycle: ['emerging'] }))

    expect(ids(view.weekPicks.topics)).toEqual(['opp_001'])
    expect(view.weekPicks.hasPublishNow).toBe(true)
  })

  it('falls back to the first three of the ranking when no topic is to publish now', () => {
    // D9: sin «Publicar ya», «Esta semana» enseña los tres primeros por puesto.
    const none = {
      ...list,
      items: list.items.map((item) => ({ ...item, recommendation: 'find_angle' as const })),
    }

    const view = buildRadarView(none, query())

    expect(ids(view.weekPicks.topics)).toEqual(['opp_001', 'opp_002', 'opp_003'])
    expect(view.weekPicks.hasPublishNow).toBe(false)
  })

  it('adds up the outlier pieces of every topic', () => {
    // Fixture: opp_001 tiene 2 outliers y el resto, 0.
    expect(buildRadarView(list, query({ lifecycle: ['peaking'] })).outlierPieces).toBe(2)
  })

  it('is empty without an analysis run', () => {
    expect(buildRadarView(null, query())).toEqual({
      total: 0,
      ranked: [],
      visible: [],
      isFiltered: false,
      plotted: [],
      unevaluatedCount: 0,
      dimmedIds: new Set(),
      selected: null,
      counts: { publishNow: 0, accelerating: 0, emerging: 0, unknown: 0 },
      activeCounter: null,
      weekPicks: { topics: [], hasPublishNow: false },
      outlierPieces: 0,
    })
  })
})

describe('counter filters', () => {
  it.each([
    { case: 'one stage', filter: { lifecycle: ['unknown'] }, active: 'unknown' },
    { case: 'publish now', filter: { recommendation: 'publish_now' }, active: 'publish_now' },
    { case: 'two stages', filter: { lifecycle: ['accelerating', 'emerging'] }, active: null },
    {
      case: 'a stage and the LATAM gap',
      filter: { lifecycle: ['emerging'], gap: true },
      active: null,
    },
    {
      case: 'a stage and publish now',
      filter: { lifecycle: ['accelerating'], recommendation: 'publish_now' },
      active: null,
    },
    { case: 'a stage no counter has', filter: { lifecycle: ['peaking'] }, active: null },
  ] satisfies { case: string; filter: Partial<RadarQuery>; active: string | null }[])(
    'active counter with $case',
    ({ filter, active }) => {
      expect(buildRadarView(list, query(filter)).activeCounter).toBe(active)
    },
  )

  it('replaces any other filter with the pressed counter', () => {
    const current = query({ lifecycle: ['peaking', 'emerging'], gap: true, highlight: ['opp_001'] })

    expect(counterPatch('publish_now', current)).toEqual({
      lifecycle: [],
      gap: false,
      highlight: [],
      recommendation: 'publish_now',
    })
    expect(counterPatch('accelerating', current)).toEqual({
      lifecycle: ['accelerating'],
      gap: false,
      highlight: [],
      recommendation: null,
    })
  })

  it('resets the view when the active counter is pressed again', () => {
    expect(counterPatch('emerging', query({ lifecycle: ['emerging'] }))).toEqual({
      lifecycle: [],
      gap: false,
      highlight: [],
      recommendation: null,
    })
  })
})

describe('describeStageUnknowns', () => {
  const MONITORING_STARTED_AT = '2026-10-16T00:00:00Z'
  const [template] = list.items as [Opportunity]

  // Como el run servido del 17/10: 38 temas y, de los que no tienen etapa, 8 preliminares.
  function topics({ preliminary, unmatched }: { preliminary: number; unmatched: number }) {
    const staged = 38 - preliminary - unmatched
    const make = (count: number, patch: Partial<Opportunity>) =>
      Array.from({ length: count }, () => ({ ...template, ...patch }))
    return [
      ...make(preliminary, { lifecycle: 'unknown', growth_status: 'preliminary' }),
      ...make(unmatched, { lifecycle: 'unknown', growth_status: 'observed' }),
      ...make(staged, { lifecycle: 'accelerating', growth_status: 'observed' }),
    ]
  }

  it.each([
    {
      case: 'for lack of data and because no rule matches',
      counts: { preliminary: 8, unmatched: 11 },
      text: '19 de 38 temas no tienen etapa: 8 por falta de datos y 11 porque ninguna regla se cumple. Datos desde el 16/10, 00:00 UTC.',
    },
    {
      case: 'only because no rule matches',
      counts: { preliminary: 0, unmatched: 19 },
      text: '19 de 38 temas no tienen etapa: ninguna regla se cumple. Datos desde el 16/10, 00:00 UTC.',
    },
    {
      case: 'one topic, in the singular',
      counts: { preliminary: 0, unmatched: 1 },
      text: '1 de 38 temas no tiene etapa: ninguna regla se cumple. Datos desde el 16/10, 00:00 UTC.',
    },
    {
      case: 'every topic has a stage',
      counts: { preliminary: 0, unmatched: 0 },
      text: 'Todos los temas tienen etapa. Datos desde el 16/10, 00:00 UTC.',
    },
  ])('$case', ({ counts, text }) => {
    expect(describeStageUnknowns(topics(counts), MONITORING_STARTED_AT)).toBe(text)
  })
})

describe('describeWeekPicks', () => {
  const [first, second, third] = buildRadarView(list, query()).ranked

  it.each([
    {
      case: 'several topics to publish now',
      picks: { topics: [first!, second!], hasPublishNow: true },
      text: '2 temas para publicar ya: crecen y encajan con la audiencia de 30X.',
    },
    {
      case: 'one topic to publish now, in the singular',
      picks: { topics: [first!], hasPublishNow: true },
      text: '1 tema para publicar ya: crece y encaja con la audiencia de 30X.',
    },
    {
      case: 'no topic to publish now',
      picks: { topics: [first!, second!, third!], hasPublishNow: false },
      text: 'Ningún tema cumple hoy las condiciones de «Publicar ya». Los primeros del ranking:',
    },
  ])('$case', ({ picks, text }) => {
    expect(describeWeekPicks(picks)).toBe(text)
  })
})

describe('radar texts', () => {
  const headline = (q: RadarQuery, source: OpportunityList = list) =>
    radarHeadline(buildRadarView(source, q), q)
  const subline = (q: RadarQuery, source: OpportunityList = list) =>
    radarSubline(buildRadarView(source, q), q)

  const HOW_TO_READ = 'Ordenados por oportunidad. Elija una burbuja o una fila para ver el tema.'

  it('counts the topics when there is no filter', () => {
    expect(headline(query())).toBe('5 temas esta semana')
  })

  it('says how many topics pass the filter out of the total', () => {
    expect(headline(query({ lifecycle: ['peaking', 'saturated'] }))).toBe('2 de 5 temas')
  })

  it('uses the singular for a single topic', () => {
    const single = { ...list, items: list.items.slice(0, 1) }

    expect(headline(query(), single)).toBe('1 tema esta semana')
    expect(subline(query(), single)).toBe(`Hay 1 tema analizado esta semana. ${HOW_TO_READ}`)
  })

  it('says how many topics were analyzed when there are fewer than ten', () => {
    expect(subline(query())).toBe(`Hay 5 temas analizados esta semana. ${HOW_TO_READ}`)
  })

  it('explains how to read the radar when there are at least ten topics', () => {
    const ten = {
      ...list,
      items: [...list.items, ...list.items].map((item, index) => ({ ...item, id: `opp_${index}` })),
    }

    expect(subline(query(), ten)).toBe(HOW_TO_READ)
  })

  it.each([
    {
      case: 'stages only',
      filter: { lifecycle: ['peaking', 'saturated'] },
      text: 'Filtro: etapa en pico o saturado. El resto queda atenuado en el radar.',
    },
    {
      case: 'publish now',
      filter: { recommendation: 'publish_now' },
      text: 'Filtro: para publicar ya. El resto queda atenuado en el radar.',
    },
    {
      case: 'stages and LATAM gap',
      filter: { lifecycle: ['peaking', 'saturated'], gap: true },
      text: 'Filtro: etapa en pico o saturado · con hueco en LATAM. El resto queda atenuado en el radar.',
    },
  ] satisfies { case: string; filter: Partial<RadarQuery>; text: string }[])(
    'describes the filter: $case',
    ({ filter, text }) => {
      expect(subline(query(filter))).toBe(text)
    },
  )
})
