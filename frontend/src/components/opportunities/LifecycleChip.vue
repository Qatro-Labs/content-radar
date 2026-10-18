<script setup lang="ts">
import { computed } from 'vue'

import HoverHint from '@/components/layout/HoverHint.vue'
import { LIFECYCLE_STYLE } from '@/lib/lifecycle'
import type { Lifecycle } from '@/lib/radarQuery'

// El chip va dentro del tooltip: las clases de quien lo usa van al chip, no al tooltip.
defineOptions({ inheritAttrs: false })
type ChipSize = 'sm' | 'md'

const { lifecycle, size = 'md' } = defineProps<{ lifecycle: Lifecycle; size?: ChipSize }>()

// `md` para el panel y el ranking; `sm` para la tarjeta flotante del radar.
const SIZE_CLASS: Record<ChipSize, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-[13px]',
}

const style = computed(() => LIFECYCLE_STYLE[lifecycle])
const help = computed(() => `${style.value.label}: ${style.value.meaning}`)

const chipColors = computed(() => ({
  backgroundColor: `var(${style.value.cssVar.bg})`,
  color: `var(${style.value.cssVar.fg})`,
}))

const dotColors = computed(() =>
  style.value.dashed
    ? { border: `1.5px dashed var(${style.value.cssVar.stroke})` }
    : { backgroundColor: `var(${style.value.cssVar.fill})` },
)
</script>

<template>
  <HoverHint :text="help">
    <span
      v-bind="$attrs"
      class="inline-flex items-center gap-1.5 rounded-full leading-[1.4] font-semibold whitespace-nowrap"
      :class="SIZE_CLASS[size]"
      :style="chipColors"
    >
      <span class="size-2 shrink-0 rounded-full" :style="dotColors" aria-hidden="true" />
      {{ style.label }}
    </span>
  </HoverHint>
</template>
