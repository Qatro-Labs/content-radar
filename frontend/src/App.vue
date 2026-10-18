<script setup lang="ts">
import { useElementBounding, useMouse, usePreferredReducedMotion } from '@vueuse/core'
import { computed, useTemplateRef } from 'vue'
import { useRoute } from 'vue-router'

import AgentDock from '@/components/agent/AgentDock.vue'
import AgentLauncher from '@/components/agent/AgentLauncher.vue'
import AgentPresence from '@/components/agent/AgentPresence.vue'
import type { RadMarkState } from '@/components/agent/RadMark.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import { useRadarAgent } from '@/composables/useRadarAgent'
import { useRadIdleLife } from '@/composables/useRadIdleLife'
import { useRadMorph } from '@/composables/useRadMorph'
import { RouteName } from '@/router/routeNames'

const agent = useRadarAgent()
// El login trae su propia marca: sin la cabecera no se piden datos que, con el login obligatorio,
// la API rechazaría antes de iniciar sesión.
const route = useRoute()
const isLoginPage = computed(() => route.name === RouteName.Login)
const { turns, status, presence, suggestions, isAvailable, isMinimized, hasUnread } = agent

// En reposo, Rad mira el cursor (y de vez en cuando, otro sitio de la página); mientras trabaja,
// mira hacia su presencia. Las coordenadas van relativas a `[data-agent-root]`, como la
// presencia. Con movimiento reducido mira al frente.
const root = useTemplateRef<HTMLElement>('root')
const rootBox = useElementBounding(root)
const cursor = useMouse({ type: 'client' })
const motionPreference = usePreferredReducedMotion()
const life = useRadIdleLife({
  isResting: computed(() => status.value === 'idle'),
  cursor,
  randomGlanceTarget: () => ({
    x: Math.random() * window.innerWidth - rootBox.left.value,
    y: Math.random() * window.innerHeight - rootBox.top.value,
  }),
})
// Al aterrizar tras reducir o abrir la barra, Rad parpadea.
const morph = useRadMorph({ onLanded: life.blink })
const lookAt = computed(() => {
  if (presence.value.visible) return { x: presence.value.x, y: presence.value.y }
  if (motionPreference.value === 'reduce') return null
  if (life.glance.value !== null) return life.glance.value
  if (cursor.sourceType.value === null) return null
  return { x: cursor.x.value - rootBox.left.value, y: cursor.y.value - rootBox.top.value }
})

// La barra es fija y flota sobre la página: el final de la página deja sitio solo para el campo
// (o para el ojo, con la barra reducida), nunca para la conversación entera.
const bottomSpace = computed(() => {
  if (!isAvailable.value) return ''
  return isMinimized.value ? 'pb-20' : 'pb-44'
})

// La marca de Rad refleja lo que hace: se abre en radar mientras trabaja, el haz pasa en cada
// paso de datos, parpadea al terminar (y de vez en cuando en reposo) y mira hacia su presencia o
// hacia el cursor (plan fe-radar-agent, C.2).
const mark = computed<RadMarkState>(() => {
  const latest = turns.value.at(-1)
  return {
    working: status.value !== 'idle',
    scanKey: latest?.steps.filter((step) => step.kind === 'data').length ?? 0,
    blinkKey: turns.value.filter((turn) => turn.status === 'done').length + life.blinks.value,
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
    <AppHeader v-if="!isLoginPage" />
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
