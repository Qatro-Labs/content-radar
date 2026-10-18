<script setup lang="ts">
import { ChevronLeft } from '@lucide/vue'
import { computed } from 'vue'

import { SECONDARY_ON_CANVAS_CLASS } from '@/components/dossier/dossierClasses'
import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import { countLabel } from '@/lib/evidenceFormat'
import { CONFIDENCE_LABEL, formatScore, GROWTH_LABEL, SCORE_MAX } from '@/lib/opportunityFormat'
import { isDescending } from '@/lib/lifecycle'
import { RouteName } from '@/router'
import type { components } from '@/types/api'

const { opportunity } = defineProps<{ opportunity: components['schemas']['Opportunity'] }>()

// Jerarquía score → explicación → acción: la cabecera da la oportunidad y su confianza.
const statusLine = computed(() =>
  [
    opportunity.opportunity_score == null
      ? 'Oportunidad no disponible'
      : `Oportunidad ${formatScore(opportunity.opportunity_score)} de ${SCORE_MAX}`,
    GROWTH_LABEL[opportunity.growth_status],
    `confianza ${CONFIDENCE_LABEL[opportunity.confidence]}`,
    countLabel(opportunity.source_count, 'fuente independiente', 'fuentes independientes'),
  ].join(' · '),
)
</script>

<template>
  <!-- Artboard B1: cabecera compacta, para que la frase del brief quede a la vista sin bajar. -->
  <div class="flex flex-col gap-3.5 pt-3">
    <div class="flex flex-wrap gap-2">
      <RouterLink :to="{ name: RouteName.Create }" :class="SECONDARY_ON_CANVAS_CLASS">
        <ChevronLeft class="size-4 text-ink-soft" aria-hidden="true" />
        Otro tema
      </RouterLink>
      <RouterLink
        :to="{ name: RouteName.Dossier, params: { id: opportunity.id } }"
        :class="SECONDARY_ON_CANVAS_CLASS"
      >
        Ver expediente
      </RouterLink>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <LifecycleChip :lifecycle="opportunity.lifecycle" :descending="isDescending(opportunity)" />
      <RecommendationChip :recommendation="opportunity.recommendation" size="sm" />
    </div>
    <h1
      class="font-display text-[clamp(2.125rem,5vw,2.875rem)] leading-[1.02] font-semibold tracking-[-0.04em] text-balance"
    >
      {{ opportunity.topic }}
    </h1>
    <p class="text-[15px] text-label">{{ statusLine }}</p>
  </div>
</template>
