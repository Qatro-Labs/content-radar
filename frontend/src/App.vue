<script setup lang="ts">
import { computed } from 'vue'

import AgentDock from '@/components/agent/AgentDock.vue'
import AgentPresence from '@/components/agent/AgentPresence.vue'
import type { RadMarkState } from '@/components/agent/RadMark.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useRadarAgent } from '@/composables/useRadarAgent'

const agent = useRadarAgent()
const { turns, status, presence, suggestions, isAvailable } = agent

// La marca de Rad refleja lo que hace: se abre en radar mientras trabaja, el haz pasa en cada
// paso de datos, parpadea al terminar y mira hacia donde está su presencia (plan fe-radar-agent,
// C.2).
const mark = computed<RadMarkState>(() => {
  const latest = turns.value.at(-1)
  return {
    working: status.value !== 'idle',
    scanKey: latest?.steps.filter((step) => step.kind === 'data').length ?? 0,
    blinkKey: turns.value.filter((turn) => turn.status === 'done').length,
    lookAt: presence.value.visible ? { x: presence.value.x, y: presence.value.y } : null,
  }
})
</script>

<template>
  <!-- `data-agent-root`: la presencia de Rad se mide y se coloca respecto a este contenedor. -->
  <div
    data-agent-root
    class="relative mx-auto flex min-h-[100dvh] max-w-[1440px] flex-col gap-6 px-4 py-4 md:px-8 md:py-6"
  >
    <AppHeader />
    <main class="flex-1">
      <RouterView />
    </main>
    <AgentDock
      v-if="isAvailable"
      :turns
      :status
      :suggestions
      :mark
      @ask="agent.ask"
      @stop="agent.stop"
      @new-conversation="agent.newConversation"
      @select-cited="agent.selectCited"
      @copy-link="agent.copyViewLink"
      @ask-from-assistant="agent.askFromAssistant"
    />
    <AgentPresence :presence />
  </div>
</template>
