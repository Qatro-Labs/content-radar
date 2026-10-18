<script lang="ts">
// `scanKey` cambia en cada paso de datos (una pasada del haz) y `blinkKey` al terminar cada
// pregunta (un parpadeo). `lookAt` va en coordenadas de `[data-agent-root]`, como la presencia.
export interface RadMarkState {
  working: boolean
  scanKey: number
  blinkKey: number
  lookAt: { x: number; y: number } | null
}

// Fuera de <script setup>: el valor por defecto de `size` se iza fuera de setup().
const DEFAULT_SIZE_PX = 40
</script>

<script setup lang="ts">
import { computed, onMounted, ref, useTemplateRef, watch } from 'vue'

interface Point {
  x: number
  y: number
}

const { state, size = DEFAULT_SIZE_PX } = defineProps<{ state: RadMarkState; size?: number }>()

// Artboard «Rad», opción C: radio de 11 px a 40 px, y las proporciones del ojo y del radar en
// unidades del viewBox (40 × 40).
const CORNER_RADIUS_RATIO = 0.275
const RESTING_SCLERA_SCALE_Y = 0.58
const RING_RADII = [8.6, 4.6]
const HIDDEN_RINGS_SCALE = 0.6
const WORKING_IRIS_SCALE = 0.48
const GAZE_REACH = 3.2
// Como un ojo de verdad: lo cercano se mira de reojo; a partir de esta distancia, hasta el borde.
const GAZE_FULL_REACH_PX = 160
// A menos de 1 px, la presencia está encima de la marca: mira al frente.
const GAZE_DEAD_ZONE_PX = 1
const LOOK_AHEAD: Point = { x: 0, y: 0 }

const mark = useTemplateRef<HTMLElement>('mark')
const gaze = ref<Point>(LOOK_AHEAD)

function gazeToward(lookAt: RadMarkState['lookAt']): Point {
  const element = mark.value
  const agentRoot = element?.closest('[data-agent-root]')
  if (lookAt === null || !element || !agentRoot) return LOOK_AHEAD
  const own = element.getBoundingClientRect()
  const origin = agentRoot.getBoundingClientRect()
  const dx = lookAt.x - (own.left - origin.left + own.width / 2)
  const dy = lookAt.y - (own.top - origin.top + own.height / 2)
  const distance = Math.hypot(dx, dy)
  if (distance < GAZE_DEAD_ZONE_PX) return LOOK_AHEAD
  const reach = GAZE_REACH * Math.min(1, distance / GAZE_FULL_REACH_PX)
  return { x: (dx / distance) * reach, y: (dy / distance) * reach }
}

function updateGaze() {
  gaze.value = gazeToward(state.lookAt)
}

onMounted(updateGaze)
watch(() => state.lookAt, updateGaze, { deep: true })

const containerStyle = computed(() => ({
  width: `${size}px`,
  height: `${size}px`,
  borderRadius: `${size * CORNER_RADIUS_RATIO}px`,
}))
// Un parpadeo al terminar, nunca mientras trabaja; una pasada del haz por cada paso de datos.
const isBlinking = computed(() => state.blinkKey > 0 && !state.working)
const isScanning = computed(() => state.working && state.scanKey > 0)
</script>

<template>
  <span ref="mark" aria-hidden="true" class="flex shrink-0 bg-primary" :style="containerStyle">
    <svg viewBox="0 0 40 40" :width="size" :height="size">
      <g :key="state.blinkKey" class="rad-layer" :class="{ 'rad-blink': isBlinking }">
        <g
          class="rad-layer"
          :style="{ transform: `scaleY(${state.working ? 1 : RESTING_SCLERA_SCALE_Y})` }"
        >
          <circle
            cx="20"
            cy="20"
            r="13"
            class="fill-none stroke-signal"
            stroke-width="2"
            vector-effect="non-scaling-stroke"
          />
        </g>
        <g
          class="rad-layer"
          :style="{
            opacity: state.working ? 1 : 0,
            transform: `scale(${state.working ? 1 : HIDDEN_RINGS_SCALE})`,
          }"
        >
          <circle
            v-for="radius in RING_RADII"
            :key="radius"
            cx="20"
            cy="20"
            :r="radius"
            class="fill-none stroke-signal"
            stroke-width="1"
            stroke-opacity="0.55"
            vector-effect="non-scaling-stroke"
          />
        </g>
        <g :key="state.scanKey" class="rad-layer rad-beam" :class="{ 'rad-sweep': isScanning }">
          <path
            d="M20 20 L20 7 A13 13 0 0 1 29.96 11.64 Z"
            class="fill-signal"
            fill-opacity="0.32"
          />
          <path d="M20 20 L29.96 11.64" class="stroke-signal" stroke-width="1.5" />
        </g>
        <g
          data-testid="rad-gaze"
          class="rad-layer rad-gaze"
          :style="{ transform: `translate(${gaze.x}px, ${gaze.y}px)` }"
        >
          <g
            class="rad-layer"
            :style="{ transform: `scale(${state.working ? WORKING_IRIS_SCALE : 1})` }"
          >
            <circle cx="20" cy="20" r="5.2" class="fill-signal" />
          </g>
          <g data-testid="rad-pupil" class="rad-layer" :style="{ opacity: state.working ? 0 : 1 }">
            <circle cx="20" cy="20" r="2.2" class="fill-foreground" />
          </g>
        </g>
      </g>
    </svg>
  </span>
</template>

<style scoped>
/* Artboard «Rad»: cada capa gira, escala o se funde sobre el centro del viewBox, solo con
   `transform` y `opacity` (DESIGN.md §7). */
.rad-layer {
  transform-box: view-box;
  transform-origin: 20px 20px;
  transition:
    transform 380ms var(--ease-out),
    opacity 380ms var(--ease-out);
}

.rad-beam {
  opacity: 0;
}

/* La pupila sigue al cursor: más rápida que el resto de capas para que no parezca que se arrastra. */
.rad-gaze {
  transition-duration: 160ms;
}

/* DESIGN.md §7: sin bucles. Una sola pasada por paso de datos y un solo parpadeo al terminar. */
.rad-sweep {
  animation: rad-sweep 1100ms linear both;
}

.rad-blink {
  animation: rad-blink 320ms ease-in-out;
}

@media (prefers-reduced-motion: reduce) {
  .rad-layer {
    transition: none;
  }

  .rad-sweep,
  .rad-blink {
    animation: none;
  }
}

@keyframes rad-sweep {
  0% {
    opacity: 1;
    transform: rotate(0deg);
  }
  85% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    transform: rotate(360deg);
  }
}

@keyframes rad-blink {
  0%,
  100% {
    transform: scaleY(1);
  }
  50% {
    transform: scaleY(0.08);
  }
}
</style>
