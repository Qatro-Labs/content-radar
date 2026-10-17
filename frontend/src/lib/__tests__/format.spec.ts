import { describe, expect, it } from 'vitest'

import { formatUtcDay, formatUtcTime, formatUtcTimestamp } from '../format'

describe('formatUtcTimestamp', () => {
  it('writes day, month and 24 h time in UTC', () => {
    expect(formatUtcTimestamp('2026-10-17T02:50:41Z')).toBe('17/10, 02:50 UTC')
  })

  it('converts offsets to UTC', () => {
    expect(formatUtcTimestamp('2026-10-17T21:05:00-05:00')).toBe('18/10, 02:05 UTC')
  })
})

describe('single-digit dates', () => {
  it('pads day, month, hour and minute', () => {
    expect(formatUtcTimestamp('2026-10-02T03:04:00Z')).toBe('02/10, 03:04 UTC')
    expect(formatUtcDay('2026-09-07T23:59:00Z')).toBe('07/09')
    expect(formatUtcTime('2026-10-17T19:09:59Z')).toBe('19:09')
  })
})
