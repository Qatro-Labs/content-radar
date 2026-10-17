<script setup lang="ts">
import { computed } from 'vue'

import { useRadarQuery } from '@/composables/useRadarQuery'
import { LIFECYCLE_STYLE } from '@/lib/lifecycle'
import { LIFECYCLES, type Lifecycle } from '@/lib/radarQuery'
import type { RadarView } from '@/lib/radarView'

const props = defineProps<{ view: RadarView }>()

const { query, update } = useRadarQuery()

const SEGMENT_CLASS =
  'flex min-h-9 items-center gap-[7px] rounded-[9px] px-3 text-sm font-medium text-ink-soft transition duration-150 ease-out hover:text-foreground active:scale-[0.98] aria-pressed:bg-card aria-pressed:font-semibold aria-pressed:text-foreground'

// Los resaltados también atenúan el radar, así que cuentan como vista cambiada y se
// restablecen con los filtros (artboard E).
const isViewChanged = computed(() => props.view.isFiltered || query.value.highlight.length > 0)

// El punto repite el color de la burbuja: la fila de filtros hace de leyenda del radar.
function stageDotStyle(lifecycle: Lifecycle) {
  const { cssVar, dashed } = LIFECYCLE_STYLE[lifecycle]
  return {
    backgroundColor: dashed ? 'transparent' : `var(${cssVar.fill})`,
    borderColor: `var(${cssVar.stroke})`,
    borderStyle: dashed ? 'dashed' : 'solid',
  }
}

function toggleStage(lifecycle: Lifecycle) {
  const stages = query.value.lifecycle
  const next = stages.includes(lifecycle)
    ? stages.filter((stage) => stage !== lifecycle)
    : [...stages, lifecycle]
  update({ lifecycle: next })
}

function resetView() {
  update({ lifecycle: [], gap: false, highlight: [] })
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-x-3 gap-y-2.5">
    <div
      role="group"
      aria-label="Filtrar por etapa"
      class="flex flex-wrap gap-0.5 rounded-lg bg-input p-1"
    >
      <button
        v-for="lifecycle in LIFECYCLES"
        :key="lifecycle"
        type="button"
        :data-agent="`filter-lc-${lifecycle}`"
        :aria-pressed="query.lifecycle.includes(lifecycle)"
        :class="SEGMENT_CLASS"
        @click="toggleStage(lifecycle)"
      >
        <span
          aria-hidden="true"
          class="size-[9px] shrink-0 rounded-full border-[1.5px]"
          :style="stageDotStyle(lifecycle)"
        />
        {{ LIFECYCLE_STYLE[lifecycle].label }}
      </button>
    </div>

    <div role="group" aria-label="Filtrar por hueco en LATAM" class="flex rounded-lg bg-input p-1">
      <button
        type="button"
        data-agent="filter-gap"
        :aria-pressed="query.gap"
        :class="SEGMENT_CLASS"
        @click="update({ gap: !query.gap })"
      >
        Hueco en LATAM
      </button>
    </div>

    <Transition
      enter-from-class="translate-y-1 opacity-0"
      enter-active-class="transition duration-300 ease-out motion-reduce:transition-none"
    >
      <div v-if="isViewChanged" class="ml-auto flex items-center gap-3">
        <span class="text-[13px] text-muted-foreground">Filtros activos</span>
        <button
          type="button"
          class="min-h-11 rounded-lg bg-card px-4 text-sm font-semibold transition duration-150 ease-out hover:bg-[#e8eaed] active:scale-[0.98]"
          @click="resetView"
        >
          Restablecer vista
        </button>
      </div>
    </Transition>
  </div>
</template>
