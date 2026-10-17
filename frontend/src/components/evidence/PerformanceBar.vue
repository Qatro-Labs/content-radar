<script setup lang="ts">
import { computed } from 'vue'

import {
  formatRatio,
  missingRatioLabel,
  PERFORMANCE_MARKS,
  PERFORMANCE_SCALE_MAX,
  performanceFraction,
} from '@/lib/evidenceFormat'
import { formatDecimal } from '@/lib/opportunityFormat'
import type { components } from '@/types/api'

const { evidence } = defineProps<{ evidence: components['schemas']['Evidence'] }>()

const ratio = computed(() => evidence.outlier_ratio ?? null)
const isOutlier = computed(() => evidence.is_outlier === true)
const marks = PERFORMANCE_MARKS.map((mark) => ({
  mark,
  left: `${(mark / PERFORMANCE_SCALE_MAX) * 100}%`,
}))
</script>

<template>
  <!-- DESIGN.md §4: barra "Rendimiento frente a su canal" con marcas en 1× y 3×, hasta 6×. El
       título lo pone quien la usa. Sin ratio no hay barra: una barra vacía se leería como 0. -->
  <p v-if="ratio === null" class="text-[13px] text-muted-foreground">
    {{ missingRatioLabel(evidence) }}
  </p>
  <div
    v-else
    class="flex items-center gap-3"
    role="img"
    :aria-label="`${formatDecimal(ratio)} veces su referencia`"
  >
    <span class="relative h-1.5 grow rounded-full bg-track" aria-hidden="true">
      <span
        class="absolute inset-y-0 left-0 w-full origin-left rounded-full transition-transform duration-[420ms] ease-out motion-reduce:transition-none"
        :class="isOutlier ? 'bg-foreground' : 'bg-reference-mark'"
        :style="{ transform: `scaleX(${performanceFraction(ratio)})` }"
      />
      <span
        v-for="{ mark, left } in marks"
        :key="mark"
        class="absolute -top-1 h-3.5 w-0.5 -translate-x-1/2 rounded-full"
        :class="mark === 1 ? 'bg-reference-mark' : 'bg-foreground'"
        :style="{ left }"
      />
    </span>
    <span
      class="shrink-0 rounded-lg px-2 py-0.5 text-[13px] font-semibold"
      :class="isOutlier ? 'bg-signal text-signal-foreground' : 'bg-neutral-action text-ink-read'"
    >
      {{ formatRatio(ratio) }}
    </span>
  </div>
</template>
