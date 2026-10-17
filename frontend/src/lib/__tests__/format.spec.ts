import { describe, expect, it } from 'vitest'

import { formatUtcTimestamp } from '../format'

describe('formatUtcTimestamp', () => {
  it('writes day, month and 24 h time in UTC', () => {
    expect(formatUtcTimestamp('2026-10-17T02:50:41Z')).toBe('17/10, 02:50 UTC')
  })

  it('converts offsets to UTC', () => {
    expect(formatUtcTimestamp('2026-10-17T21:05:00-05:00')).toBe('18/10, 02:05 UTC')
  })
})
