<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { LIFECYCLE_STYLE } from '@/lib/lifecycle'
import { formatScore } from '@/lib/opportunityFormat'
import {
  bubblePosition,
  detectionDelayMs,
  shownBubbleSize,
  translateTo,
  type PlotPoint,
  type PlotSize,
} from '@/lib/radarChart'
import { hasAudienceFit, type PlottedOpportunity, type RankedOpportunity } from '@/lib/radarView'

import RadarFloatingCard from './RadarFloatingCard.vue'

const {
  selected,
  hovered,
  size,
  sweeping,
  hoverCard = true,
} = defineProps<{
  selected: RankedOpportunity | null
  hovered: RankedOpportunity | null
  size: PlotSize
  sweeping: boolean
  // `false`: el hover marca la burbuja sin su tarjeta flotante.
  hoverCard?: boolean
}>()

// DESIGN.md §7: tres ondas del trazo de la etapa, separadas 160 ms.
const PING_WAVES = [0, 1, 2]
const PING_STAGGER_MS = 160
// Un instante después de que el haz detecte la burbuja, cuando ya empieza a aparecer.
const AFTER_DETECTION_MS = 50
// DESIGN.md §7: la mira, las lecturas, los anillos y la tarjeta se deslizan en 320 ms, solo con
// `transform`; el centrado va en `translate`, aparte, y sigue al diámetro sin deslizarse.
const SLIDE = 'transition-transform duration-[320ms] ease-out motion-reduce:transition-none'
// DESIGN.md §8: anillo de Tinta de 2 px separado por 2 px de blanco.
const RING = 'absolute top-0 left-0 z-[3] -translate-1/2 rounded-full ring-2 ring-offset-2'
const READING =
  'absolute z-[3] rounded-[6px] bg-primary px-1.5 py-px text-xs font-semibold whitespace-nowrap text-primary-foreground'

interface Spot {
  opportunity: PlottedOpportunity
  point: PlotPoint
  diameter: number
}

// Una oportunidad sin encaje (seleccionada desde el ranking) no tiene burbuja que marcar.
function spotOf(opportunity: RankedOpportunity | null): Spot | null {
  if (!opportunity || !hasAudienceFit(opportunity) || size.width === 0 || size.height === 0) {
    return null
  }
  const focus = { selectedId: selected?.id ?? null, hoveredId: hovered?.id ?? null }
  return {
    opportunity,
    point: bubblePosition(opportunity, size),
    diameter: shownBubbleSize(opportunity, focus),
  }
}

// El radar se remonta con cada barrido (al cargar y cuando Rad empieza a leer datos). Una selección que
// llega mientras el haz barre (`?selected=` al cargar) espera a que detecte su burbuja
// (DESIGN.md §7): la mira, las lecturas, el anillo y el ping. Fuera del barrido responde al
// instante; sin esto, la primera selección tras el barrido también esperaba.
const waitsForSweep = ref(sweeping)
watch(
  () => selected?.id,
  () => {
    waitsForSweep.value = sweeping
  },
)
const entryClass = computed(() => ({ 'radar-entry': waitsForSweep.value }))

function ringBox({ point, diameter }: Spot) {
  return { width: `${diameter}px`, height: `${diameter}px`, transform: translateTo(point) }
}

const layout = computed(() => {
  const spot = spotOf(selected)
  if (!spot) return null
  const { x, y } = spot.point
  const delayMs = waitsForSweep.value ? detectionDelayMs(spot.opportunity) + AFTER_DETECTION_MS : 0
  const entry = { animationDelay: `${delayMs}ms` }
  return {
    spot,
    delayMs,
    horizontal: { ...entry, transform: `translateY(${y}px) scaleX(${x / size.width})` },
    vertical: {
      ...entry,
      transform: `${translateTo(spot.point)} scaleY(${(size.height - y) / size.height})`,
    },
    momentumReading: { ...entry, transform: `translateY(calc(${y}px - 50%))` },
    fitReading: { ...entry, transform: `translateX(calc(${x}px - 50%))` },
    ring: { ...entry, ...ringBox(spot) },
    pingColor: `var(${LIFECYCLE_STYLE[spot.opportunity.lifecycle].cssVar.stroke})`,
  }
})

// DESIGN.md §7: la tarjeta flotante sigue al cursor, no a la selección. La seleccionada ya lleva
// su anillo y su tema está en el panel lateral: sobre ella no hay anillo de hover ni tarjeta.
const hoverSpot = computed(() => (hovered?.id === selected?.id ? null : spotOf(hovered)))
</script>

<template>
  <div class="pointer-events-none absolute inset-0" aria-hidden="true">
    <template v-if="layout">
      <span
        class="absolute top-0 left-0 z-[1] h-px w-full origin-left bg-foreground/28"
        :class="[SLIDE, entryClass]"
        :style="layout.horizontal"
      />
      <span
        class="absolute top-0 left-0 z-[1] h-full w-px origin-top bg-foreground/28"
        :class="[SLIDE, entryClass]"
        :style="layout.vertical"
      />
      <span
        :class="[READING, SLIDE, entryClass, 'top-0 right-[calc(100%+4px)]']"
        :style="layout.momentumReading"
      >
        {{ formatScore(layout.spot.opportunity.momentum_score) }}
      </span>
      <span
        :class="[READING, SLIDE, entryClass, 'top-[calc(100%+5px)] left-0']"
        :style="layout.fitReading"
      >
        {{ formatScore(layout.spot.opportunity.audience_fit_score) }}
      </span>
      <span :class="[RING, SLIDE, entryClass, 'ring-foreground']" :style="layout.ring" />
      <div
        :key="layout.spot.opportunity.id"
        class="absolute top-0 left-0 z-[3]"
        :style="{ transform: translateTo(layout.spot.point) }"
      >
        <span
          v-for="wave in PING_WAVES"
          :key="wave"
          class="radar-ping"
          :style="{
            width: `${layout.spot.diameter}px`,
            height: `${layout.spot.diameter}px`,
            borderColor: layout.pingColor,
            animationDelay: `${layout.delayMs + wave * PING_STAGGER_MS}ms`,
          }"
        />
      </div>
    </template>
    <template v-if="hoverSpot">
      <span :class="[RING, SLIDE, 'ring-foreground/30']" :style="ringBox(hoverSpot)" />
      <RadarFloatingCard
        v-if="hoverCard"
        :opportunity="hoverSpot.opportunity"
        :point="hoverSpot.point"
        class="absolute top-0 left-0 z-[4]"
      />
    </template>
  </div>
</template>

<style scoped>
/* DESIGN.md §7: tres ondas de 1,1 s que se escalan ×4,6. Sin movimiento, no hay ping. */
.radar-ping {
  position: absolute;
  top: 0;
  left: 0;
  translate: -50% -50%;
  border: 1.5px solid;
  border-radius: 9999px;
  opacity: 0;
  animation: radar-ping 1100ms cubic-bezier(0.2, 0.6, 0.35, 1) forwards;
}

.radar-entry {
  animation: radar-entry 260ms var(--ease-out) both;
}

@media (prefers-reduced-motion: reduce) {
  .radar-ping,
  .radar-entry {
    animation: none;
  }
}

@keyframes radar-ping {
  from {
    opacity: 0.75;
    transform: scale(1);
  }
  to {
    opacity: 0;
    transform: scale(4.6);
  }
}

@keyframes radar-entry {
  from {
    opacity: 0;
  }
}
</style>
