<script setup lang="ts">
import { nextTick, onMounted, ref, useTemplateRef, watch } from 'vue'

import type { AgentTurnView } from '@/lib/agentTypes'

import AgentTurn from './AgentTurn.vue'

const { turns } = defineProps<{ turns: AgentTurnView[] }>()

const emit = defineEmits<{
  selectCited: [id: string]
  copyLink: []
  askFromAssistant: [question: string]
  peekCited: [id: string | null]
}>()

const scroller = useTemplateRef<HTMLElement>('scroller')
// Al abrirse (también con «Ver respuesta») empieza abajo, en la última respuesta, sin recorrer
// la conversación: el scroll suave solo acompaña lo que llega después.
const followsSmoothly = ref(false)

function scrollToEnd() {
  const element = scroller.value
  if (element) element.scrollTop = element.scrollHeight
}

onMounted(() => {
  scrollToEnd()
  followsSmoothly.value = true
})

// Los pasos y las palabras llegan abajo: la transcripción los sigue. Asignar `scrollTop` respeta
// `scroll-smooth`, que solo se aplica sin movimiento reducido.
watch(
  () => turns.at(-1),
  async () => {
    await nextTick()
    scrollToEnd()
  },
  { deep: true },
)
</script>

<template>
  <!-- El margen de 4 px deja sitio al anillo de foco (DESIGN.md §4), que el scroll recortaría. -->
  <div
    ref="scroller"
    class="-mx-1 flex max-h-[46vh] min-h-0 flex-col gap-6 overflow-y-auto px-1 pt-1 pb-4"
    :class="{ 'motion-safe:scroll-smooth': followsSmoothly }"
  >
    <AgentTurn
      v-for="(turn, index) in turns"
      :key="turn.id"
      :turn
      :collapsed="index < turns.length - 1"
      @select-cited="(id) => emit('selectCited', id)"
      @copy-link="emit('copyLink')"
      @ask-from-assistant="(question) => emit('askFromAssistant', question)"
      @peek-cited="(id) => emit('peekCited', id)"
    />
  </div>
</template>
