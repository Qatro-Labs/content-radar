<script setup lang="ts">
import { CircleHelp } from '@lucide/vue'

import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

// `label` nombra lo que se explica para los lectores de pantalla: «Qué es Publicar ya».
const { text, label } = defineProps<{ text: string; label: string }>()
</script>

<template>
  <!-- Ayuda junto a un rótulo: un icono enfocable con teclado que abre la explicación al pasar
       el cursor o al enfocarlo. No va dentro de otro botón (HTML no anida controles): ahí se usa
       `HoverHint`. -->
  <Tooltip>
    <TooltipTrigger
      type="button"
      :aria-label="`Qué es ${label}`"
      class="inline-flex size-5 shrink-0 cursor-help items-center justify-center rounded-full align-middle text-muted-foreground transition-colors duration-150 ease-out hover:text-foreground"
      @click.stop.prevent
    >
      <CircleHelp class="size-3.5" :stroke-width="2" aria-hidden="true" />
    </TooltipTrigger>
    <TooltipContent>{{ text }}</TooltipContent>
  </Tooltip>
</template>
