import { BarChart, EffectScatterChart, ScatterChart } from 'echarts/charts'
import { GridComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { LabelLayout } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'

// Solo lo que se pinta en canvas: burbujas y latido del radar (scatter + effectScatter), timeline
// de Explorar (barras) y la rejilla. Cuadrantes, mira, ping y barrido son HTML sobre el canvas,
// para moverlos solo con `transform` (DESIGN.md §7). Sin `LabelLayout`, el `labelLayout` de una
// serie (ocultar las etiquetas que se pisan en el radar) se ignora en silencio.
use([CanvasRenderer, ScatterChart, EffectScatterChart, BarChart, GridComponent, LabelLayout])

// Los gráficos importan VChart desde aquí para que el registro de arriba siempre haya corrido.
export { default as VChart } from 'vue-echarts'
