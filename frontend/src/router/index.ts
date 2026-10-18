import { createRouter, createWebHistory } from 'vue-router'

import { hasSession } from '@/composables/useAuth'
import { BRIEF_PARAM } from '@/lib/briefView'
import { AUTH_REQUIRED, supabase } from '@/lib/supabase'
import DiscoverView from '@/views/DiscoverView.vue'

import { createAuthGuard } from './authGuard'
import { RouteName } from './routeNames'

export { RouteName }

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  // Una vista nueva empieza arriba; los filtros y la selección cambian solo la query y no mueven
  // la página. Atrás y adelante recuperan la posición guardada. En Crear, el tema va en la query,
  // pero elegir otro abre otra pantalla (de la lista de temas al estudio): también empieza arriba.
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.path !== from.path) return { top: 0 }
    if (to.query[BRIEF_PARAM.opportunity] !== from.query[BRIEF_PARAM.opportunity]) return { top: 0 }
    return false
  },
  routes: [
    // El Radar cabe en la ventana en escritorio: lo largo se desplaza dentro de su tarjeta.
    { path: '/', name: RouteName.Discover, component: DiscoverView, meta: { fitsViewport: true } },
    {
      path: '/explore',
      name: RouteName.Explore,
      component: () => import('@/views/ExploreView.vue'),
    },
    {
      path: '/explore/:id',
      name: RouteName.Dossier,
      component: () => import('@/views/DossierView.vue'),
    },
    {
      path: '/create',
      name: RouteName.Create,
      component: () => import('@/views/CreateView.vue'),
    },
    {
      path: '/login',
      name: RouteName.Login,
      component: () => import('@/views/LoginView.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: { name: RouteName.Discover } },
  ],
})

// Login opcional por defecto: sin `VITE_AUTH_REQUIRED=true` no hay guard y la app se ve igual. Sin
// Supabase configurado tampoco: nadie podría iniciar sesión y la app quedaría cerrada.
if (AUTH_REQUIRED && supabase !== null) router.beforeEach(createAuthGuard(hasSession))
