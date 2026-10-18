<script setup lang="ts">
import { ArrowUpRight } from '@lucide/vue'
import { computed } from 'vue'

import {
  briefFootnote,
  briefPoints,
  HOOK_MISSING,
  NO_LIMITATIONS,
  WHY_IT_FITS_MISSING,
} from '@/lib/briefView'
import type { components } from '@/types/api'

import BriefResultHeader from './BriefResultHeader.vue'

const { brief } = defineProps<{ brief: components['schemas']['EditorialBrief'] }>()

const emit = defineEmits<{ edit: [] }>()

// DESIGN.md §7: los bloques del resultado entran escalonados 80 ms, con fundido y 4 px de subida,
// como el final de una respuesta de Rad.
const BLOCK_STAGGER_MS = 80
const BLOCK_ENTER_CLASS =
  'animate-in fade-in slide-in-from-bottom-1 duration-300 ease-out fill-mode-backwards motion-reduce:animate-none'
const SECTION_LABEL_CLASS = 'text-sm font-semibold text-label'

function enter(order: number) {
  return { animationDelay: `${order * BLOCK_STAGGER_MS}ms` }
}

const points = computed(() => briefPoints(brief))
</script>

<template>
  <!-- Todo el texto viene del LLM y de las fuentes: se pinta con interpolación, nunca como HTML
       (CLAUDE.md §2.6). Sin `overflow` en la tarjeta: rompería la cabecera pegada. -->
  <section aria-label="Brief generado" class="flex min-w-0 flex-col rounded-card bg-card">
    <BriefResultHeader :brief @edit="emit('edit')" />

    <div class="flex flex-col gap-[26px] p-6 sm:px-7 sm:pb-7">
      <!-- El gancho primero: es lo que se publica tal cual. -->
      <div :class="BLOCK_ENTER_CLASS" :style="enter(0)" class="flex flex-col gap-2">
        <h3 :class="SECTION_LABEL_CLASS">Gancho</h3>
        <p
          v-if="brief.hook"
          class="font-display text-[clamp(1.375rem,3.4vw,1.75rem)] leading-[1.25] font-semibold tracking-[-0.02em] text-pretty"
        >
          «{{ brief.hook }}»
        </p>
        <p v-else class="text-[15px] text-muted-foreground">{{ HOOK_MISSING }}</p>
      </div>

      <div :class="BLOCK_ENTER_CLASS" :style="enter(1)" class="flex flex-col gap-2">
        <h3 :class="SECTION_LABEL_CLASS">Ángulo</h3>
        <p class="max-w-[720px] text-[17px] leading-[1.6] text-ink-read">{{ brief.angle }}</p>
      </div>

      <div :class="BLOCK_ENTER_CLASS" :style="enter(2)" class="flex flex-col gap-2.5">
        <h3 :class="SECTION_LABEL_CLASS">Estructura</h3>
        <!-- Por índice: el LLM puede repetir un paso y la clave dejaría de ser única. -->
        <ol class="flex flex-col gap-2">
          <li
            v-for="(step, index) in brief.structure"
            :key="index"
            class="flex gap-3 text-base leading-[1.5] text-ink-read"
          >
            <span class="w-[18px] shrink-0 font-semibold text-muted-foreground">{{
              index + 1
            }}</span>
            {{ step }}
          </li>
        </ol>
      </div>

      <div :class="BLOCK_ENTER_CLASS" :style="enter(3)" class="flex flex-col gap-2.5">
        <h3 :class="SECTION_LABEL_CLASS">Puntos clave · cada uno con la pieza que lo respalda</h3>
        <div
          v-for="(point, index) in points"
          :key="index"
          class="flex flex-col gap-2.5 rounded-tile bg-sunken px-[18px] py-3.5"
        >
          <p class="text-base leading-[1.5] text-ink-read">{{ point.text }}</p>
          <div class="flex flex-wrap gap-1.5">
            <a
              v-for="chip in point.chips"
              :key="chip.url"
              :href="chip.url"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex min-h-8 items-center gap-1 rounded-lg bg-card px-2.5 text-[13px] font-semibold text-ink-read transition-colors duration-150 ease-out hover:bg-secondary-hover"
            >
              {{ chip.label }}
              <ArrowUpRight class="size-3.5 text-muted-foreground" aria-hidden="true" />
            </a>
          </div>
        </div>
      </div>

      <div :class="BLOCK_ENTER_CLASS" :style="enter(4)" class="flex flex-col gap-2">
        <h3 :class="SECTION_LABEL_CLASS">Por qué encaja con 30X</h3>
        <p v-if="brief.why_it_fits" class="max-w-[720px] text-base leading-[1.55] text-ink-read">
          {{ brief.why_it_fits }}
        </p>
        <p v-else class="text-[15px] text-muted-foreground">{{ WHY_IT_FITS_MISSING }}</p>
      </div>

      <!-- DESIGN.md §4: «Qué no sabemos» es obligatorio en todo detalle. -->
      <div
        :class="BLOCK_ENTER_CLASS"
        :style="enter(5)"
        class="flex flex-col gap-1.5 rounded-tile bg-notice px-5 py-[18px]"
      >
        <h3 class="text-[15px] font-semibold text-notice-foreground">Qué no sabemos</h3>
        <template v-if="brief.limitations.length > 0">
          <p
            v-for="(limitation, index) in brief.limitations"
            :key="index"
            class="text-[14.5px] leading-[1.5] text-ink-soft"
          >
            {{ limitation }}
          </p>
        </template>
        <p v-else class="text-[14.5px] leading-[1.5] text-ink-soft">{{ NO_LIMITATIONS }}</p>
      </div>

      <!-- DESIGN.md §9: el texto del LLM se rotula como evaluación editorial, con su modelo. -->
      <p :class="BLOCK_ENTER_CLASS" :style="enter(6)" class="text-[13.5px] text-muted-foreground">
        {{ briefFootnote(brief) }}
      </p>
    </div>
  </section>
</template>
