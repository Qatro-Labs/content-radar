<script setup lang="ts">
import RadMark, { type RadMarkState } from '@/components/agent/RadMark.vue'

// En Crear, Rad no maneja la página (DESIGN.md §4): su marca solo firma lo que va a escribir y lo
// que escribió, quieta y mirando al frente.
const AT_REST: RadMarkState = { working: false, scanKey: 0, blinkKey: 0, lookAt: null }
const SIZE_PX = 32
</script>

<template>
  <RadMark :state="AT_REST" :size="SIZE_PX" />
</template>
