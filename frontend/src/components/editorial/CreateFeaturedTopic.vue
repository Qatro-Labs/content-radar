<script setup lang="ts">
import { ArrowRight } from '@lucide/vue'
import { computed } from 'vue'

import { useOpportunityEvidence } from '@/api/opportunities'
import RadMark, { type RadMarkState } from '@/components/agent/RadMark.vue'
import {
  CARD_CLASS,
  PRIMARY_BUTTON_CLASS,
  SECONDARY_BUTTON_CLASS,
} from '@/components/dossier/dossierClasses'
import LifecycleChip from '@/components/opportunities/LifecycleChip.vue'
import RecommendationChip from '@/components/opportunities/RecommendationChip.vue'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { BRIEF_PARAM, featuredPieces } from '@/lib/briefView'
import { featuredSummary, featuredTiles, morePiecesLine } from '@/lib/createPicker'
import { outlierBadge } from '@/lib/evidenceFormat'
import { PLATFORM_LABEL } from '@/lib/evidenceFormat'
import { formatUtcDay } from '@/lib/format'
import { cn } from '@/lib/utils'
import { isDescending } from '@/lib/lifecycle'
import { RouteName } from '@/router'
import type { components } from '@/types/api'

const { opportunity, note } = defineProps<{
  opportunity: components['schemas']['Opportunity']
  // "El único tema en «Publicar ya» esta semana": lo calcula quien conoce la lista entera.
  note: string
}>()

// Marca pequeña y quieta: aquí Rad no trabaja, solo firma lo que va a escribir.
const RAD_MARK_SIZE_PX = 28
const RESTING_MARK: RadMarkState = { working: false, scanKey: 0, blinkKey: 0, lookAt: null }
const SKELETON_PIECES = 3

const evidenceQuery = useOpportunityEvidence(() => opportunity.id)

const summary = computed(() => featuredSummary(opportunity))
const tiles = computed(() => featuredTiles(opportunity))
const pieces = computed(() => featuredPieces(evidenceQuery.data.value ?? []))
const moreLine = computed(() =>
  morePiecesLine(evidenceQuery.data.value?.length ?? 0, pieces.value.length),
)
</script>

<template>
  <section
    :aria-label="`Para escribir ya: ${opportunity.topic}`"
    :class="[CARD_CLASS, 'flex-wrap gap-7']"
  >
    <div class="flex min-w-0 flex-[999_1_520px] flex-col gap-4">
      <div class="flex flex-wrap items-center gap-2">
        <RecommendationChip :recommendation="opportunity.recommendation" size="sm" />
        <LifecycleChip
          :lifecycle="opportunity.lifecycle"
          :descending="isDescending(opportunity)"
          :title="opportunity.lifecycle_reason"
        />
        <span class="text-sm text-muted-foreground">{{ note }}</span>
      </div>
      <h2
        class="font-display text-[clamp(1.75rem,3.5vw,2.375rem)] leading-[1.05] font-semibold tracking-[-0.03em]"
      >
        {{ opportunity.topic }}
      </h2>
      <p v-if="summary" class="line-clamp-3 max-w-[620px] text-base leading-[1.55] text-ink-read">
        {{ summary }}
      </p>

      <div class="flex flex-wrap gap-2">
        <div
          v-for="tile in tiles"
          :key="tile.label"
          class="flex min-w-[120px] flex-col gap-0.5 rounded-tile bg-sunken px-4 py-3"
        >
          <span
            class="font-display leading-[1.1] font-semibold tracking-[-0.02em] whitespace-nowrap"
            :class="{
              'text-[26px]': !tile.isMissing,
              'text-lg text-muted-foreground': tile.isMissing,
              'text-destructive': tile.isNegative,
            }"
          >
            {{ tile.value }}
          </span>
          <span class="text-[13px] text-label">{{ tile.label }}</span>
        </div>
      </div>

      <div class="flex flex-wrap gap-2.5 pt-1">
        <RouterLink
          :to="{ name: RouteName.Create, query: { [BRIEF_PARAM.opportunity]: opportunity.id } }"
          :class="cn(PRIMARY_BUTTON_CLASS, 'min-h-12 gap-2 px-5')"
        >
          Crear brief de este tema
          <ArrowRight class="size-4" aria-hidden="true" />
        </RouterLink>
        <RouterLink
          :to="{ name: RouteName.Dossier, params: { id: opportunity.id } }"
          :class="cn(SECONDARY_BUTTON_CLASS, 'min-h-12 px-[18px]')"
        >
          Ver expediente
        </RouterLink>
      </div>
    </div>

    <!-- Antes de pedir nada, la tarjeta ya enseña con qué se escribirá: las piezas que mejor
         rinden frente a su canal. -->
    <div class="flex min-w-0 flex-[1_1_360px] flex-col gap-2.5">
      <div class="flex items-center gap-2.5">
        <RadMark :state="RESTING_MARK" :size="RAD_MARK_SIZE_PX" />
        <span class="text-[15px] font-semibold">Rad escribirá con estas piezas</span>
      </div>

      <template v-if="evidenceQuery.isPending.value">
        <SkeletonBone v-for="piece in SKELETON_PIECES" :key="piece" class="h-[68px] rounded-tile" />
      </template>
      <p v-else-if="evidenceQuery.isError.value" role="alert" class="text-[15px] text-ink-soft">
        No se pudo cargar la evidencia. El brief se puede crear igual.
      </p>
      <p v-else-if="pieces.length === 0" class="text-[15px] text-ink-soft">
        Este tema no tiene piezas en la evidencia servida.
      </p>
      <template v-else>
        <a
          v-for="piece in pieces"
          :key="piece.url"
          :href="piece.url"
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-center gap-3.5 rounded-tile bg-sunken px-3.5 py-3 transition-colors duration-150 ease-out hover:bg-secondary-hover"
        >
          <span class="flex min-w-0 flex-1 flex-col gap-[3px]">
            <span class="text-[13px] text-label">
              <span class="font-semibold text-ink-read">{{ PLATFORM_LABEL[piece.platform] }}</span>
              · {{ piece.source }} · {{ formatUtcDay(piece.published_at) }}
            </span>
            <!-- Texto externo: interpolado, nunca como HTML (CLAUDE.md §2.6). -->
            <span class="text-[15px] leading-[1.3] font-semibold">{{ piece.title }}</span>
          </span>
          <span
            v-if="outlierBadge(piece)"
            class="shrink-0 rounded-lg bg-signal px-[9px] py-[3px] text-[13px] font-semibold text-signal-foreground"
          >
            {{ outlierBadge(piece) }}
          </span>
        </a>
        <span v-if="moreLine" class="pl-0.5 text-[13px] text-muted-foreground">
          {{ moreLine }}
        </span>
      </template>
    </div>
  </section>
</template>
