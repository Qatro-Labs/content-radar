<script setup lang="ts">
import { ArrowRight, ChevronLeft } from '@lucide/vue'
import { computed } from 'vue'

import HoverHint from '@/components/layout/HoverHint.vue'
import InfoTip from '@/components/layout/InfoTip.vue'
import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import ScoreRing from '@/components/opportunities/ScoreRing.vue'
import { countLabel } from '@/lib/evidenceFormat'
import { HELP } from '@/lib/helpText'
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
  help: string
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
  {
    label: 'Nuevas',
    value: newPieces.value,
    valueClass: cn('whitespace-nowrap'),
    help: HELP.tileNewPieces,
  },
  {
    label: 'Encaje',
    value: formatFit(opportunity.audience_fit_score),
    valueClass: '',
    help: HELP.tileFit,
  },
  {
    label: 'Outliers',
    value: String(opportunity.outlier_count),
    valueClass: '',
    help: HELP.outliers,
  },
])

// DESIGN.md §4.
const BUTTON_CLASS =
  'flex min-h-[46px] items-center justify-center gap-2 rounded-xl px-4 font-semibold whitespace-nowrap transition-[background-color,scale] duration-150 ease-out active:scale-[0.98]'
</script>

<template>
  <div data-agent="detail" class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <HoverHint :text="HELP.backToRanking">
        <button
          type="button"
          class="flex min-h-10 items-center gap-1.5 rounded-[10px] bg-secondary pr-3 pl-2 text-sm font-semibold transition-[background-color,scale] duration-150 ease-out hover:bg-secondary-hover active:scale-[0.98]"
          @click="emit('clear')"
        >
          <ChevronLeft class="size-4 text-ink-soft" aria-hidden="true" />
          Ranking
        </button>
      </HoverHint>
      <div class="flex flex-wrap items-center gap-2">
        <LifecycleChip :lifecycle="opportunity.lifecycle" />
        <RecommendationChip :recommendation="opportunity.recommendation" />
      </div>
    </div>

    <div class="flex items-center gap-[18px]">
      <ScoreRing :score="opportunity.opportunity_score ?? null" :size-px="PREVIEW_RING_SIZE_PX" />
      <div :key="opportunity.id" class="flex min-w-0 flex-col gap-1.5" :class="TEXT_ENTER_CLASS">
        <h2 class="font-display text-[26px] leading-[1.08] font-semibold tracking-[-0.03em]">
          {{ opportunity.topic }}
        </h2>
        <span class="flex flex-wrap items-center gap-x-1 text-sm text-muted-foreground">
          Oportunidad · puesto {{ opportunity.rank }} de {{ total }} · {{ evidenceSummary }}
          <InfoTip label="la oportunidad" :text="HELP.colScore" />
        </span>
      </div>
    </div>

    <!-- Ejecuciones anteriores a #23 no traen la regla: sin texto, no "no disponible". -->
    <p
      v-if="reason"
      :key="`reason-${opportunity.id}`"
      class="text-[15px] text-ink-soft"
      :class="TEXT_ENTER_CLASS"
    >
      {{ reason }}
    </p>

    <!-- D8: solo el inicio; el texto entero vive en el expediente. -->
    <p
      v-if="opportunity.why_it_matters"
      :key="`why-${opportunity.id}`"
      class="line-clamp-3 text-[15px] leading-[1.55] text-ink-read"
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
        <span class="flex items-center gap-0.5 text-[13px] text-muted-foreground">
          {{ tile.label }}
          <InfoTip :label="tile.label" :text="tile.help" />
        </span>
        <span
          class="font-display text-xl leading-[1.1] font-semibold tracking-[-0.02em]"
          :class="tile.valueClass"
        >
          {{ tile.value }}
        </span>
      </div>
    </div>

    <div class="mt-auto flex flex-wrap gap-2">
      <HoverHint :text="HELP.openDossier">
        <RouterLink
          :data-agent="AGENT_ANCHOR.openDossier"
          :to="{ name: RouteName.Dossier, params: { id: opportunity.id } }"
          class="flex-[1_1_180px] bg-primary text-primary-foreground hover:bg-primary-hover"
          :class="BUTTON_CLASS"
        >
          Ver expediente
          <ArrowRight class="size-4" aria-hidden="true" />
        </RouterLink>
      </HoverHint>
      <HoverHint :text="HELP.generateBrief">
        <RouterLink
          :to="{ name: RouteName.Create, query: { opportunity: opportunity.id } }"
          class="flex-[1_1_160px] bg-secondary text-secondary-foreground hover:bg-secondary-hover"
          :class="BUTTON_CLASS"
        >
          Generar brief
        </RouterLink>
      </HoverHint>
    </div>
  </div>
</template>
