import { describe, expect, it } from 'vitest'

import fixture from '@fixtures/opportunities.json'
import type { components } from '@/types/api'

import {
  citationChips,
  componentRows,
  describePenalties,
  rankOf,
  splitTimeline,
} from '../dossierView'

type Schemas = components['schemas']

// TS lee los enums del JSON como `string`; el fixture cumple el contrato (opportunities.spec.ts).
const list = fixture.opportunities as Schemas['OpportunityList']
const evidence = fixture.evidence as Record<string, Schemas['Evidence'][]>
const timeline = fixture.timeline as Record<string, Schemas['OpportunityTimeline']>

const LAST_UPDATED = '2026-10-17T19:09:00Z'

function flatTimeline(): Schemas['OpportunityTimeline'] {
  const dates = ['10-12', '10-13', '10-14', '10-15', '10-16', '10-17']
  return {
    opportunity_id: 'opp_x',
    window_days: 3,
    points: dates.map((date, index) => ({
      date: `2026-${date}`,
      count: 0,
      window: index < 3 ? 'previous' : 'current',
    })),
  }
}

describe('rankOf', () => {
  it('finds the position of a topic in the served list', () => {
    expect(rankOf(list, 'opp_003')).toEqual({ rank: 3, total: 5 })
  })

  it('returns null for a topic that is not in the list', () => {
    expect(rankOf(list, 'opp_999')).toBeNull()
  })
})

describe('splitTimeline', () => {
  it('splits the six periods into the previous and the current window', () => {
    const windows = splitTimeline(timeline.opp_001!, LAST_UPDATED)

    expect(windows.previousLabel).toBe('Ventana anterior · 12–14/10')
    expect(windows.currentLabel).toBe('Ventana actual · 15–17/10')
    expect(windows.previous.map((bar) => bar.count)).toEqual([2, 3, 2])
    expect(windows.current.map((bar) => bar.label)).toEqual(['15/10', '16/10', '17/10'])
    expect(windows.scaleMax).toBe(6)
    expect(windows.cutoffTime).toBe('19:09')
  })

  it('keeps a scale of 1 when no period has pieces', () => {
    expect(splitTimeline(flatTimeline(), LAST_UPDATED).scaleMax).toBe(1)
  })

  it('writes both months when a window crosses into the next one', () => {
    const crossing = flatTimeline()
    crossing.points = ['09-27', '09-28', '09-29', '09-30', '10-01', '10-02'].map((date, index) => ({
      ...crossing.points[index]!,
      date: `2026-${date}`,
    }))

    expect(splitTimeline(crossing, LAST_UPDATED).currentLabel).toBe('Ventana actual · 30/09–02/10')
  })
})

describe('componentRows', () => {
  it('keeps the API order and writes the weight as a percentage', () => {
    const rows = componentRows(list.items[0]!.score_breakdown!)

    expect(rows.map((row) => row.label)).toEqual([
      'Momentum',
      'Encaje con 30X',
      'Fuentes independientes',
      'Frescura',
      'Accionabilidad',
    ])
    expect(rows[0]).toMatchObject({ value: 78.8, display: '79', weightLabel: 'peso 30 %' })
    expect(rows[1]!.display).toBe('Alto · 83')
  })
})

describe('describePenalties', () => {
  it.each([
    { name: 'no penalty', penalties: [], expected: 'sin penalizaciones' },
    {
      name: 'both penalties with U+2212',
      penalties: [
        { name: 'single_source', points: 10 },
        { name: 'small_sample', points: 10 },
      ] satisfies Schemas['ScorePenalty'][],
      expected: 'Una sola fuente −10 · Muestra pequeña −10',
    },
  ])('describes $name', ({ penalties, expected }) => {
    expect(describePenalties(penalties)).toBe(expected)
  })
})

describe('citationChips', () => {
  const criterion: Schemas['AudienceFitCriterion'] = {
    criterion: 'business_impact',
    justification: 'Cita una pieza servida y otra que no está en la evidencia.',
    evidence_urls: ['https://example.com/mock/1', 'https://www.infobae.com/tecno/epic'],
    level: 4,
  }

  it('names a cited piece by its short source and an unknown url by its host', () => {
    const chips = citationChips(criterion, evidence.opp_001!)

    expect(chips).toEqual([
      {
        url: 'https://example.com/mock/1',
        label: 'Fuente mock youtube business',
        isInEvidence: true,
      },
      { url: 'https://www.infobae.com/tecno/epic', label: 'www.infobae.com', isInEvidence: false },
    ])
  })
})
