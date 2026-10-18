<script setup lang="ts">
import { computed } from 'vue'

import { useOpportunities } from '@/api/opportunities'
import { CARD_CLASS, SECONDARY_BUTTON_CLASS } from '@/components/dossier/dossierClasses'
import ViewHeader from '@/components/layout/ViewHeader.vue'
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'
import { featuredNote, splitByPublishNow } from '@/lib/createPicker'

import CreateFeaturedTopic from './CreateFeaturedTopic.vue'
import CreateTopicList from './CreateTopicList.vue'

const SKELETON_ROWS = 5

const listQuery = useOpportunities()

const items = computed(() => listQuery.data.value?.items ?? [])
// Sin temas en «Publicar ya» no hay destacado: la lista lo dice y nunca asciende a otro
// (CLAUDE.md §2.3).
const split = computed(() => splitByPublishNow(items.value))
const note = computed(() => featuredNote(split.value.featured.length))
const hasFeatured = computed(() => split.value.featured.length > 0)
</script>

<template>
  <div class="flex flex-col gap-5 pt-5">
    <!-- Ninguna vista pide «elige algo» (DESIGN.md §1): responde con el tema que conviene
         escribir ya y deja cualquier otro a un clic. -->
    <ViewHeader title="¿De qué conviene escribir esta semana?">
      Rad prepara el brief a partir de la evidencia del tema: ángulo, gancho, estructura y puntos
      clave con sus fuentes.
    </ViewHeader>

    <div v-if="listQuery.isPending.value" class="flex flex-col gap-5" aria-busy="true">
      <SkeletonBone class="h-[360px] rounded-card" />
      <div :class="[CARD_CLASS, 'flex-col gap-2']">
        <SkeletonBone class="mb-2 h-7 w-64 rounded-lg" />
        <SkeletonBone v-for="row in SKELETON_ROWS" :key="row" class="h-[52px] rounded-tile" />
      </div>
    </div>

    <section
      v-else-if="listQuery.isError.value"
      aria-label="Temas"
      :class="[CARD_CLASS, 'flex-col items-start gap-3']"
    >
      <p role="alert" class="text-[15px] text-ink-soft">No se pudieron cargar los temas.</p>
      <button type="button" :class="SECONDARY_BUTTON_CLASS" @click="listQuery.refetch()">
        Reintentar
      </button>
    </section>

    <section v-else-if="items.length === 0" aria-label="Temas" :class="CARD_CLASS">
      <p class="text-[15px] text-ink-soft">Todavía no hay temas analizados.</p>
    </section>

    <template v-else>
      <CreateFeaturedTopic
        v-for="topic in split.featured"
        :key="topic.id"
        :opportunity="topic"
        :note
      />
      <!-- Si todos los temas están en «Publicar ya», no queda «otro tema» que ofrecer. -->
      <CreateTopicList
        v-if="split.others.length > 0"
        :topics="split.others"
        :has-featured="hasFeatured"
      />
    </template>
  </div>
</template>
