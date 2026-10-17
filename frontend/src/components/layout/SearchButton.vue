<script setup lang="ts">
import { Search } from '@lucide/vue'
import { onKeyStroke } from '@vueuse/core'
import { ref } from 'vue'

import { Dialog, DialogTrigger } from '@/components/ui/dialog'

import SearchPalette from './SearchPalette.vue'

const LABEL = 'Buscar tema o pieza'

const open = ref(false)

// ⌘K en Mac y Ctrl+K en el resto. Sin `preventDefault`, Ctrl+K lleva el foco a la barra de
// búsqueda del navegador.
onKeyStroke(['k', 'K'], (event) => {
  if (!event.metaKey && !event.ctrlKey) return
  event.preventDefault()
  open.value = !open.value
})
</script>

<template>
  <Dialog v-model:open="open">
    <!-- Por debajo de 768px solo queda la lupa: el nombre accesible va siempre en aria-label. -->
    <DialogTrigger as-child>
      <button
        type="button"
        :aria-label="LABEL"
        aria-keyshortcuts="Meta+K Control+K"
        class="flex h-11 min-w-11 shrink-0 items-center justify-center gap-2.5 rounded-xl bg-card px-3 text-sm text-muted-foreground transition-colors duration-150 ease-out hover:bg-secondary-hover md:w-[280px] md:shrink"
      >
        <Search class="size-4 shrink-0" :stroke-width="2" aria-hidden="true" />
        <span class="hidden flex-1 truncate text-left md:inline">{{ LABEL }}</span>
        <kbd
          class="hidden rounded-md bg-secondary px-[7px] py-0.5 font-sans text-[12.5px] font-semibold text-label md:inline"
        >
          ⌘K
        </kbd>
      </button>
    </DialogTrigger>
    <SearchPalette v-model:open="open" />
  </Dialog>
</template>
