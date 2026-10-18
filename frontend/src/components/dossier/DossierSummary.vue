<script setup lang="ts">
import InfoTip from '@/components/layout/InfoTip.vue'
import { HELP } from '@/lib/helpText'
import { computed, ref } from 'vue'

import type { QueryState } from '@/api/opportunities'
import { dossierLimitations } from '@/lib/dossierView'
import { countLabel } from '@/lib/evidenceFormat'
import { formatFit, NOT_AVAILABLE, windowTotals } from '@/lib/opportunityFormat'
import type { components } from '@/types/api'

import { CARD_CLASS, CARD_TITLE_CLASS } from './dossierClasses'

type Schemas = components['schemas']

const { opportunity, timeline } = defineProps<{
  opportunity: Schemas['Opportunity']
  timeline: QueryState<Schemas['OpportunityTimeline'] | null>
}>()

const isWhyOpen = ref(false)

const totals = computed(() => windowTotals(timeline.data?.points ?? []))
const newPieces = computed(() => {
  if (timeline.isPending) return '…'
  return totals.value ? countLabel(totals.value.current, 'pieza', 'piezas') : NOT_AVAILABLE
})
const newPiecesNote = computed(() =>
  totals.value ? `en los últimos 3 días · antes ${totals.value.previous}` : 'nuevas en 3 días',
)
const limitations = computed(() => dossierLimitations(opportunity))

const TILE_CLASS = 'flex min-w-0 flex-[1_1_180px] flex-col gap-0.5 rounded-tile bg-card px-5 py-4'
const TILE_VALUE_CLASS =
  'font-display text-[26px] leading-[1.1] font-semibold tracking-[-0.02em] whitespace-nowrap'
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Resumen en tres cifras: crecimiento, encaje y fuentes. El detalle de cada una sigue abajo. -->
    <div class="flex flex-wrap gap-2">
      <div :class="TILE_CLASS">
        <span :class="TILE_VALUE_CLASS">{{ newPieces }}</span>
        <span class="flex items-center gap-0.5 text-sm text-ink-soft">
          {{ newPiecesNote }}
          <InfoTip label="las piezas nuevas" :text="HELP.tileNewPieces" />
        </span>
      </div>
      <div :class="TILE_CLASS">
        <span :class="TILE_VALUE_CLASS">{{ formatFit(opportunity.audience_fit_score) }}</span>
        <span class="flex items-center gap-0.5 text-sm text-ink-soft">
          encaje con 30X · evaluación editorial
          <InfoTip label="el encaje con 30X" :text="HELP.tileFit" />
        </span>
      </div>
      <div :class="TILE_CLASS">
        <span :class="TILE_VALUE_CLASS">
          {{ countLabel(opportunity.source_count, 'fuente', 'fuentes') }}
        </span>
        <span class="flex items-center gap-0.5 text-sm text-ink-soft">
          un medio o canal cuenta una vez
          <InfoTip label="las fuentes" :text="HELP.tileSources" />
        </span>
      </div>
    </div>

    <div class="flex flex-wrap items-start gap-4">
      <section
        aria-label="Por qué importa"
        :class="[CARD_CLASS, 'flex-[999_1_560px] flex-col gap-2.5']"
      >
        <h2 :class="[CARD_TITLE_CLASS, 'flex items-center gap-1.5']">
          Por qué importa
          <InfoTip label="Por qué importa" :text="HELP.whyItMatters" />
        </h2>
        <p
          class="max-w-[720px] text-[17px] leading-[1.55] text-ink-read"
          :class="{ 'line-clamp-3': !isWhyOpen }"
        >
          {{ opportunity.why_it_matters }}
        </p>
        <button
          type="button"
          :aria-expanded="isWhyOpen"
          class="self-start text-sm font-semibold underline underline-offset-4"
          @click="isWhyOpen = !isWhyOpen"
        >
          {{ isWhyOpen ? 'Ver menos' : 'Leer completo' }}
        </button>
      </section>

      <!-- DESIGN.md §4: «Qué no sabemos» es obligatorio en todo detalle; va arriba, junto a la
           explicación, no al final de la página. -->
      <section
        data-agent="limit"
        aria-label="Qué no sabemos"
        class="flex min-w-0 flex-[1_1_320px] flex-col gap-2 rounded-card bg-notice px-6 py-5"
      >
        <h2 class="flex items-center gap-1 text-[15px] font-semibold text-notice-foreground">
          Qué no sabemos
          <InfoTip label="Qué no sabemos" :text="HELP.limits" />
        </h2>
        <template v-if="limitations.length > 0">
          <!-- Por índice: el LLM puede repetir una limitación y la clave dejaría de ser única. -->
          <p
            v-for="(limitation, index) in limitations"
            :key="index"
            class="text-[14.5px] text-ink-soft"
          >
            {{ limitation }}
          </p>
        </template>
        <p v-else class="text-[14.5px] text-ink-soft">
          No hay limitaciones registradas para este tema.
        </p>
      </section>
    </div>
  </div>
</template>
