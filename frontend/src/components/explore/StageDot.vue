<script setup lang="ts">
import { computed } from 'vue'

import HoverHint from '@/components/layout/HoverHint.vue'
import { LIFECYCLE_STYLE } from '@/lib/lifecycle'
import type { Lifecycle } from '@/lib/radarQuery'

const { lifecycle } = defineProps<{ lifecycle: Lifecycle }>()

const style = computed(() => LIFECYCLE_STYLE[lifecycle])

// DESIGN.md §2: con el trazo de la etapa, el punto Acelerando se distingue sobre blanco; "Sin
// etapa" va hueco y con trazo discontinuo.
const dotStyle = computed(() => ({
  border: `1.5px ${style.value.dashed ? 'dashed' : 'solid'} var(${style.value.cssVar.stroke})`,
  backgroundColor: style.value.dashed ? 'transparent' : `var(${style.value.cssVar.fill})`,
}))
</script>

<template>
  <!-- El color nunca va solo (DESIGN.md §4): la etapa se lee en el nombre accesible y, al pasar
       el cursor, con lo que significa. -->
  <HoverHint :text="`${style.label}: ${style.meaning}`">
    <span
      role="img"
      :aria-label="style.label"
      class="size-[9px] shrink-0 cursor-help rounded-full"
      :style="dotStyle"
    />
  </HoverHint>
</template>
