<script lang="ts">
export interface CitationView {
  name: string
  isChecked: boolean
}
</script>

<script setup lang="ts">
import { Check } from '@lucide/vue'

import {
  BONE_DRAW_MS,
  BONE_LEAD_MS,
  BONE_STAGGER_MS,
  DRAFT_ENTER_DELAY_MS,
  DRAFT_SKETCH,
} from '@/lib/briefStages'
import { TEXT_ENTER_CLASS } from '@/lib/motion'

// Vacío hasta que empieza la comprobación de citas.
const { citations } = defineProps<{ citations: readonly CitationView[] }>()

// Nace cuando Rad ya ha absorbido las piezas que ocupaban su sitio.
const enterStyle = { animationDelay: `${DRAFT_ENTER_DELAY_MS}ms` }

// Los huesos se dibujan de izquierda a derecha, escalonados a lo largo de todas las secciones, y
// después laten como cualquier skeleton (DESIGN.md §4) hasta que llega el brief.
const sections = DRAFT_SKETCH.map((section, sectionIndex) => {
  const before = DRAFT_SKETCH.slice(0, sectionIndex).reduce(
    (total, previous) => total + previous.bones.length,
    0,
  )
  return {
    ...section,
    bones: section.bones.map((width, boneIndex) => ({
      width: `${width}%`,
      '--bone-delay': `${BONE_LEAD_MS + (before + boneIndex) * BONE_STAGGER_MS}ms`,
      '--bone-draw': `${BONE_DRAW_MS}ms`,
    })),
  }
})
</script>

<template>
  <!-- El brief no existe hasta que responde la API: el borrador lleva las secciones reales y
       huesos de tinta en lugar de palabras (CLAUDE.md §2.3). -->
  <div
    data-generating-draft
    aria-hidden="true"
    :class="[
      TEXT_ENTER_CLASS,
      'flex flex-col gap-4 rounded-tile bg-sunken p-5 fill-mode-backwards',
    ]"
    :style="enterStyle"
  >
    <div v-for="section in sections" :key="section.label" class="flex flex-col gap-2">
      <span class="text-[13px] font-semibold text-label">{{ section.label }}</span>
      <span
        v-for="(bone, index) in section.bones"
        :key="index"
        class="brief-bone block rounded-full bg-track"
        :class="section.isTall ? 'h-5' : 'h-3.5'"
        :style="bone"
      />
    </div>
    <ul v-if="citations.length > 0" :class="[TEXT_ENTER_CLASS, 'flex flex-wrap gap-1.5']">
      <li
        v-for="citation in citations"
        :key="citation.name"
        class="relative isolate inline-flex h-7 items-center gap-1.5 rounded-lg bg-card px-2.5 text-[13px] font-semibold text-foreground"
      >
        <!-- Comprobada: la lima entra como un rotulador, con `scaleX` (DESIGN.md §7). -->
        <span
          class="brief-cite-fill absolute inset-0 -z-10 rounded-lg bg-signal"
          :class="{ 'is-checked': citation.isChecked }"
        />
        <span class="relative flex size-3 items-center justify-center">
          <span
            class="size-1.5 rounded-full bg-window-empty transition-opacity duration-200 ease-out"
            :class="{ 'opacity-0': citation.isChecked }"
          />
          <Check
            class="brief-cite-tick absolute size-3"
            :class="{ 'is-checked': citation.isChecked }"
            :stroke-width="3.4"
          />
        </span>
        {{ citation.name }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.brief-bone {
  transform-origin: left;
  animation:
    brief-bone-draw var(--bone-draw) var(--ease-out) var(--bone-delay) both,
    brief-bone-pulse 1.6s ease-in-out calc(var(--bone-delay) + var(--bone-draw)) infinite;
}

.brief-cite-fill {
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 300ms var(--ease-out);
}

.brief-cite-tick {
  opacity: 0;
  transform: scale(0.4);
  transition:
    opacity 240ms var(--ease-out),
    transform 240ms var(--ease-out);
}

.brief-cite-fill.is-checked,
.brief-cite-tick.is-checked {
  opacity: 1;
  transform: none;
}

@media (prefers-reduced-motion: reduce) {
  .brief-bone {
    animation: none;
  }

  .brief-cite-fill,
  .brief-cite-tick {
    transition: none;
  }
}

/* El mismo latido que SkeletonBone: de Pista a Lienzo en 1,6 s. */
@keyframes brief-bone-pulse {
  50% {
    background-color: var(--background);
  }
}

@keyframes brief-bone-draw {
  from {
    transform: scaleX(0);
  }
  to {
    transform: none;
  }
}
</style>
