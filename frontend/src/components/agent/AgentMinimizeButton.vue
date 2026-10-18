<script setup lang="ts">
import { Minus } from '@lucide/vue'

import HoverHint from '@/components/layout/HoverHint.vue'
import { HELP } from '@/lib/helpText'

const emit = defineEmits<{ minimize: [] }>()
</script>

<template>
  <!-- La barra se reduce al ojo de Rad para no tapar la página; la conversación se conserva. -->
  <HoverHint :text="HELP.minimizeRad">
    <button
      type="button"
      aria-label="Minimizar Rad"
      class="flex size-8 shrink-0 items-center justify-center rounded-[10px] text-ink-soft transition-[background-color,scale] duration-150 ease-out hover:bg-secondary active:scale-[0.96]"
      @click="emit('minimize')"
    >
      <Minus class="size-4" :stroke-width="2" aria-hidden="true" />
    </button>
  </HoverHint>
</template>
