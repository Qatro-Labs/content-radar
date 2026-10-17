<script setup lang="ts">
import { TransitionPresets, usePreferredReducedMotion, useTransition } from '@vueuse/core'
import { computed } from 'vue'

import { formatScore, SCORE_MAX } from '@/lib/opportunityFormat'

const { score } = defineProps<{ score: number | null }>()

// DESIGN.md §4 y §7: anillo de 112 px con trazo de 9 px; la cifra cuenta en 450 ms con la
// curva ease-out de la UI (`easeOutExpo` es la misma cubic-bezier(0.16, 1, 0.3, 1)).
const RING_SIZE = 112
const STROKE_WIDTH = 9
const COUNT_DURATION_MS = 450
const CENTER = RING_SIZE / 2
const RADIUS = (RING_SIZE - STROKE_WIDTH) / 2
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

const reducedMotion = usePreferredReducedMotion()

// Sin score no se dibuja el arco ni la cifra: el 0 solo es el punto de partida de la animación.
const animatedScore = useTransition(() => score ?? 0, {
  duration: COUNT_DURATION_MS,
  easing: TransitionPresets.easeOutExpo,
  disabled: computed(() => reducedMotion.value === 'reduce'),
})

const shownScore = computed(() => formatScore(score === null ? null : animatedScore.value))
const dashOffset = computed(() => CIRCUMFERENCE * (1 - animatedScore.value / SCORE_MAX))
const accessibleLabel = computed(() =>
  score === null
    ? `Puntuación ${formatScore(null)}`
    : `Puntuación ${formatScore(score)} de ${SCORE_MAX}`,
)
</script>

<template>
  <div class="relative size-28 shrink-0" role="img" :aria-label="accessibleLabel">
    <svg :viewBox="`0 0 ${RING_SIZE} ${RING_SIZE}`" class="block size-full" aria-hidden="true">
      <circle
        :cx="CENTER"
        :cy="CENTER"
        :r="RADIUS"
        fill="none"
        class="stroke-track"
        :stroke-width="STROKE_WIDTH"
      />
      <circle
        v-if="score !== null"
        :cx="CENTER"
        :cy="CENTER"
        :r="RADIUS"
        fill="none"
        class="score-ring-arc stroke-foreground"
        :stroke-width="STROKE_WIDTH"
        stroke-linecap="round"
        :stroke-dasharray="CIRCUMFERENCE"
        :stroke-dashoffset="dashOffset"
        :transform="`rotate(-90 ${CENTER} ${CENTER})`"
        :style="{ '--ring-length': `${CIRCUMFERENCE}px` }"
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
