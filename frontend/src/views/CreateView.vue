<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import CreateStudio from '@/components/editorial/CreateStudio.vue'
import CreateTopicPicker from '@/components/editorial/CreateTopicPicker.vue'
import { parseBriefQuery } from '@/lib/briefView'

const route = useRoute()
const opportunityId = computed(() => parseBriefQuery(route.query).opportunityId)
</script>

<template>
  <!-- Sin tema, la vista propone de qué escribir; con tema, prepara su brief. -->
  <CreateTopicPicker v-if="opportunityId === null" />
  <!-- Por tema: otro tema empieza en blanco, sin el brief del anterior. -->
  <CreateStudio v-else :key="opportunityId" :opportunity-id="opportunityId" />
</template>
