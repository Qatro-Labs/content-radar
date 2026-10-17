<script setup lang="ts">
import { RECOMMENDATION_LABEL } from '@/lib/opportunityFormat'
import type { components } from '@/types/api'

type Recommendation = components['schemas']['Recommendation']
type ChipSize = 'sm' | 'md'

const { recommendation, size = 'md' } = defineProps<{
  recommendation: Recommendation
  size?: ChipSize
}>()

// DESIGN.md §2 y §4.
const NEUTRAL_ACTION_CLASS = 'bg-neutral-action text-ink-read'
const TONE_CLASS: Record<Recommendation, string> = {
  publish_now: 'bg-signal text-signal-foreground',
  find_angle: NEUTRAL_ACTION_CLASS,
  wait_for_case: NEUTRAL_ACTION_CLASS,
  discard: 'bg-negative-bg text-destructive',
}

// `md` para el panel de detalle; `sm` para el ranking.
const SIZE_CLASS: Record<ChipSize, string> = {
  sm: 'rounded-lg px-3 py-[5px] text-[13px]',
  md: 'rounded-[10px] px-3.5 py-2 text-[15px]',
}
</script>

<template>
  <span
    class="inline-flex leading-[1.4] font-semibold whitespace-nowrap"
    :class="[TONE_CLASS[recommendation], SIZE_CLASS[size]]"
  >
    {{ RECOMMENDATION_LABEL[recommendation] }}
  </span>
</template>
