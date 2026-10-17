<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useOpportunityTimelines, type QueryState } from '@/api/opportunities'
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

const COLUMNS = ['Puesto', 'Tema', 'Etapa', '6 días', 'Aceleración', 'Oportunidad'] as const
// DESIGN.md §4: el ranking enseña 10 filas y el resto se despliega.
const COLLAPSED_ROWS = 10
const PENDING_TIMELINE: QueryState<OpportunityTimeline | null> = {
  data: undefined,
  isPending: true,
  isError: false,
}

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

// D5 del plan fe-dashboard-v2: no hay endpoint de conteos, así que se pide `/timeline` solo para
// las filas a la vista.
const timelines = useOpportunityTimelines(() => shownRows.value.map((row) => row.id))

const BARS_NOTE = 'Barras: piezas nuevas por periodo de 24 h'

// Las fechas salen del primer timeline cargado: todos comparten ventana. Sin ninguno, sin fechas.
const barsNote = computed(() => {
  const points = [...timelines.value.values()]
    .map((state) => state.data?.points ?? [])
    .find((loaded) => loaded.length > 0)
  const first = points?.at(0)
  const last = points?.at(-1)
  if (!first || !last) return BARS_NOTE
  return `${BARS_NOTE}, del ${formatUtcDay(first.date)} al ${formatUtcDay(last.date)}`
})
</script>

<template>
  <section
    data-agent="ranking"
    aria-label="Ranking"
    class="flex min-w-0 flex-col gap-1 rounded-card bg-card px-5 pt-5 pb-3"
  >
    <div class="flex flex-wrap items-center justify-between gap-3 px-1 pb-2">
      <h2 class="font-display text-[22px] font-semibold tracking-[-0.02em]">Ranking</h2>
      <span class="text-[13.5px] text-muted-foreground">{{ barsNote }}</span>
    </div>

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
        <div class="min-w-[780px]">
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
            :timeline="timelines.get(row.id) ?? PENDING_TIMELINE"
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
    </template>
  </section>
</template>
