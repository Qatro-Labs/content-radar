<script setup lang="ts">
import HoverHint from '@/components/layout/HoverHint.vue'
import InfoTip from '@/components/layout/InfoTip.vue'
import { HELP, SCORE_COMPONENT_HELP } from '@/lib/helpText'
import { computed } from 'vue'

import { componentRows, compositionSubline } from '@/lib/dossierView'
import { formatScore, SCORE_MAX } from '@/lib/opportunityFormat'
import type { components } from '@/types/api'

// `rankText` es null mientras la lista no ha llegado: no se escribe un puesto que aún no se sabe.
const { opportunity, rankText } = defineProps<{
  opportunity: components['schemas']['Opportunity']
  rankText: string | null
}>()

// DESIGN.md §7: las barras crecen escalonadas, 50 ms cada una.
const BAR_STAGGER_MS = 50

const breakdown = computed(() => opportunity.score_breakdown ?? null)
const rows = computed(() => (breakdown.value ? componentRows(breakdown.value) : []))

const subline = computed(() => compositionSubline(rankText, breakdown.value))
</script>

<template>
  <!-- Para quien quiere auditar el score: sale del botón «Cómo se calcula» de la tarjeta de la
       oportunidad (DossierActions), junto al anillo. -->
  <div class="flex flex-col gap-4">
    <div class="flex flex-col gap-0.5">
      <h2 class="flex items-center gap-1.5 font-display text-lg font-semibold tracking-[-0.02em]">
        Cómo se calcula el {{ formatScore(opportunity.opportunity_score) }}
        <InfoTip label="el desglose" :text="HELP.scoreBreakdown" />
      </h2>
      <span class="text-[13.5px] text-muted-foreground">{{ subline }}</span>
    </div>

    <template v-if="breakdown">
      <div class="flex flex-col gap-3">
        <div v-for="(row, index) in rows" :key="row.name" class="flex items-center gap-3">
          <HoverHint :text="SCORE_COMPONENT_HELP[row.name]">
            <span class="w-[148px] shrink-0 cursor-help text-sm text-label">{{ row.label }}</span>
          </HoverHint>
          <span class="h-1.5 grow overflow-hidden rounded-full bg-track" aria-hidden="true">
            <span
              class="composition-bar block h-full origin-left rounded-full bg-foreground"
              :style="{
                transform: `scaleX(${row.value / SCORE_MAX})`,
                animationDelay: `${index * BAR_STAGGER_MS}ms`,
              }"
            />
          </span>
          <span class="w-14 shrink-0 text-right text-sm font-semibold whitespace-nowrap">
            {{ row.display }}
          </span>
          <span
            class="w-16 shrink-0 text-right text-[13px] whitespace-nowrap text-muted-foreground"
          >
            {{ row.weightLabel }}
          </span>
        </div>
      </div>
      <p class="text-[13px] text-muted-foreground">
        «Poco cubierto todavía» sube cuanto menos contenido parecido hay: hoy, saturación
        {{ formatScore(opportunity.saturation_score) }} de 100 dentro de las fuentes monitoreadas.
      </p>
    </template>
    <p v-else class="text-[15px] text-ink-soft">
      Sin desglose: falta el encaje con la audiencia, así que no hay puntuación de oportunidad.
    </p>
  </div>
</template>

<style scoped>
/* DESIGN.md §7: las barras crecen hasta su valor en 420 ms, solo con `transform`. */
.composition-bar {
  animation: composition-bar-grow 420ms var(--ease-out) backwards;
}

@media (prefers-reduced-motion: reduce) {
  .composition-bar {
    animation: none;
  }
}

@keyframes composition-bar-grow {
  from {
    transform: scaleX(0);
  }
}
</style>
