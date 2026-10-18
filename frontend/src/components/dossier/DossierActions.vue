<script setup lang="ts">
import { useClipboard } from '@vueuse/core'

import ScoreRing from '@/components/opportunities/ScoreRing.vue'
import { RouteName } from '@/router'
import type { components } from '@/types/api'

import { CARD_CLASS, PRIMARY_BUTTON_CLASS, SECONDARY_BUTTON_CLASS } from './dossierClasses'

// `rankText` es null mientras la lista no ha llegado: no se escribe un puesto que aún no se sabe.
const { opportunity, rankText } = defineProps<{
  opportunity: components['schemas']['Opportunity']
  rankText: string | null
}>()

// El aviso «Enlace copiado» dura lo justo para leerlo y vuelve al texto del botón.
const COPIED_FEEDBACK_MS = 2000
const RING_SIZE_PX = 104
// DESIGN.md §4: los dos botones de acción miden 46 px.
const ACTION_CLASS = 'min-h-[46px] w-full'

const { copy, copied } = useClipboard({ copiedDuring: COPIED_FEEDBACK_MS })

function copyLink() {
  void copy(window.location.href)
}
</script>

<template>
  <!-- La acción del recorrido de demo va en la primera pantalla, junto al score: antes estaba al
       final del expediente. El desglose del score sigue abajo, en «Cómo se calcula». -->
  <section
    data-agent="dossier-score"
    aria-label="Oportunidad y siguiente paso"
    :class="[CARD_CLASS, 'flex-[1_1_320px] flex-col gap-5 self-start']"
  >
    <div class="flex items-center gap-5">
      <ScoreRing :score="opportunity.opportunity_score ?? null" :size-px="RING_SIZE_PX" />
      <div class="flex flex-col gap-1">
        <h2 class="font-display text-xl font-semibold tracking-[-0.02em]">Oportunidad</h2>
        <span v-if="rankText" class="text-sm text-muted-foreground">{{ rankText }}</span>
        <a
          href="#como-se-calcula"
          class="text-sm font-medium text-ink-soft underline underline-offset-4"
        >
          Cómo se calcula
        </a>
      </div>
    </div>
    <div class="flex flex-col gap-2">
      <RouterLink
        :to="{ name: RouteName.Create, query: { opportunity: opportunity.id } }"
        :class="[PRIMARY_BUTTON_CLASS, ACTION_CLASS]"
      >
        Generar brief
      </RouterLink>
      <button
        type="button"
        aria-live="polite"
        :class="[SECONDARY_BUTTON_CLASS, ACTION_CLASS]"
        @click="copyLink"
      >
        {{ copied ? 'Enlace copiado' : 'Copiar enlace' }}
      </button>
    </div>
  </section>
</template>
