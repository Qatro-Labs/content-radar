import '@fontsource-variable/bricolage-grotesque'
import '@fontsource-variable/geist'
import './assets/main.css'

import { VueQueryPlugin } from '@tanstack/vue-query'
import { createApp } from 'vue'

import { vueQueryOptions } from './api/queryClient'
import App from './App.vue'
import { router } from './router'

createApp(App).use(router).use(VueQueryPlugin, vueQueryOptions).mount('#app')
