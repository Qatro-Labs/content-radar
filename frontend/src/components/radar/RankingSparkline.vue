<script setup lang="ts">
import { computed } from 'vue'

import type { QueryState } from '@/api/opportunities'
import { NOT_AVAILABLE } from '@/lib/opportunityFormat'
import type { components } from '@/types/api'

type Schemas = components['schemas']
type OpportunityTimeline = Schemas['OpportunityTimeline']
type TimelineWindow = Schemas['TimelineWindow']

const { timeline } = defineProps<{ timeline: QueryState<OpportunityTimeline | null> }>()

// DESIGN.md §4: escala común a todas las filas para poder compararlas; 5 piezas en un periodo
// llenan la barra y lo que pasa se recorta.
const SPARK_SCALE_MAX = 5
const SPARK_HEIGHT_PX = 24
// Un periodo sin piezas es un trazo, no una barra vacía que se confunda con "sin dato".
const EMPTY_PERIOD_PX = 2
const WINDOW_CLASS: Record<TimelineWindow, string> = {
  previous: 'bg-window-previous',
  current: 'bg-foreground',
}

const points = computed(() => timeline.data?.points ?? [])

const bars = computed(() =>
  points.value.map((point) => ({
    date: point.date,
    heightPx:
      point.count === 0
        ? EMPTY_PERIOD_PX
        : (Math.min(point.count, SPARK_SCALE_MAX) / SPARK_SCALE_MAX) * SPARK_HEIGHT_PX,
    colorClass: point.count === 0 ? 'bg-window-empty' : WINDOW_CLASS[point.window],
  })),
)

const accessibleLabel = computed(
  () => `Piezas nuevas por periodo de 24 h: ${points.value.map((point) => point.count).join(', ')}`,
)
</script>

<template>
  <span
    v-if="timeline.isPending"
    class="block h-6 w-[66px] animate-pulse rounded-md bg-track motion-reduce:animate-none"
    aria-label="Cargando piezas nuevas por periodo"
  />
  <!-- CLAUDE.md §2.3: sin timeline no se dibujan barras a 0. -->
  <span v-else-if="points.length === 0" class="text-xs text-muted-foreground">
    {{ NOT_AVAILABLE }}
  </span>
  <span v-else role="img" :aria-label="accessibleLabel" class="flex h-6 items-end gap-[3px]">
    <span
      v-for="bar in bars"
      :key="bar.date"
      class="w-2 shrink-0 rounded-[2px]"
      :class="bar.colorClass"
      :style="{ height: `${bar.heightPx}px` }"
    />
  </span>
</template>
