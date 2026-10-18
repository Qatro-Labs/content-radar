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

// DESIGN.md §4, contador-filtro: baldosa blanca de radio 16px y cifra Bricolage de 32px.
const TILE_CLASS = 'flex min-w-[128px] flex-col items-start gap-0.5 rounded-2xl bg-card px-5 py-4'
const VALUE_CLASS = 'font-display text-[32px] leading-[1.05] font-semibold tracking-[-0.03em]'
</script>

<template>
  <section class="flex flex-wrap items-end justify-between gap-x-10 gap-y-5">
    <ViewHeader title="Lo que está funcionando">{{ exploreSummary(view) }}</ViewHeader>

    <ul class="flex flex-wrap gap-2" aria-label="Filtrar piezas">
      <li v-for="counter in counters" :key="counter.filter" class="flex">
        <button
          type="button"
          :aria-pressed="filter === counter.filter"
          class="text-left transition-[background-color,box-shadow,scale] duration-150 ease-out hover:bg-sunken active:scale-[0.98] aria-pressed:ring-2 aria-pressed:ring-foreground"
          :class="TILE_CLASS"
          @click="emit('toggle', counter.filter)"
        >
          <span :class="VALUE_CLASS">{{ formatCount(counter.value) }}</span>
          <span class="text-sm text-ink-soft">{{ counter.label }}</span>
        </button>
      </li>
      <!-- RSS no publica métricas: no hay rendimiento que filtrar, solo se cuenta. -->
      <li :class="TILE_CLASS">
        <span :class="VALUE_CLASS">{{ formatCount(view.counts.rss) }}</span>
        <span class="text-sm text-ink-soft">{{ PLATFORM_LABEL.rss }}</span>
        <span class="text-[13px] text-muted-foreground">sin métricas públicas</span>
      </li>
    </ul>
  </section>
</template>
