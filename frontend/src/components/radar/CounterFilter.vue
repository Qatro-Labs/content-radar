<script lang="ts">
import type { Lifecycle } from '@/lib/radarQuery'

// La muestra de «Publicar ya» es la Lima señal; la de cada etapa, su relleno (DESIGN.md §4).
export type CounterSwatch = 'signal' | Lifecycle
</script>

<script setup lang="ts">
import { computed } from 'vue'

import { formatCount } from '@/lib/evidenceFormat'
import { LIFECYCLE_STYLE } from '@/lib/lifecycle'

const { count, label, swatch, pressed } = defineProps<{
  count: number
  label: string
  swatch: CounterSwatch
  pressed: boolean
}>()

// La Lima sobre blanco no tiene contraste: lleva un anillo interior de Tinta al 15 %.
const SIGNAL_SWATCH_CLASS = 'bg-signal ring-1 ring-foreground/15 ring-inset'

// «Sin etapa» se dibuja hueca, con trazo discontinuo, como su burbuja (DESIGN.md §2).
const swatchStyle = computed(() => {
  if (swatch === 'signal') return undefined
  const { cssVar, dashed } = LIFECYCLE_STYLE[swatch]
  if (dashed) return { border: `1.5px dashed var(${cssVar.stroke})` }
  return { backgroundColor: `var(${cssVar.fill})` }
})
</script>

<template>
  <!-- DESIGN.md §4: contador-filtro. Activo, anillo de Tinta de 2 px. -->
  <button
    type="button"
    :aria-pressed="pressed"
    class="flex min-w-32 flex-col items-start gap-0.5 rounded-2xl bg-card px-4 py-3 text-left transition-[background-color,box-shadow,scale] duration-150 ease-out hover:bg-sunken active:scale-[0.98] aria-pressed:ring-2 aria-pressed:ring-foreground"
  >
    <span class="font-display text-[32px] leading-[1.05] font-semibold tracking-[-0.03em]">
      {{ formatCount(count) }}
    </span>
    <span class="flex items-center gap-[7px] text-sm text-label">
      <span
        aria-hidden="true"
        class="size-2.5 shrink-0 rounded-[3px]"
        :class="{ [SIGNAL_SWATCH_CLASS]: swatch === 'signal' }"
        :style="swatchStyle"
      />
      {{ label }}
    </span>
  </button>
</template>
