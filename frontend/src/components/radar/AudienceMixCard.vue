<script setup lang="ts">
import { TEXT_ENTER_CLASS } from '@/lib/motion'
import { computed } from 'vue'

import { audienceReading, formatShare } from '@/lib/opportunityFormat'
import type { RankedOpportunity } from '@/lib/radarView'
import type { components } from '@/types/api'

type Segment = components['schemas']['Segment']

const { opportunity } = defineProps<{ opportunity: RankedOpportunity }>()

interface SegmentStyle {
  segment: Segment
  label: string
  colorClass: string
  swatchEdgeClass?: string
}

// La lima sobre blanco no tiene contraste (DESIGN.md §2): en la leyenda la marca un filo de tinta.
const LIME_SWATCH_EDGE_CLASS = 'inset-ring inset-ring-foreground/15'

// DESIGN.md §2 "Audiencia" y §9: `latam_es` mezcla España y Latinoamérica, así que se rotula
// "En español".
const SEGMENTS: readonly SegmentStyle[] = [
  { segment: 'tech', label: 'Tech', colorClass: 'bg-foreground' },
  { segment: 'business', label: 'Negocio', colorClass: 'bg-audience-business' },
  {
    segment: 'latam_es',
    label: 'En español',
    colorClass: 'bg-signal',
    swatchEdgeClass: LIME_SWATCH_EDGE_CLASS,
  },
]

const shares = computed(() =>
  SEGMENTS.map((style) => ({ ...style, share: opportunity.audience_mix[style.segment] })),
)

// Un segmento vacío dejaría un hueco de 3 px sin color en la barra.
const barSegments = computed(() => shares.value.filter(({ share }) => share > 0))

const reading = computed(() => audienceReading(opportunity))
</script>

<template>
  <section
    data-agent="mix"
    aria-label="Para quién importa"
    class="flex min-w-0 flex-col gap-4 rounded-card bg-card px-6 py-[22px]"
  >
    <h2 class="font-display text-xl font-semibold tracking-[-0.02em]">Para quién importa</h2>

    <div
      :key="opportunity.id"
      class="mix-bar flex h-3 origin-left gap-[3px] overflow-hidden rounded-full"
      aria-hidden="true"
    >
      <!-- `flex-grow` con base 0 reparte el ancho sin los huecos; si las proporciones no suman 1,
           el resto queda vacío en lugar de estirarse. -->
      <span
        v-for="segment in barSegments"
        :key="segment.segment"
        class="h-full basis-0"
        :class="segment.colorClass"
        :style="{ flexGrow: segment.share }"
      />
    </div>

    <div class="grid grid-cols-3 gap-2">
      <div v-for="segment in shares" :key="segment.segment" class="flex flex-col">
        <span class="font-display text-[28px] leading-[1.1] font-semibold tracking-[-0.02em]">
          {{ formatShare(segment.share) }}
        </span>
        <span class="flex items-center gap-1.5 text-sm text-label">
          <span
            class="size-[9px] shrink-0 rounded-[3px]"
            :class="[segment.colorClass, segment.swatchEdgeClass]"
            aria-hidden="true"
          />
          {{ segment.label }}
        </span>
      </div>
    </div>

    <p :key="opportunity.id" class="text-[14.5px] text-ink-soft" :class="TEXT_ENTER_CLASS">
      {{ reading }}
    </p>
  </section>
</template>

<style scoped>
/* DESIGN.md §7: la barra crece hasta su valor (420 ms) al cambiar de selección, solo con
   `transform`; animar el ancho de cada segmento movería el layout. */
.mix-bar {
  animation: mix-bar-grow 420ms var(--ease-out) backwards;
}

@media (prefers-reduced-motion: reduce) {
  .mix-bar {
    animation: none;
  }
}

@keyframes mix-bar-grow {
  from {
    transform: scaleX(0);
  }
}
</style>
