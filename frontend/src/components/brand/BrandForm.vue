<script setup lang="ts">
import { computed } from 'vue'

import {
  capitalized,
  MAX_TONE_WORDS,
  toggleTone,
  toneOptions,
  type BrandDraft,
  type BrandDraftErrors,
} from '@/lib/brandProfile'

import BrandDays from './BrandDays.vue'
import BrandField from './BrandField.vue'
import { CARD_CLASS, CHIP_CLASS, CHIP_ON_CLASS, CHIP_READ_CLASS, LABEL_CLASS } from './brandClasses'

const props = defineProps<{ editable: boolean; errors: BrandDraftErrors }>()
const draft = defineModel<BrandDraft>({ required: true })

// Cada cambio crea un borrador nuevo: el perfil en caché de la API nunca se toca.
function field<K extends keyof BrandDraft>(key: K) {
  return computed({
    get: () => draft.value[key],
    set: (value: BrandDraft[K]) => (draft.value = { ...draft.value, [key]: value }),
  })
}

const audience = field('audience')
const targetRegion = field('target_region')
const createsAbout = field('creates_about')
const callToAction = field('call_to_action')
const neverSay = field('never_say')
const publishingDays = field('publishing_days')
const goal = field('goal')

// En solo lectura se ve solo el tono elegido; al editar, también las sugerencias.
const tones = computed(() => (props.editable ? toneOptions(draft.value.tone) : draft.value.tone))
const toneIsFull = computed(() => draft.value.tone.length >= MAX_TONE_WORDS)

function isChosen(word: string): boolean {
  return draft.value.tone.includes(word)
}

function pickTone(word: string) {
  draft.value = { ...draft.value, tone: toggleTone(draft.value.tone, word) }
}
</script>

<template>
  <section aria-label="Datos de tu marca" class="flex min-w-0 flex-[999_1_460px] flex-col gap-3">
    <div :class="CARD_CLASS">
      <BrandField
        id="brand-audience"
        v-model="audience"
        label="Tu cliente"
        multiline
        :editable="editable"
        :error="errors.audience"
      />
      <BrandField
        id="brand-region"
        v-model="targetRegion"
        label="Dónde está"
        :editable="editable"
        :error="errors.target_region"
      />
      <BrandField
        id="brand-about"
        v-model="createsAbout"
        label="Sobre qué creas contenido"
        :editable="editable"
        :error="errors.creates_about"
      />
    </div>

    <div :class="CARD_CLASS">
      <div class="flex flex-col gap-2">
        <span id="brand-tone-label" :class="LABEL_CLASS">
          Tono
          <span v-if="editable" class="font-normal text-muted-foreground">
            · hasta {{ MAX_TONE_WORDS }} palabras
          </span>
        </span>
        <div class="flex flex-wrap gap-2" role="group" aria-labelledby="brand-tone-label">
          <template v-for="word in tones" :key="word">
            <button
              v-if="editable"
              type="button"
              :class="isChosen(word) ? CHIP_ON_CLASS : CHIP_CLASS"
              :aria-pressed="isChosen(word)"
              :disabled="!isChosen(word) && toneIsFull"
              @click="pickTone(word)"
            >
              {{ capitalized(word) }}
            </button>
            <span v-else :class="CHIP_READ_CLASS">{{ capitalized(word) }}</span>
          </template>
        </div>
        <p v-if="editable && errors.tone" class="text-[13px] font-medium text-destructive">
          {{ errors.tone }}
        </p>
      </div>
      <BrandField
        id="brand-cta"
        v-model="callToAction"
        label="Qué quieres que haga quien te lee"
        :editable="editable"
        :error="errors.call_to_action"
      />
      <BrandField
        id="brand-never"
        v-model="neverSay"
        label="Qué nunca decimos"
        multiline
        :editable="editable"
        :error="errors.never_say"
      />
    </div>

    <div :class="CARD_CLASS">
      <BrandDays
        v-model:days="publishingDays"
        v-model:goal="goal"
        :editable="editable"
        :error="errors.publishing_days"
      />
    </div>
  </section>
</template>
