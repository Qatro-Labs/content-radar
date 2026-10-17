<script setup lang="ts">
import AppHeader from '@/components/layout/AppHeader.vue'
</script>

<template>
  <div class="mx-auto flex min-h-[100dvh] max-w-[1440px] flex-col gap-6 px-4 py-4 md:px-8 md:py-6">
    <AppHeader />
    <main class="flex-1">
      <RouterView />
    </main>
  </div>
</template>
