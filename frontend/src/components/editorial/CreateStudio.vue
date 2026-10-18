<script setup lang="ts">
import { Check } from '@lucide/vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useBrief } from '@/api/editorial'
import { useOpportunity, useOpportunityEvidence } from '@/api/opportunities'
import DossierStates, { DossierPlaceholder } from '@/components/dossier/DossierStates.vue'
import {
  type BriefOptions,
  featuredPieces,
  parseBriefQuery,
  sameRequest,
  serializeBriefQuery,
} from '@/lib/briefView'
import type { components } from '@/types/api'

import BriefComposer from './BriefComposer.vue'
import BriefErrorCard from './BriefErrorCard.vue'
import BriefGenerating from './BriefGenerating.vue'
import BriefResult from './BriefResult.vue'
import CreateHeader from './CreateHeader.vue'

type BriefRequest = components['schemas']['BriefRequest']

const { opportunityId } = defineProps<{ opportunityId: string }>()

const route = useRoute()
const router = useRouter()

const briefQuery = computed(() => parseBriefQuery(route.query))

const opportunityQuery = useOpportunity(() => opportunityId)
const evidenceQuery = useOpportunityEvidence(() => opportunityId)
const brief = useBrief()

const opportunity = computed(() => opportunityQuery.data.value ?? null)
const evidence = computed(() => ({
  data: evidenceQuery.data.value,
  isPending: evidenceQuery.isPending.value,
  isError: evidenceQuery.isError.value,
}))

const placeholder = computed<DossierPlaceholder | null>(() => {
  if (opportunityQuery.isPending.value) return DossierPlaceholder.Loading
  if (opportunityQuery.isError.value) return DossierPlaceholder.Error
  if (opportunity.value === null) return DossierPlaceholder.NotFound
  return null
})

// Las opciones viven en la URL, como los filtros del Radar: elegir una no genera nada.
const options = computed<BriefOptions>({
  get: () => briefQuery.value.options,
  set: (next) => void router.replace({ query: { ...route.query, ...next } }),
})

const request = computed<BriefRequest>(() => ({
  opportunity_id: opportunityId,
  ...options.value,
}))

// La respuesta en pantalla es de la última petición: con otras opciones, vuelve la frase.
const isCurrent = computed(() => sameRequest(brief.variables.value, request.value))
const hasCurrentBrief = computed(() => brief.isSuccess.value && isCurrent.value)
// «Cambiar enfoque» vuelve a la frase sin perder el brief; generar lo cierra.
const editing = ref(false)
const showsResult = computed(() => hasCurrentBrief.value && !editing.value)
const showsError = computed(() => brief.isError.value && isCurrent.value)

// DESIGN.md §7: un brief cacheado llega en un segundo, así que Rad solo aparece si la espera pasa de
// este umbral. Una vez en pantalla, se queda hasta su cierre (`finished`) o hasta un error.
const GENERATING_DELAY_MS = 800
const showsGenerating = ref(false)
let generatingTimer: ReturnType<typeof setTimeout> | undefined
watch(
  () => brief.isPending.value,
  (pending) => {
    clearTimeout(generatingTimer)
    if (pending)
      generatingTimer = setTimeout(() => (showsGenerating.value = true), GENERATING_DELAY_MS)
  },
)
watch(
  () => brief.isError.value,
  (failed) => {
    if (failed) showsGenerating.value = false
  },
)
onBeforeUnmount(() => clearTimeout(generatingTimer))
const featured = computed(() => featuredPieces(evidence.value.data ?? []))

function generate() {
  editing.value = false
  // Con las opciones del brief que ya hay, la API devolvería el mismo (lo cachea): se vuelve a él
  // sin pedirlo otra vez.
  if (hasCurrentBrief.value) return
  void router.replace({ query: serializeBriefQuery(request.value) })
  brief.mutate(request.value)
}

// El brief es más largo que la frase: sin subir, la página quedaría abajo, a media tarjeta.
function editBrief() {
  editing.value = true
  window.scrollTo({ top: 0 })
}

// Un enlace con las cuatro opciones abre su brief: la API lo devuelve cacheado, sin LLM. Cuenta la
// URL con la que se abrió la vista; elegir opciones después también las escribe, y eso no genera.
let pendingBriefLink = briefQuery.value.isComplete
watch(
  opportunity,
  (loaded) => {
    if (loaded === null || !pendingBriefLink) return
    pendingBriefLink = false
    brief.mutate(request.value)
  },
  { immediate: true },
)
</script>

<template>
  <DossierStates
    v-if="placeholder"
    title="Crear"
    :state="placeholder"
    @retry="opportunityQuery.refetch()"
  />

  <!-- Artboard B1 «Estudio en una columna»: la cabecera y una sola tarjeta que pasa de la frase
       al brief. Sin panel lateral, no queda hueco en blanco debajo. -->
  <div v-else-if="opportunity" class="mx-auto flex w-full max-w-[880px] flex-col gap-5">
    <CreateHeader :opportunity />

    <BriefGenerating
      v-if="showsGenerating"
      :pieces="featured"
      :piece-count="evidence.data?.length ?? null"
      :options
      :done="brief.isSuccess.value"
      @finished="showsGenerating = false"
    />
    <template v-else-if="showsResult && brief.data.value">
      <!-- Solo con sesión la API lo guarda y devuelve su id. -->
      <p
        v-if="brief.data.value.id != null"
        class="-mb-3 flex items-center gap-1.5 px-1 text-[13.5px] text-muted-foreground"
      >
        <Check class="size-3.5" :stroke-width="2.5" aria-hidden="true" />
        Guardado en Mis briefs
      </p>
      <BriefResult :brief="brief.data.value" @edit="editBrief" />
    </template>
    <template v-else>
      <!-- DESIGN.md §4: el error va inline y la frase sigue debajo, para cambiar de opciones. -->
      <BriefErrorCard
        v-if="showsError && brief.error.value"
        :error="brief.error.value"
        @retry="generate"
      />
      <BriefComposer
        v-model:options="options"
        :opportunity
        :evidence
        :pending="brief.isPending.value"
        @generate="generate"
      />
    </template>
  </div>
</template>
