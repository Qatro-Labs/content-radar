<script lang="ts">
// Lo que ocupa el sitio del expediente mientras no hay un tema que pintar.
export const DossierPlaceholder = {
  Loading: 'loading',
  NotFound: 'not-found',
  Error: 'error',
} as const
export type DossierPlaceholder = (typeof DossierPlaceholder)[keyof typeof DossierPlaceholder]
</script>

<script setup lang="ts">
import { RouteName } from '@/router'

import { CARD_CLASS, CARD_TITLE_CLASS, SECONDARY_BUTTON_CLASS } from './dossierClasses'
import SkeletonBone from './SkeletonBone.vue'

const { state } = defineProps<{ state: DossierPlaceholder }>()

const emit = defineEmits<{ retry: [] }>()

const SKELETON_COMPONENTS = 5
const SKELETON_BARS = 6
const SKELETON_CRITERIA = 3
const SKELETON_PIECES = 4
</script>

<template>
  <div
    v-if="state === DossierPlaceholder.Loading"
    class="flex flex-col gap-4"
    aria-busy="true"
    aria-label="Cargando el expediente del tema"
  >
    <div class="flex flex-wrap items-stretch gap-4 pt-3">
      <div class="flex flex-[999_1_640px] flex-col gap-4 pt-1">
        <SkeletonBone class="h-11 w-24 rounded-xl" />
        <SkeletonBone class="h-7 w-28 rounded-full" />
        <SkeletonBone class="h-14 w-4/5 rounded-xl" />
        <SkeletonBone class="h-5 w-full max-w-[640px] rounded-full" />
        <SkeletonBone class="mt-auto h-10 w-32 rounded-[10px]" />
      </div>
      <div :class="[CARD_CLASS, 'flex-col flex-[1_1_440px] gap-[18px]']">
        <div class="flex items-center gap-5">
          <SkeletonBone class="size-28 shrink-0 rounded-full" />
          <div class="flex grow flex-col gap-2">
            <SkeletonBone class="h-6 w-40 rounded-lg" />
            <SkeletonBone class="h-4 w-3/4 rounded-full" />
          </div>
        </div>
        <SkeletonBone v-for="bar in SKELETON_COMPONENTS" :key="bar" class="h-2 rounded-full" />
      </div>
    </div>

    <div :class="[CARD_CLASS, 'flex-col gap-3']">
      <SkeletonBone class="h-7 w-32 rounded-lg" />
      <div class="flex h-[180px] items-end gap-2.5">
        <SkeletonBone
          v-for="bar in SKELETON_BARS"
          :key="bar"
          class="h-3/5 grow rounded-t-lg rounded-b-[3px]"
        />
      </div>
    </div>

    <div :class="[CARD_CLASS, 'flex-col gap-4']">
      <SkeletonBone class="h-7 w-40 rounded-lg" />
      <SkeletonBone class="h-5 w-full max-w-[720px] rounded-full" />
      <SkeletonBone class="h-5 w-2/3 rounded-full" />
      <SkeletonBone
        v-for="criterion in SKELETON_CRITERIA"
        :key="criterion"
        class="h-16 rounded-tile"
      />
    </div>

    <div :class="[CARD_CLASS, 'flex-col gap-2']">
      <SkeletonBone class="mb-2 h-7 w-32 rounded-lg" />
      <SkeletonBone v-for="piece in SKELETON_PIECES" :key="piece" class="h-24 rounded-tile" />
    </div>
  </div>

  <section v-else aria-label="Expediente del tema" :class="[CARD_CLASS, 'flex-col mt-3 gap-4']">
    <h1 :class="CARD_TITLE_CLASS">Expediente</h1>
    <template v-if="state === DossierPlaceholder.NotFound">
      <p class="text-[17px] leading-[1.55] text-ink-soft">
        Este tema no está en el análisis servido: los temas cambian entre ejecuciones.
      </p>
      <RouterLink
        :to="{ name: RouteName.Discover }"
        :class="[SECONDARY_BUTTON_CLASS, 'self-start']"
      >
        Volver al Radar
      </RouterLink>
    </template>
    <template v-else>
      <p role="alert" class="text-[17px] leading-[1.55] text-ink-soft">
        No se pudo cargar el tema.
      </p>
      <button type="button" :class="[SECONDARY_BUTTON_CLASS, 'self-start']" @click="emit('retry')">
        Reintentar
      </button>
    </template>
  </section>
</template>
