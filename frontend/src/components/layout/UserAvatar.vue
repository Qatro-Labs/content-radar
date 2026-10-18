<script setup lang="ts">
import { User } from '@lucide/vue'
import { computed } from 'vue'

const props = withDefaults(defineProps<{ email: string | null; size?: 'sm' | 'md' }>(), {
  size: 'sm',
})

// Sin el anillo interior el lima se funde con el blanco de la tarjeta.
const BASE_CLASS =
  'inline-flex shrink-0 items-center justify-center rounded-full bg-signal font-display leading-none font-bold tracking-[-0.03em] text-signal-foreground inset-ring inset-ring-foreground/15'

const SIZE_CLASS = {
  sm: 'size-8 text-[15px]',
  md: 'size-10 text-lg',
} as const

const initial = computed(() => props.email?.match(/[\p{L}\p{N}]/u)?.[0]?.toUpperCase() ?? null)
</script>

<template>
  <span :class="[BASE_CLASS, SIZE_CLASS[size]]" aria-hidden="true">
    <template v-if="initial">{{ initial }}</template>
    <User v-else class="size-1/2" :stroke-width="2" />
  </span>
</template>
