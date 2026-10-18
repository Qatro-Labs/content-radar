<script setup lang="ts">
import type { QueryState } from '@/api/opportunities'
import { CARD_CLASS, PRIMARY_BUTTON_CLASS } from '@/components/dossier/dossierClasses'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import { type BriefOptions, isAdvisedAgainst } from '@/lib/briefView'
import type { components } from '@/types/api'

import BriefRadMark from './BriefRadMark.vue'
import BriefSentence from './BriefSentence.vue'
import BriefSources from './BriefSources.vue'

type Schemas = components['schemas']

const { opportunity, evidence, pending } = defineProps<{
  opportunity: Schemas['Opportunity']
  evidence: QueryState<Schemas['Evidence'][]>
  // Mientras se redacta, el primario no vuelve a pedirlo.
  pending: boolean
}>()

const options = defineModel<BriefOptions>('options', { required: true })

const emit = defineEmits<{ generate: [] }>()
</script>

<template>
  <!-- Artboard B1 «Estudio en una columna»: la frase con sus huecos, con qué piezas se escribirá y
       el primario, en una sola tarjeta. -->
  <section aria-label="Preparar el brief" :class="[CARD_CLASS, 'flex-col gap-[22px] sm:p-7']">
    <div class="flex items-center gap-2.5">
      <BriefRadMark />
      <h2 class="text-[15px] font-semibold">Qué va a escribir Rad</h2>
    </div>

    <BriefSentence v-model:options="options" />

    <BriefSources :evidence />

    <!-- La API genera el brief igual y lo devuelve con la recomendación: la UI no lo esconde,
         pero avisa antes de que se pida. -->
    <div
      v-if="isAdvisedAgainst(opportunity.recommendation)"
      class="flex flex-col items-start gap-2 rounded-tile bg-sunken px-4 py-3.5"
    >
      <RecommendationChip :recommendation="opportunity.recommendation" size="sm" />
      <p v-if="opportunity.recommendation_reason" class="text-sm text-ink-soft">
        {{ opportunity.recommendation_reason }}
      </p>
    </div>

    <div class="flex flex-wrap items-center justify-between gap-3.5 pt-1">
      <p class="max-w-[420px] text-sm text-muted-foreground">
        Unos 15 segundos. Solo eliges opciones: ningún texto tuyo llega al modelo.
      </p>
      <!-- `h-13`: 52 px sin pelear con el `min-h` de la clase base (DESIGN.md §4, ≥ 46 px). -->
      <button
        type="button"
        :disabled="pending"
        :class="[
          PRIMARY_BUTTON_CLASS,
          'h-13 pr-[22px] pl-3.5 disabled:pointer-events-none disabled:opacity-50 max-sm:w-full',
        ]"
        @click="emit('generate')"
      >
        <!-- El ojo de Rad en reposo, sin su cuadrado: el botón ya es de Tinta. -->
        <svg viewBox="0 0 40 40" class="size-[26px] shrink-0" aria-hidden="true">
          <ellipse
            cx="20"
            cy="20"
            rx="13"
            ry="7.6"
            class="fill-none stroke-signal"
            stroke-width="2.4"
          />
          <circle cx="20" cy="20" r="5.2" class="fill-signal" />
          <circle cx="20" cy="20" r="2.2" class="fill-foreground" />
        </svg>
        Generar brief
      </button>
    </div>
  </section>
</template>
