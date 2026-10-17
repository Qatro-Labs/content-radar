<script setup lang="ts">
import { useResizeObserver } from '@vueuse/core'
import { ref, useTemplateRef, watch } from 'vue'

import { TEXT_ENTER_CLASS } from '@/lib/motion'
import type { RankedOpportunity } from '@/lib/radarView'

const { opportunity } = defineProps<{ opportunity: RankedOpportunity }>()

const WHY_TEXT_ID = 'why-it-matters-text'

// El texto del LLM ocupa 500–900 caracteres: la tarjeta muestra 3 líneas (más o menos la primera
// frase) y el resto se abre aquí. Se corta con CSS y no por frases: "EE. UU." parte un texto real.
const whyText = useTemplateRef('whyText')
const expanded = ref(false)
const clamped = ref(false)

useResizeObserver(whyText, () => {
  const el = whyText.value
  // Abierto, el texto ya no desborda: se conserva la medida para poder volver a cerrarlo.
  if (!el || expanded.value) return
  clamped.value = el.scrollHeight > el.clientHeight
})

watch(
  () => opportunity.id,
  () => {
    expanded.value = false
  },
)
</script>

<template>
  <section
    aria-label="Por qué importa"
    class="flex min-w-0 flex-col gap-3.5 rounded-card bg-card px-6 py-[22px]"
  >
    <h2 class="font-display text-xl font-semibold tracking-[-0.02em]">Por qué importa</h2>

    <div class="flex flex-col items-start gap-1">
      <p
        :id="WHY_TEXT_ID"
        ref="whyText"
        :key="opportunity.id"
        class="max-w-[720px] text-lg leading-[1.55] text-ink-read"
        :class="[TEXT_ENTER_CLASS, { 'line-clamp-3': !expanded }]"
      >
        {{ opportunity.why_it_matters }}
      </p>
      <button
        v-if="clamped"
        type="button"
        :aria-expanded="expanded"
        :aria-controls="WHY_TEXT_ID"
        class="min-h-11 text-[15px] font-semibold text-foreground underline decoration-[1.5px] underline-offset-4 hover:text-ink-soft"
        @click="expanded = !expanded"
      >
        {{ expanded ? 'Ver menos' : 'Leer completo' }}
      </button>
    </div>

    <div
      data-agent="limit"
      class="mt-auto flex flex-wrap gap-x-3 gap-y-1 rounded-tile bg-notice px-4 py-3.5"
    >
      <h3 class="text-sm font-semibold text-notice-foreground">Qué no sabemos</h3>
      <ul
        v-if="opportunity.limitations.length > 0"
        :key="opportunity.id"
        class="flex flex-[1_1_280px] flex-col gap-1 text-[14.5px] text-ink-soft"
        :class="TEXT_ENTER_CLASS"
      >
        <!-- Por índice: el LLM puede repetir una limitación y la clave dejaría de ser única. -->
        <li v-for="(limitation, index) in opportunity.limitations" :key="index">
          {{ limitation }}
        </li>
      </ul>
      <p
        v-else
        :key="opportunity.id"
        class="flex-[1_1_280px] text-[14.5px] text-ink-soft"
        :class="TEXT_ENTER_CLASS"
      >
        El análisis no registró limitaciones.
      </p>
    </div>
  </section>
</template>
