<script setup lang="ts">
import { computed } from 'vue'

import HoverHint from '@/components/layout/HoverHint.vue'
import InfoTip from '@/components/layout/InfoTip.vue'
import StageDot from '@/components/explore/StageDot.vue'
import { countLabel } from '@/lib/evidenceFormat'
import { HELP } from '@/lib/helpText'
import { LIFECYCLE_STYLE } from '@/lib/lifecycle'
import {
  formatAcceleration,
  formatScore,
  growthCaveat,
  isDeclining,
  recommendationReasonText,
} from '@/lib/opportunityFormat'
import { describeStageUnknowns, type RadarView } from '@/lib/radarView'
import { RouteName } from '@/router'

const { view, monitoringStartedAt } = defineProps<{
  view: RadarView
  monitoringStartedAt: string
}>()

const emit = defineEmits<{
  select: [id: string]
  hover: [id: string | null]
}>()

// D9 del plan fe-dashboard-v2: sin «Publicar ya», los primeros del ranking, y se dice.
const subline = computed(() => {
  const { topics, hasPublishNow } = view.weekPicks
  if (!hasPublishNow) return 'Ningún tema para publicar ya: estos son los primeros del ranking.'
  return `${countLabel(topics.length, 'tema', 'temas')} para publicar ya.`
})

const picks = computed(() =>
  view.weekPicks.topics.map((topic) => ({
    topic,
    stage: LIFECYCLE_STYLE[topic.lifecycle].label,
    acceleration: formatAcceleration(topic.acceleration),
    declining: isDeclining(topic.acceleration),
    caveat: growthCaveat(topic.growth_status),
    reason: recommendationReasonText(topic),
  })),
)

const outliers = computed(() => ({
  count: countLabel(view.outlierPieces, 'pieza', 'piezas'),
  verb: view.outlierPieces === 1 ? 'rinde' : 'rinden',
}))

const TILE_CLASS =
  'flex w-full items-center gap-3 rounded-tile bg-sunken px-3.5 py-3 text-left transition-colors duration-150 ease-out hover:bg-track'
</script>

<template>
  <div class="flex flex-col gap-[18px]">
    <div class="flex flex-col gap-1">
      <h2
        class="flex items-center gap-1.5 font-display text-2xl leading-tight font-semibold tracking-[-0.02em]"
      >
        Esta semana
        <InfoTip label="Esta semana" :text="HELP.weekPublishNow" />
      </h2>
      <p class="text-[14.5px] text-label">{{ subline }}</p>
    </div>

    <ul class="flex flex-col gap-2">
      <li v-for="pick in picks" :key="pick.topic.id">
        <HoverHint :text="pick.reason ?? HELP.weekPublishNow">
          <button
            type="button"
            :class="[TILE_CLASS, 'min-h-[68px]']"
            @click="emit('select', pick.topic.id)"
            @mouseenter="emit('hover', pick.topic.id)"
            @mouseleave="emit('hover', null)"
          >
            <span class="flex min-w-0 grow flex-col gap-1">
              <span class="text-[15px] leading-[1.3] font-semibold">{{ pick.topic.topic }}</span>
              <!-- CLAUDE.md §2.5: junto a la aceleración, lo que no es observado. -->
              <span class="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[13px] text-label">
                <StageDot :lifecycle="pick.topic.lifecycle" />
                {{ pick.stage }} ·
                <span :class="{ 'text-muted-foreground': pick.declining }">{{
                  pick.acceleration
                }}</span>
                <span v-if="pick.caveat" class="text-muted-foreground">· {{ pick.caveat }}</span>
              </span>
            </span>
            <span
              class="shrink-0"
              :class="
                pick.topic.opportunity_score == null
                  ? 'text-[13px] text-muted-foreground'
                  : 'font-display text-2xl font-semibold tracking-[-0.02em]'
              "
            >
              {{ formatScore(pick.topic.opportunity_score) }}
            </span>
          </button>
        </HoverHint>
      </li>
    </ul>

    <HoverHint :text="HELP.outliers">
      <RouterLink
        :to="{ name: RouteName.Explore }"
        :class="[TILE_CLASS, 'justify-between text-sm']"
      >
        <span v-if="view.outlierPieces > 0">
          <strong class="font-semibold">{{ outliers.count }}</strong>
          {{ outliers.verb }} 3× o más que lo normal en su canal
        </span>
        <span v-else>Ninguna pieza rinde 3× o más que lo normal todavía.</span>
        <span class="shrink-0 font-semibold">Ver ›</span>
      </RouterLink>
    </HoverHint>

    <p class="rounded-tile bg-notice px-3.5 py-3 text-[13.5px] leading-normal text-ink-soft">
      <strong class="font-semibold text-notice-foreground">Qué no sabemos.</strong>
      {{ describeStageUnknowns(view.ranked, monitoringStartedAt) }}
    </p>
  </div>
</template>
