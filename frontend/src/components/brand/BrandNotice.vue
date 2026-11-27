<script setup lang="ts">
// Aviso bajo el título de «Tu marca» (propuesta A de Task 7). No hay tokens de éxito ni de
// información en DESIGN.md: se usan los fondos y textos de los chips de etapa, que ya cumplen
// contraste sobre su fondo.
export type NoticeTone = 'success' | 'danger' | 'info'

const TONE_CLASS: Record<NoticeTone, string> = {
  success: 'bg-(--lc-accelerating-bg) text-(--lc-accelerating-fg)',
  danger: 'bg-negative-bg text-destructive',
  info: 'bg-(--lc-emerging-bg) text-(--lc-emerging-fg)',
}

defineProps<{ tone: NoticeTone; title: string; text: string }>()
</script>

<template>
  <div
    :role="tone === 'danger' ? 'alert' : 'status'"
    :class="[
      TONE_CLASS[tone],
      'flex flex-wrap items-center justify-between gap-3 rounded-tile px-[18px] py-3.5',
    ]"
  >
    <div class="flex min-w-0 flex-col gap-0.5">
      <strong class="text-[15px] font-semibold">{{ title }}</strong>
      <span class="text-sm leading-[1.4]">{{ text }}</span>
    </div>
    <slot />
  </div>
</template>
