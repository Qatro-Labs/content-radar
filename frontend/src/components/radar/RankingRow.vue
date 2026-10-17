<script lang="ts">
// DESIGN.md §6: por debajo de 1000 px la tabla hace scroll dentro de su tarjeta. Las columnas en
// px del artboard E suman unos 1300 px; estos mínimos suman 1000 con los huecos y el padding.
// La cabecera de OpportunityRanking comparte la rejilla.
export const RANKING_GRID_CLASS =
  'grid grid-cols-[56px_minmax(152px,2.4fr)_minmax(120px,1fr)_minmax(92px,0.8fr)_minmax(112px,1fr)_minmax(60px,0.5fr)_minmax(140px,1.3fr)_minmax(124px,1fr)] items-center gap-x-4 px-4'
</script>

<script setup lang="ts">
import { computed } from 'vue'

import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import {
  formatAcceleration,
  formatOutliers,
  formatScore,
  GROWTH_LABEL,
  isDeclining,
  SCORE_MAX,
} from '@/lib/opportunityFormat'
import type { RankedOpportunity } from '@/lib/radarView'

const { row, index, selected, hovered } = defineProps<{
  row: RankedOpportunity
  // Posición en la tabla: escalona la entrada.
  index: number
  selected: boolean
  hovered: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  hover: [id: string | null]
}>()

// DESIGN.md §7: las filas entran escalonadas, 40 ms cada una.
const ROW_STAGGER_MS = 40
const ROW_ENTER_CLASS =
  'animate-in fade-in slide-in-from-bottom-[6px] animation-duration-[420ms] ease-out fill-mode-backwards motion-reduce:animate-none'

const enterDelay = computed(() => `${index * ROW_STAGGER_MS}ms`)

// DESIGN.md §2 y §4: la seleccionada en lavado de señal (0.18) y el hover en Superficie hundida,
// también cuando llega desde el radar.
const toneClass = computed(() => {
  if (selected) return 'bg-signal/18'
  if (hovered) return 'bg-sunken'
  return 'bg-card hover:bg-sunken'
})
</script>

<template>
  <button
    type="button"
    :aria-pressed="selected"
    class="min-h-14 w-full border-t border-table-line text-left text-[15px] transition-colors duration-150 ease-out"
    :class="[RANKING_GRID_CLASS, ROW_ENTER_CLASS, toneClass]"
    :style="{ animationDelay: enterDelay }"
    @click="emit('select', row.id)"
    @mouseenter="emit('hover', row.id)"
    @mouseleave="emit('hover', null)"
  >
    <span :class="selected ? 'font-bold text-foreground' : 'font-medium text-muted-foreground'">
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
    <!-- CLAUDE.md §2.5 y DESIGN.md §4: sin dos mediciones, el tipo de evidencia va junto a la
         aceleración. -->
    <span class="flex flex-wrap items-baseline gap-x-1">
      <span
        class="font-medium whitespace-nowrap"
        :class="{ 'text-destructive': isDeclining(row.acceleration) }"
      >
        {{ formatAcceleration(row.acceleration) }}
      </span>
      <span v-if="row.growth_status !== 'observed'" class="whitespace-nowrap text-muted-foreground">
        · {{ GROWTH_LABEL[row.growth_status] }}
      </span>
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
            animationDelay: enterDelay,
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
    <RecommendationChip :recommendation="row.recommendation" size="sm" class="justify-self-start" />
  </button>
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
