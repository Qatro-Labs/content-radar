<script setup lang="ts">
import { TEXT_ENTER_CLASS } from '@/lib/motion'
import { computed } from 'vue'

import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import MetricBar from '@/components/opportunities/MetricBar.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import ScoreRing from '@/components/opportunities/ScoreRing.vue'
import {
  CONFIDENCE_LABEL,
  formatAcceleration,
  formatFit,
  formatOutliers,
  formatScore,
  GROWTH_LABEL,
  isDeclining,
  latamGapLabel,
} from '@/lib/opportunityFormat'
import type { RankedOpportunity } from '@/lib/radarView'
import { cn } from '@/lib/utils'
import { RouteName } from '@/router'

const { opportunity, total } = defineProps<{ opportunity: RankedOpportunity; total: number }>()

interface StatTile {
  label: string
  value: string
  valueClass: string
}

const SUMMARY_SEPARATOR = ' · '

const evidenceSummary = computed(() =>
  [
    GROWTH_LABEL[opportunity.growth_status],
    `confianza ${CONFIDENCE_LABEL[opportunity.confidence]}`,
    latamGapLabel(opportunity.latam_gap),
  ].join(SUMMARY_SEPARATOR),
)

const tiles = computed<StatTile[]>(() => [
  {
    label: 'Aceleración',
    value: formatAcceleration(opportunity.acceleration),
    // "↑ +100 %" no cabe en la baldosa y partiría el "%" solo en otra línea; los outliers sí
    // pueden partirse por el "·". DESIGN.md §2: la aceleración negativa va en Negativo.
    valueClass: cn('whitespace-nowrap', {
      'text-destructive': isDeclining(opportunity.acceleration),
    }),
  },
  {
    label: 'Outliers',
    value: formatOutliers(opportunity.outlier_count, opportunity.top_outlier_ratio),
    valueClass: '',
  },
  { label: 'Fuentes', value: String(opportunity.source_count), valueClass: '' },
])

// DESIGN.md §4. Los hovers de los botones no tienen token en main.css.
const BUTTON_CLASS =
  'flex min-h-[46px] flex-[1_1_140px] items-center justify-center rounded-xl px-4 font-semibold transition-[background-color,scale] duration-150 ease-out active:scale-[0.98]'
</script>

<template>
  <aside
    data-agent="detail"
    aria-label="Oportunidad seleccionada"
    class="flex min-w-0 flex-col gap-5 rounded-card bg-card p-6"
  >
    <div :key="opportunity.id" class="flex flex-col gap-2.5" :class="TEXT_ENTER_CLASS">
      <LifecycleChip :lifecycle="opportunity.lifecycle" class="self-start" />
      <h2 class="font-display text-[30px] leading-[1.08] font-semibold tracking-[-0.03em]">
        {{ opportunity.topic }}
      </h2>
      <p class="text-sm text-muted-foreground">{{ evidenceSummary }}</p>
      <p class="text-sm text-ink-soft">{{ opportunity.lifecycle_reason }}</p>
    </div>

    <div class="flex items-center gap-5">
      <ScoreRing :score="opportunity.opportunity_score ?? null" />
      <div class="flex min-w-0 flex-col items-start gap-2">
        <span class="text-sm text-muted-foreground">
          Oportunidad · puesto {{ opportunity.rank }} de {{ total }}
        </span>
        <RecommendationChip :recommendation="opportunity.recommendation" />
      </div>
    </div>

    <div class="grid grid-cols-3 gap-2">
      <div
        v-for="tile in tiles"
        :key="tile.label"
        class="flex min-w-0 flex-col gap-0.5 rounded-tile bg-sunken px-3.5 py-3"
      >
        <span class="text-[13px] text-muted-foreground">{{ tile.label }}</span>
        <span
          class="font-display text-xl leading-[1.1] font-semibold tracking-[-0.02em]"
          :class="tile.valueClass"
        >
          {{ tile.value }}
        </span>
      </div>
    </div>

    <div class="flex flex-col gap-3">
      <MetricBar
        label="Momentum"
        :value="opportunity.momentum_score"
        :display="formatScore(opportunity.momentum_score)"
      />
      <MetricBar
        label="Encaje con 30X"
        :value="opportunity.audience_fit_score ?? null"
        :display="formatFit(opportunity.audience_fit_score)"
      />
      <MetricBar
        label="Saturación"
        :value="opportunity.saturation_score"
        :display="formatScore(opportunity.saturation_score)"
        tone="saturation"
      />
    </div>

    <div class="mt-auto flex flex-wrap gap-2">
      <RouterLink
        :to="{ name: RouteName.Explore, params: { id: opportunity.id } }"
        class="bg-secondary text-secondary-foreground hover:bg-[#e8eaed]"
        :class="BUTTON_CLASS"
      >
        Ver evidencia
      </RouterLink>
      <RouterLink
        :to="{ name: RouteName.Create, query: { opportunity: opportunity.id } }"
        class="bg-primary text-primary-foreground hover:bg-[#2a2e35]"
        :class="BUTTON_CLASS"
      >
        Generar brief
      </RouterLink>
    </div>
  </aside>
</template>
