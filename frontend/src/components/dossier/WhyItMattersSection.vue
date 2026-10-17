<script setup lang="ts">
import { computed } from 'vue'

import { citationChips } from '@/lib/dossierView'
import { formatFit } from '@/lib/opportunityFormat'
import type { components } from '@/types/api'

import { CARD_CLASS, CARD_TITLE_CLASS, SECONDARY_BUTTON_CLASS } from './dossierClasses'
import FitCriterion from './FitCriterion.vue'

type Schemas = components['schemas']

const { opportunity, evidence, citedUrl } = defineProps<{
  opportunity: Schemas['Opportunity']
  evidence: Schemas['Evidence'][]
  citedUrl: string | null
}>()

const emit = defineEmits<{ cite: [url: string | null] }>()

const criteria = computed(() =>
  (opportunity.audience_fit_criteria ?? []).map((criterion) => ({
    criterion,
    chips: citationChips(criterion, evidence),
  })),
)
</script>

<template>
  <section
    data-agent="dossier-fit"
    aria-label="Por qué importa"
    :class="[CARD_CLASS, 'flex-col gap-7']"
  >
    <div class="flex flex-col gap-2.5">
      <h2 :class="CARD_TITLE_CLASS">Por qué importa</h2>
      <p class="max-w-[720px] text-lg leading-[1.55] text-ink-read">
        {{ opportunity.why_it_matters }}
      </p>
    </div>

    <div class="flex flex-wrap gap-x-10 gap-y-6">
      <div class="flex flex-[1_1_260px] flex-col gap-2">
        <h3 class="text-[15px] font-semibold">Encaje con 30X</h3>
        <span class="font-display text-5xl leading-none font-semibold tracking-[-0.04em]">
          {{ formatFit(opportunity.audience_fit_score) }}
        </span>
        <!-- DESIGN.md §9: el encaje se rotula como evaluación editorial, no como medición. -->
        <p class="text-sm text-muted-foreground">
          Evaluación editorial, no una medición. Seis criterios de 0 a 5. Pulse una pieza para ver
          dónde está en la evidencia.
        </p>
        <button
          v-if="citedUrl"
          type="button"
          :class="[SECONDARY_BUTTON_CLASS, 'mt-2 self-start']"
          @click="emit('cite', null)"
        >
          Quitar resaltado
        </button>
      </div>

      <div class="flex min-w-0 flex-[999_1_640px] flex-col gap-[22px]">
        <FitCriterion
          v-for="{ criterion, chips } in criteria"
          :key="criterion.criterion"
          :criterion
          :chips
          :cited-url="citedUrl"
          @cite="emit('cite', $event)"
        />
        <p v-if="criteria.length === 0" class="text-[15px] text-ink-soft">
          Encaje no disponible: el tema no se evaluó.
        </p>
      </div>
    </div>
  </section>
</template>
