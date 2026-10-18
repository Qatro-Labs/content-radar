<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useAllTimelines, type QueryState } from '@/api/opportunities'
import { useRadarQuery } from '@/composables/useRadarQuery'
import { formatUtcDay } from '@/lib/format'
import { resetViewPatch } from '@/lib/radarQuery'
import type { RankedOpportunity } from '@/lib/radarView'
import type { components } from '@/types/api'

import RankingRow, { RANKING_GRID_CLASS } from './RankingRow.vue'

type OpportunityTimeline = components['schemas']['OpportunityTimeline']

const { rows, isFiltered, selectedId, hoveredId } = defineProps<{
  rows: RankedOpportunity[]
  isFiltered: boolean
  selectedId: string | null
  hoveredId: string | null
}>()

const emit = defineEmits<{
  select: [id: string]
  hover: [id: string | null]
}>()

const { update } = useRadarQuery()

const COLUMNS = ['Puesto', 'Tema', 'Últimos 6 días', 'Piezas nuevas', 'Oportunidad'] as const
// DESIGN.md §4: el ranking enseña 10 filas y el resto se despliega.
const COLLAPSED_ROWS = 10

const isExpanded = ref(false)
// Vuelve a 10 filas cuando cambia lo que entra en el ranking, no al seleccionar ni al pasar por
// encima (cambian la URL o el estado, pero no las filas).
watch(
  () => rows.map((row) => row.id).join(),
  () => {
    isExpanded.value = false
  },
)

const isCollapsible = computed(() => rows.length > COLLAPSED_ROWS)
const shownRows = computed(() => (isExpanded.value ? rows : rows.slice(0, COLLAPSED_ROWS)))
const isEmptyAfterFilter = computed(() => isFiltered && rows.length === 0)

const {
  data: timelines,
  isPending: isTimelinesPending,
  isError: isTimelinesError,
} = useAllTimelines()

// Un tema que no está en la respuesta, o una respuesta fallida, queda en `null`: «no disponible».
function timelineOf(id: string): QueryState<OpportunityTimeline | null> {
  return {
    data: timelines.value?.get(id) ?? null,
    isPending: isTimelinesPending.value,
    isError: isTimelinesError.value,
  }
}

const WINDOWS_NOTE =
  'en gris los 3 días anteriores y en negro los últimos 3, que son las piezas nuevas'

// Las fechas salen del primer timeline con puntos: todos comparten ventana. Sin ninguno, sin fechas.
const barsNote = computed(() => {
  const points = [...(timelines.value?.values() ?? [])]
    .map((timeline) => timeline.points)
    .find((loaded) => loaded.length > 0)
  const first = points?.at(0)
  const last = points?.at(-1)
  const span = first && last ? ` del ${formatUtcDay(first.date)} al ${formatUtcDay(last.date)}` : ''
  return `Barras: piezas nuevas cada 24 h${span}; ${WINDOWS_NOTE}.`
})
</script>

<template>
  <section
    data-agent="ranking"
    aria-label="Ranking"
    class="flex min-w-0 flex-col gap-1 rounded-card bg-card px-5 pt-5 pb-3"
  >
    <h2 class="px-1 pb-2 font-display text-[22px] font-semibold tracking-[-0.02em]">Ranking</h2>

    <div v-if="isEmptyAfterFilter" class="flex flex-wrap items-center gap-x-4 gap-y-3 px-1 py-6">
      <p class="text-[15px] text-ink-soft">Ningún tema cumple estos filtros.</p>
      <button
        type="button"
        class="min-h-11 rounded-xl bg-secondary px-4 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]"
        @click="update(resetViewPatch())"
      >
        Restablecer vista
      </button>
    </div>

    <template v-else>
      <div class="overflow-x-auto">
        <div class="min-w-[660px]">
          <div class="py-2 text-[13px] text-muted-foreground" :class="RANKING_GRID_CLASS">
            <span v-for="column in COLUMNS" :key="column">{{ column }}</span>
          </div>
          <RankingRow
            v-for="(row, index) in shownRows"
            :key="row.id"
            :row
            :index
            :selected="row.id === selectedId"
            :hovered="row.id === hoveredId"
            :timeline="timelineOf(row.id)"
            @select="(id) => emit('select', id)"
            @hover="(id) => emit('hover', id)"
          />
        </div>
      </div>
      <button
        v-if="isCollapsible"
        type="button"
        :aria-expanded="isExpanded"
        class="mt-2 min-h-10 self-center rounded-[10px] bg-secondary px-4 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]"
        @click="isExpanded = !isExpanded"
      >
        {{ isExpanded ? 'Ver menos' : `Ver los ${rows.length} temas` }}
      </button>
      <p class="px-1 pt-2 text-[13px] text-muted-foreground">{{ barsNote }}</p>
    </template>
  </section>
</template>
