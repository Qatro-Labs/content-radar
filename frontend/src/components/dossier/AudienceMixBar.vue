<script setup lang="ts">
import { computed } from 'vue'

import { SEGMENT_LABEL } from '@/lib/evidenceFormat'
import { audienceReading, formatShare } from '@/lib/opportunityFormat'
import type { components } from '@/types/api'

import { SEGMENT_COLOR_CLASS, SEGMENT_SWATCH_CLASS } from './dossierClasses'

type Schemas = components['schemas']
type Segment = Schemas['Segment']

const { opportunity } = defineProps<{ opportunity: Schemas['Opportunity'] }>()

const SEGMENT_ORDER = Object.keys(SEGMENT_LABEL) as Segment[]

const shares = computed(() =>
  SEGMENT_ORDER.map((segment) => ({
    segment,
    label: SEGMENT_LABEL[segment],
    share: opportunity.audience_mix[segment],
  })),
)

// Un segmento vacío dejaría un hueco de 3 px sin color en la barra.
const barSegments = computed(() => shares.value.filter(({ share }) => share > 0))

const reading = computed(() => audienceReading(opportunity))
</script>

<template>
  <div class="flex min-w-0 flex-col gap-2">
    <h3 class="text-sm font-semibold">Para quién importa</h3>
    <!-- `flex-grow` con base 0 reparte el ancho sin los huecos; si las proporciones no suman 1,
         el resto queda vacío en lugar de estirarse. -->
    <div
      class="mix-bar flex h-3 origin-left gap-[3px] overflow-hidden rounded-full"
      aria-hidden="true"
    >
      <span
        v-for="segment in barSegments"
        :key="segment.segment"
        class="h-full basis-0"
        :class="SEGMENT_COLOR_CLASS[segment.segment]"
        :style="{ flexGrow: segment.share }"
      />
    </div>
    <p class="flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-soft">
      <span
        v-for="segment in shares"
        :key="segment.segment"
        class="inline-flex items-center gap-1.5"
      >
        <span
          class="size-[9px] shrink-0 rounded-[3px]"
          :class="SEGMENT_SWATCH_CLASS[segment.segment]"
          aria-hidden="true"
        />
        {{ segment.label }} {{ formatShare(segment.share) }}
      </span>
    </p>
    <p class="text-[13.5px] text-muted-foreground">{{ reading }}</p>
  </div>
</template>

<style scoped>
/* DESIGN.md §7: la barra crece hasta su valor (420 ms), solo con `transform`. */
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
