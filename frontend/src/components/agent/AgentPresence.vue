<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { AGENT_TIMING } from '@/lib/agentMotion'
import type { PresenceView, RingBox } from '@/lib/agentTypes'

const { presence } = defineProps<{ presence: PresenceView }>()

// DESIGN.md §4: punto de 16 px y rótulo a 14 px de él.
const DOT_SIZE_PX = 16
const LABEL_GAP_PX = 14
const LABEL_OFFSET = `${DOT_SIZE_PX + LABEL_GAP_PX}px`

// El anillo guarda su última caja: al desaparecer se funde donde estaba en lugar de saltar.
const lastRing = ref<RingBox | null>(null)
watch(
  () => presence.ring,
  (ring) => {
    if (ring) lastRing.value = ring
  },
  { immediate: true },
)

const isRingShown = computed(() => presence.visible && presence.ring !== null)

// DESIGN.md §7: solo se anima `transform`. Un salto (primera aparición o movimiento reducido)
// no tiene transición.
function transitionOf(properties: string[], durationMs: number): string {
  if (presence.instant) return 'none'
  return properties.map((property) => `${property} ${durationMs}ms var(--ease-out)`).join(', ')
}

const markerStyle = computed(() => ({
  transform: `translate(${presence.x - DOT_SIZE_PX / 2}px, ${presence.y - DOT_SIZE_PX / 2}px)`,
  opacity: presence.visible ? 1 : 0,
  transition: transitionOf(['transform'], AGENT_TIMING.travelMs),
}))

const labelStyle = computed(() =>
  presence.labelOnLeft ? { right: LABEL_OFFSET } : { left: LABEL_OFFSET },
)

// El tamaño y el radio cambian sin transición; solo se desliza la posición.
function ringStyle(box: RingBox) {
  const durationMs = isRingShown.value ? AGENT_TIMING.ringMs : AGENT_TIMING.ringFadeMs
  return {
    width: `${box.width}px`,
    height: `${box.height}px`,
    borderRadius: `${box.radius}px`,
    transform: `translate(${box.x}px, ${box.y}px)`,
    opacity: isRingShown.value ? 1 : 0,
    transition: transitionOf(['transform', 'opacity'], durationMs),
  }
}
</script>

<template>
  <!-- Recorta lo que sobresale (un rótulo largo junto al borde): la página no hace scroll
       horizontal (DESIGN.md §6). -->
  <div class="pointer-events-none absolute inset-0 z-50 overflow-hidden" aria-hidden="true">
    <span
      v-if="lastRing"
      class="absolute top-0 left-0 border-2 border-foreground"
      :style="ringStyle(lastRing)"
    />

    <div class="absolute top-0 left-0 size-4" :style="markerStyle">
      <span
        v-if="presence.tapCount > 0"
        :key="presence.tapCount"
        class="presence-tap absolute inset-0 rounded-full border-2 border-foreground"
        :style="{ animationDuration: `${AGENT_TIMING.tapMs}ms` }"
      />
      <span class="absolute inset-0 rounded-full bg-signal shadow-float ring-2 ring-foreground" />
      <!-- Como mucho 320 px: cabe en el margen en el que el rótulo cambia de lado
           (LABEL_FLIP_MARGIN_PX) y una etiqueta larga con el nombre del tema no se sale. -->
      <span
        v-if="presence.label"
        class="absolute top-1/2 max-w-[320px] -translate-y-1/2 truncate rounded-[10px] bg-primary px-2.5 py-1 text-[13px] font-semibold text-primary-foreground"
        :style="labelStyle"
      >
        {{ presence.label }}
      </span>
    </div>
  </div>
</template>

<style scoped>
/* DESIGN.md §4: al pulsar algo, la presencia deja una onda de Tinta. Sin movimiento, no hay onda. */
.presence-tap {
  opacity: 0;
  animation-name: presence-tap;
  animation-timing-function: var(--ease-out);
  animation-fill-mode: forwards;
}

@media (prefers-reduced-motion: reduce) {
  .presence-tap {
    animation: none;
  }
}

@keyframes presence-tap {
  from {
    opacity: 0.5;
    transform: scale(1);
  }
  to {
    opacity: 0;
    transform: scale(2.4);
  }
}
</style>
