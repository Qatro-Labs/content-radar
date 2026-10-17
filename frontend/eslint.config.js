import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import prettier from 'eslint-config-prettier/flat'
import pluginVue from 'eslint-plugin-vue'
import { globalIgnores } from 'eslint/config'

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,vue}'],
  },

  globalIgnores(['**/dist/**', '**/coverage/**', 'src/types/api.ts']),

  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,

  {
    // Los componentes de shadcn-vue llegan de su CLI y no se reescriben (estándares §9): se
    // nombran como la primitiva (Button.vue) y dejan sus props opcionales sin default.
    name: 'app/shadcn-ui',
    files: ['src/components/ui/**/*.vue'],
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/require-default-prop': 'off',
    },
  },

  prettier,
)
