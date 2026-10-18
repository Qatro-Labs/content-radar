<script setup lang="ts">
import { computed } from 'vue'

import type { QueryState } from '@/api/opportunities'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { featuredPieces, featuredPiecesCaption } from '@/lib/briefView'
import { outlierBadge } from '@/lib/evidenceFormat'
import { PLATFORM_LABEL } from '@/lib/evidenceFormat'
import { formatUtcDay } from '@/lib/format'
import type { components } from '@/types/api'

const { evidence } = defineProps<{ evidence: QueryState<components['schemas']['Evidence'][]> }>()

const SKELETON_PIECES = 3
const TITLE = 'Con qué lo escribirá'

const pieces = computed(() => featuredPieces(evidence.data ?? []))
const caption = computed(() => {
  const total = evidence.data?.length ?? 0
  return total === 0 ? TITLE : `${TITLE} · ${featuredPiecesCaption(total)}`
})
</script>

<template>
  <!-- Antes de generar, la tarjeta ya enseña algo real: con qué piezas se escribirá el brief. -->
  <div class="flex flex-col gap-2.5">
    <h3 class="text-sm font-semibold text-label">{{ caption }}</h3>

    <template v-if="evidence.isPending">
      <SkeletonBone v-for="piece in SKELETON_PIECES" :key="piece" class="h-[66px] rounded-tile" />
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
      class="flex items-center gap-3.5 rounded-tile bg-sunken px-3.5 py-3 transition-colors duration-150 ease-out hover:bg-secondary-hover"
    >
      <span class="flex min-w-0 grow flex-col gap-0.5">
        <span class="text-[13px] text-label">
          <span class="font-semibold text-ink-read">{{ PLATFORM_LABEL[piece.platform] }}</span>
          · {{ piece.source }} · {{ formatUtcDay(piece.published_at) }}
        </span>
        <!-- Texto externo: interpolado, nunca como HTML (CLAUDE.md §2.6). -->
        <span class="text-[15px] leading-[1.3] font-semibold">{{ piece.title }}</span>
      </span>
      <!-- DESIGN.md §4: badge de outlier en Lima señal con texto Tinta. -->
      <span
        v-if="outlierBadge(piece)"
        class="shrink-0 rounded-lg bg-signal px-2.5 py-1 text-[13px] font-semibold whitespace-nowrap text-signal-foreground"
      >
        {{ outlierBadge(piece) }}
      </span>
    </a>
  </div>
</template>
