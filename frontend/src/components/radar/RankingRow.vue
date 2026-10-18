<script lang="ts">
// D6 del plan fe-dashboard-v2 (artboard D2): por debajo de 780 px la tabla hace scroll dentro de
// su tarjeta. La cabecera de OpportunityRanking comparte la rejilla.
export const RANKING_GRID_CLASS =
  'grid grid-cols-[52px_minmax(240px,2fr)_128px_84px_104px_150px] items-center gap-x-3.5 px-3.5'
</script>

<script setup lang="ts">
import { computed } from 'vue'

import type { QueryState } from '@/api/opportunities'
import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import { rowAnchor } from '@/lib/agentTargets'
import {
  formatAcceleration,
  formatScore,
  GROWTH_LABEL,
  isDeclining,
  SCORE_MAX,
} from '@/lib/opportunityFormat'
import type { RankedOpportunity } from '@/lib/radarView'
import type { components } from '@/types/api'

import RankingSparkline from './RankingSparkline.vue'

const { row, index, selected, hovered, timeline } = defineProps<{
  row: RankedOpportunity
  // Posición en la tabla: escalona la entrada.
  index: number
  selected: boolean
  hovered: boolean
  timeline: QueryState<components['schemas']['OpportunityTimeline'] | null>
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
    :data-agent="rowAnchor(row.id)"
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
    <RankingSparkline :timeline />
    <!-- CLAUDE.md §2.5 y DESIGN.md §4: el tipo de evidencia va siempre junto a la aceleración. -->
    <span class="flex flex-col py-2">
      <span
        class="font-medium whitespace-nowrap"
        :class="{ 'text-destructive': isDeclining(row.acceleration) }"
      >
        {{ formatAcceleration(row.acceleration) }}
      </span>
      <span class="text-[13px] whitespace-nowrap text-muted-foreground">
        {{ GROWTH_LABEL[row.growth_status] }}
      </span>
    </span>
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
