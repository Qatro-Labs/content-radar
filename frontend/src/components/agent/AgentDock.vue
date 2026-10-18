<script setup lang="ts">
import type { AgentStatus, AgentTurnView } from '@/lib/agentTypes'

import AgentComposer from './AgentComposer.vue'
import AgentTranscript from './AgentTranscript.vue'
import type { RadMarkState } from './RadMark.vue'

const { turns, status, suggestions, mark } = defineProps<{
  turns: AgentTurnView[]
  status: AgentStatus
  suggestions: string[]
  mark: RadMarkState
}>()

const emit = defineEmits<{
  ask: [question: string]
  stop: []
  newConversation: []
  selectCited: [id: string]
  copyLink: []
  askFromAssistant: [question: string]
  minimize: []
}>()
</script>

<template>
  <!-- DESIGN.md §4 y §5: la barra flota sobre la página (fija, fuera del flujo: la conversación no
       deja un hueco vacío al final de la página) y por eso lleva la sombra flotante.
       `data-agent-dock` marca dónde acaba el hueco visible para la presencia. -->
  <section
    data-agent-dock
    aria-label="Rad, el agente del Radar"
    class="fixed inset-x-4 bottom-4 z-40 mx-auto flex max-w-[840px] flex-col gap-3 rounded-card bg-card p-4 shadow-float md:bottom-6"
  >
    <AgentTranscript
      v-if="turns.length > 0"
      :turns
      @new-conversation="emit('newConversation')"
      @select-cited="(id) => emit('selectCited', id)"
      @copy-link="emit('copyLink')"
      @ask-from-assistant="(question) => emit('askFromAssistant', question)"
    />
    <AgentComposer
      :busy="status !== 'idle'"
      :suggestions
      :mark
      @ask="(question) => emit('ask', question)"
      @stop="emit('stop')"
      @minimize="emit('minimize')"
    />
  </section>
</template>
