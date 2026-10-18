<script setup lang="ts">
import type { TooltipRootEmits, TooltipRootProps } from 'reka-ui'

import { TooltipRoot, useForwardPropsEmits } from 'reka-ui'

import TooltipProvider from './TooltipProvider.vue'

const props = defineProps<TooltipRootProps>()
const emits = defineEmits<TooltipRootEmits>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <TooltipProvider>
    <!-- Cada tooltip trae su proveedor, como shadcn-vue: funciona en cualquier sitio, también en
         los tests de componentes. -->
    <TooltipRoot data-slot="tooltip" v-bind="forwarded">
      <slot />
    </TooltipRoot>
  </TooltipProvider>
</template>
