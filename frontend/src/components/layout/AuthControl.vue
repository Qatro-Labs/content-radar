<script setup lang="ts">
import { LogOut } from '@lucide/vue'
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

import UserAvatar from './UserAvatar.vue'

// Discreto a propósito: el login es opcional y la demo no debe cambiar por él. Sin Supabase
// configurado no se muestra nada.
const LINK_CLASS =
  'flex h-11 items-center rounded-[10px] px-3 text-sm font-medium text-muted-foreground transition-colors duration-150 ease-out hover:text-foreground'

// El anillo exterior marca hover, foco y menú abierto sin tocar el relleno lima del avatar.
const TRIGGER_RING_CLASS = [
  'transition-shadow duration-150 ease-out',
  'group-hover:ring-2 group-hover:ring-foreground group-hover:ring-offset-2 group-hover:ring-offset-card',
  'group-focus-visible:ring-2 group-focus-visible:ring-foreground group-focus-visible:ring-offset-2 group-focus-visible:ring-offset-card',
  'group-aria-expanded:ring-2 group-aria-expanded:ring-foreground group-aria-expanded:ring-offset-2 group-aria-expanded:ring-offset-card',
]

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
        class="group flex size-11 items-center justify-center rounded-full outline-none"
      >
        <UserAvatar :email="email" :class="TRIGGER_RING_CLASS" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" class="w-64 max-w-[calc(100vw-2rem)]">
        <DropdownMenuLabel class="flex items-center gap-3 px-2.5 py-2 font-normal">
          <UserAvatar :email="email" size="md" />
          <span class="flex min-w-0 flex-col gap-0.5">
            <span class="truncate text-sm font-semibold" :title="email ?? undefined">
              {{ email }}
            </span>
            <span class="text-[12.5px] text-muted-foreground">Sesión iniciada</span>
          </span>
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
