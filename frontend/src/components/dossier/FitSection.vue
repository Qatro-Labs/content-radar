<script setup lang="ts">
import InfoTip from '@/components/layout/InfoTip.vue'
import { HELP } from '@/lib/helpText'
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
    aria-label="Encaje con 30X"
    :class="[CARD_CLASS, 'flex-col gap-5']"
  >
    <div class="flex flex-wrap gap-x-10 gap-y-6">
      <div class="flex flex-[1_1_260px] flex-col gap-2">
        <h2 :class="[CARD_TITLE_CLASS, 'flex items-center gap-1.5']">
          Encaje con 30X
          <InfoTip label="el encaje con 30X" :text="HELP.fit" />
        </h2>
        <span class="font-display text-5xl leading-none font-semibold tracking-[-0.04em]">
          {{ formatFit(opportunity.audience_fit_score) }}
        </span>
        <!-- DESIGN.md §9: el encaje se rotula como evaluación editorial, no como medición. -->
        <p class="text-sm text-muted-foreground">
          Evaluación editorial, no una medición. Seis criterios de 0 a 5: abra uno para ver por qué
          y en qué piezas se apoya.
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

      <div class="flex min-w-0 flex-[999_1_640px] flex-col">
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
