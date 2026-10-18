<script setup lang="ts">
import type { TooltipContentEmits, TooltipContentProps } from 'reka-ui'

import type { HTMLAttributes } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import { cn } from 'cn'
import { TooltipContent, TooltipPortal, useForwardPropsEmits } from 'reka-ui'

defineOptions({
  inheritAttrs: false,
})

const props = withDefaults(
  defineProps<TooltipContentProps & { class?: HTMLAttributes['class'] }>(),
  {
    sideOffset: 6,
  },
)
const emits = defineEmits<TooltipContentEmits>()

const delegatedProps = reactiveOmit(props, 'class')
const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <TooltipPortal>
    <!-- Tema (DESIGN.md §4 y §5): blanca, radio 14 px y la sombra flotante, como la tarjeta
         flotante del radar. -->
    <TooltipContent
      data-slot="tooltip-content"
      v-bind="{ ...$attrs, ...forwarded }"
      :class="
        cn(
          'z-50 max-w-[300px] rounded-tile bg-popover px-3.5 py-2.5 text-[13.5px] leading-[1.45] font-normal text-popover-foreground shadow-float data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=delayed-open]:animate-in data-[state=delayed-open]:fade-in-0 motion-reduce:animate-none',
          props.class,
        )
      "
    >
      <slot />
    </TooltipContent>
  </TooltipPortal>
</template>
