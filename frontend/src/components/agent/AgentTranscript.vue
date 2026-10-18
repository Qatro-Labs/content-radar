<script setup lang="ts">
import { nextTick, useTemplateRef, watch } from 'vue'

import type { AgentTurnView } from '@/lib/agentTypes'

import AgentTurn from './AgentTurn.vue'

const { turns } = defineProps<{ turns: AgentTurnView[] }>()

const emit = defineEmits<{
  newConversation: []
  selectCited: [id: string]
  copyLink: []
  askFromAssistant: [question: string]
}>()

const scroller = useTemplateRef<HTMLElement>('scroller')

// Los pasos y las palabras llegan abajo: la transcripción los sigue. Asignar `scrollTop` respeta
// `scroll-smooth`, que solo se aplica sin movimiento reducido.
watch(
  () => turns.at(-1),
  async () => {
    await nextTick()
    const element = scroller.value
    if (element) element.scrollTop = element.scrollHeight
  },
  { deep: true },
)
</script>

<template>
  <!-- La cabecera queda fuera del scroll para que «Nueva conversación» esté siempre a mano. -->
  <div class="flex max-h-[46vh] flex-col">
    <div class="flex shrink-0 justify-end">
      <button
        type="button"
        class="flex min-h-10 items-center text-sm text-muted-foreground underline underline-offset-4 transition-colors duration-150 ease-out hover:text-foreground"
        @click="emit('newConversation')"
      >
        Nueva conversación
      </button>
    </div>

    <!-- El margen de 4 px deja sitio al anillo de foco (DESIGN.md §4), que el scroll recortaría. -->
    <div
      ref="scroller"
      class="-mx-1 flex min-h-0 flex-col gap-6 overflow-y-auto px-1 pt-1 pb-4 motion-safe:scroll-smooth"
    >
      <AgentTurn
        v-for="(turn, index) in turns"
        :key="turn.id"
        :turn
        :collapsed="index < turns.length - 1"
        @select-cited="(id) => emit('selectCited', id)"
        @copy-link="emit('copyLink')"
        @ask-from-assistant="(question) => emit('askFromAssistant', question)"
      />
    </div>
  </div>
</template>
