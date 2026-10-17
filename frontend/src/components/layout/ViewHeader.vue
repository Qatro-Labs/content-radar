<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
  <div class="flex max-w-[720px] flex-col gap-3">
    <h1
      class="font-display text-[clamp(2.25rem,4vw,3.5rem)] leading-none font-semibold tracking-[-0.04em]"
    >
      {{ title }}
    </h1>
    <p class="text-[17px] leading-[1.55] text-ink-soft">
      <slot />
    </p>
  </div>
</template>
