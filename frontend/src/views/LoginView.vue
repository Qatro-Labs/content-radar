<script setup lang="ts">
import { ref, useId } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import {
  CARD_CLASS,
  CARD_TITLE_CLASS,
  PRIMARY_BUTTON_CLASS,
  SECONDARY_BUTTON_CLASS,
} from '@/components/dossier/dossierClasses'
import { useAuth } from '@/composables/useAuth'
import { RouteName } from '@/router/routeNames'
import { REDIRECT_PARAM, safeRedirect } from '@/router/authGuard'

const FIELD_CLASS =
  'h-12 w-full min-w-0 rounded-xl bg-secondary px-4 text-[15px] text-foreground placeholder:text-muted-foreground'
const LABEL_CLASS = 'text-[13px] font-semibold text-label'

const route = useRoute()
const router = useRouter()
const { isConfigured, isSignedIn, email: signedInEmail, signIn, signOut } = useAuth()

const emailId = useId()
const passwordId = useId()
const email = ref('')
const password = ref('')
const isSubmitting = ref(false)
const errorMessage = ref<string | null>(null)

function goToApp() {
  const redirect = safeRedirect(route.query[REDIRECT_PARAM])
  return router.replace(redirect ?? { name: RouteName.Discover })
}

async function submit() {
  if (isSubmitting.value) return
  isSubmitting.value = true
  errorMessage.value = null
  let failure: string | null
  try {
    failure = await signIn(email.value.trim(), password.value)
  } finally {
    isSubmitting.value = false
  }
  if (failure !== null) {
    errorMessage.value = failure
    return
  }
  password.value = ''
  await goToApp()
}
</script>

<template>
  <div class="mx-auto flex w-full max-w-[420px] flex-col gap-6 pt-[8vh]">
    <div class="flex items-center gap-2 font-display text-xl font-bold tracking-[-0.03em]">
      <span class="size-3.5 rounded-[4px] bg-signal" aria-hidden="true" />
      30X Signal
    </div>

    <section v-if="!isConfigured" :class="CARD_CLASS" class="flex-col gap-3">
      <h1 :class="CARD_TITLE_CLASS">Login no configurado</h1>
      <p class="text-[15px] text-ink-soft">
        Este despliegue no tiene Supabase configurado. El Radar funciona igual, sin iniciar sesión.
      </p>
      <RouterLink :to="{ name: RouteName.Discover }" :class="SECONDARY_BUTTON_CLASS" class="mt-2">
        Ir al Radar
      </RouterLink>
    </section>

    <section v-else-if="isSignedIn" :class="CARD_CLASS" class="flex-col gap-3">
      <h1 :class="CARD_TITLE_CLASS">Sesión iniciada</h1>
      <p class="text-[15px] text-ink-soft">
        Entraste como <span class="font-semibold text-foreground">{{ signedInEmail }}</span
        >.
      </p>
      <div class="mt-2 flex flex-wrap gap-2">
        <button type="button" :class="PRIMARY_BUTTON_CLASS" @click="goToApp">Ir al Radar</button>
        <button type="button" :class="SECONDARY_BUTTON_CLASS" @click="signOut">
          Cerrar sesión
        </button>
      </div>
    </section>

    <form
      v-else
      :class="CARD_CLASS"
      class="flex-col gap-5"
      :aria-busy="isSubmitting"
      @submit.prevent="submit"
    >
      <div class="flex flex-col gap-1.5">
        <h1 :class="CARD_TITLE_CLASS">Iniciar sesión</h1>
        <p class="text-[15px] text-ink-soft">Entra con la cuenta que te dio el equipo.</p>
      </div>

      <div class="flex flex-col gap-1.5">
        <label :for="emailId" :class="LABEL_CLASS">Correo</label>
        <input
          :id="emailId"
          v-model="email"
          type="email"
          autocomplete="email"
          required
          :class="FIELD_CLASS"
        />
      </div>

      <div class="flex flex-col gap-1.5">
        <label :for="passwordId" :class="LABEL_CLASS">Contraseña</label>
        <input
          :id="passwordId"
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
          :class="FIELD_CLASS"
        />
      </div>

      <p
        v-if="errorMessage"
        role="alert"
        class="rounded-[14px] bg-negative-bg px-4 py-3 text-sm font-medium text-destructive"
      >
        {{ errorMessage }}
      </p>

      <button
        type="submit"
        :disabled="isSubmitting"
        :class="PRIMARY_BUTTON_CLASS"
        class="min-h-[46px] disabled:opacity-60"
      >
        {{ isSubmitting ? 'Iniciando sesión…' : 'Iniciar sesión' }}
      </button>
    </form>
  </div>
</template>
