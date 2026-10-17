<script setup lang="ts">
import { useElementSize, usePreferredReducedMotion } from '@vueuse/core'
import type { ECElementEvent } from 'echarts/core'
import { computed, useTemplateRef } from 'vue'

import { VChart } from '@/lib/echarts'
import { resolveLifecyclePalette } from '@/lib/lifecycle'
import { buildRadarOption, RADAR_ASPECT } from '@/lib/radarChart'
import type { RadarView } from '@/lib/radarView'

import RadarSelectionLayer from './RadarSelectionLayer.vue'
import RadarSweep from './RadarSweep.vue'

const { view, hoveredId, sweepKey } = defineProps<{
  view: RadarView
  hoveredId: string | null
  // Cambia con el periodo: remonta el gráfico y repite el barrido (DESIGN.md §7).
  sweepKey: string
}>()

const emit = defineEmits<{
  select: [id: string]
  hover: [id: string | null]
}>()

// DESIGN.md §6: en un área estrecha las etiquetas se pisan y queda la tarjeta flotante.
const LABELS_MIN_WIDTH_PX = 640
// Línea de dato (#E2E5E9, DESIGN.md §2): no tiene token en main.css.
const DATA_LINE = 'absolute bg-[#e2e5e9]'
const QUADRANT_NOTE = 'absolute z-[1] text-[13px] text-muted-foreground'
const PLOT_ASPECT = `${RADAR_ASPECT.width} / ${RADAR_ASPECT.height}`
// Capas del área: nombres de cuadrante y mira (z-1) quedan bajo las burbujas; anillos, ping y
// tarjeta flotante (z-3 y z-4, RadarSelectionLayer) van encima.
const CHART_LAYER = 'relative z-[2]'

const plot = useTemplateRef('plot')
const { width, height } = useElementSize(plot)
const plotSize = computed(() => ({ width: width.value, height: height.value }))
// El gráfico se monta con el tamaño ya medido: las entradas se programan en su primer render, y
// una actualización a mitad del barrido (las etiquetas al conocer el ancho) las adelantaría.
const isMeasured = computed(() => width.value > 0)
const showLabels = computed(() => width.value >= LABELS_MIN_WIDTH_PX)
const motionPreference = usePreferredReducedMotion()
// Los colores de etapa viven en main.css (DESIGN.md §11) y el canvas no lee `var()`: se leen una vez.
const palette = resolveLifecyclePalette(getComputedStyle(document.documentElement))

const hovered = computed(
  () => view.plotted.find((opportunity) => opportunity.id === hoveredId) ?? null,
)

const option = computed(() =>
  buildRadarOption({
    plotted: view.plotted,
    dimmedIds: view.dimmedIds,
    selectedId: view.selected?.id ?? null,
    hoveredId,
    palette,
    reducedMotion: motionPreference.value === 'reduce',
    showLabels: showLabels.value,
  }),
)

// D3 del plan fe-radar-view: sin encaje no hay burbuja, y la nota dice cuántas faltan.
const unevaluatedNote = computed(() => {
  const count = view.unevaluatedCount
  if (count === 0) return null
  if (count === 1) return '1 tema sin evaluar no aparece en el radar'
  return `${count} temas sin evaluar no aparecen en el radar`
})

// Cada burbuja lleva el id de su oportunidad como `name` (radarChart.ts).
const selectBubble = (event: ECElementEvent) => emit('select', event.name)
const hoverBubble = (event: ECElementEvent) => emit('hover', event.name)
const leaveBubble = () => emit('hover', null)
</script>

<template>
  <!-- `overflow-x-clip`: en un área estrecha la tarjeta flotante se sale del radar, y sin recorte
       la página haría scroll horizontal (DESIGN.md §6). -->
  <section
    data-agent="radar"
    aria-label="Radar de oportunidades"
    class="flex min-w-0 flex-col gap-3.5 overflow-x-clip rounded-card bg-card px-6 pt-5 pb-[22px]"
  >
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 class="font-display text-[22px] leading-tight font-semibold tracking-[-0.02em]">Radar</h2>
      <span class="text-[13.5px] text-muted-foreground">Las que laten están creciendo</span>
    </div>
    <div class="relative pt-1 pb-[30px] pl-[30px]">
      <span
        class="absolute top-1/2 left-0 -translate-y-1/2 rotate-180 text-[13px] whitespace-nowrap text-muted-foreground [writing-mode:vertical-rl]"
      >
        Momentum
      </span>
      <div
        class="absolute right-0 bottom-0 left-[30px] flex justify-between text-[13px] text-muted-foreground"
      >
        <span>0</span>
        <span>Encaje con la audiencia de 30X</span>
        <span>100</span>
      </div>
      <!-- `max-w-full`: con `aspect-ratio`, el alto mínimo ensancharía el área a 533 px; así, en
           un área estrecha el radar solo crece en alto. -->
      <div
        ref="plot"
        class="relative isolate min-h-[300px] max-w-full rounded-tile bg-plot"
        :style="{ aspectRatio: PLOT_ASPECT }"
      >
        <div
          class="absolute top-0 right-0 bottom-1/2 left-1/2 rounded-tr-tile bg-signal-wash"
          aria-hidden="true"
        />
        <div :class="[DATA_LINE, 'inset-y-0 left-1/2 w-px']" aria-hidden="true" />
        <div :class="[DATA_LINE, 'inset-x-0 top-1/2 h-px']" aria-hidden="true" />
        <span class="absolute top-3 right-4 z-[1] text-sm font-semibold">Prioridad</span>
        <span :class="[QUADRANT_NOTE, 'top-3 left-4']">Momentum sin encaje</span>
        <span :class="[QUADRANT_NOTE, 'right-4 bottom-3']">Encaje sin momentum</span>
        <span :class="[QUADRANT_NOTE, 'bottom-3 left-4']">Poca señal</span>
        <div v-if="isMeasured" :key="sweepKey" class="absolute inset-0">
          <RadarSweep />
          <VChart
            :class="CHART_LAYER"
            autoresize
            :option="option"
            @click="selectBubble"
            @mouseover="hoverBubble"
            @mouseout="leaveBubble"
          />
          <RadarSelectionLayer :selected="view.selected" :hovered="hovered" :size="plotSize" />
        </div>
      </div>
    </div>
    <p v-if="unevaluatedNote" class="text-[13.5px] text-muted-foreground">{{ unevaluatedNote }}</p>
  </section>
</template>
