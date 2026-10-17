<script setup lang="ts">
import { TransitionPresets, usePreferredReducedMotion, useTransition } from '@vueuse/core'
import { computed } from 'vue'

import { formatScore, SCORE_MAX } from '@/lib/opportunityFormat'

// DESIGN.md §4: anillo de 112 px; la vista previa del Radar lo usa a 104 px (D8 del plan
// fe-dashboard-v2).
const DEFAULT_RING_SIZE_PX = 112

const { score, sizePx = DEFAULT_RING_SIZE_PX } = defineProps<{
  score: number | null
  sizePx?: number
}>()

// DESIGN.md §4 y §7: trazo de 9 px; la cifra cuenta en 450 ms con la curva ease-out de la UI
// (`easeOutExpo` es la misma cubic-bezier(0.16, 1, 0.3, 1)).
const STROKE_WIDTH = 9
const COUNT_DURATION_MS = 450

const center = computed(() => sizePx / 2)
const radius = computed(() => (sizePx - STROKE_WIDTH) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)

const reducedMotion = usePreferredReducedMotion()

// Sin score no se dibuja el arco ni la cifra: el 0 solo es el punto de partida de la animación.
const animatedScore = useTransition(() => score ?? 0, {
  duration: COUNT_DURATION_MS,
  easing: TransitionPresets.easeOutExpo,
  disabled: computed(() => reducedMotion.value === 'reduce'),
})

const shownScore = computed(() => formatScore(score === null ? null : animatedScore.value))
const dashOffset = computed(() => circumference.value * (1 - animatedScore.value / SCORE_MAX))
const accessibleLabel = computed(() =>
  score === null
    ? `Puntuación ${formatScore(null)}`
    : `Puntuación ${formatScore(score)} de ${SCORE_MAX}`,
)
</script>

<template>
  <div
    class="relative shrink-0"
    :style="{ width: `${sizePx}px`, height: `${sizePx}px` }"
    role="img"
    :aria-label="accessibleLabel"
  >
    <svg :viewBox="`0 0 ${sizePx} ${sizePx}`" class="block size-full" aria-hidden="true">
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        class="stroke-track"
        :stroke-width="STROKE_WIDTH"
      />
      <circle
        v-if="score !== null"
        :cx="center"
        :cy="center"
        :r="radius"
        fill="none"
        class="score-ring-arc stroke-foreground"
        :stroke-width="STROKE_WIDTH"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        :transform="`rotate(-90 ${center} ${center})`"
        :style="{ '--ring-length': `${circumference}px` }"
      />
    </svg>
    <div class="absolute inset-0 flex flex-col items-center justify-center" aria-hidden="true">
      <template v-if="score !== null">
        <span class="font-display text-[38px] leading-none font-semibold tracking-[-0.04em]">
          {{ shownScore }}
        </span>
        <span class="text-xs text-muted-foreground">de {{ SCORE_MAX }}</span>
      </template>
      <span v-else class="px-4 text-center text-[13px] leading-tight text-muted-foreground">
        {{ shownScore }}
      </span>
    </div>
  </div>
</template>

<style scoped>
/* DESIGN.md §7: el anillo se dibuja al cargar (1.1 s); al cambiar de valor lo mueve la cifra. */
.score-ring-arc {
  animation: score-ring-draw 1100ms var(--ease-out) backwards;
}

@media (prefers-reduced-motion: reduce) {
  .score-ring-arc {
    animation: none;
  }
}

@keyframes score-ring-draw {
  from {
    stroke-dashoffset: var(--ring-length);
  }
}
</style>
