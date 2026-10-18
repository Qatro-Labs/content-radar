<script setup lang="ts">
import { CircleUser, LogOut } from '@lucide/vue'
import { useRouter } from 'vue-router'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/composables/useAuth'
import { AUTH_REQUIRED } from '@/lib/supabase'
import { RouteName } from '@/router/routeNames'

// Discreto a propósito: el login es opcional y la demo no debe cambiar por él. Sin Supabase
// configurado no se muestra nada.
const LINK_CLASS =
  'flex h-11 items-center rounded-[10px] px-3 text-sm font-medium text-muted-foreground transition-colors duration-150 ease-out hover:text-foreground'

const router = useRouter()
const { isConfigured, isReady, isSignedIn, email, signOut } = useAuth()

async function leave() {
  await signOut()
  if (AUTH_REQUIRED) await router.push({ name: RouteName.Login })
}
</script>

<template>
  <div v-if="isConfigured && isReady" class="flex items-center gap-1">
    <DropdownMenu v-if="isSignedIn">
      <DropdownMenuTrigger
        aria-label="Cuenta"
        class="flex size-11 items-center justify-center rounded-[10px] text-muted-foreground transition-colors duration-150 ease-out hover:text-foreground aria-expanded:bg-card aria-expanded:text-foreground"
      >
        <CircleUser class="size-5" :stroke-width="1.75" aria-hidden="true" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" class="w-60 max-w-[calc(100vw-2rem)]">
        <DropdownMenuLabel class="truncate text-[13px] font-normal" :title="email ?? undefined">
          {{ email }}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem class="min-h-11 rounded-[10px] px-2.5" @select="leave">
          <LogOut :stroke-width="1.75" aria-hidden="true" />
          Cerrar sesión
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
    <RouterLink v-else :to="{ name: RouteName.Login }" :class="LINK_CLASS">
      Iniciar sesión
    </RouterLink>
  </div>
</template>
