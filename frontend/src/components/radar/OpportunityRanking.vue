<script setup lang="ts">
import { computed } from 'vue'

import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import { useRadarQuery } from '@/composables/useRadarQuery'
import { formatAcceleration, formatOutliers, formatScore, SCORE_MAX } from '@/lib/opportunityFormat'
import { RANKING_SORTS, type RankingSort } from '@/lib/radarQuery'
import type { RankedOpportunity } from '@/lib/radarView'

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

// DESIGN.md §6: por debajo de 1000 px la tabla hace scroll dentro de su tarjeta. Las columnas en
// px del artboard E suman unos 1300 px; estos mínimos suman 1000 con los huecos y el padding.
// Etiqueta (#4A505A), Línea de tabla (#EEF0F2) y el hover del secundario (#E8EAED) no tienen
// token en main.css (DESIGN.md §2 y §4).
const ROW_GRID_CLASS =
  'grid grid-cols-[56px_minmax(152px,2.4fr)_minmax(120px,1fr)_minmax(92px,0.8fr)_minmax(112px,1fr)_minmax(60px,0.5fr)_minmax(140px,1.3fr)_minmax(124px,1fr)] items-center gap-x-4 px-4'

// DESIGN.md §7: las filas entran escalonadas, 40 ms cada una.
const ROW_STAGGER_MS = 40
const ROW_ENTER_CLASS =
  'animate-in fade-in slide-in-from-bottom-[6px] animation-duration-[420ms] ease-out fill-mode-backwards motion-reduce:animate-none'

const title = computed(() => (isFiltered ? `Ranking · ${rows.length} de ${total}` : 'Ranking'))
const isEmptyAfterFilter = computed(() => isFiltered && rows.length === 0)

function staggerDelay(index: number): string {
  return `${index * ROW_STAGGER_MS}ms`
}

// DESIGN.md §2 y §4: la seleccionada en lavado de señal (0.18) y el hover en Superficie hundida,
// también cuando llega desde el radar.
function rowToneClass(id: string): string {
  if (id === selectedId) return 'bg-signal/18'
  if (id === hoveredId) return 'bg-sunken'
  return 'bg-card hover:bg-sunken'
}

function resetView() {
  update({ lifecycle: [], gap: false, highlight: [] })
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
          class="min-h-9 rounded-[9px] px-3.5 text-sm font-medium text-[#4a505a] transition-colors duration-150 ease-out aria-pressed:bg-card aria-pressed:font-semibold aria-pressed:text-foreground"
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
        class="min-h-11 rounded-xl bg-secondary px-4 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-[#e8eaed] active:scale-[0.98]"
        @click="resetView"
      >
        Restablecer vista
      </button>
    </div>

    <div v-else class="overflow-x-auto">
      <div class="min-w-[1000px]">
        <div class="py-2 text-[13px] text-muted-foreground" :class="ROW_GRID_CLASS">
          <span v-for="column in COLUMNS" :key="column">{{ column }}</span>
        </div>
        <button
          v-for="(row, index) in rows"
          :key="row.id"
          type="button"
          :aria-pressed="row.id === selectedId"
          class="min-h-14 w-full border-t border-[#eef0f2] text-left text-[15px] transition-colors duration-150 ease-out"
          :class="[ROW_GRID_CLASS, ROW_ENTER_CLASS, rowToneClass(row.id)]"
          :style="{ animationDelay: staggerDelay(index) }"
          @click="emit('select', row.id)"
          @mouseenter="emit('hover', row.id)"
          @mouseleave="emit('hover', null)"
        >
          <span
            :class="
              row.id === selectedId
                ? 'font-bold text-foreground'
                : 'font-medium text-muted-foreground'
            "
          >
            {{ row.rank }}
          </span>
          <span class="flex min-w-0 flex-col py-2">
            <span class="font-medium">{{ row.topic }}</span>
            <span v-if="row.audience_fit_score == null" class="text-[13px] text-muted-foreground">
              Encaje no disponible
            </span>
          </span>
          <LifecycleChip
            :lifecycle="row.lifecycle"
            :title="row.lifecycle_reason"
            class="justify-self-start"
          />
          <span
            class="font-medium whitespace-nowrap"
            :class="{ 'text-destructive': row.acceleration < 0 }"
          >
            {{ formatAcceleration(row.acceleration) }}
          </span>
          <span class="text-ink-soft">
            {{ formatOutliers(row.outlier_count, row.top_outlier_ratio) }}
          </span>
          <span class="text-ink-soft">{{ row.source_count }}</span>
          <span class="flex items-center gap-2.5">
            <span class="h-1.5 grow overflow-hidden rounded-full bg-track" aria-hidden="true">
              <span
                v-if="row.opportunity_score != null"
                class="ranking-bar block h-full origin-left rounded-full bg-foreground"
                :style="{
                  transform: `scaleX(${row.opportunity_score / SCORE_MAX})`,
                  animationDelay: staggerDelay(index),
                }"
              />
            </span>
            <span
              class="min-w-[26px] text-right"
              :class="row.opportunity_score == null ? 'text-muted-foreground' : 'font-semibold'"
            >
              {{ formatScore(row.opportunity_score) }}
            </span>
          </span>
          <RecommendationChip
            :recommendation="row.recommendation"
            size="sm"
            class="justify-self-start"
          />
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* DESIGN.md §7: las barras de score del ranking crecen hasta su valor (420 ms) al entrar. */
.ranking-bar {
  animation: ranking-bar-grow 420ms var(--ease-out) backwards;
}

@media (prefers-reduced-motion: reduce) {
  .ranking-bar {
    animation: none;
  }
}

@keyframes ranking-bar-grow {
  from {
    transform: scaleX(0);
  }
}
</style>
