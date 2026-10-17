<script setup lang="ts">
import { usePreferredReducedMotion } from '@vueuse/core'
import { computed, nextTick, ref, useTemplateRef, watch } from 'vue'

import type { QueryState } from '@/api/opportunities'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import {
  ALL_PLATFORMS,
  filterByPlatform,
  type PlatformFilter,
  platformCounts,
  rowEmphasis,
} from '@/lib/dossierView'
import { countLabel, EVIDENCE_LIMIT, PERFORMANCE_LEGEND, VELOCITY_NOTE } from '@/lib/evidenceFormat'
import type { components } from '@/types/api'

import AudienceMixBar from './AudienceMixBar.vue'
import { CARD_CLASS, CARD_TITLE_CLASS, SECONDARY_BUTTON_CLASS } from './dossierClasses'
import EvidenceRow from './EvidenceRow.vue'

type Schemas = components['schemas']

const { opportunity, evidence, citedUrl } = defineProps<{
  opportunity: Schemas['Opportunity']
  evidence: QueryState<Schemas['Evidence'][]>
  citedUrl: string | null
}>()

const emit = defineEmits<{ retry: [] }>()

const SKELETON_ROWS = 4

const pieces = computed(() => evidence.data ?? [])
const platform = ref<PlatformFilter>(ALL_PLATFORMS)
const segments = computed(() => platformCounts(pieces.value))
const shown = computed(() => filterByPlatform(pieces.value, platform.value))
const isCapped = computed(() => pieces.value.length >= EVIDENCE_LIMIT)

const list = useTemplateRef<HTMLElement>('list')
const reducedMotion = usePreferredReducedMotion()

function scrollToPiece(url: string) {
  const rows = list.value?.querySelectorAll<HTMLElement>('[data-evidence-url]') ?? []
  const row = Array.from(rows).find((element) => element.dataset.evidenceUrl === url)
  row?.scrollIntoView({
    block: 'center',
    behavior: reducedMotion.value === 'reduce' ? 'auto' : 'smooth',
  })
}

// D11: citar una pieza quita el filtro de plataforma para que su fila esté en la lista.
watch(
  () => citedUrl,
  async (url) => {
    if (url === null) return
    platform.value = ALL_PLATFORMS
    await nextTick()
    scrollToPiece(url)
  },
)
</script>

<template>
  <section
    data-agent="dossier-evidence"
    aria-label="Evidencia"
    :class="[CARD_CLASS, 'flex-col gap-4']"
  >
    <div class="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
      <div class="flex flex-col gap-2.5">
        <div class="flex flex-col gap-0.5">
          <h2 :class="CARD_TITLE_CLASS">Evidencia</h2>
          <span v-if="evidence.data" class="text-sm text-muted-foreground">
            {{ countLabel(shown.length, 'pieza', 'piezas') }} · outliers primero
          </span>
        </div>
        <div
          v-if="pieces.length > 0"
          role="group"
          aria-label="Plataforma"
          class="flex flex-wrap gap-0.5 self-start rounded-xl bg-secondary p-1"
        >
          <button
            v-for="segment in segments"
            :key="segment.platform"
            type="button"
            :aria-pressed="platform === segment.platform"
            class="min-h-9 rounded-[9px] px-3.5 text-sm transition-colors duration-150 ease-out"
            :class="
              platform === segment.platform
                ? 'bg-card font-semibold text-foreground'
                : 'font-medium text-label hover:text-foreground'
            "
            @click="platform = segment.platform"
          >
            {{ segment.label }} · {{ segment.count }}
          </button>
        </div>
      </div>
      <AudienceMixBar :opportunity class="flex-[0_1_420px]" />
    </div>

    <div v-if="evidence.isPending" class="flex flex-col gap-2" aria-busy="true">
      <SkeletonBone v-for="row in SKELETON_ROWS" :key="row" class="h-24 rounded-tile" />
    </div>

    <div v-else-if="evidence.isError" class="flex flex-wrap items-center gap-x-4 gap-y-3 py-2">
      <p role="alert" class="text-[15px] text-ink-soft">No se pudo cargar la evidencia.</p>
      <button type="button" :class="SECONDARY_BUTTON_CLASS" @click="emit('retry')">
        Reintentar
      </button>
    </div>

    <p v-else-if="pieces.length === 0" class="text-[15px] text-ink-soft">
      Este tema no tiene piezas en la evidencia servida.
    </p>

    <template v-else>
      <div ref="list" class="flex flex-col gap-2">
        <EvidenceRow
          v-for="(piece, index) in shown"
          :key="piece.url"
          :evidence="piece"
          :emphasis="rowEmphasis(piece.url, citedUrl)"
          :index
        />
      </div>
      <div class="flex flex-col gap-1 text-[13.5px] text-muted-foreground">
        <p>{{ PERFORMANCE_LEGEND }} {{ VELOCITY_NOTE }}</p>
        <p v-if="isCapped">Se muestran las {{ EVIDENCE_LIMIT }} primeras piezas del tema.</p>
      </div>
    </template>
  </section>
</template>
