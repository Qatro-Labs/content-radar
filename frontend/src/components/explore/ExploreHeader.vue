<script setup lang="ts">
import { computed } from 'vue'

import ViewHeader from '@/components/layout/ViewHeader.vue'
import { formatCount, PLATFORM_LABEL } from '@/lib/evidenceFormat'
import { exploreSummary, type ExploreFilter, type ExploreViewModel } from '@/lib/exploreView'

const { view, filter } = defineProps<{ view: ExploreViewModel; filter: ExploreFilter | null }>()

const emit = defineEmits<{ toggle: [filter: ExploreFilter] }>()

interface Counter {
  filter: ExploreFilter
  label: string
  value: number
}

// Totales fijos y selección única, como los contadores-filtro del Radar (D2 del plan
// fe-dashboard-v2): cuentan todas las piezas, no lo filtrado.
const counters = computed<Counter[]>(() => [
  { filter: 'outliers', label: 'Outliers', value: view.counts.outliers },
  ...view.counts.platforms.map(({ platform, count }) => ({
    filter: platform,
    label: PLATFORM_LABEL[platform],
    value: count,
  })),
])

// Un segmented control en una fila (como el periodo): siete baldosas grandes empujaban la tabla
// fuera de la primera pantalla. «Todas» quita el filtro.
const SEGMENT_CLASS =
  'flex min-h-9 items-center gap-1.5 rounded-[9px] px-3.5 text-sm font-medium whitespace-nowrap text-ink-soft transition duration-150 ease-out hover:text-foreground active:scale-[0.98] aria-pressed:bg-card aria-pressed:font-semibold aria-pressed:text-foreground'

function clearFilter() {
  if (filter !== null) emit('toggle', filter)
}
</script>

<template>
  <section class="flex flex-col gap-5">
    <ViewHeader title="Lo que está funcionando">{{ exploreSummary(view) }}</ViewHeader>

    <div
      role="group"
      aria-label="Filtrar piezas"
      class="flex flex-wrap gap-0.5 self-start rounded-xl bg-input p-1"
    >
      <button
        type="button"
        :aria-pressed="filter === null"
        :class="SEGMENT_CLASS"
        @click="clearFilter"
      >
        Todas
        <span class="text-muted-foreground">{{ formatCount(view.counts.total) }}</span>
      </button>
      <button
        v-for="counter in counters"
        :key="counter.filter"
        type="button"
        :aria-pressed="filter === counter.filter"
        :class="SEGMENT_CLASS"
        @click="emit('toggle', counter.filter)"
      >
        {{ counter.label }}
        <span class="text-muted-foreground">{{ formatCount(counter.value) }}</span>
      </button>
    </div>
  </section>
</template>
