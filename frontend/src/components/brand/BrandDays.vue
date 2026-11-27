<script setup lang="ts">
import {
  BRIEF_FORMAT_LABEL,
  BRIEF_FORMATS,
  BRIEF_GOAL_LABEL,
  BRIEF_GOALS,
  BRIEF_PLATFORM_LABEL,
  BRIEF_PLATFORMS,
} from '@/lib/briefView'
import { publishingSummary, toggleDay, WEEKDAY_LABEL, WEEKDAYS } from '@/lib/brandProfile'
import type { components } from '@/types/api'

import {
  CHIP_CLASS,
  CHIP_ON_CLASS,
  LABEL_CLASS,
  READ_VALUE_CLASS,
  SELECT_CLASS,
} from './brandClasses'

type Schemas = components['schemas']
type PublishingDay = Schemas['PublishingDay']
type Weekday = Schemas['Weekday']

defineProps<{ editable: boolean; error?: string }>()
const days = defineModel<PublishingDay[]>('days', { required: true })
const goal = defineModel<Schemas['BriefGoal']>('goal', { required: true })

function entryOf(day: Weekday): PublishingDay | undefined {
  return days.value.find((entry) => entry.day === day)
}

function patchDay(day: Weekday, patch: Partial<Omit<PublishingDay, 'day'>>) {
  days.value = days.value.map((entry) => (entry.day === day ? { ...entry, ...patch } : entry))
}

function selected(event: Event): string {
  return (event.target as HTMLSelectElement).value
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <span :class="LABEL_CLASS">Días de publicación</span>
    <ul v-if="editable" class="flex flex-col gap-2">
      <li v-for="day in WEEKDAYS" :key="day" class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          :class="[entryOf(day) ? CHIP_ON_CLASS : CHIP_CLASS, 'w-28 justify-center']"
          :aria-pressed="entryOf(day) !== undefined"
          @click="days = toggleDay(days, day)"
        >
          {{ WEEKDAY_LABEL[day] }}
        </button>
        <template v-if="entryOf(day)">
          <select
            :class="SELECT_CLASS"
            :aria-label="`Dónde publicas el ${WEEKDAY_LABEL[day].toLowerCase()}`"
            :value="entryOf(day)?.channel"
            @change="patchDay(day, { channel: selected($event) as PublishingDay['channel'] })"
          >
            <option v-for="channel in BRIEF_PLATFORMS" :key="channel" :value="channel">
              {{ BRIEF_PLATFORM_LABEL[channel] }}
            </option>
          </select>
          <select
            :class="SELECT_CLASS"
            :aria-label="`Formato del ${WEEKDAY_LABEL[day].toLowerCase()}`"
            :value="entryOf(day)?.format"
            @change="patchDay(day, { format: selected($event) as PublishingDay['format'] })"
          >
            <option v-for="format in BRIEF_FORMATS" :key="format" :value="format">
              {{ BRIEF_FORMAT_LABEL[format] }}
            </option>
          </select>
        </template>
      </li>
    </ul>
    <p v-else :class="READ_VALUE_CLASS">{{ publishingSummary(days) }}</p>
    <p
      v-if="editable && error"
      id="brand-days-error"
      class="text-[13px] font-medium text-destructive"
    >
      {{ error }}
    </p>
  </div>

  <div class="flex flex-col gap-1.5">
    <label v-if="editable" for="brand-goal" :class="LABEL_CLASS">Objetivo</label>
    <span v-else :class="LABEL_CLASS">Objetivo</span>
    <select
      v-if="editable"
      id="brand-goal"
      :class="SELECT_CLASS"
      :value="goal"
      @change="goal = selected($event) as Schemas['BriefGoal']"
    >
      <option v-for="option in BRIEF_GOALS" :key="option" :value="option">
        {{ BRIEF_GOAL_LABEL[option] }}
      </option>
    </select>
    <p v-else :class="READ_VALUE_CLASS">{{ BRIEF_GOAL_LABEL[goal] }}</p>
  </div>
</template>
