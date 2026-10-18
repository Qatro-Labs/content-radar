<script setup lang="ts">
import { computed } from 'vue'

import PerformanceBar from '@/components/evidence/PerformanceBar.vue'
import type { RowEmphasis } from '@/lib/dossierView'
import { formatMetrics, formatVelocity, PLATFORM_LABEL, SEGMENT_LABEL } from '@/lib/evidenceFormat'
import { formatUtcDay } from '@/lib/format'
import type { components } from '@/types/api'

import { SEGMENT_SWATCH_CLASS } from './dossierClasses'

const { evidence, emphasis, index } = defineProps<{
  evidence: components['schemas']['Evidence']
  emphasis: RowEmphasis
  index: number
}>()

// DESIGN.md §7: las filas entran escalonadas, 40 ms cada una.
const ROW_STAGGER_MS = 40
const ROW_ENTER_CLASS =
  'animate-in fade-in slide-in-from-bottom-[6px] animation-duration-[420ms] ease-out fill-mode-backwards motion-reduce:animate-none'

// D11: la pieza citada en lavado de señal (como la fila seleccionada del ranking) y el resto a 0.4.
const EMPHASIS_CLASS: Record<RowEmphasis, string> = {
  cited: 'bg-signal/18',
  dimmed: 'bg-sunken opacity-40',
  none: 'bg-sunken',
}

const metrics = computed(() => formatMetrics(evidence.metrics))
const velocity = computed(() => formatVelocity(evidence.velocity))
</script>

<template>
  <article
    :data-evidence-url="evidence.url"
    class="flex flex-wrap items-center gap-x-8 gap-y-3 rounded-tile px-[18px] py-4 transition-[background-color,opacity] duration-[320ms] ease-out motion-reduce:transition-none"
    :class="[EMPHASIS_CLASS[emphasis], ROW_ENTER_CLASS]"
    :style="{ animationDelay: `${index * ROW_STAGGER_MS}ms` }"
  >
    <div class="flex min-w-0 flex-[1_1_520px] flex-col gap-1.5">
      <p class="flex flex-wrap items-center gap-x-1.5 text-[13.5px] text-label">
        <span class="font-semibold text-ink-read">{{ PLATFORM_LABEL[evidence.platform] }}</span>
        · {{ evidence.source }} · {{ formatUtcDay(evidence.published_at) }} ·
        <span class="inline-flex items-center gap-1.5">
          <span
            class="size-[9px] shrink-0 rounded-[3px]"
            :class="SEGMENT_SWATCH_CLASS[evidence.segment]"
            aria-hidden="true"
          />
          {{ SEGMENT_LABEL[evidence.segment] }}
        </span>
      </p>
      <!-- Texto externo: se pinta con interpolación, nunca como HTML (CLAUDE.md §2, regla 6). -->
      <a
        :href="evidence.url"
        target="_blank"
        rel="noopener noreferrer"
        class="text-base leading-[1.35] font-semibold text-foreground hover:underline"
      >
        {{ evidence.title }}
      </a>
      <p class="text-[13.5px]" :class="metrics ? 'text-ink-soft' : 'text-muted-foreground'">
        {{ metrics ?? 'Métricas: no disponible' }}
      </p>
    </div>

    <!-- El rótulo «Frente a lo normal en su canal» va una vez, en la cabecera de la sección, y la
         velocidad ausente se dice allí (EvidenceSection): aquí solo se escribe la que existe. -->
    <div class="flex min-w-[240px] flex-[0_1_300px] flex-col gap-1.5">
      <PerformanceBar :evidence />
      <span v-if="velocity" class="text-sm font-medium text-ink-read">{{ velocity }}</span>
    </div>
  </article>
</template>
