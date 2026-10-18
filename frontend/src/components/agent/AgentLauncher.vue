<script setup lang="ts">
import { computed } from 'vue'

import RadMark, { type RadMarkState } from './RadMark.vue'

const { mark, hasUnread } = defineProps<{ mark: RadMarkState; hasUnread: boolean }>()

const emit = defineEmits<{ open: [] }>()

const LAUNCHER_SIZE_PX = 56

const label = computed(() => (hasUnread ? 'Abrir Rad: hay una respuesta nueva' : 'Abrir Rad'))
</script>

<template>
  <!-- DESIGN.md §4: con la barra reducida, Rad queda como su ojo flotando abajo a la derecha. Sigue
       vivo: se abre en radar mientras trabaja y mira hacia su presencia. Es el ancla «composer» de
       la presencia mientras la barra está reducida. -->
  <button
    type="button"
    data-agent="composer"
    :aria-label="label"
    class="group fixed right-4 bottom-4 z-40 rounded-[16px] shadow-float transition-transform duration-150 ease-out hover:scale-[1.04] active:scale-[0.96] motion-reduce:transition-none md:right-8 md:bottom-6"
    @click="emit('open')"
  >
    <RadMark :state="mark" :size="LAUNCHER_SIZE_PX" />
    <span
      v-if="hasUnread"
      class="absolute -top-1 -right-1 size-3.5 rounded-full bg-signal ring-2 ring-card"
      aria-hidden="true"
    />
    <span
      class="pointer-events-none absolute top-1/2 right-[calc(100%+12px)] -translate-y-1/2 rounded-[10px] bg-primary px-2.5 py-1 text-[13px] font-semibold whitespace-nowrap text-primary-foreground opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100"
      aria-hidden="true"
    >
      {{ hasUnread ? 'Rad respondió' : 'Pregúntale a Rad' }}
    </span>
  </button>
</template>
