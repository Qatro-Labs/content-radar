<script lang="ts">
import type { Lifecycle } from '@/lib/radarQuery'

// La muestra de «Publicar ya» es la Lima señal; la de cada etapa, su relleno; la de «Todos», un
// círculo hueco (DESIGN.md §4).
export type CounterSwatch = 'all' | 'signal' | Lifecycle
</script>

<script setup lang="ts">
import { computed } from 'vue'

import { formatCount } from '@/lib/evidenceFormat'
import { LIFECYCLE_STYLE } from '@/lib/lifecycle'

const { count, label, swatch, checked } = defineProps<{
  count: number
  label: string
  swatch: CounterSwatch
  checked: boolean
}>()

// La Lima sobre blanco no tiene contraste: lleva un anillo interior de Tinta al 15 %.
const SIGNAL_SWATCH_CLASS = 'rounded-[3px] bg-signal ring-1 ring-foreground/15 ring-inset'
// Sobre la Tinta del activo, el anillo Apagado no se vería: pasa al gris claro de la etiqueta.
const ALL_SWATCH_CLASS =
  'rounded-full shadow-[inset_0_0_0_1.5px_var(--muted-foreground)] group-aria-checked:shadow-[inset_0_0_0_1.5px_var(--on-ink-muted)]'

const swatchClass = computed(() => {
  if (swatch === 'all') return ALL_SWATCH_CLASS
  if (swatch === 'signal') return SIGNAL_SWATCH_CLASS
  return 'rounded-[3px]'
})

// «Sin etapa» se dibuja hueca, con trazo discontinuo, como su burbuja (DESIGN.md §2).
const swatchStyle = computed(() => {
  if (swatch === 'signal' || swatch === 'all') return undefined
  const { cssVar, dashed } = LIFECYCLE_STYLE[swatch]
  if (dashed) return { border: `1.5px dashed var(${cssVar.stroke})` }
  return { backgroundColor: `var(${cssVar.fill})` }
})
</script>

<template>
  <!-- DESIGN.md §4: contador-filtro, una opción de un grupo de selección única. Activo, relleno
       de Tinta: un anillo se confundía con el foco del teclado. -->
  <button
    type="button"
    role="radio"
    :aria-checked="checked"
    class="group flex min-w-32 cursor-pointer flex-col items-start gap-0.5 rounded-2xl bg-card px-4 py-3 text-left transition-[background-color,color,scale] duration-150 ease-out not-aria-checked:hover:bg-secondary-hover active:scale-[0.98] aria-checked:bg-foreground aria-checked:text-primary-foreground"
  >
    <span class="font-display text-[32px] leading-[1.05] font-semibold tracking-[-0.03em]">
      {{ formatCount(count) }}
    </span>
    <span
      class="flex items-center gap-[7px] text-sm text-label group-aria-checked:text-on-ink-muted"
    >
      <span
        aria-hidden="true"
        class="size-2.5 shrink-0"
        :class="swatchClass"
        :style="swatchStyle"
      />
      {{ label }}
    </span>
  </button>
</template>
