<script setup lang="ts">
import { ChevronDown } from '@lucide/vue'
import { type ComponentPublicInstance, computed, ref, useId } from 'vue'

import {
  BRIEF_FORMAT_LABEL,
  BRIEF_FORMAT_WORD,
  BRIEF_FORMATS,
  BRIEF_GOAL_LABEL,
  BRIEF_GOAL_WORD,
  BRIEF_GOALS,
  BRIEF_PLATFORM_LABEL,
  BRIEF_PLATFORM_WORD,
  BRIEF_PLATFORMS,
  type BriefOptions,
} from '@/lib/briefView'

import BriefOptionGroup from './BriefOptionGroup.vue'

type Slot = keyof BriefOptions

const options = defineModel<BriefOptions>('options', { required: true })

// «Un [formato] en [plataforma] para [objetivo].» El espacio duro deja cada palabra pegada a su
// hueco cuando la frase salta de línea.
const SLOTS: readonly { key: Slot; lead: string }[] = [
  { key: 'format', lead: 'Un ' },
  { key: 'platform', lead: ' en ' },
  { key: 'goal', lead: ' para ' },
]
const SLOT_LABEL: Record<Slot, string> = {
  format: 'Formato',
  platform: 'Plataforma',
  goal: 'Objetivo',
}
// La lima es siempre relleno bajo tinta (DESIGN.md §2): lavada en reposo y entera con el hueco abierto.
const SLOT_CLASS =
  'mx-0.5 inline-flex items-center gap-1.5 rounded-xl px-2.5 pb-0.5 whitespace-nowrap text-foreground transition-colors duration-150 ease-out'
const SLOT_TONE_CLASS = { open: 'bg-signal', closed: 'bg-signal/42 hover:bg-signal/70' }
const ENTER_CLASS =
  'animate-in fade-in slide-in-from-bottom-1 duration-300 ease-out motion-reduce:animate-none'

const openSlot = ref<Slot | null>(null)
const slotButtons: Partial<Record<Slot, HTMLButtonElement>> = {}
const panelId = useId()

const words = computed<Record<Slot, string>>(() => ({
  format: BRIEF_FORMAT_WORD[options.value.format],
  platform: BRIEF_PLATFORM_WORD[options.value.platform],
  goal: BRIEF_GOAL_WORD[options.value.goal],
}))

function registerSlot(slot: Slot, element: Element | ComponentPublicInstance | null) {
  if (element instanceof HTMLButtonElement) slotButtons[slot] = element
}

function toggle(slot: Slot) {
  openSlot.value = openSlot.value === slot ? null : slot
}

// El foco vuelve al hueco que se cerró: quien navega con teclado sigue en la frase.
function close() {
  const slot = openSlot.value
  if (slot === null) return
  openSlot.value = null
  slotButtons[slot]?.focus()
}

// Elegir solo escribe la opción (en la URL, vía CreateStudio): nunca genera.
function pick<K extends Slot>(slot: K, value: BriefOptions[K]) {
  options.value = { ...options.value, [slot]: value }
  close()
}
</script>

<template>
  <div class="flex flex-col gap-3.5" @keydown.esc="close">
    <p
      class="font-display text-[clamp(1.625rem,4.6vw,2.125rem)] leading-[1.5] font-semibold tracking-[-0.025em]"
    >
      <!-- Vue quita los saltos de línea entre etiquetas: los espacios de la frase van en `lead`. -->
      <template v-for="slot in SLOTS" :key="slot.key">
        <span>{{ slot.lead }}</span>
        <button
          :ref="(element) => registerSlot(slot.key, element)"
          type="button"
          :aria-label="`${SLOT_LABEL[slot.key]}: ${words[slot.key]}`"
          :aria-expanded="openSlot === slot.key"
          :aria-controls="`${panelId}-${slot.key}`"
          :class="[
            SLOT_CLASS,
            openSlot === slot.key ? SLOT_TONE_CLASS.open : SLOT_TONE_CLASS.closed,
          ]"
          @click="toggle(slot.key)"
        >
          {{ words[slot.key] }}
          <ChevronDown
            class="size-[18px] shrink-0 transition-transform duration-200 ease-out motion-reduce:transition-none"
            :class="{ 'rotate-180': openSlot === slot.key }"
            aria-hidden="true"
          />
        </button>
      </template>
      <span>.</span>
    </p>

    <!-- Un hueco abierto a la vez; la clave repite la entrada al pasar de uno a otro. -->
    <div v-if="openSlot" :id="`${panelId}-${openSlot}`" :key="openSlot" :class="ENTER_CLASS">
      <BriefOptionGroup
        v-if="openSlot === 'format'"
        :label="SLOT_LABEL.format"
        :options="BRIEF_FORMATS"
        :labels="BRIEF_FORMAT_LABEL"
        :model-value="options.format"
        @update:model-value="pick('format', $event)"
      />
      <BriefOptionGroup
        v-else-if="openSlot === 'platform'"
        :label="SLOT_LABEL.platform"
        :options="BRIEF_PLATFORMS"
        :labels="BRIEF_PLATFORM_LABEL"
        :model-value="options.platform"
        @update:model-value="pick('platform', $event)"
      />
      <BriefOptionGroup
        v-else
        :label="SLOT_LABEL.goal"
        :options="BRIEF_GOALS"
        :labels="BRIEF_GOAL_LABEL"
        :model-value="options.goal"
        @update:model-value="pick('goal', $event)"
      />
    </div>
  </div>
</template>
