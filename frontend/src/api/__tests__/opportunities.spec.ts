import { describe, expect, it } from 'vitest'

import fixture from '@fixtures/opportunities.json'
import { SCORE_MAX } from '@/lib/opportunityFormat'
import { CONFIDENCES, LIFECYCLES } from '@/lib/radarQuery'

import type { Schemas } from '../client'

// Solo los tests necesitan estos dos enums en tiempo de ejecución; los demás vienen de radarQuery.
// `satisfies` hace que el type-check avise si un valor deja de existir en el contrato
// (src/types/api.ts); el test avisa si el fixture usa uno que no está en la lista.
const RECOMMENDATIONS = [
  'publish_now',
  'find_angle',
  'wait_for_case',
  'discard',
] as const satisfies readonly Schemas['Recommendation'][]
const GROWTH_STATUSES = [
  'observed',
  'estimated',
  'preliminary',
] as const satisfies readonly Schemas['GrowthStatus'][]

const SCORE_KEYS = [
  'momentum_score',
  'audience_fit_score',
  'cross_source_score',
  'saturation_score',
  'actionability_score',
  'opportunity_score',
] as const satisfies readonly (keyof Schemas['Opportunity'])[]
const SCORE_MIN = 0
const PLATFORMS = [
  'youtube',
  'hackernews',
  'rss',
  'brave',
  'linkedin',
  'instagram',
  'tiktok',
] as const satisfies readonly Schemas['Platform'][]
// GET /timeline: dos ventanas de 3 periodos de 24 h, la anterior primero (CLAUDE.md §7).
const TIMELINE_WINDOWS = ['previous', 'previous', 'previous', 'current', 'current', 'current']

const items = fixture.opportunities.items

describe('opportunities fixture', () => {
  it('declares itself as mock data', () => {
    expect(fixture._fixture).toMatch(/^MOCK/)
  })

  it.each(items)('marks the topic of $id as mock', (item) => {
    expect(item.topic).toMatch(/^\[MOCK\]/)
  })

  it.each(items)('uses only contract enum values in $id', (item) => {
    expect(LIFECYCLES).toContain(item.lifecycle)
    expect(RECOMMENDATIONS).toContain(item.recommendation)
    expect(GROWTH_STATUSES).toContain(item.growth_status)
    expect(CONFIDENCES).toContain(item.confidence)
  })

  it.each(items)('keeps every non-null score of $id between 0 and 100', (item) => {
    for (const key of SCORE_KEYS) {
      const score = item[key]
      if (score === null) continue
      expect(score, key).toBeGreaterThanOrEqual(SCORE_MIN)
      expect(score, key).toBeLessThanOrEqual(SCORE_MAX)
    }
  })

  it.each(Object.entries(fixture.timeline))('orders the timeline windows of %s', (_, timeline) => {
    expect(timeline.points.map((point) => point.window)).toEqual(TIMELINE_WINDOWS)
  })

  it.each(Object.entries(fixture.evidence))(
    'keys the evidence of %s by unique url',
    (_, pieces) => {
      const urls = pieces.map((piece) => piece.url)
      expect(new Set(urls).size).toBe(urls.length)
      for (const piece of pieces) expect(PLATFORMS).toContain(piece.platform)
    },
  )
})
