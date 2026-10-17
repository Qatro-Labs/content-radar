import { describe, expect, it } from 'vitest'

import fixture from '@fixtures/opportunities.json'
import type { components } from '@/types/api'

import type { RadarQuery } from '../radarQuery'
import { buildRadarView, radarHeadline, radarSubline } from '../radarView'

type OpportunityList = components['schemas']['OpportunityList']

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
    ...patch,
  }
}

const ids = (items: { id: string }[]) => items.map((item) => item.id)

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
    expect(view.counts).toEqual({ accelerating: 1, emerging: 1, latamGap: 1 })
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
    expect(view.counts).toEqual({ accelerating: 0, emerging: 0, latamGap: 0 })
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
    { case: 'an unknown id falls back to rank 1', selected: 'opp_999', rank: 1 },
    { case: 'no id falls back to rank 1', selected: null, rank: 1 },
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
      counts: { accelerating: 0, emerging: 0, latamGap: 0 },
    })
  })
})

describe('radar texts', () => {
  const headline = (q: RadarQuery, source: OpportunityList = list) =>
    radarHeadline(buildRadarView(source, q), q)
  const subline = (q: RadarQuery, source: OpportunityList = list) =>
    radarSubline(buildRadarView(source, q), q)

  it('counts the opportunities when there is no filter', () => {
    expect(headline(query())).toBe('5 oportunidades esta semana')
  })

  it('says how many topics pass the filter out of the total', () => {
    expect(headline(query({ lifecycle: ['peaking', 'saturated'] }))).toBe('2 de 5 temas')
  })

  it('uses the singular for a single opportunity', () => {
    const single = { ...list, items: list.items.slice(0, 1) }

    expect(headline(query(), single)).toBe('1 oportunidad esta semana')
    expect(subline(query(), single)).toBe('Hay 1 tema analizado esta semana.')
  })

  it('says how many topics were analyzed when there are fewer than ten', () => {
    expect(subline(query())).toBe('Hay 5 temas analizados esta semana.')
  })

  it('describes the radar when there are at least ten topics', () => {
    const ten = {
      ...list,
      items: [...list.items, ...list.items].map((item, index) => ({ ...item, id: `opp_${index}` })),
    }

    expect(subline(query(), ten)).toBe(
      'Los temas de IA que más rápido crecen, ordenados por su encaje con líderes y equipos de LATAM.',
    )
  })

  it.each([
    {
      case: 'stages only',
      filter: { lifecycle: ['peaking', 'saturated'] },
      text: 'Filtro: etapa en pico o saturado.',
    },
    {
      case: 'stages and LATAM gap',
      filter: { lifecycle: ['peaking', 'saturated'], gap: true },
      text: 'Filtro: etapa en pico o saturado · con hueco en LATAM.',
    },
  ] satisfies { case: string; filter: Partial<RadarQuery>; text: string }[])(
    'describes the filter: $case',
    ({ filter, text }) => {
      expect(subline(query(filter))).toBe(text)
    },
  )
})
