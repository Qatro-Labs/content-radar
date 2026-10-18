<script setup lang="ts">
import { ArrowRight, ChevronLeft } from '@lucide/vue'
import { computed } from 'vue'

import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import ScoreRing from '@/components/opportunities/ScoreRing.vue'
import { countLabel } from '@/lib/evidenceFormat'
import { TEXT_ENTER_CLASS } from '@/lib/motion'
import { useAllTimelines } from '@/api/opportunities'
import {
  CONFIDENCE_LABEL,
  formatFit,
  GROWTH_LABEL,
  NOT_AVAILABLE,
  recommendationReasonText,
  windowTotals,
} from '@/lib/opportunityFormat'
import type { RankedOpportunity } from '@/lib/radarView'
import { cn } from '@/lib/utils'
import { AGENT_ANCHOR } from '@/lib/agentTargets'
import { RouteName } from '@/router'

const { opportunity, total } = defineProps<{ opportunity: RankedOpportunity; total: number }>()

const emit = defineEmits<{ clear: [] }>()

interface StatTile {
  label: string
  value: string
  valueClass: string
}

// D8 del plan fe-dashboard-v2: en el panel lateral el anillo baja a 104 px.
const PREVIEW_RING_SIZE_PX = 104
const SUMMARY_SEPARATOR = ' · '

const evidenceSummary = computed(() =>
  [
    GROWTH_LABEL[opportunity.growth_status],
    `confianza ${CONFIDENCE_LABEL[opportunity.confidence]}`,
    countLabel(opportunity.source_count, 'fuente', 'fuentes'),
  ].join(SUMMARY_SEPARATOR),
)

// La misma consulta que las mini barras del ranking: ya está en caché.
const { data: timelines } = useAllTimelines()
const newPieces = computed(() => {
  const totals = windowTotals(timelines.value?.get(opportunity.id)?.points ?? [])
  return totals ? `${totals.current} · antes ${totals.previous}` : NOT_AVAILABLE
})
const reason = computed(() => recommendationReasonText(opportunity))

const tiles = computed<StatTile[]>(() => [
  // Piezas de los últimos 3 días frente a los 3 anteriores: con bases pequeñas, un porcentaje
  // exagera (+104 % son 2 piezas frente a 1).
  { label: 'Piezas nuevas', value: newPieces.value, valueClass: cn('whitespace-nowrap') },
  { label: 'Encaje', value: formatFit(opportunity.audience_fit_score), valueClass: '' },
  { label: 'Outliers', value: String(opportunity.outlier_count), valueClass: '' },
])

// DESIGN.md §4.
const BUTTON_CLASS =
  'flex min-h-[46px] items-center justify-center gap-2 rounded-xl px-4 font-semibold whitespace-nowrap transition-[background-color,scale] duration-150 ease-out active:scale-[0.98]'
</script>

<template>
  <div data-agent="detail" class="flex flex-col gap-[18px]">
    <button
      type="button"
      class="flex min-h-10 items-center gap-1.5 self-start rounded-[10px] bg-secondary pr-3 pl-2 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]"
      @click="emit('clear')"
    >
      <ChevronLeft class="size-4 text-ink-soft" aria-hidden="true" />
      Esta semana
    </button>

    <div :key="opportunity.id" class="flex flex-col gap-2" :class="TEXT_ENTER_CLASS">
      <LifecycleChip :lifecycle="opportunity.lifecycle" class="self-start" />
      <h2 class="font-display text-[28px] leading-[1.08] font-semibold tracking-[-0.03em]">
        {{ opportunity.topic }}
      </h2>
      <p class="text-sm text-muted-foreground">{{ evidenceSummary }}</p>
    </div>

    <div class="flex items-center gap-[18px]">
      <ScoreRing :score="opportunity.opportunity_score ?? null" :size-px="PREVIEW_RING_SIZE_PX" />
      <div class="flex min-w-0 flex-col items-start gap-2">
        <span class="text-sm text-muted-foreground">
          Oportunidad · puesto {{ opportunity.rank }} de {{ total }}
        </span>
        <RecommendationChip :recommendation="opportunity.recommendation" />
      </div>
    </div>

    <!-- Ejecuciones anteriores a #23 no traen la regla: sin texto, no "no disponible". -->
    <p
      v-if="reason"
      :key="`reason-${opportunity.id}`"
      class="text-sm text-ink-soft"
      :class="TEXT_ENTER_CLASS"
    >
      {{ reason }}
    </p>

    <!-- D8: solo el inicio; el texto entero vive en el expediente. -->
    <p
      v-if="opportunity.why_it_matters"
      :key="`why-${opportunity.id}`"
      class="line-clamp-3 text-base leading-[1.55] text-ink-read"
      :class="TEXT_ENTER_CLASS"
    >
      {{ opportunity.why_it_matters }}
    </p>

    <div class="grid grid-cols-3 gap-2">
      <div
        v-for="tile in tiles"
        :key="tile.label"
        class="flex min-w-0 flex-col gap-0.5 rounded-tile bg-sunken px-3 py-2.5"
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

    <div class="flex flex-wrap gap-2">
      <RouterLink
        :data-agent="AGENT_ANCHOR.openDossier"
        :to="{ name: RouteName.Dossier, params: { id: opportunity.id } }"
        class="flex-[1_1_150px] bg-primary text-primary-foreground hover:bg-primary-hover"
        :class="BUTTON_CLASS"
      >
        Ver expediente
        <ArrowRight class="size-4" aria-hidden="true" />
      </RouterLink>
      <RouterLink
        :to="{ name: RouteName.Create, query: { opportunity: opportunity.id } }"
        class="flex-[1_1_130px] bg-secondary text-secondary-foreground hover:bg-secondary-hover"
        :class="BUTTON_CLASS"
      >
        Generar brief
      </RouterLink>
    </div>
  </div>
</template>
