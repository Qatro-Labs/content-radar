<script setup lang="ts">
import { useElementSize, usePreferredReducedMotion, useTimeoutFn } from '@vueuse/core'
import type { ECElementEvent } from 'echarts/core'
import { computed, ref, useTemplateRef, watch } from 'vue'

import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import { bubbleAnchor } from '@/lib/agentTargets'
import { VChart } from '@/lib/echarts'
import {
  bubblePosition,
  buildRadarOption,
  PLOT_ASPECT,
  resolveRadarPalette,
  SWEEP,
  translateTo,
} from '@/lib/radarChart'
import { LIFECYCLES } from '@/lib/radarQuery'
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
const DATA_LINE = 'absolute bg-data-line'
const QUADRANT_NOTE = 'absolute z-[1] text-[13px] text-muted-foreground'
// Capas del área: nombres de cuadrante y mira (z-1) quedan bajo las burbujas; anillos, ping y
// tarjeta flotante (z-3 y z-4, RadarSelectionLayer) van encima.
const CHART_LAYER = 'relative z-[2]'
// D13: anillos y etiquetas esperan a que el haz termine de pasar.
const SWEEP_END_MS = SWEEP.delayMs + SWEEP.durationMs

const plot = useTemplateRef('plot')
const { width, height } = useElementSize(plot)
const plotSize = computed(() => ({ width: width.value, height: height.value }))
// El gráfico se monta con el tamaño ya medido: las entradas se programan en su primer render, y
// una actualización a mitad del barrido (las etiquetas al conocer el ancho) las adelantaría.
const isMeasured = computed(() => width.value > 0)
const showLabels = computed(() => width.value >= LABELS_MIN_WIDTH_PX)
const motionPreference = usePreferredReducedMotion()
const reducedMotion = computed(() => motionPreference.value === 'reduce')
// Los colores viven en main.css (DESIGN.md §11) y el canvas no lee `var()`: se leen una vez.
const palette = resolveRadarPalette(getComputedStyle(document.documentElement))

const hovered = computed(
  () => view.plotted.find((opportunity) => opportunity.id === hoveredId) ?? null,
)

// El gráfico se remonta al medir el área y con cada `sweepKey`, y cada montaje repite el barrido.
const isSweeping = ref(false)
const { start: startSweepTimer } = useTimeoutFn(() => (isSweeping.value = false), SWEEP_END_MS, {
  immediate: false,
})
watch([isMeasured, () => sweepKey], ([measured]) => {
  if (!measured) return
  isSweeping.value = true
  startSweepTimer()
})

const option = computed(() =>
  buildRadarOption({
    plotted: view.plotted,
    dimmedIds: view.dimmedIds,
    selectedId: view.selected?.id ?? null,
    hoveredId,
    palette,
    reducedMotion: reducedMotion.value,
    showLabels: showLabels.value,
    entering: isSweeping.value && !reducedMotion.value,
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
      <!-- La leyenda es HTML para que sea accesible (DESIGN.md §8); no filtra. -->
      <ul aria-label="Etapas" class="flex flex-wrap gap-1.5">
        <li v-for="lifecycle in LIFECYCLES" :key="lifecycle">
          <LifecycleChip :lifecycle size="sm" />
        </li>
      </ul>
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
          <RadarSelectionLayer
            :selected="view.selected"
            :hovered="hovered"
            :size="plotSize"
            :sweeping="isSweeping"
          />
          <!-- Las burbujas son canvas: la presencia de Rad apunta a estas anclas invisibles, una
               en el centro de cada burbuja (plan fe-radar-agent, D8). -->
          <span
            v-for="opportunity in view.plotted"
            :key="opportunity.id"
            :data-agent="bubbleAnchor(opportunity.id)"
            class="pointer-events-none absolute top-0 left-0 size-0"
            :style="{ transform: translateTo(bubblePosition(opportunity, plotSize)) }"
            aria-hidden="true"
          />
        </div>
      </div>
    </div>
    <!-- DESIGN.md §7: el latido codifica la aceleración, y la nota lo dice. -->
    <p class="text-[13.5px] text-muted-foreground">
      Las burbujas que laten están creciendo: cuanto más rápido laten, más aceleran. El tamaño es la
      fuerza de la evidencia.
    </p>
    <p v-if="unevaluatedNote" class="text-[13.5px] text-muted-foreground">{{ unevaluatedNote }}</p>
  </section>
</template>
