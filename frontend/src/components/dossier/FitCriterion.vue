<script setup lang="ts">
import { ChevronRight } from '@lucide/vue'
import { computed } from 'vue'

import { type CitationChip, CRITERION_LABEL } from '@/lib/dossierView'
import type { components } from '@/types/api'

const { criterion, chips, citedUrl } = defineProps<{
  criterion: components['schemas']['AudienceFitCriterion']
  chips: CitationChip[]
  citedUrl: string | null
}>()

const emit = defineEmits<{ cite: [url: string | null] }>()

// La rúbrica del LLM va de 0 a 5 (CLAUDE.md §7).
const LEVEL_MAX = 5
const segments = computed(() =>
  Array.from({ length: LEVEL_MAX }, (_, index) => index < criterion.level),
)

// Pulsar la pieza ya resaltada quita el resaltado (D11).
function toggle(url: string) {
  emit('cite', citedUrl === url ? null : url)
}
</script>

<template>
  <!-- Plegado: una línea por criterio; la justificación del LLM y sus citas se abren a demanda. -->
  <details class="group border-t border-table-line first:border-t-0">
    <summary
      class="flex min-h-12 cursor-pointer list-none flex-wrap items-center justify-between gap-x-4 gap-y-1.5 rounded-lg px-1 py-2 transition-colors duration-150 ease-out hover:bg-sunken [&::-webkit-details-marker]:hidden"
    >
      <h3 class="flex items-center gap-2 text-[15.5px] font-semibold">
        <ChevronRight
          class="size-4 text-muted-foreground transition-transform duration-200 ease-out group-open:rotate-90 motion-reduce:transition-none"
          aria-hidden="true"
        />
        {{ CRITERION_LABEL[criterion.criterion] }}
      </h3>
      <span class="flex items-center gap-2.5">
        <span class="flex gap-[3px]" role="img" :aria-label="`${criterion.level} de ${LEVEL_MAX}`">
          <span
            v-for="(filled, index) in segments"
            :key="index"
            class="h-1.5 w-[22px] rounded-full"
            :class="filled ? 'bg-foreground' : 'bg-track'"
          />
        </span>
        <span class="w-10 text-right text-[13.5px] font-semibold text-ink-soft" aria-hidden="true">
          {{ criterion.level }} de {{ LEVEL_MAX }}
        </span>
      </span>
    </summary>
    <div class="flex flex-col gap-2 pt-1 pb-4 pl-7">
      <p class="max-w-[720px] text-[14.5px] text-ink-read">{{ criterion.justification }}</p>
      <div v-if="chips.length > 0" class="flex flex-wrap items-center gap-1.5">
        <span class="text-[13px] text-muted-foreground">Se apoya en</span>
        <!-- Una cita que no está entre las piezas servidas no tiene fila que resaltar. Por índice:
           el LLM puede citar la misma pieza dos veces. -->
        <button
          v-for="(chip, index) in chips"
          :key="index"
          type="button"
          :disabled="!chip.isInEvidence"
          :aria-pressed="chip.isInEvidence ? citedUrl === chip.url : undefined"
          class="min-h-9 rounded-lg px-2.5 text-[13px] font-semibold transition-colors duration-150 ease-out disabled:text-muted-foreground"
          :class="
            citedUrl === chip.url
              ? 'bg-signal text-signal-foreground'
              : 'bg-secondary enabled:hover:bg-secondary-hover'
          "
          @click="toggle(chip.url)"
        >
          {{ chip.label }}
        </button>
      </div>
      <p v-else class="text-[13px] text-muted-foreground">Sin piezas citadas</p>
    </div>
  </details>
</template>
