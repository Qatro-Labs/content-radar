<script setup lang="ts">
import { computed } from 'vue'

import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import { countLabel } from '@/lib/evidenceFormat'
import { formatAcceleration, formatScore, GROWTH_LABEL, isDeclining } from '@/lib/opportunityFormat'
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

const LINK_ROW_CLASS =
  'flex min-h-12 items-center justify-between gap-3 rounded-tile bg-sunken px-3.5 text-sm transition-colors duration-150 ease-out hover:bg-track'
</script>

<template>
  <div class="flex flex-col gap-[18px]">
    <div class="flex flex-col gap-1">
      <h2 class="font-display text-2xl leading-tight font-semibold tracking-[-0.02em]">
        Esta semana
      </h2>
      <p class="text-[14.5px] text-label">{{ describeWeekPicks(view.weekPicks) }}</p>
    </div>

    <ul class="flex flex-col gap-2">
      <li v-for="topic in view.weekPicks.topics" :key="topic.id">
        <button
          type="button"
          class="flex min-h-[68px] w-full items-center gap-3 rounded-tile bg-sunken px-3.5 py-3 text-left transition-colors duration-150 ease-out hover:bg-track"
          @click="emit('select', topic.id)"
          @mouseenter="emit('hover', topic.id)"
          @mouseleave="emit('hover', null)"
        >
          <span class="flex min-w-0 grow flex-col gap-1">
            <span class="text-[15px] leading-[1.3] font-semibold">{{ topic.topic }}</span>
            <!-- CLAUDE.md §2.5: sin dos mediciones, el tipo de evidencia va junto a la
                 aceleración. -->
            <span class="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-label">
              <RecommendationChip :recommendation="topic.recommendation" size="sm" />
              <span
                class="whitespace-nowrap"
                :class="{ 'text-destructive': isDeclining(topic.acceleration) }"
              >
                {{ formatAcceleration(topic.acceleration) }}
              </span>
              <span v-if="topic.growth_status !== 'observed'" class="text-muted-foreground">
                · {{ GROWTH_LABEL[topic.growth_status] }}
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

    <RouterLink :to="{ name: RouteName.Explore }" :class="LINK_ROW_CLASS">
      <span v-if="view.outlierPieces > 0">
        <strong class="font-semibold">{{ outlierLine.count }}</strong>
        {{ outlierLine.verb }} 3× o más que su canal
      </span>
      <span v-else>Ninguna pieza rinde 3× o más que su canal todavía.</span>
      <span class="shrink-0 font-semibold">Ver ›</span>
    </RouterLink>

    <p class="rounded-tile bg-notice px-3.5 py-3 text-[13.5px] text-ink-soft">
      <strong class="font-semibold text-notice-foreground">Qué no sabemos.</strong>
      {{ describeStageUnknowns(view.ranked, monitoringStartedAt) }}
    </p>
  </div>
</template>
