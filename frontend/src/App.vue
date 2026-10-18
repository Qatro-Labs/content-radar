<script setup lang="ts">
import { computed } from 'vue'

import AgentDock from '@/components/agent/AgentDock.vue'
import AgentLauncher from '@/components/agent/AgentLauncher.vue'
import AgentPresence from '@/components/agent/AgentPresence.vue'
import type { RadMarkState } from '@/components/agent/RadMark.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useRadarAgent } from '@/composables/useRadarAgent'

const agent = useRadarAgent()
const { turns, status, presence, suggestions, isAvailable, isMinimized, hasUnread } = agent

// La barra es fija y flota sobre la página: el final de la página deja sitio solo para el campo
// (o para el ojo, con la barra reducida), nunca para la conversación entera.
const bottomSpace = computed(() => {
  if (!isAvailable.value) return ''
  return isMinimized.value ? 'pb-20' : 'pb-44'
})

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
    <main class="flex-1" :class="bottomSpace">
      <RouterView />
    </main>
    <!-- Reducir la barra la encoge hacia el ojo de Rad, abajo a la derecha (DESIGN.md §4). -->
    <Transition
      enter-from-class="translate-y-3 scale-[0.98] opacity-0"
      enter-active-class="origin-bottom-right transition duration-[280ms] ease-out motion-reduce:transition-none"
      leave-active-class="origin-bottom-right transition duration-200 ease-out motion-reduce:transition-none"
      leave-to-class="translate-y-3 scale-[0.96] opacity-0"
    >
      <AgentDock
        v-if="isAvailable && !isMinimized"
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
        @minimize="agent.minimize"
      />
    </Transition>
    <Transition
      enter-from-class="scale-50 opacity-0"
      enter-active-class="transition duration-[280ms] ease-[var(--ease-pop)] motion-reduce:transition-none"
      leave-active-class="transition duration-150 ease-out motion-reduce:transition-none"
      leave-to-class="scale-75 opacity-0"
    >
      <AgentLauncher
        v-if="isAvailable && isMinimized"
        :mark
        :has-unread="hasUnread"
        @open="agent.expand"
      />
    </Transition>
    <AgentPresence :presence />
  </div>
</template>
