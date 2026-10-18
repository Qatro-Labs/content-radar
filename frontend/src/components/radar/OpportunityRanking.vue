<script setup lang="ts">
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import { useAllTimelines, type QueryState } from '@/api/opportunities'
import { useRadarQuery } from '@/composables/useRadarQuery'
import InfoTip from '@/components/layout/InfoTip.vue'
import { formatUtcDay } from '@/lib/format'
import { HELP } from '@/lib/helpText'
import { rowAnchor } from '@/lib/agentTargets'
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

const COLUMNS = [
  { label: '#', name: 'el puesto', help: HELP.colRank },
  { label: 'Tema', name: 'la columna Tema', help: HELP.colTopic },
  { label: '6 días', name: 'las barras de 6 días', help: HELP.colBars },
  { label: 'Aceleración', name: 'la aceleración', help: HELP.colAcceleration },
  { label: 'Recomendación', name: 'la recomendación', help: HELP.colRecommendation },
  { label: 'Oportunidad', name: 'la oportunidad', help: HELP.colScore },
] as const
// 10 temas por página para no saturar; en escritorio las filas se desplazan dentro de la tarjeta.
const PAGE_SIZE = 10

const page = ref(0)
const pageCount = computed(() => Math.max(1, Math.ceil(rows.length / PAGE_SIZE)))
const pageRows = computed(() => rows.slice(page.value * PAGE_SIZE, (page.value + 1) * PAGE_SIZE))
const pageRange = computed(() => {
  const first = page.value * PAGE_SIZE + 1
  const last = Math.min(rows.length, first + PAGE_SIZE - 1)
  return `${first}–${last} de ${rows.length}`
})

const scroller = useTemplateRef<HTMLElement>('scroller')

function goTo(target: number) {
  page.value = Math.min(Math.max(target, 0), pageCount.value - 1)
  scroller.value?.scrollTo({ top: 0 })
}

// Vuelve a la primera página cuando cambia lo que entra en el ranking (filtros, orden), no al
// seleccionar ni al pasar por encima.
watch(
  () => rows.map((row) => row.id).join(),
  () => goTo(0),
)

// Un tema elegido en el radar, en el panel o por Rad abre su página y su fila se trae a la vista.
watch(
  () => [selectedId, rows] as const,
  async ([id]) => {
    const index = id ? rows.findIndex((row) => row.id === id) : -1
    if (index < 0) return
    page.value = Math.floor(index / PAGE_SIZE)
    await nextTick()
    const row = scroller.value?.querySelector(`[data-agent="${CSS.escape(rowAnchor(id!))}"]`)
    row?.scrollIntoView({ block: 'nearest' })
  },
  { immediate: true, flush: 'post' },
)

const PAGE_BUTTON_CLASS =
  'flex size-9 items-center justify-center rounded-[10px] text-sm font-semibold transition-colors duration-150 ease-out hover:bg-secondary disabled:pointer-events-none disabled:opacity-35'

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

// Las fechas salen del primer timeline con puntos: todos comparten ventana. Sin ninguno, sin nota.
// Qué son las barras lo explica el tooltip de la columna.
const barsNote = computed(() => {
  const points = [...(timelines.value?.values() ?? [])]
    .map((timeline) => timeline.points)
    .find((loaded) => loaded.length > 0)
  const first = points?.at(0)
  const last = points?.at(-1)
  if (!first || !last) return ''
  return `Barras de 6 días: del ${formatUtcDay(first.date)} al ${formatUtcDay(last.date)}.`
})
</script>

<template>
  <section
    data-agent="ranking"
    aria-label="Ranking"
    class="flex min-w-0 flex-col rounded-card bg-card lg:min-h-0 lg:flex-1"
  >
    <div class="flex flex-col gap-1 px-4 pt-5 pb-3 lg:min-h-0 lg:flex-1">
      <div class="flex flex-wrap items-center justify-between gap-3 pb-2">
        <slot name="title">
          <h2
            class="flex items-center gap-1.5 px-1 font-display text-[22px] font-semibold tracking-[-0.02em]"
          >
            Ranking
            <InfoTip label="el ranking" :text="HELP.ranking" />
          </h2>
        </slot>
        <p v-if="barsNote" class="px-1 text-[13px] text-muted-foreground">{{ barsNote }}</p>
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
        <div ref="scroller" class="overflow-x-auto lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
          <div class="min-w-[720px]">
            <div
              class="sticky top-0 z-[1] bg-card py-2 text-[13px] text-muted-foreground"
              :class="RANKING_GRID_CLASS"
            >
              <span v-for="column in COLUMNS" :key="column.label" class="flex items-center gap-0.5">
                {{ column.label }}
                <InfoTip :label="column.name" :text="column.help" />
              </span>
            </div>
            <RankingRow
              v-for="(row, index) in pageRows"
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
        <nav
          v-if="pageCount > 1"
          aria-label="Páginas del ranking"
          class="flex shrink-0 items-center justify-between gap-3 border-t border-table-line px-1 pt-3"
        >
          <span class="text-[13px] text-muted-foreground">Temas {{ pageRange }}</span>
          <span class="flex items-center gap-1">
            <button
              type="button"
              aria-label="Página anterior"
              :disabled="page === 0"
              :class="PAGE_BUTTON_CLASS"
              @click="goTo(page - 1)"
            >
              <ChevronLeft class="size-4" aria-hidden="true" />
            </button>
            <button
              v-for="index in pageCount"
              :key="index"
              type="button"
              :aria-label="`Página ${index}`"
              :aria-current="page === index - 1 ? 'page' : undefined"
              :class="[
                PAGE_BUTTON_CLASS,
                page === index - 1
                  ? 'bg-foreground text-primary-foreground hover:bg-foreground'
                  : '',
              ]"
              @click="goTo(index - 1)"
            >
              {{ index }}
            </button>
            <button
              type="button"
              aria-label="Página siguiente"
              :disabled="page === pageCount - 1"
              :class="PAGE_BUTTON_CLASS"
              @click="goTo(page + 1)"
            >
              <ChevronRight class="size-4" aria-hidden="true" />
            </button>
          </span>
        </nav>
      </template>
    </div>
  </section>
</template>
