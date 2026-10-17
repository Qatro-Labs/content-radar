<script setup lang="ts">
import { computed } from 'vue'

import { SCORE_MAX } from '@/lib/opportunityFormat'

type BarTone = 'ink' | 'saturation'

const {
  label,
  value,
  display,
  tone = 'ink',
} = defineProps<{
  label: string
  value: number | null
  display: string
  tone?: BarTone
}>()

// DESIGN.md §2: la saturación va en naranja porque es una alerta suave, no un logro.
const TONE_CLASS: Record<BarTone, string> = {
  ink: 'bg-foreground',
  saturation: 'bg-saturation',
}

// Sin valor la pista queda vacía; la cifra la escribe quien llama ("no disponible").
const fill = computed(() => (value === null ? 0 : value / SCORE_MAX))
</script>

<template>
  <div class="flex items-center gap-3">
    <span class="w-[120px] shrink-0 text-sm text-label">{{ label }}</span>
    <span class="h-1.5 grow overflow-hidden rounded-full bg-track" aria-hidden="true">
      <span
        class="block h-full origin-left rounded-full transition-transform duration-[420ms] ease-out motion-reduce:transition-none"
        :class="TONE_CLASS[tone]"
        :style="{ transform: `scaleX(${fill})` }"
      />
    </span>
    <span class="min-w-[72px] shrink-0 whitespace-nowrap text-right text-sm font-medium">{{
      display
    }}</span>
  </div>
</template>
