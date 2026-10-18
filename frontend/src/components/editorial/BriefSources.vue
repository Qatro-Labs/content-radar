<script setup lang="ts">
import { computed } from 'vue'

import type { QueryState } from '@/api/opportunities'
import { CARD_CLASS, CARD_TITLE_CLASS } from '@/components/dossier/dossierClasses'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { featuredPieces, featuredRatioLabel } from '@/lib/briefView'
import { PLATFORM_LABEL } from '@/lib/evidenceFormat'
import { formatUtcDay } from '@/lib/format'
import { formatFit } from '@/lib/opportunityFormat'
import type { components } from '@/types/api'

type Schemas = components['schemas']

const { opportunity, evidence } = defineProps<{
  opportunity: Schemas['Opportunity']
  evidence: QueryState<Schemas['Evidence'][]>
}>()

const SKELETON_PIECES = 3

const pieces = computed(() => featuredPieces(evidence.data ?? []))
</script>

<template>
  <!-- Antes de generar, la vista ya enseña algo real: con qué piezas se escribirá el brief. -->
  <section aria-label="Con qué se escribirá" :class="[CARD_CLASS, 'flex-col gap-4']">
    <div class="flex flex-col gap-1.5">
      <h2 :class="CARD_TITLE_CLASS">Con qué se escribirá</h2>
      <p class="text-[15px] text-ink-soft">
        Las piezas que mejor rinden frente a lo normal en su canal. Encaje con 30X:
        {{ formatFit(opportunity.audience_fit_score) }}.
      </p>
    </div>

    <template v-if="evidence.isPending">
      <SkeletonBone v-for="piece in SKELETON_PIECES" :key="piece" class="h-[72px] rounded-tile" />
    </template>
    <p v-else-if="evidence.isError" role="alert" class="text-[15px] text-ink-soft">
      No se pudo cargar la evidencia. El brief se puede generar igual.
    </p>
    <p v-else-if="pieces.length === 0" class="text-[15px] text-ink-soft">
      Este tema no tiene piezas en la evidencia servida.
    </p>
    <a
      v-for="piece in pieces"
      v-else
      :key="piece.url"
      :href="piece.url"
      target="_blank"
      rel="noopener noreferrer"
      class="flex items-center gap-4 rounded-tile bg-sunken px-[18px] py-3.5 transition-colors duration-150 ease-out hover:bg-secondary-hover"
    >
      <span class="flex min-w-0 grow flex-col gap-1">
        <span class="text-[13.5px] text-label">
          <span class="font-semibold text-ink-read">{{ PLATFORM_LABEL[piece.platform] }}</span>
          · {{ piece.source }} · {{ formatUtcDay(piece.published_at) }}
        </span>
        <!-- Texto externo: interpolado, nunca como HTML (CLAUDE.md §2.6). -->
        <span class="text-base leading-[1.35] font-semibold">{{ piece.title }}</span>
      </span>
      <!-- DESIGN.md §4: badge de outlier en Lima señal con texto Tinta. -->
      <span
        v-if="featuredRatioLabel(piece)"
        class="shrink-0 rounded-lg px-2.5 py-1 text-[13px] font-semibold"
        :class="
          piece.is_outlier === true ? 'bg-signal text-signal-foreground' : 'bg-card text-ink-read'
        "
      >
        {{ featuredRatioLabel(piece) }}
      </span>
    </a>
  </section>
</template>
