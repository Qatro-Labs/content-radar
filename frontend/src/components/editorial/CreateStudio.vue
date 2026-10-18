<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useBrief } from '@/api/editorial'
import { useOpportunity, useOpportunityEvidence } from '@/api/opportunities'
import DossierStates, { DossierPlaceholder } from '@/components/dossier/DossierStates.vue'
import {
  type BriefOptions,
  briefPlainText,
  parseBriefQuery,
  sameRequest,
  serializeBriefQuery,
} from '@/lib/briefView'
import type { components } from '@/types/api'

import BriefErrorCard from './BriefErrorCard.vue'
import BriefPanel, { BriefStage } from './BriefPanel.vue'
import BriefResult from './BriefResult.vue'
import BriefSkeleton from './BriefSkeleton.vue'
import BriefSources from './BriefSources.vue'
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

// El brief en pantalla es de la última petición; si la persona cambia una opción, sigue visible
// pero el primario vuelve a ser «Generar brief».
const isCurrent = computed(() => sameRequest(brief.variables.value, request.value))
const stage = computed<BriefStage>(() => {
  if (brief.isPending.value) return BriefStage.Pending
  if (brief.isSuccess.value && isCurrent.value) return BriefStage.Ready
  return BriefStage.Idle
})
const plainText = computed(() =>
  stage.value === BriefStage.Ready && brief.data.value ? briefPlainText(brief.data.value) : null,
)

function generate() {
  void router.replace({ query: serializeBriefQuery(request.value) })
  brief.mutate(request.value)
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

  <div v-else-if="opportunity" class="flex flex-col gap-4">
    <CreateHeader :opportunity />

    <!-- La rejilla del Radar y de Explorar: contenido a la izquierda y panel sticky a la derecha.
         Por debajo de 768 px el panel sube encima, para tener el primario a mano. -->
    <div class="flex flex-wrap items-start gap-4">
      <div class="flex min-w-0 flex-[999_1_640px] flex-col gap-4">
        <BriefSkeleton
          v-if="stage === BriefStage.Pending"
          :pieces="evidence.data?.length ?? null"
        />
        <BriefErrorCard
          v-else-if="brief.isError.value && brief.error.value"
          :error="brief.error.value"
          @retry="generate"
        />
        <BriefResult v-else-if="brief.data.value" :brief="brief.data.value" />
        <BriefSources v-else :opportunity :evidence />
      </div>
      <div class="flex min-w-0 flex-[1_1_360px] flex-col max-md:order-first md:sticky md:top-4">
        <BriefPanel
          v-model:options="options"
          :opportunity
          :stage
          :plain-text="plainText"
          @generate="generate"
        />
      </div>
    </div>
  </div>
</template>
