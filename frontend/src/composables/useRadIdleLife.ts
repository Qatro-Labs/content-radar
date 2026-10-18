import { tryOnScopeDispose, useDocumentVisibility, usePreferredReducedMotion } from '@vueuse/core'
import { computed, ref, watch, type Ref } from 'vue'

// Rad en reposo parece vivo: parpadea de vez en cuando (a veces dos veces) y, si el cursor se queda
// quieto, mira un momento a otro sitio de la página. Es su personaje, no un dato: es la única
// excepción a «nada de bucles» de DESIGN.md §7, y se para mientras trabaja, con la pestaña oculta
// y con movimiento reducido.

export const IDLE_LIFE = {
  // Un parpadeo de «hola» poco después de cargar.
  firstBlinkMs: 900,
  blinkMinMs: 3200,
  blinkMaxMs: 7000,
  doubleBlinkChance: 0.25,
  doubleBlinkGapMs: 320,
  glanceAfterIdleMs: 2500,
  glanceHoldMs: 1300,
  glanceEveryMinMs: 3500,
  glanceEveryMaxMs: 7000,
} as const

interface Point {
  x: number
  y: number
}

export interface IdleLifeOptions {
  isResting: Ref<boolean>
  cursor: { x: Ref<number>; y: Ref<number> }
  // Un punto de la ventana, en coordenadas de `[data-agent-root]`, al que mirar un momento.
  randomGlanceTarget: () => Point
  random?: () => number
}

export function useRadIdleLife({
  isResting,
  cursor,
  randomGlanceTarget,
  random = Math.random,
}: IdleLifeOptions) {
  const blinks = ref(0)
  const glance = ref<Point | null>(null)
  const motionPreference = usePreferredReducedMotion()
  const visibility = useDocumentVisibility()
  const isAlive = computed(
    () => isResting.value && motionPreference.value !== 'reduce' && visibility.value === 'visible',
  )
  const timers = new Set<ReturnType<typeof setTimeout>>()
  let blinkTimer: ReturnType<typeof setTimeout> | undefined
  let glanceTimer: ReturnType<typeof setTimeout> | undefined

  function later(callback: () => void, ms: number) {
    const timer = setTimeout(() => {
      timers.delete(timer)
      callback()
    }, ms)
    timers.add(timer)
    return timer
  }

  function cancel(timer: ReturnType<typeof setTimeout> | undefined) {
    if (timer === undefined) return
    clearTimeout(timer)
    timers.delete(timer)
  }

  function between(min: number, max: number): number {
    return min + random() * (max - min)
  }

  function blink() {
    blinks.value += 1
  }

  function scheduleBlink(delayMs: number) {
    cancel(blinkTimer)
    blinkTimer = later(() => {
      if (isAlive.value) {
        blink()
        if (random() < IDLE_LIFE.doubleBlinkChance) later(blink, IDLE_LIFE.doubleBlinkGapMs)
      }
      scheduleBlink(between(IDLE_LIFE.blinkMinMs, IDLE_LIFE.blinkMaxMs))
    }, delayMs)
  }

  function lookBack() {
    glance.value = null
    scheduleGlance(between(IDLE_LIFE.glanceEveryMinMs, IDLE_LIFE.glanceEveryMaxMs))
  }

  function scheduleGlance(delayMs: number) {
    cancel(glanceTimer)
    glanceTimer = later(() => {
      if (!isAlive.value) return scheduleGlance(IDLE_LIFE.glanceAfterIdleMs)
      glance.value = randomGlanceTarget()
      glanceTimer = later(lookBack, IDLE_LIFE.glanceHoldMs)
    }, delayMs)
  }

  // Mover el cursor le devuelve la mirada al instante y reinicia la espera.
  watch([cursor.x, cursor.y], () => {
    glance.value = null
    scheduleGlance(IDLE_LIFE.glanceAfterIdleMs)
  })
  watch(isAlive, (alive) => {
    if (!alive) glance.value = null
  })

  scheduleBlink(IDLE_LIFE.firstBlinkMs)
  scheduleGlance(IDLE_LIFE.glanceAfterIdleMs)
  tryOnScopeDispose(() => {
    for (const timer of timers) clearTimeout(timer)
    timers.clear()
  })

  return { blinks, glance, blink }
}
