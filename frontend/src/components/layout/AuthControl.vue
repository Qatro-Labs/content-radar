<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuth } from '@/composables/useAuth'
import { AUTH_REQUIRED } from '@/lib/supabase'
import { RouteName } from '@/router/routeNames'

// Discreto a propósito: el login es opcional y la demo no debe cambiar por él. Sin Supabase
// configurado no se muestra nada.
const LINK_CLASS =
  'flex h-11 items-center rounded-[10px] px-3 text-sm font-medium text-muted-foreground transition-colors duration-150 ease-out hover:text-foreground'

const router = useRouter()
const { isConfigured, isSignedIn, email, signOut } = useAuth()

async function leave() {
  await signOut()
  if (AUTH_REQUIRED) await router.push({ name: RouteName.Login })
}
</script>

<template>
  <div v-if="isConfigured" class="flex items-center gap-1">
    <template v-if="isSignedIn">
      <span class="max-w-[220px] truncate text-[13px] text-muted-foreground">{{ email }}</span>
      <button type="button" :class="LINK_CLASS" @click="leave">Cerrar sesión</button>
    </template>
    <RouterLink v-else :to="{ name: RouteName.Login }" :class="LINK_CLASS">
      Iniciar sesión
    </RouterLink>
  </div>
</template>
