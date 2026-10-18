import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'

import { IDLE_LIFE, useRadIdleLife } from '../useRadIdleLife'

const GLANCE_TARGET = { x: 900, y: 120 }

function setUp({ resting = true } = {}) {
  const isResting = ref(resting)
  const cursor = { x: ref(0), y: ref(0) }
  const scope = effectScope()
  // `random` fijo a 0,99: el siguiente parpadeo llega casi en el máximo y nunca hay doble
  // parpadeo (solo sale con valores por debajo de su probabilidad).
  const life = scope.run(() =>
    useRadIdleLife({
      isResting,
      cursor,
      randomGlanceTarget: () => GLANCE_TARGET,
      random: () => 0.99,
    }),
  )!
  return { life, isResting, cursor, scope }
}

describe('useRadIdleLife', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('says hello with a blink and keeps blinking now and then while resting', async () => {
    const { life, scope } = setUp()

    await vi.advanceTimersByTimeAsync(IDLE_LIFE.firstBlinkMs)
    expect(life.blinks.value).toBe(1)

    await vi.advanceTimersByTimeAsync(IDLE_LIFE.blinkMaxMs)
    expect(life.blinks.value).toBe(2)
    scope.stop()
  })

  it('does not blink on its own while Rad works', async () => {
    const { life, scope } = setUp({ resting: false })

    await vi.advanceTimersByTimeAsync(IDLE_LIFE.firstBlinkMs + IDLE_LIFE.blinkMaxMs)

    expect(life.blinks.value).toBe(0)
    scope.stop()
  })

  it('glances somewhere else when the cursor rests, then looks back', async () => {
    const { life, scope } = setUp()

    await vi.advanceTimersByTimeAsync(IDLE_LIFE.glanceAfterIdleMs)
    expect(life.glance.value).toEqual(GLANCE_TARGET)

    await vi.advanceTimersByTimeAsync(IDLE_LIFE.glanceHoldMs)
    expect(life.glance.value).toBeNull()
    scope.stop()
  })

  it('stops glancing as soon as the cursor moves', async () => {
    const { life, cursor, scope } = setUp()
    await vi.advanceTimersByTimeAsync(IDLE_LIFE.glanceAfterIdleMs)

    cursor.x.value = 40
    await nextTick()

    expect(life.glance.value).toBeNull()
    scope.stop()
  })
})
