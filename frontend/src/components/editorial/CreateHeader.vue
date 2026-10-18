<script setup lang="ts">
import { ChevronLeft } from '@lucide/vue'
import { computed } from 'vue'

import { SECONDARY_ON_CANVAS_CLASS } from '@/components/dossier/dossierClasses'
import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import { countLabel } from '@/lib/evidenceFormat'
import { formatScore, SCORE_MAX } from '@/lib/opportunityFormat'
import { RouteName } from '@/router'
import type { components } from '@/types/api'

const { opportunity } = defineProps<{ opportunity: components['schemas']['Opportunity'] }>()

// Lo que decide al escribir: la oportunidad y de cuántas fuentes sale. La confianza y el tipo de
// evidencia están en el expediente, a un clic.
const statusLine = computed(() =>
  [
    opportunity.opportunity_score == null
      ? 'Oportunidad no disponible'
      : `Oportunidad ${formatScore(opportunity.opportunity_score)} de ${SCORE_MAX}`,
    countLabel(opportunity.source_count, 'fuente', 'fuentes'),
  ].join(' · '),
)
</script>

<template>
  <div class="flex flex-col gap-4 pt-4 pb-1">
    <RouterLink
      :to="{ name: RouteName.Dossier, params: { id: opportunity.id } }"
      :class="[SECONDARY_ON_CANVAS_CLASS, 'self-start']"
    >
      <ChevronLeft class="size-4 text-ink-soft" aria-hidden="true" />
      Expediente
    </RouterLink>
    <div class="flex flex-wrap items-center gap-2.5">
      <LifecycleChip :lifecycle="opportunity.lifecycle" />
      <RecommendationChip :recommendation="opportunity.recommendation" size="sm" />
    </div>
    <h1
      class="max-w-[860px] font-display text-[clamp(2.25rem,4vw,3.5rem)] leading-none font-semibold tracking-[-0.04em]"
    >
      {{ opportunity.topic }}
    </h1>
    <p class="text-base text-label">{{ statusLine }}</p>
  </div>
</template>
