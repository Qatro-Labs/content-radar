<script setup lang="ts">
import { computed } from 'vue'

import { useRadarQuery } from '@/composables/useRadarQuery'
import { RANKING_SORTS, resetViewPatch, type RankingSort } from '@/lib/radarQuery'
import type { RankedOpportunity } from '@/lib/radarView'

import RankingRow, { RANKING_GRID_CLASS } from './RankingRow.vue'

const { rows, total, isFiltered, selectedId, hoveredId } = defineProps<{
  rows: RankedOpportunity[]
  total: number
  isFiltered: boolean
  selectedId: string | null
  hoveredId: string | null
}>()

const emit = defineEmits<{
  select: [id: string]
  hover: [id: string | null]
}>()

const { query, update } = useRadarQuery()

const SORT_LABEL: Record<RankingSort, string> = {
  opportunity: 'Oportunidad',
  acceleration: 'Aceleración',
}

const COLUMNS = [
  'Puesto',
  'Tema',
  'Etapa',
  'Aceleración',
  'Outliers',
  'Fuentes',
  'Oportunidad',
  'Acción',
] as const

const title = computed(() => (isFiltered ? `Ranking · ${rows.length} de ${total}` : 'Ranking'))
const isEmptyAfterFilter = computed(() => isFiltered && rows.length === 0)

function resetView() {
  update(resetViewPatch())
}
</script>

<template>
  <section
    data-agent="ranking"
    aria-label="Ranking"
    class="flex min-w-0 flex-col gap-1.5 rounded-card bg-card px-5 pt-5 pb-3"
  >
    <div class="flex flex-wrap items-center justify-between gap-3 px-1 pb-2">
      <h2 class="font-display text-[22px] font-semibold tracking-[-0.02em]">{{ title }}</h2>
      <div role="group" aria-label="Ordenar por" class="flex gap-0.5 rounded-xl bg-secondary p-1">
        <button
          v-for="sort in RANKING_SORTS"
          :key="sort"
          type="button"
          :aria-pressed="query.sort === sort"
          class="min-h-9 rounded-[9px] px-3.5 text-sm font-medium text-label transition-colors duration-150 ease-out aria-pressed:bg-card aria-pressed:font-semibold aria-pressed:text-foreground"
          @click="update({ sort })"
        >
          {{ SORT_LABEL[sort] }}
        </button>
      </div>
    </div>

    <div v-if="isEmptyAfterFilter" class="flex flex-wrap items-center gap-x-4 gap-y-3 px-1 py-6">
      <p class="text-[15px] text-ink-soft">Ningún tema cumple estos filtros.</p>
      <button
        type="button"
        class="min-h-11 rounded-xl bg-secondary px-4 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]"
        @click="resetView"
      >
        Restablecer vista
      </button>
    </div>

    <div v-else class="overflow-x-auto">
      <div class="min-w-[1000px]">
        <div class="py-2 text-[13px] text-muted-foreground" :class="RANKING_GRID_CLASS">
          <span v-for="column in COLUMNS" :key="column">{{ column }}</span>
        </div>
        <RankingRow
          v-for="(row, index) in rows"
          :key="row.id"
          :row
          :index
          :selected="row.id === selectedId"
          :hovered="row.id === hoveredId"
          @select="(id) => emit('select', id)"
          @hover="(id) => emit('hover', id)"
        />
      </div>
    </div>
  </section>
</template>
