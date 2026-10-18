<script setup lang="ts">
import { computed } from 'vue'

import { BRIEF_NOT_FOUND, BriefError, NO_RESPONSE } from '@/api/editorial'
import {
  CARD_CLASS,
  CARD_TITLE_CLASS,
  SECONDARY_BUTTON_CLASS,
} from '@/components/dossier/dossierClasses'
import { RouteName } from '@/router'

const { error } = defineProps<{ error: Error }>()

const emit = defineEmits<{ retry: [] }>()

// 502 (falló el LLM) y la red caída se pueden reintentar; 409, 429 y 503 no cambian al momento.
const BAD_GATEWAY = 502
const RETRYABLE = [BAD_GATEWAY, NO_RESPONSE]

const status = computed(() => (error instanceof BriefError ? error.status : NO_RESPONSE))
const message = computed(() =>
  error instanceof BriefError ? error.message : 'No se pudo generar el brief.',
)
</script>

<template>
  <!-- DESIGN.md §4: el error va inline, en la tarjeta afectada; lo demás sigue visible. -->
  <section aria-label="Brief" :class="[CARD_CLASS, 'flex-col items-start gap-3']">
    <h2 :class="CARD_TITLE_CLASS">No se pudo generar el brief</h2>
    <p role="alert" class="text-[17px] leading-[1.55] text-ink-soft">{{ message }}</p>
    <RouterLink
      v-if="status === BRIEF_NOT_FOUND"
      :to="{ name: RouteName.Discover }"
      :class="SECONDARY_BUTTON_CLASS"
    >
      Volver al Radar
    </RouterLink>
    <button
      v-else-if="RETRYABLE.includes(status)"
      type="button"
      :class="SECONDARY_BUTTON_CLASS"
      @click="emit('retry')"
    >
      Reintentar
    </button>
  </section>
</template>
