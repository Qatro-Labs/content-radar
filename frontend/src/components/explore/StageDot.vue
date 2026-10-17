<script setup lang="ts">
import { computed } from 'vue'

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
  <!-- El color nunca va solo (DESIGN.md §4): la etapa también se lee como texto. -->
  <span
    role="img"
    :aria-label="style.label"
    :title="style.label"
    class="size-[9px] shrink-0 rounded-full"
    :style="dotStyle"
  />
</template>
