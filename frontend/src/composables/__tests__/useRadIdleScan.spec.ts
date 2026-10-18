import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'

import { IDLE_SCAN, useRadIdleScan } from '../useRadIdleScan'

function setUp() {
  const enabled = ref(true)
  const blinkKey = ref(0)
  const scope = effectScope()
  // `random` fijo a 0: cada pasada llega justo en el mínimo del intervalo.
  const scan = scope.run(() => useRadIdleScan({ enabled, blinkKey, random: () => 0 }))!
  return { scan, enabled, blinkKey, scope }
}

describe('useRadIdleScan', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('waits before the first pass, opens, sweeps once and blinks when it is an eye again', async () => {
    const { scan, scope } = setUp()

    await vi.advanceTimersByTimeAsync(IDLE_SCAN.everyMinMs - 1)
    expect(scan.isOpen.value).toBe(false)

    await vi.advanceTimersByTimeAsync(1)
    expect(scan.isOpen.value).toBe(true)
    expect(scan.scanKey.value).toBe(0)

    await vi.advanceTimersByTimeAsync(IDLE_SCAN.morphMs)
    expect(scan.scanKey.value).toBe(1)

    await vi.advanceTimersByTimeAsync(IDLE_SCAN.sweepMs)
    expect(scan.isOpen.value).toBe(false)
    expect(scan.blinkKey.value).toBe(0)

    await vi.advanceTimersByTimeAsync(IDLE_SCAN.morphMs)
    expect(scan.blinkKey.value).toBe(1)
    scope.stop()
  })

  it('holds outside blinks during the pass so the radar is not cut', async () => {
    const { scan, blinkKey, scope } = setUp()
    await vi.advanceTimersByTimeAsync(IDLE_SCAN.everyMinMs + IDLE_SCAN.morphMs)

    blinkKey.value = 5
    await nextTick()
    expect(scan.blinkKey.value).toBe(0)

    await vi.advanceTimersByTimeAsync(IDLE_SCAN.sweepMs + IDLE_SCAN.morphMs)
    expect(scan.blinkKey.value).toBe(6)
    scope.stop()
  })

  it('folds back to an eye without blinking when disabled mid-pass, and waits to be enabled', async () => {
    const { scan, enabled, scope } = setUp()
    await vi.advanceTimersByTimeAsync(IDLE_SCAN.everyMinMs + IDLE_SCAN.morphMs)

    enabled.value = false
    await nextTick()
    expect(scan.isOpen.value).toBe(false)

    await vi.advanceTimersByTimeAsync(IDLE_SCAN.everyMaxMs * 2)
    expect(scan.isOpen.value).toBe(false)
    expect(scan.blinkKey.value).toBe(0)

    enabled.value = true
    await nextTick()
    await vi.advanceTimersByTimeAsync(IDLE_SCAN.everyMinMs)
    expect(scan.isOpen.value).toBe(true)
    scope.stop()
  })
})
