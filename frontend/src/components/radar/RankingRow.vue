<script lang="ts">
// D6 del plan fe-dashboard-v2 (artboard D2): por debajo de 660 px la tabla hace scroll dentro de
// su tarjeta. La cabecera de OpportunityRanking comparte la rejilla. La etapa va bajo el tema.
export const RANKING_GRID_CLASS =
  'grid grid-cols-[52px_minmax(260px,2.4fr)_84px_112px_150px] items-center gap-x-3.5 px-3.5'
</script>

<script setup lang="ts">
import { computed } from 'vue'

import type { QueryState } from '@/api/opportunities'
import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import { rowAnchor } from '@/lib/agentTargets'
import {
  formatScore,
  growthCaveat,
  NOT_AVAILABLE,
  SCORE_MAX,
  windowTotals,
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

const totals = computed(() => windowTotals(timeline.data?.points ?? []))
const caveat = computed(() => growthCaveat(row.growth_status))

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
    <span class="flex min-w-0 flex-col gap-1.5 py-2.5">
      <span class="font-medium">{{ row.topic }}</span>
      <span class="flex flex-wrap items-center gap-1.5">
        <LifecycleChip :lifecycle="row.lifecycle" :title="row.lifecycle_reason" size="sm" />
        <!-- Lo que la persona viene a buscar: solo se marca «Publicar ya», el resto está en el detalle. -->
        <RecommendationChip
          v-if="row.recommendation === 'publish_now'"
          :recommendation="row.recommendation"
          size="sm"
        />
        <span v-if="row.audience_fit_score == null" class="text-[13px] text-muted-foreground">
          Encaje no disponible
        </span>
      </span>
    </span>
    <RankingSparkline :timeline />
    <span class="flex flex-col py-2 whitespace-nowrap">
      <span
        v-if="timeline.isPending"
        class="h-4 w-14 animate-pulse rounded bg-track motion-reduce:animate-none"
      />
      <span v-else-if="totals" class="font-medium">
        {{ totals.current }}
        <span class="font-normal text-muted-foreground">· antes {{ totals.previous }}</span>
      </span>
      <span v-else class="text-[13px] text-muted-foreground">{{ NOT_AVAILABLE }}</span>
      <!-- CLAUDE.md §2.5: se marca lo que no es observado; observado es lo normal. -->
      <span v-if="caveat" class="text-[13px] text-muted-foreground">{{ caveat }}</span>
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
