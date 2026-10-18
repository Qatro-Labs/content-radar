<script setup lang="ts">
import { ChevronRight } from '@lucide/vue'
import { computed } from 'vue'

import { componentRows, compositionSubline } from '@/lib/dossierView'
import { formatScore, SCORE_MAX } from '@/lib/opportunityFormat'
import type { components } from '@/types/api'

import { CARD_CLASS } from './dossierClasses'

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
  <!-- Para quien quiere auditar el score, no para decidir: va al final y plegado. El anillo está en
       la cabecera (DossierActions), que enlaza aquí. -->
  <details
    id="como-se-calcula"
    aria-label="Cómo se calcula la oportunidad"
    :class="[CARD_CLASS, 'group flex-col gap-[18px]']"
  >
    <summary
      class="flex cursor-pointer list-none flex-wrap items-center gap-x-3 gap-y-1 [&::-webkit-details-marker]:hidden"
    >
      <ChevronRight
        class="size-5 text-muted-foreground transition-transform duration-200 ease-out group-open:rotate-90 motion-reduce:transition-none"
        aria-hidden="true"
      />
      <h2 class="font-display text-xl font-semibold tracking-[-0.02em]">
        Cómo se calcula el {{ formatScore(opportunity.opportunity_score) }}
      </h2>
      <span class="text-sm text-muted-foreground">{{ subline }}</span>
    </summary>

    <template v-if="breakdown">
      <div class="flex flex-col gap-3">
        <div v-for="(row, index) in rows" :key="row.name" class="flex items-center gap-3">
          <span class="w-[156px] shrink-0 text-sm text-label">{{ row.label }}</span>
          <span class="h-1.5 grow overflow-hidden rounded-full bg-track" aria-hidden="true">
            <span
              class="composition-bar block h-full origin-left rounded-full bg-foreground"
              :style="{
                transform: `scaleX(${row.value / SCORE_MAX})`,
                animationDelay: `${index * BAR_STAGGER_MS}ms`,
              }"
            />
          </span>
          <span class="w-[72px] shrink-0 text-right text-sm font-semibold whitespace-nowrap">
            {{ row.display }}
          </span>
          <span
            class="w-16 shrink-0 text-right text-[13px] whitespace-nowrap text-muted-foreground"
          >
            {{ row.weightLabel }}
          </span>
        </div>
      </div>
      <p class="text-[13.5px] text-muted-foreground">
        «Poco cubierto todavía» sube cuanto menos contenido parecido hay: hoy, saturación
        {{ formatScore(opportunity.saturation_score) }} de 100 dentro de las fuentes monitoreadas.
      </p>
    </template>
    <p v-else class="text-[15px] text-ink-soft">
      Sin desglose: falta el encaje con la audiencia, así que no hay puntuación de oportunidad.
    </p>
  </details>
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
