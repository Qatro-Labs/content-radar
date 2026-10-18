import { tryOnScopeDispose, useDocumentVisibility, usePreferredReducedMotion } from '@vueuse/core'
import { computed, ref, toValue, watch, type MaybeRefOrGetter } from 'vue'

// Con la barra reducida, Rad hace de vez en cuando lo mismo que al trabajar: se abre en radar, su
// haz da una pasada y vuelve a ser un ojo que parpadea. Es su personaje, como la vida en reposo
// (useRadIdleLife), y como ella se para con la pestaña oculta y con movimiento reducido.

export const IDLE_SCAN = {
  // Espaciado para que se lea como un gesto suyo de vez en cuando y no como un aviso que pide
  // atención; el primero tampoco llega antes, así que nunca coincide con la carga ni con el vuelo
  // del ojo al reducir la barra.
  everyMinMs: 25_000,
  everyMaxMs: 45_000,
  // Lo que tarda RadMark en abrirse en radar o volver a ser ojo (su transición de 380 ms): el haz
  // espera a que el radar esté abierto, y el parpadeo, a que vuelva a ser un ojo.
  morphMs: 380,
  // Una pasada del haz (`rad-sweep` en RadMark).
  sweepMs: 1100,
} as const

type ScanPhase = 'eye' | 'opening' | 'sweeping' | 'closing'

export interface IdleScanOptions {
  // `false` mientras Rad trabaja o la persona tiene el cursor o el foco encima: cancela la pasada
  // en curso, que vuelve a ojo sin pausas.
  enabled: MaybeRefOrGetter<boolean>
  // El `blinkKey` que llega de fuera (parpadeos de la vida en reposo y al terminar una pregunta).
  blinkKey: MaybeRefOrGetter<number>
  random?: () => number
}

export function useRadIdleScan({ enabled, blinkKey, random = Math.random }: IdleScanOptions) {
  const phase = ref<ScanPhase>('eye')
  const passes = ref(0)
  const blinks = ref(0)
  const motionPreference = usePreferredReducedMotion()
  const visibility = useDocumentVisibility()
  const canScan = computed(
    () => toValue(enabled) && motionPreference.value !== 'reduce' && visibility.value === 'visible',
  )
  let timer: ReturnType<typeof setTimeout> | undefined

  function next(callback: () => void, ms: number) {
    clearTimeout(timer)
    timer = setTimeout(callback, ms)
  }

  function between(min: number, max: number): number {
    return min + random() * (max - min)
  }

  function scheduleScan() {
    next(open, between(IDLE_SCAN.everyMinMs, IDLE_SCAN.everyMaxMs))
  }

  function open() {
    phase.value = 'opening'
    next(sweep, IDLE_SCAN.morphMs)
  }

  function sweep() {
    passes.value += 1
    phase.value = 'sweeping'
    next(() => close({ blinkAtEnd: true }), IDLE_SCAN.sweepMs)
  }

  // Cerrar siempre pasa por la vuelta a ojo, también al cancelar: nunca salta de radar a ojo.
  function close({ blinkAtEnd }: { blinkAtEnd: boolean }) {
    phase.value = 'closing'
    next(() => settle({ blinkAtEnd }), IDLE_SCAN.morphMs)
  }

  function settle({ blinkAtEnd }: { blinkAtEnd: boolean }) {
    phase.value = 'eye'
    if (blinkAtEnd) blinks.value += 1
    if (canScan.value) scheduleScan()
  }

  watch(
    canScan,
    (can) => {
      if (can) {
        // Si está volviendo a ojo, al llegar programa la siguiente.
        if (phase.value === 'eye') scheduleScan()
        return
      }
      if (phase.value === 'eye') return clearTimeout(timer)
      close({ blinkAtEnd: false })
    },
    { immediate: true },
  )

  tryOnScopeDispose(() => clearTimeout(timer))

  // Un parpadeo cambia la `key` de la marca y la remonta: durante la pasada cortaría el radar de
  // golpe. Se retiene hasta que vuelve a ser un ojo y entonces parpadea una vez.
  const ownBlinkKey = computed(() => toValue(blinkKey) + blinks.value)
  const heldBlinkKey = ref(ownBlinkKey.value)
  const isHoldingBlink = computed(() => phase.value !== 'eye')
  watch(isHoldingBlink, (holding) => {
    if (holding) heldBlinkKey.value = ownBlinkKey.value
  })

  return {
    isOpen: computed(() => phase.value === 'opening' || phase.value === 'sweeping'),
    // 0 mientras se abre: RadMark solo pasa el haz con un `scanKey` nuevo y mayor que 0.
    scanKey: computed(() => (phase.value === 'sweeping' ? passes.value : 0)),
    blinkKey: computed(() => (isHoldingBlink.value ? heldBlinkKey.value : ownBlinkKey.value)),
  }
}
