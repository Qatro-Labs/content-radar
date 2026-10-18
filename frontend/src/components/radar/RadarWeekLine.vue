<script setup lang="ts">
import { computed } from 'vue'

import HoverHint from '@/components/layout/HoverHint.vue'
import InfoTip from '@/components/layout/InfoTip.vue'
import { countLabel } from '@/lib/evidenceFormat'
import { HELP } from '@/lib/helpText'
import { formatScore } from '@/lib/opportunityFormat'
import { describeStageUnknowns, type RadarView } from '@/lib/radarView'
import { RouteName } from '@/router'

const { view, monitoringStartedAt } = defineProps<{
  view: RadarView
  monitoringStartedAt: string
}>()

const emit = defineEmits<{
  select: [id: string]
  hover: [id: string | null]
}>()

// Sin «Publicar ya» no se ofrecen sustitutos: el ranking está al lado (CLAUDE.md §2.3).
const picks = computed(() => (view.weekPicks.hasPublishNow ? view.weekPicks.topics : []))
const outliers = computed(() => ({
  count: countLabel(view.outlierPieces, 'pieza', 'piezas'),
  verb: view.outlierPieces === 1 ? 'rinde' : 'rinden',
}))
const unknownShare = computed(() => `${view.counts.unknown} de ${view.total} sin tendencia clara`)
const unknownDetail = computed(() => describeStageUnknowns(view.ranked, monitoringStartedAt))

const PILL_CLASS =
  'inline-flex min-h-9 items-center gap-1.5 rounded-[10px] px-3 text-[13.5px] transition-colors duration-150 ease-out'
</script>

<template>
  <div class="flex flex-col gap-3">
    <!-- Lo que antes era el panel «Esta semana», en la cabecera: el tema que conviene publicar
         (pulsarlo lo abre al lado del radar), lo que funciona y lo que no sabemos. -->
    <p
      class="flex flex-wrap items-baseline gap-x-1.5 gap-y-1 text-[17px] leading-[1.55] text-ink-soft"
    >
      <template v-if="picks.length > 0">
        <span class="inline-flex items-center gap-1">
          Para publicar ya:
          <InfoTip label="Publicar ya" :text="HELP.weekPublishNow" />
        </span>
        <template v-for="(topic, index) in picks" :key="topic.id">
          <button
            type="button"
            class="font-semibold text-foreground underline decoration-signal decoration-[3px] underline-offset-4 transition-colors duration-150 ease-out hover:decoration-foreground"
            @click="emit('select', topic.id)"
            @mouseenter="emit('hover', topic.id)"
            @mouseleave="emit('hover', null)"
          >
            {{ topic.topic }}
          </button>
          <span
            >({{ formatScore(topic.opportunity_score) }}){{
              index < picks.length - 1 ? ',' : '.'
            }}</span
          >
        </template>
      </template>
      <template v-else>Ningún tema cumple hoy las condiciones de «Publicar ya».</template>
    </p>

    <div class="flex flex-wrap gap-2">
      <HoverHint :text="HELP.outliers">
        <RouterLink
          :to="{ name: RouteName.Explore }"
          :class="[PILL_CLASS, 'bg-card hover:bg-secondary-hover']"
        >
          <span v-if="view.outlierPieces > 0">
            <strong class="font-semibold">{{ outliers.count }}</strong>
            {{ outliers.verb }} 3× o más que lo normal
          </span>
          <span v-else>Ninguna pieza rinde 3× o más que lo normal todavía</span>
          <span class="font-semibold">Ver ›</span>
        </RouterLink>
      </HoverHint>
      <!-- DESIGN.md §4: «Qué no sabemos» siempre a la vista; el detalle, en el tooltip. -->
      <HoverHint :text="unknownDetail">
        <span tabindex="0" :class="[PILL_CLASS, 'cursor-help bg-notice']">
          <strong class="font-semibold text-notice-foreground">Qué no sabemos</strong>
          {{ unknownShare }}
        </span>
      </HoverHint>
    </div>
  </div>
</template>
