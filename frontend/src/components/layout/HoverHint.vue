<script setup lang="ts">
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

// Explicación al pasar el cursor sobre el elemento que envuelve (un chip, un botón, un rótulo).
// El elemento es el disparador (`as-child`), así que no añade otro control.
const { text } = defineProps<{ text: string | null | undefined }>()
</script>

<template>
  <Tooltip v-if="text">
    <TooltipTrigger as-child>
      <slot />
    </TooltipTrigger>
    <TooltipContent>{{ text }}</TooltipContent>
  </Tooltip>
  <slot v-else />
</template>
