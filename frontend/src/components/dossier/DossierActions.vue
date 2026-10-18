<script setup lang="ts">
import HoverHint from '@/components/layout/HoverHint.vue'
import InfoTip from '@/components/layout/InfoTip.vue'
import { HELP } from '@/lib/helpText'
import { useClipboard } from '@vueuse/core'

import ScoreRing from '@/components/opportunities/ScoreRing.vue'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { RouteName } from '@/router'
import type { components } from '@/types/api'

import { CARD_CLASS, PRIMARY_BUTTON_CLASS, SECONDARY_BUTTON_CLASS } from './dossierClasses'
import ScoreComposition from './ScoreComposition.vue'

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
       final del expediente. El desglose del score sale de «Cómo se calcula», junto al anillo. -->
  <section
    data-agent="dossier-score"
    aria-label="Oportunidad y siguiente paso"
    :class="[CARD_CLASS, 'flex-[1_1_320px] flex-col gap-5 self-start']"
  >
    <div class="flex items-center gap-5">
      <ScoreRing :score="opportunity.opportunity_score ?? null" :size-px="RING_SIZE_PX" />
      <div class="flex flex-col gap-1">
        <h2 class="flex items-center gap-1.5 font-display text-xl font-semibold tracking-[-0.02em]">
          Oportunidad
          <InfoTip label="la oportunidad" :text="HELP.opportunityRing" />
        </h2>
        <span v-if="rankText" class="text-sm text-muted-foreground">{{ rankText }}</span>
        <Popover>
          <PopoverTrigger
            class="self-start text-sm font-medium text-ink-soft underline underline-offset-4 transition-colors duration-150 ease-out hover:text-foreground data-[state=open]:text-foreground"
          >
            Cómo se calcula
          </PopoverTrigger>
          <PopoverContent
            align="start"
            :side-offset="8"
            aria-label="Cómo se calcula la oportunidad"
            class="w-[460px] p-5"
          >
            <ScoreComposition :opportunity :rank-text="rankText" />
          </PopoverContent>
        </Popover>
      </div>
    </div>
    <div class="flex flex-col gap-2">
      <HoverHint :text="HELP.generateBrief">
        <RouterLink
          :to="{ name: RouteName.Create, query: { opportunity: opportunity.id } }"
          :class="[PRIMARY_BUTTON_CLASS, ACTION_CLASS]"
        >
          Generar brief
        </RouterLink>
      </HoverHint>
      <HoverHint :text="HELP.copyLink">
        <button
          type="button"
          aria-live="polite"
          :class="[SECONDARY_BUTTON_CLASS, ACTION_CLASS]"
          @click="copyLink"
        >
          {{ copied ? 'Enlace copiado' : 'Copiar enlace' }}
        </button>
      </HoverHint>
    </div>
  </section>
</template>
