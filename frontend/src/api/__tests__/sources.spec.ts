import { describe, expect, it } from 'vitest'

import type { Schemas } from '../client'
import { latestObservation } from '../sources'

function source(id: number, lastObservedAt: string | null): Schemas['SourceStatus'] {
  return {
    id,
    platform: 'hackernews',
    name: `fuente ${id}`,
    segment: 'tech',
    active: true,
    items: 0,
    last_observed_at: lastObservedAt,
  }
}

describe('latestObservation', () => {
  it('returns the most recent observation across sources', () => {
    const sources = [
      source(1, '2026-10-17T02:50:00Z'),
      source(2, '2026-10-17T14:10:00Z'),
      source(3, '2026-10-17T08:30:00Z'),
    ]

    expect(latestObservation(sources)).toBe('2026-10-17T14:10:00Z')
  })

  it('returns null when no source has been collected yet', () => {
    expect(latestObservation([source(1, null), source(2, null)])).toBeNull()
  })
})
