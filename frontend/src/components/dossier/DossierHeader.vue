<script setup lang="ts">
import { ChevronLeft } from '@lucide/vue'
import { computed } from 'vue'

import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import { dossierStatusLine } from '@/lib/dossierView'
import { recommendationReasonText } from '@/lib/opportunityFormat'
import { isDescending } from '@/lib/lifecycle'
import { RouteName } from '@/router'
import type { components } from '@/types/api'

import { SECONDARY_ON_CANVAS_CLASS } from './dossierClasses'

const { opportunity } = defineProps<{ opportunity: components['schemas']['Opportunity'] }>()

const statusLine = computed(() => dossierStatusLine(opportunity))
const reason = computed(() => recommendationReasonText(opportunity))
</script>

<template>
  <div class="flex min-w-0 flex-[999_1_640px] flex-col gap-4 pt-1 pb-2">
    <!-- Vuelve al Radar con el tema seleccionado, para seguir comparándolo con el resto (D13). -->
    <RouterLink
      :to="{ name: RouteName.Discover, query: { selected: opportunity.id } }"
      :class="[SECONDARY_ON_CANVAS_CLASS, 'self-start']"
    >
      <ChevronLeft class="size-4 text-ink-soft" aria-hidden="true" />
      Radar
    </RouterLink>
    <LifecycleChip
      :lifecycle="opportunity.lifecycle"
      :descending="isDescending(opportunity)"
      class="self-start"
    />
    <h1
      class="max-w-[860px] font-display text-[clamp(2.25rem,4vw,3.5rem)] leading-none font-semibold tracking-[-0.04em]"
    >
      {{ opportunity.topic }}
    </h1>
    <div class="flex flex-wrap items-center gap-x-3.5 gap-y-2.5">
      <RecommendationChip :recommendation="opportunity.recommendation" />
      <!-- Ejecuciones anteriores a #23 no traen la regla: sin texto, no "no disponible". -->
      <p v-if="reason" class="text-[17px] text-ink-read">{{ reason }}</p>
    </div>
    <p class="text-[15px] text-label">{{ statusLine }}</p>
  </div>
</template>
