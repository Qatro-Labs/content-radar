import { describe, expect, it } from 'vitest'

import {
  countLabel,
  formatCount,
  formatMetrics,
  formatRatio,
  formatVelocity,
  missingRatioLabel,
  performanceFraction,
  ratioLabel,
  shortSourceName,
} from '@/lib/evidenceFormat'
import type { components } from '@/types/api'

type Evidence = components['schemas']['Evidence']

const NO_METRICS = { views: null, likes: null, comments: null, points: null, shares: null }

function piece(overrides: Partial<Evidence>): Evidence {
  return {
    url: 'https://example.com/a',
    source: 'Canal',
    platform: 'youtube',
    segment: 'tech',
    title: 'Pieza',
    published_at: '2026-10-07T10:00:00Z',
    observed_at: '2026-10-17T19:00:00Z',
    metrics: { ...NO_METRICS, views: 1000 },
    collection: 'automatic',
    replica_count: 0,
    ...overrides,
  }
}

describe('formatCount', () => {
  it('groups four-digit numbers', () => {
    expect(formatCount(1363)).toBe('1.363')
    expect(formatCount(658220)).toBe('658.220')
  })
})

describe('countLabel', () => {
  it.each([
    ['the singular for one', 1, '1 fuente'],
    ['the plural for none', 0, '0 fuentes'],
    ['grouped thousands in the plural', 1363, '1.363 fuentes'],
  ])('writes %s', (_, count, expected) => {
    expect(countLabel(count, 'fuente', 'fuentes')).toBe(expected)
  })
})

describe('formatMetrics', () => {
  it('returns null when the source exposes no metric', () => {
    expect(formatMetrics(NO_METRICS)).toBeNull()
  })

  it('lists the exposed metrics in a fixed order', () => {
    expect(formatMetrics({ ...NO_METRICS, likes: 4367, views: 213269 })).toBe(
      '213.269 vistas · 4.367 me gusta',
    )
  })
})

describe('formatVelocity', () => {
  it.each([
    ['a stalled HN story', { value: 0, unit: 'points/h' }, '0 puntos/h'],
    ['a fast video', { value: 1363.4, unit: 'views/h' }, '1.363 vistas/h'],
    ['a slow rate', { value: 2.44, unit: 'points/h' }, '2,4 puntos/h'],
  ])('formats %s', (_, velocity, expected) => {
    expect(formatVelocity(velocity)).toBe(expected)
  })

  it('returns null without two snapshots', () => {
    expect(formatVelocity(null)).toBeNull()
  })
})

describe('ratios', () => {
  it('writes the ratio with a decimal comma', () => {
    expect(formatRatio(26.9)).toBe('26,9×')
  })

  it.each([
    ['caps a big outlier at the end of the bar', 26.9, 1],
    ['puts 3× at the middle', 3, 0.5],
  ])('%s', (_, ratio, fraction) => {
    expect(performanceFraction(ratio)).toBe(fraction)
  })

  it.each([
    ['an outlier', piece({ outlier_ratio: 5.1, is_outlier: true }), 'Outlier'],
    ['a highlighted piece', piece({ outlier_ratio: 2.4, is_outlier: false }), 'Destacada'],
    ['an ordinary piece', piece({ outlier_ratio: 1.2, is_outlier: false }), null],
  ])('labels %s', (_, evidence, label) => {
    expect(ratioLabel(evidence)).toBe(label)
  })

  it.each([
    ['RSS', piece({ platform: 'rss', metrics: NO_METRICS }), 'Sin métricas públicas'],
    ['YouTube with views', piece({ platform: 'youtube' }), 'Sin línea base del canal'],
  ])('explains a missing ratio on %s', (_, evidence, label) => {
    expect(missingRatioLabel(evidence)).toBe(label)
  })
})

describe('shortSourceName', () => {
  it.each([
    ['Xataka · Inteligencia artificial', 'Xataka'],
    ['The AI Daily Brief: Artificial Intelligence News', 'The AI Daily Brief'],
    ['midudev', 'midudev'],
  ])('shortens %s', (source, expected) => {
    expect(shortSourceName(source)).toBe(expected)
  })
})
