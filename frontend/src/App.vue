<script setup lang="ts">
import { useElementBounding, useMouse, usePreferredReducedMotion } from '@vueuse/core'
import { computed, useTemplateRef } from 'vue'

import AgentDock from '@/components/agent/AgentDock.vue'
import AgentLauncher from '@/components/agent/AgentLauncher.vue'
import AgentPresence from '@/components/agent/AgentPresence.vue'
import type { RadMarkState } from '@/components/agent/RadMark.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useRadarAgent } from '@/composables/useRadarAgent'
import { useRadMorph } from '@/composables/useRadMorph'

const agent = useRadarAgent()
const { turns, status, presence, suggestions, isAvailable, isMinimized, hasUnread } = agent
const morph = useRadMorph()

// En reposo, Rad mira el cursor; mientras trabaja, mira hacia su presencia. Las coordenadas van
// relativas a `[data-agent-root]`, como la presencia. Con movimiento reducido mira al frente.
const root = useTemplateRef<HTMLElement>('root')
const rootBox = useElementBounding(root)
const cursor = useMouse({ type: 'client' })
const motionPreference = usePreferredReducedMotion()
const lookAt = computed(() => {
  if (presence.value.visible) return { x: presence.value.x, y: presence.value.y }
  if (motionPreference.value === 'reduce' || cursor.sourceType.value === null) return null
  return { x: cursor.x.value - rootBox.left.value, y: cursor.y.value - rootBox.top.value }
})

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
    lookAt: lookAt.value,
  }
})
</script>

<template>
  <!-- `data-agent-root`: la presencia de Rad se mide y se coloca respecto a este contenedor. -->
  <div
    ref="root"
    data-agent-root
    class="relative mx-auto flex min-h-[100dvh] max-w-[1440px] flex-col gap-6 px-4 py-4 md:px-8 md:py-6"
  >
    <AppHeader />
    <main class="flex-1" :class="bottomSpace">
      <RouterView />
    </main>
    <!-- Reducir la barra: el ojo de Rad sale volando de ella hasta la esquina; abrirla, vuelve
         (useRadMorph, DESIGN.md §4). -->
    <Transition :css="false" @enter="morph.onDockEnter" @leave="morph.onDockLeave">
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
    <Transition :css="false" @enter="morph.onEyeEnter" @leave="morph.onEyeLeave">
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
