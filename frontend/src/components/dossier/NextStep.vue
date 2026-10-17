<script setup lang="ts">
import { useClipboard } from '@vueuse/core'

import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import { RouteName } from '@/router'
import type { components } from '@/types/api'

import {
  CARD_CLASS,
  CARD_TITLE_CLASS,
  PRIMARY_BUTTON_CLASS,
  SECONDARY_BUTTON_CLASS,
} from './dossierClasses'

const { opportunity } = defineProps<{ opportunity: components['schemas']['Opportunity'] }>()

// El aviso «Enlace copiado» dura lo justo para leerlo y vuelve al texto del botón.
const COPIED_FEEDBACK_MS = 2000
// DESIGN.md §4: los dos botones de acción miden 46 px y se reparten el ancho.
const ACTION_CLASS = 'min-h-[46px]'

const { copy, copied } = useClipboard({ copiedDuring: COPIED_FEEDBACK_MS })

function copyLink() {
  void copy(window.location.href)
}
</script>

<template>
  <section aria-label="Siguiente paso" :class="[CARD_CLASS, 'flex-wrap gap-4']">
    <div class="flex min-w-0 flex-[1_1_420px] flex-col gap-3.5">
      <h2 :class="CARD_TITLE_CLASS">Siguiente paso</h2>
      <div class="flex flex-wrap items-center gap-x-3.5 gap-y-2.5">
        <RecommendationChip :recommendation="opportunity.recommendation" />
        <p class="text-[15px] text-ink-soft">
          El brief parte de esta evidencia y de los criterios de encaje.
        </p>
      </div>
      <div class="mt-auto flex flex-wrap gap-2">
        <RouterLink
          :to="{ name: RouteName.Create, query: { opportunity: opportunity.id } }"
          :class="[PRIMARY_BUTTON_CLASS, ACTION_CLASS, 'flex-[1_1_200px]']"
        >
          Generar brief
        </RouterLink>
        <button
          type="button"
          aria-live="polite"
          :class="[SECONDARY_BUTTON_CLASS, ACTION_CLASS, 'flex-[1_1_160px]']"
          @click="copyLink"
        >
          {{ copied ? 'Enlace copiado' : 'Copiar enlace' }}
        </button>
      </div>
    </div>

    <!-- DESIGN.md §4: «Qué no sabemos» es obligatorio en todo detalle. -->
    <div
      data-agent="limit"
      class="flex min-w-0 flex-[1_1_420px] flex-col gap-2 rounded-tile bg-notice px-5 py-[18px]"
    >
      <h3 class="text-[15px] font-semibold text-notice-foreground">Qué no sabemos</h3>
      <template v-if="opportunity.limitations.length > 0">
        <!-- Por índice: el LLM puede repetir una limitación y la clave dejaría de ser única. -->
        <p
          v-for="(limitation, index) in opportunity.limitations"
          :key="index"
          class="text-[14.5px] text-ink-soft"
        >
          {{ limitation }}
        </p>
      </template>
      <p v-else class="text-[14.5px] text-ink-soft">
        No hay limitaciones registradas para este tema.
      </p>
    </div>
  </section>
</template>
