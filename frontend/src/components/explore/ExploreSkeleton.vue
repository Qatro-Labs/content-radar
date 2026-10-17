<script setup lang="ts">
import SkeletonBone from '@/components/ui-states/SkeletonBone.vue'

const CARD = 'flex min-w-0 flex-col rounded-card bg-card'
// Ocho filas dan la forma de la tabla sin alargar la página mientras carga.
const SKELETON_ROWS = 8
const SKELETON_COUNTERS = 4
const SKELETON_TOPICS = 5
</script>

<template>
  <div class="flex flex-col gap-4" aria-busy="true" aria-label="Cargando piezas">
    <div class="flex flex-wrap items-end justify-between gap-x-10 gap-y-5">
      <div class="flex w-full max-w-[600px] flex-col gap-3">
        <SkeletonBone class="h-14 w-4/5 rounded-xl" />
        <SkeletonBone class="h-5 w-full rounded-full" />
      </div>
      <div class="flex flex-wrap gap-2">
        <div
          v-for="counter in SKELETON_COUNTERS"
          :key="counter"
          class="flex h-[86px] w-[128px] flex-col justify-center gap-2.5 rounded-2xl bg-card px-5"
        >
          <SkeletonBone class="h-8 w-12 rounded-lg" />
          <SkeletonBone class="h-3.5 w-20 rounded-full" />
        </div>
      </div>
    </div>

    <div class="flex flex-wrap items-start gap-4">
      <div :class="[CARD, 'flex-[999_1_720px] gap-1.5 px-5 pt-5 pb-3']">
        <div class="mx-1 mb-3 flex justify-between gap-3">
          <SkeletonBone class="h-7 w-40 rounded-lg" />
          <SkeletonBone class="h-11 w-[260px] rounded-[10px]" />
        </div>
        <SkeletonBone v-for="row in SKELETON_ROWS" :key="row" class="h-[52px] rounded-lg" />
      </div>
      <div :class="[CARD, 'flex-[1_1_360px] gap-[18px] p-[22px]']">
        <SkeletonBone class="h-7 w-56 rounded-lg" />
        <SkeletonBone v-for="topic in SKELETON_TOPICS" :key="topic" class="h-12 rounded-xl" />
        <SkeletonBone class="h-24 rounded-tile" />
      </div>
    </div>
  </div>
</template>
