<script setup lang="ts">
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

import { FIELD_CLASS, LABEL_CLASS, READ_VALUE_CLASS } from './brandClasses'

// Un campo de texto del perfil: editable para el equipo y texto plano en solo lectura. El valor es
// texto del usuario: se pinta siempre con interpolación, nunca como HTML.
defineProps<{
  id: string
  label: string
  editable: boolean
  multiline?: boolean
  error?: string
  emptyText?: string
}>()
const value = defineModel<string>({ required: true })
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label v-if="editable" :for="id" :class="LABEL_CLASS">{{ label }}</label>
    <span v-else :class="LABEL_CLASS">{{ label }}</span>

    <template v-if="editable">
      <Textarea
        v-if="multiline"
        :id="id"
        v-model="value"
        :class="FIELD_CLASS"
        :aria-invalid="error ? true : undefined"
        :aria-describedby="error ? `${id}-error` : undefined"
      />
      <Input
        v-else
        :id="id"
        v-model="value"
        :class="FIELD_CLASS"
        :aria-invalid="error ? true : undefined"
        :aria-describedby="error ? `${id}-error` : undefined"
      />
      <p v-if="error" :id="`${id}-error`" class="text-[13px] font-medium text-destructive">
        {{ error }}
      </p>
    </template>
    <p v-else :class="READ_VALUE_CLASS">{{ value.trim() || emptyText || 'Sin definir' }}</p>
  </div>
</template>
