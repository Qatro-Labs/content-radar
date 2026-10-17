<script setup lang="ts">
import type { ExploreViewModel, Piece } from '@/lib/exploreView'

import PieceDetail from './PieceDetail.vue'
import WhereItWorks from './WhereItWorks.vue'

const { view, selected } = defineProps<{ view: ExploreViewModel; selected: Piece | null }>()

const emit = defineEmits<{ clear: [] }>()

// DESIGN.md §4 y §7: el panel cambia de estado con fundido y 6px de subida (280ms). Con
// movimiento reducido, aparece sin animación.
const PANEL_ENTER_CLASS =
  'animate-in fade-in slide-in-from-bottom-[6px] animation-duration-[280ms] ease-out motion-reduce:animate-none'
</script>

<template>
  <!-- DESIGN.md §4: sticky, visible mientras se baja por la tabla de piezas. -->
  <aside
    aria-label="Panel de la pieza"
    class="sticky top-4 flex min-w-0 flex-[1_1_360px] flex-col self-start rounded-card bg-card p-[22px]"
  >
    <PieceDetail
      v-if="selected"
      :key="selected.url"
      :piece="selected"
      :class="PANEL_ENTER_CLASS"
      @clear="emit('clear')"
    />
    <WhereItWorks
      v-else
      :top-topics="view.topTopics"
      :top-sources="view.topSources"
      :class="PANEL_ENTER_CLASS"
    />
  </aside>
</template>
