<script setup lang="ts">
import { computed } from 'vue'

import { useAllTimelines } from '@/api/opportunities'
import InfoTip from '@/components/layout/InfoTip.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import { HELP } from '@/lib/helpText'
import { countLabel } from '@/lib/evidenceFormat'
import { formatScore, growthCaveat, windowTotals } from '@/lib/opportunityFormat'
import { describeStageUnknowns, describeWeekPicks, type RadarView } from '@/lib/radarView'
import { RouteName } from '@/router'

const { view, monitoringStartedAt } = defineProps<{
  view: RadarView
  monitoringStartedAt: string
}>()

const emit = defineEmits<{
  select: [id: string]
  hover: [id: string | null]
}>()

// Σ `outlier_count`: piezas que rinden 3× o más que su referencia (CLAUDE.md §7).
const outlierLine = computed(() => {
  const count = view.outlierPieces
  return {
    count: countLabel(count, 'pieza', 'piezas'),
    verb: count === 1 ? 'rinde' : 'rinden',
  }
})

// La misma consulta que las mini barras del ranking: ya está en caché.
const { data: timelines } = useAllTimelines()

function newPiecesOf(id: string): string | null {
  const totals = windowTotals(timelines.value?.get(id)?.points ?? [])
  return totals
    ? `${countLabel(totals.current, 'pieza nueva', 'piezas nuevas')} · antes ${totals.previous}`
    : null
}

const LINK_ROW_CLASS =
  'flex min-h-12 items-center justify-between gap-3 rounded-tile bg-sunken px-3.5 text-sm transition-colors duration-150 ease-out hover:bg-track'
</script>

<template>
  <div
    class="grid gap-5 lg:grid-cols-[minmax(200px,0.8fr)_minmax(0,2fr)_minmax(260px,1fr)] lg:items-start"
  >
    <!-- A lo ancho, debajo del radar y del ranking: qué publicar a la izquierda, los temas en el
         centro y lo que funciona y lo que no sabemos a la derecha. En móvil se apila. -->
    <div class="flex flex-col gap-1">
      <h2
        class="flex items-center gap-1.5 font-display text-2xl leading-tight font-semibold tracking-[-0.02em]"
      >
        Esta semana
        <InfoTip label="Esta semana" :text="HELP.weekSummary" />
      </h2>
      <p class="text-[14.5px] text-label">{{ describeWeekPicks(view.weekPicks) }}</p>
    </div>

    <ul class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
      <li v-for="topic in view.weekPicks.topics" :key="topic.id" class="flex">
        <button
          type="button"
          class="flex min-h-[68px] w-full items-center gap-3 rounded-tile bg-sunken px-3.5 py-3 text-left transition-colors duration-150 ease-out hover:bg-track"
          @click="emit('select', topic.id)"
          @mouseenter="emit('hover', topic.id)"
          @mouseleave="emit('hover', null)"
        >
          <span class="flex min-w-0 grow flex-col gap-1">
            <span class="text-[15px] leading-[1.3] font-semibold">{{ topic.topic }}</span>
            <!-- CLAUDE.md §2.5: sin dos mediciones, el tipo de evidencia va junto al dato. -->
            <span class="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-label">
              <RecommendationChip :recommendation="topic.recommendation" size="sm" />
              <span v-if="newPiecesOf(topic.id)" class="whitespace-nowrap">
                {{ newPiecesOf(topic.id) }}
              </span>
              <span v-if="growthCaveat(topic.growth_status)" class="text-muted-foreground">
                · {{ growthCaveat(topic.growth_status) }}
              </span>
            </span>
          </span>
          <span
            class="shrink-0"
            :class="
              topic.opportunity_score == null
                ? 'text-[13px] text-muted-foreground'
                : 'font-display text-2xl font-semibold tracking-[-0.02em]'
            "
          >
            {{ formatScore(topic.opportunity_score) }}
          </span>
        </button>
      </li>
    </ul>

    <div class="flex flex-col gap-2">
      <div class="flex items-center gap-1">
        <RouterLink :to="{ name: RouteName.Explore }" :class="[LINK_ROW_CLASS, 'grow']">
          <span v-if="view.outlierPieces > 0">
            <strong class="font-semibold">{{ outlierLine.count }}</strong>
            {{ outlierLine.verb }} 3× o más que lo normal en su canal
          </span>
          <span v-else>Ninguna pieza rinde 3× o más que lo normal en su canal todavía.</span>
          <span class="shrink-0 font-semibold">Ver ›</span>
        </RouterLink>
        <InfoTip label="un outlier" :text="HELP.outliers" />
      </div>

      <p class="rounded-tile bg-notice px-3.5 py-3 text-[13.5px] text-ink-soft">
        <strong class="font-semibold text-notice-foreground">Qué no sabemos.</strong>
        {{ describeStageUnknowns(view.ranked, monitoringStartedAt) }}
      </p>
    </div>
  </div>
</template>
