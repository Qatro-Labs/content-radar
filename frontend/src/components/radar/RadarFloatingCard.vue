<script setup lang="ts">
import { computed } from 'vue'

import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import { formatAcceleration, formatScore, GROWTH_LABEL } from '@/lib/opportunityFormat'
import { translateTo, type PlotPoint } from '@/lib/radarChart'
import type { PlottedOpportunity } from '@/lib/radarView'

const { opportunity, point } = defineProps<{
  opportunity: PlottedOpportunity
  point: PlotPoint
}>()

// Artboard E: la tarjeta va a 26 px de la burbuja y, con encaje > 62, a su izquierda, porque a la
// derecha ya no cabe.
const CARD_GAP_PX = 26
const CARD_FLIP_FIT_MIN = 62

const placement = computed(() => {
  const side =
    opportunity.audience_fit_score > CARD_FLIP_FIT_MIN
      ? `translate(calc(-100% - ${CARD_GAP_PX}px), -50%)`
      : `translate(${CARD_GAP_PX}px, -50%)`
  return { transform: `${translateTo(point)} ${side}` }
})
</script>

<template>
  <div
    class="flex w-60 flex-col gap-1.5 rounded-tile bg-card px-3.5 py-3 shadow-float"
    :style="placement"
  >
    <LifecycleChip :lifecycle="opportunity.lifecycle" size="sm" class="self-start" />
    <span class="text-[15px] leading-tight font-semibold">{{ opportunity.topic }}</span>
    <!-- CLAUDE.md §2.5 y DESIGN.md §4: sin dos mediciones, el tipo de evidencia va junto a la
         aceleración. -->
    <span class="text-[13px] text-label">
      Oportunidad {{ formatScore(opportunity.opportunity_score) }} ·
      {{ formatAcceleration(opportunity.acceleration) }}
      <span v-if="opportunity.growth_status !== 'observed'" class="text-muted-foreground">
        · {{ GROWTH_LABEL[opportunity.growth_status] }}
      </span>
    </span>
  </div>
</template>
