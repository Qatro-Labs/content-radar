import { EffectScatterChart, ScatterChart, BarChart } from 'echarts/charts'
import {
  GraphicComponent,
  GridComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

// Solo lo que piden DESIGN.md §7–8: burbujas y latido (scatter + effectScatter), timeline
// (barras), cuadrante "Prioridad" y medianas (markArea + markLine) y el ping (graphic).
use([
  CanvasRenderer,
  ScatterChart,
  EffectScatterChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  MarkAreaComponent,
  MarkLineComponent,
  GraphicComponent,
])

// Los gráficos importan VChart desde aquí para que el registro de arriba siempre haya corrido.
export { default as VChart } from 'vue-echarts'
