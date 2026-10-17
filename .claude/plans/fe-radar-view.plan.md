# fe-radar-view — Vista Radar (Discover) del artboard E, sin el agente

> Plan generado con `/spec`. Lo implementa `plan-implementer` con contexto limpio.
> El implementador NO ve la conversación que produjo este documento: todo lo que necesite tiene que
> estar escrito aquí.

## Metadatos

- **Slug:** `fe-radar-view` · **Issue:** ninguno
- **Owner (CLAUDE.md §3):** Frontend lead
- **Prioridad (CLAUDE.md §12):** P0 · **Checkpoint que desbloquea (§13):** primera integración (sáb 20:30 ESP) y
  MVP P0 end-to-end (dom 00:30 ESP)
- **Valor (filtro de CLAUDE.md §12):** "abrir el Radar → elegir una oportunidad → revisar scores y evidencia → entender
  por qué importa" · **Preguntas de `docs/brief.md` §4:** 1, 2, 3 y 4 (y la 5 a través de `latam_gap`)
- **Repo:** `/Users/dacorredor/projects/personal/qatro_labs/content-radar` (el plan se escribió en el worktree
  `.claude/worktrees/agent-ac51ad62865b13558`, rama `fe/radar-view`)
- **Rama base:** `main` @ `24862ea`
- **Rama de trabajo:** `fe/radar-view`
- **Fecha:** 2026-10-17 18:47 ESP
- **Contratos tocados:** ninguno. Solo **consume** `Opportunity` / `OpportunityList` (PR #7) y `GET /opportunities`
  (PR #9), sin cambiarlos. `src/types/api.ts` se regenera (generado, nunca a mano).
- **Auditoría tras `/build`:** sí (`code-standards-auditor`): es la vista principal de la demo
- **Estado del gate:** `LISTO`

## Problema

`frontend/` tiene el scaffold (PR #15) pero la vista Radar (`/`) está vacía. Sin ella no existe el primer paso del
recorrido de demo: nadie puede abrir el Radar, ver qué temas crecen, filtrarlos, seleccionar uno y entender su score,
para quién importa, por qué importa y qué no sabemos. El diseño aprobado es el artboard **E** (sin su agente). El
contrato y las rutas todavía no están en `main` (PR #7 y #9 abiertos), así que hay que poder desarrollar y enseñar la
vista con fixtures marcados como tales.

## Criterios de aceptación

Acordados en el interrogatorio. Cada uno se verifica con fixtures (`VITE_USE_FIXTURES=true pnpm dev`) salvo que diga
otra cosa.

1. `/` muestra, en este orden (DESIGN.md §5): cabecera con H1 + frase + tres contadores → fila de filtros → radar y
   panel de detalle en la misma fila → bento "Para quién importa" + "Por qué importa" → ranking → nota al pie.
2. **Radar:** cada oportunidad con `audience_fit_score` no nulo es una burbuja con X = `audience_fit_score`,
   Y = `momentum_score`, tamaño `round(18 + 0.34 · evidence_strength)` px y color según `lifecycle` (DESIGN.md §2 y §8).
   Las de `lifecycle = unknown` son huecas, con trazo discontinuo. Hay cuatro cuadrantes con nombre y lavado de señal en
   "Prioridad".
3. Las oportunidades con `audience_fit_score = null` **no se dibujan**. Aparecen en el ranking con "Encaje no
   disponible", y bajo el radar hay una nota: "1 tema sin evaluar no aparece en el radar" ("N temas…" en plural). Si
   N = 0, no hay nota.
4. **Latido:** solo laten las oportunidades que crecen, con el periodo de la tabla de DESIGN.md §7 (≥ 1.0 → 1.4 s ·
   ≥ 0.5 → 2.0 s · > 0.2 → 2.8 s · > 0 → 3.6 s · ≤ 0 o `unknown` → estática).
5. **Barrido** al cargar y al cambiar de periodo, con aparición de burbujas sincronizada (DESIGN.md §7). **Ping** al
   seleccionar. Con `prefers-reduced-motion: reduce` no hay barrido, ping, latido ni entradas.
6. **Selección:** clic en una burbuja o en una fila → `?selected=<id>` en la URL. La mira (líneas + dos lecturas en
   píldora), el anillo de selección y la tarjeta flotante se mueven a la burbuja. El panel de detalle, el bento y la
   fila resaltada del ranking cambian. Sin `selected` válido en la URL, la seleccionada es la primera del ranking.
7. **Hover enlazado:** pasar el cursor por una fila resalta su burbuja, y al revés.
8. **Filtros** (fila de filtros, DESIGN.md §4): selección múltiple de etapas (`?lifecycle=emerging,peaking`) y "Hueco
   en LATAM" (`?gap=1`, solo `latam_gap === true`). Lo que no entra **se atenúa** en el radar (opacidad 0.16, sin
   etiqueta ni latido) y **desaparece** del ranking, que conserva el puesto global. El H1 pasa a "V de N temas", la
   frase dice el filtro, los contadores cuentan solo lo filtrado y aparece "Restablecer vista". La seleccionada nunca se
   atenúa.
9. **Periodo:** segmented 24 h · 7 días · 30 días en la cabecera de la app, solo en la ruta Discover, ligado a
   `?period=`. Cambiarlo vuelve a pedir `GET /opportunities?period=…` y repite el barrido. Si la respuesta trae un
   `period` distinto del pedido, al lado del control aparece "Solo hay datos calculados para 7 días" (con la etiqueta
   del periodo real).
10. **Panel de detalle:** chip de etapa, tema, "{Observado|Estimado|Preliminar} · confianza {alta|media|baja} · {hueco
    en LATAM | ya cubierto en LATAM | hueco en LATAM no disponible}", `lifecycle_reason`, anillo de score con
    `opportunity_score` (cuenta hasta el valor al cambiar de selección), "Oportunidad · puesto R de N", chip de
    recomendación, baldosas Aceleración · Outliers · Fuentes, barras Momentum · Encaje con 30X ("Alto · 82") ·
    Saturación, y los enlaces "Ver evidencia" (`/explore/:id`) y "Generar brief" (`/create?opportunity=:id`).
11. **Ranking:** columnas Puesto · Tema · Etapa (con `lifecycle_reason` como `title`) · Aceleración · Outliers ·
    Fuentes · Oportunidad (barra + cifra) · Acción. Orden "Oportunidad" (orden de la API) o "Aceleración"
    (`?sort=acceleration`).
12. **Datos ausentes:** nunca 0 ni guion. `audience_fit_score`, `opportunity_score` y `actionability_score` nulos →
    "no disponible". `latam_gap` nulo → "hueco en LATAM no disponible".
13. **Estados:** skeletons con la forma del contenido mientras carga · `GET /opportunities` = `null` → "Todavía no hay
    análisis: el job `analyze` no ha corrido." · error → mensaje inline en las tarjetas afectadas · menos de 10
    oportunidades → se muestran las que hay y la frase dice "Hay N temas con datos suficientes esta semana."
14. **Fixtures:** con `VITE_USE_FIXTURES=true`, los datos salen de `data/fixtures/opportunities.json` y la cabecera
    muestra el chip "Datos de ejemplo". Sin el flag, los datos salen solo de la API. **Nunca** se cae a los fixtures si
    la API falla.
15. La nota al pie dice desde cuándo se monitorea (`monitoring_started_at`, formato "16/10, 09:00 UTC") y las lecturas
    de DESIGN.md §9 (latido, tamaño, saturación "dentro de las fuentes monitoreadas", encaje "evaluación editorial, no
    una medición").
16. `pnpm lint && pnpm type-check && pnpm test && pnpm build` en verde.

## No-objetivos

- El agente del Radar (barra de pregunta, presencia, stream). Solo se dejan marcas `data-agent` (D11).
- Las vistas Explorar y Crear, las evidencias (`/evidence`), el timeline, el panel de coste y el tema oscuro.
- Filtros de confianza y de tema en la UI: los campos se quedan en la URL, sin control.
- Pulido móvil más allá de no romperse: a < 768px todo baja a una columna, las etiquetas de burbuja se ocultan y el
  ranking hace scroll dentro de su tarjeta (DESIGN.md §6).
- Cambiar el backend, el contrato o `data/fixtures/opportunities.json` (se copia tal cual).
- Componentes shadcn-vue nuevos. Basta el `Button` que ya existe, más HTML con los tokens.

## Reglas de CLAUDE.md §2 en juego

- **Regla 3 (nunca inventar datos):** las oportunidades sin encaje no se colocan en el radar (D3). Los nulos se
  escriben "no disponible". El periodo real se avisa si difiere del pedido (D1). Los fixtures solo se usan con un flag
  explícito y con el chip "Datos de ejemplo"; sus temas ya llevan el prefijo `[MOCK]` y un test lo vigila (paso 4).
- **Regla 4 (el LLM no calcula) / estándares §9 (el frontend no calcula scores):** el frontend solo formatea, filtra,
  ordena por un campo y aplica las lecturas de texto fijadas en CLAUDE.md §7 (D7). Ningún score se calcula en el front.
- **Regla 5 (tipo de evidencia):** `growth_status` se muestra siempre en el panel ("Observado · Estimado ·
  Preliminar").
- **Regla 6 (texto externo no confiable):** `topic`, `why_it_matters`, `limitations` y `lifecycle_reason` se pintan
  con interpolación de texto de Vue. **Nunca `v-html`.**

## Contexto verificado del código

| Qué | Dónde | Estado actual |
| --- | --- | --- |
| Vista Radar vacía | `frontend/src/views/DiscoverView.vue:1` | Solo `ViewHeader` con "Vista en construcción" |
| Estado del Radar en la URL | `frontend/src/lib/radarQuery.ts:19` | `RadarQuery` con `lifecycle: Lifecycle \| null` (una sola etapa), sin `gap` ni `sort` |
| Enums replicados a mano | `frontend/src/lib/radarQuery.ts:3-12` | El comentario pide comprobarlos con `satisfies` contra `api.ts` cuando llegue el contrato |
| Composable de la URL | `frontend/src/composables/useRadarQuery.ts:11` | `{ query, update(patch) }` con `router.replace`; conserva los params ajenos |
| Tests de la URL | `frontend/src/composables/__tests__/useRadarQuery.spec.ts:32` | Esperan `lifecycle: null` y `lifecycle=emerging`: hay que actualizarlos |
| Cliente de la API | `frontend/src/api/client.ts:1` | `openapi-fetch` con `paths` de `@/types/api`; exporta `Schemas` |
| Patrón de composable de datos | `frontend/src/api/sources.ts:17` | `fetchX()` lanza `Error` si hay `error`; `useQuery` con `queryKey` |
| Tipos generados | `frontend/src/types/api.ts` | Solo `SourceStatus` (generado desde `main`) |
| Script de tipos | `frontend/package.json` (`gen:api`) | `openapi-typescript ${OPENAPI_URL:-http://localhost:8000/openapi.json} -o src/types/api.ts && prettier --write …` |
| Registro de ECharts | `frontend/src/lib/echarts.ts:1` | Scatter, EffectScatter, Bar, Grid, Tooltip, MarkArea, MarkLine, Graphic. Exporta `VChart` |
| Config de Vite | `frontend/vite.config.ts:1` | Alias `@`, proxy `/api` → `API_DEV_TARGET`, Vitest con `jsdom`. Sin `fs.allow` |
| Tipos de entorno | `frontend/env.d.ts:1` | Solo `/// <reference types="vite/client" />` |
| `resolveJsonModule` | `frontend/node_modules/@vue/tsconfig/tsconfig.json:17` | `true` |
| Cabecera de la app | `frontend/src/components/layout/AppHeader.vue:17` | Marca + nav + `DataStatus`. Sin periodo ni chip de ejemplo |
| Rutas | `frontend/src/router/index.ts:5` | `RouteName.Discover` (`/`), `Explore` (`/explore/:id?`), `Create` (`/create`) |
| Formato de fechas | `frontend/src/lib/format.ts:13` | `formatUtcTimestamp(iso)` → "17/10, 02:50 UTC" |
| VueUse | `frontend/package.json` | `@vueuse/core@^14.4.0` directa (misma copia que Reka UI) |
| Contrato `Opportunity` | `origin/intel/engine:backend/app/schemas/opportunity.py` (PR #7) | Igual byte a byte en `origin/data/opportunity-routes` (comprobado con `git diff`) |
| `OpportunityList` | mismo archivo | `items`, `period`, `generated_at`, `monitoring_started_at` |
| Ruta `GET /opportunities` | `origin/data/opportunity-routes:backend/app/api/routes/opportunities.py` (PR #9) | `response_model=OpportunityList \| None`. Acepta `period`, `lifecycle` (una), `confidence`, `topic`. Solo se calcula 7d y la respuesta dice el periodo real. `null` sin ejecución de `analyze` |
| Orden del ranking | `origin/data/opportunity-routes:backend/app/services/opportunities.py:132` | `.order_by(OpportunityRecord.rank)`: la API ya devuelve el orden del ranking |
| Fixture | `origin/intel/engine:data/fixtures/opportunities.json` | `{ _fixture, opportunities: OpportunityList, evidence, timeline }`. 5 items (`opp_001`…`opp_005`), temas con prefijo `[MOCK]`, `opp_005` con `audience_fit_score: null` y `lifecycle: unknown`, `period: "7d"` |
| `rippleEffect` por dato | `apache/echarts` `src/chart/effectScatter/EffectScatterSeries.ts` | `EffectScatterDataItemOption.rippleEffect` existe: el periodo del latido se fija por burbuja en una sola serie |
| Referencia visual | `/private/tmp/claude-501/-Users-dacorredor-projects-personal-qatro-labs-content-radar/c501a572-9be0-4018-8234-abef9ef6b30d/scratchpad/artifact-files/54fe4073-4e4a-4a08-852d-0feded10e166/project/Agent.dc.html` | Artboard E (prototipo HTML, **datos de ejemplo**). Layout, textos y movimiento de referencia. Su agente (barra inferior, presencia) **no** entra. Anima `left/top/width`: no copiarlo (DESIGN.md §7) |
| Sistema de diseño | `DESIGN.md` §4 (l. 101), §5 (l. 166), §7 (l. 197), §8 (l. 263), §9 (l. 280), §11 (l. 321) | Fuente de verdad visual: leerlo entero antes de escribir componentes |
| Lecturas de audiencia | `CLAUDE.md:214-217` | Reglas de "Para quién importa" |

Si al empezar `origin/intel/engine` o `origin/data/opportunity-routes` ya se mergearon en `main`, el paso 1 usa
`main` como fuente (ver el paso).

## Decisiones tomadas

### D1 — Periodo: tres segmentos activos y aviso del periodo real

- **Elegido:** segmented 24 h · 7 días · 30 días en `AppHeader`, solo en la ruta Discover, ligado a `?period=`
  (`useRadarQuery`). La query de datos usa `period` en su `queryKey`. Si `OpportunityList.period` ≠ el pedido, se
  muestra al lado "Solo hay datos calculados para {etiqueta del periodo real}".
- **Por qué:** lo pidió David (mantener el artboard). El aviso cumple la regla 3, porque la API solo calcula 7d.
- **Descartado:** un rótulo fijo "7 días" o segmentos desactivados *(David prefirió el layout del artboard)*.

### D2 — Fixtures explícitos y tipos generados desde la rama de #9

- **Elegido:** copiar `data/fixtures/opportunities.json` **idéntico** al de `origin/intel/engine`, en la misma ruta
  (al mergear #7 no hay conflicto, porque el contenido es el mismo). Generar `src/types/api.ts` desde el OpenAPI de
  `origin/data/opportunity-routes`. Flag `VITE_USE_FIXTURES=true` → los datos vienen del fixture y aparece el chip
  "Datos de ejemplo". Sin el flag, solo API.
- **Por qué:** la integración de las 20:30 no puede esperar a #7 y #9. Los tipos siguen siendo generados (estándares
  §9), no escritos a mano.
- **Descartado:** esperar a los merges *(bloquea el checkpoint)* · MSW *(dependencia nueva para lo mismo)* · caer a los
  fixtures si la API falla *(mostraría datos falsos como reales)*.

### D3 — Oportunidades sin encaje, fuera del radar

- **Elegido:** si `audience_fit_score === null`, la burbuja no se dibuja. En el ranking y en el panel: "Encaje no
  disponible". Bajo el radar: "N tema(s) sin evaluar no aparece(n) en el radar".
- **Descartado:** dibujarlas en x = 0 *(se leería "encaje 0")*.

### D4 — Botones del panel, a sus vistas

- **Elegido:** "Ver evidencia" → `RouterLink` a `{ name: RouteName.Explore, params: { id } }`. "Generar brief" →
  `{ name: RouteName.Create, query: { opportunity: id } }`. Las vistas destino son las vacías del scaffold.

### D5 — Filtrado en el cliente sobre la lista completa; la URL crece

- **Elegido:** una sola llamada `GET /opportunities?period=…` sin otros filtros. Etapas, hueco y orden se aplican en
  el cliente. `RadarQuery` pasa a `lifecycle: Lifecycle[]` (lista separada por comas en la URL) y gana `gap: boolean`
  (`gap=1`) y `sort: 'opportunity' | 'acceleration'` (por defecto `opportunity`, que se omite en la URL). `confidence`,
  `topic`, `selected` y `highlight` se quedan como están.
- **Por qué:** el radar necesita todas las burbujas para atenuar las que no entran. La API solo filtra por una etapa y
  no por hueco. Filtrar y ordenar por un campo no es calcular un score.

### D6 — El puesto es el orden de la API

- **Elegido:** `rank = índice + 1` en el orden de `items` (el backend ordena por `OpportunityRecord.rank`). Con
  "Aceleración" se reordena la tabla por `acceleration` descendente (empate → `rank`), pero cada fila conserva su
  puesto. Los filtros no cambian el puesto.

### D7 — La lectura de "Para quién importa" sigue CLAUDE.md §7, con constantes

- **Elegido:** función pura `audienceReading(opportunity)`, primera regla que se cumple:
  1. `tech ≥ 0.6`, `business < 0.3` y `audience_fit_score ≥ 60` → "Mucho tech y poco negocio: todavía no llegó a
     ejecutivos. Hay que traducirlo a negocio."
  2. `latam_gap === true` → "Ya lo empujan fuentes de negocio y casi no hay evidencia de fuentes latinoamericanas."
  3. `latam_gap === false` → "Ya hay cobertura en fuentes latinoamericanas: conviene buscar otro ángulo."
  4. en otro caso → "Con estos datos no hay una lectura clara de audiencia."
  Umbrales como constantes con nombre (`TECH_HEAVY_MIN = 0.6`, `BUSINESS_LOW_MAX = 0.3`, `FIT_HIGH_MIN = 60`) y un
  comentario que cite `CLAUDE.md` §7 (el 60 es el mismo umbral de encaje que `publish_now`).
- **Por qué:** se usa `latam_gap` del contrato y no `audience_mix.latam_es`, que mezcla España y Latinoamérica
  (CLAUDE.md §7). Así el front no recalcula el hueco.

### D8 — Reglas visuales fijadas en DESIGN.md

- **Banda de encaje:** Alto ≥ 67 · Medio ≥ 34 · Bajo < 34 (DESIGN.md §9), en constantes.
- **Tamaño de burbuja:** `round(18 + 0.34 · evidence_strength)` px. La seleccionada mide +6 px.
- **Latido:** la tabla del criterio 4.
- **Formato:** aceleración "↑ +86 %", "↓ −30 %" (signo menos U+2212) y "→ 0 %", con `Math.round(acceleration · 100)`.
  Decimales con coma ("6,1×"). Espacio antes de %. Outliers: "2 · máx. 6,1×" si `outlier_count > 0` y
  `top_outlier_ratio` no es nulo; "2" si es nulo; "0" si no hay outliers. Proporciones de `audience_mix` como
  `round(x · 100)` + " %".
- **Etiquetas fijas** (DESIGN.md §9): Emergente · Acelerando · En pico · Saturado · Sin etapa | Publicar ya · Buscar
  ángulo · Esperar caso · Descartar | Observado · Estimado · Preliminar | confianza alta · media · baja.

### D9 — Coordenadas del radar en porcentaje; las capas en HTML

- **Elegido:** el grid de ECharts ocupa todo el área (`left/right/top/bottom: 0`), los ejes van de 0 a 100 y están
  ocultos (`show: false`), y la serie usa `clip: false`. Así la posición de una burbuja es `x = fit %`, `y = (100 −
  momentum) %` del área, sin `convertToPixel`. Los cuadrantes, los nombres de los ejes, la mira, las lecturas, el
  anillo de selección y de hover, el ping, la tarjeta flotante y el barrido son **HTML/CSS sobre el canvas**, como en el
  artboard E. Las capas que se mueven usan `transform` en px, calculados con el tamaño del área
  (`useElementSize` de VueUse), y transiciones de `transform`/`opacity` (DESIGN.md §7: nada de animar
  `left/top/width/height`).
- **ECharts solo pinta:** una serie `scatter` (burbujas estáticas o atenuadas) y una `effectScatter` (las que laten y
  están a la vista), con `rippleEffect.period` por dato, `brushType: 'stroke'`, `scale: 2.4`, `number: 1`, el color
  del trazo de su etapa y `showEffectOn: 'render'`. Las etiquetas de burbuja van en el canvas (`label` por dato, con
  `overflow: 'truncate'`) y se ocultan si el área mide menos de 640 px de ancho o la burbuja está atenuada.
- **Entrada:** `animationDelay` por dato con el ángulo del barrido (fórmula del artboard: `dx = (100 − fit) · 16`,
  `dy = (100 − momentum) · 9`, `φ = atan2(dx, dy)` en grados, `delay = 0.2 + ((10 + φ) / 120) · 1.8` s),
  `animationDuration: 480` y `animationEasing: 'backOut'`. Repetir el barrido = remontar el `VChart` con una `key` que
  cambia con el periodo.
- **Colores:** `buildRadarOption` recibe una paleta (`Record<Lifecycle, { fill, stroke }>` en hex), que
  `OpportunityRadar.vue` resuelve una vez con `getComputedStyle(document.documentElement)` a partir de las variables
  `--lc-*` de `main.css` (DESIGN.md §11: una sola fuente de colores). Los tests pasan una paleta fija.
- **Movimiento reducido:** `usePreferredReducedMotion()` → sin `effectScatter` (todo en `scatter`), `animation:
  false`, sin barrido ni ping.
- **Descartado:** `markArea`/`markLine`/`graphic` para cuadrantes y mira *(más difícil de animar con transform y de
  mantener)*. Al terminar, `lib/echarts.ts` registra solo lo que se usa: Scatter, EffectScatter, Bar (lo usará el
  timeline) y Grid. Se quitan Tooltip, MarkArea, MarkLine y Graphic y se actualiza su comentario.

### D10 — Selección por defecto y hover

- **Elegido:** `selected` = la oportunidad de `?selected=` si existe en la lista; si no, la primera del ranking. El
  hover es estado local de `DiscoverView` (no va en la URL) y se pasa a radar y ranking por props/emits.

### D11 — Marcas para el agente (solo atributos)

- **Elegido:** `data-agent` en los bloques DOM: `filter-lc-<etapa>`, `filter-gap`, `radar`, `detail`, `mix`,
  `limit` (bloque "Qué no sabemos") y `ranking`. Nada más del agente.

### D12 — Estados y textos

- **Carga:** skeletons con la forma de cada tarjeta (#ECEEF1 → #F2F3F5, 1.6s; DESIGN.md §4). Sin spinners.
- **`null`:** tarjeta única "Todavía no hay análisis: el job `analyze` no ha corrido." en lugar del radar y el ranking.
- **Error:** inline en el radar y en el ranking: "No se pudieron cargar las oportunidades." + "Reintentar" (secundario,
  `refetch`).
- **Lista vacía tras filtrar:** el radar sigue con todo atenuado. En el ranking: "Ningún tema cumple estos filtros." +
  "Restablecer vista".
- **H1:** sin filtro, "N oportunidades esta semana" ("1 oportunidad…"); con filtro, "V de N temas". Frase sin filtro:
  "Los temas de IA que más rápido crecen, ordenados por su encaje con líderes y equipos de LATAM."; si N < 10, "Hay N
  temas con datos suficientes esta semana." (constante `EXPECTED_OPPORTUNITIES = 10`, la pregunta de CLAUDE.md §1). Con
  filtro: "Filtro: etapa en pico o saturado · con hueco en LATAM." (las partes que haya).
- **Contadores:** "acelerando", "emergentes" y "con hueco en LATAM", sobre lo filtrado.

## Diseño de módulos

- **Seam principal: `buildRadarView(list, query)`** en `src/lib/radarView.ts`, función pura. Entra la
  `OpportunityList` (o `null`) y el `RadarQuery`, y sale todo lo que la vista pinta. Los componentes no filtran, no
  ordenan ni cuentan: leen el `RadarView`. Es el seam más alto que se puede testear sin DOM, y el que reutilizará el
  agente.
  ```ts
  type Opportunity = Schemas['Opportunity']
  export interface RankedOpportunity extends Opportunity { rank: number }
  export interface RadarView {
    total: number                       // items en la lista
    ranked: RankedOpportunity[]         // orden de la API, rank 1..N
    visible: RankedOpportunity[]        // tras etapas + hueco, ordenado según query.sort
    isFiltered: boolean                 // lifecycle.length > 0 || gap
    plotted: RankedOpportunity[]        // ranked con audience_fit_score != null
    unevaluatedCount: number            // ranked con audience_fit_score == null
    dimmedIds: Set<string>              // plotted fuera de visible o fuera de highlight (si hay); nunca la seleccionada
    selected: RankedOpportunity | null  // D10; null solo si la lista está vacía
    counts: { accelerating: number; emerging: number; latamGap: number }  // sobre visible
  }
  export function buildRadarView(list: OpportunityList | null, query: RadarQuery): RadarView
  ```
  Invariantes: `rank` nunca cambia por filtros ni por orden. `visible ⊆ ranked`. `selected` siempre pertenece a
  `ranked`. Con `list === null` devuelve todo vacío (`total: 0`, `selected: null`).
- **`buildRadarOption(input)`** en `src/lib/radarChart.ts`, pura:
  `{ plotted, dimmedIds, selectedId, hoveredId, palette, reducedMotion, showLabels } → EChartsOption` (D9). También
  exporta `sweepDelaySeconds(fit, momentum)`.
- **Formateo** en `src/lib/opportunityFormat.ts` (puras): `formatAcceleration`, `formatOutliers`, `formatDecimal`,
  `formatScore` (nulo → "no disponible"), `fitBand`, `formatFit`, `formatShare`, `latamGapLabel`, `audienceReading`,
  `pulsePeriodSeconds`, `bubbleSize`, y los mapas de etiquetas `RECOMMENDATION_LABEL`, `GROWTH_LABEL` y
  `CONFIDENCE_LABEL`.
- **Etapas** en `src/lib/lifecycle.ts`: `LIFECYCLE_STYLE: Record<Lifecycle, { label; cssVar: { fill; stroke; bg; fg }; dashed }>`
  (el `Record` obliga a cubrir todas las etapas del contrato) y `resolveLifecyclePalette(style: CSSStyleDeclaration)`.
- **Datos** en `src/api/opportunities.ts`: `useOpportunities(period: Ref<Period>)`, con TanStack Query, `queryKey`
  `['opportunities', period]`, y `USING_FIXTURES` exportado para el chip.
- **Ubicación (CLAUDE.md §10):** `src/lib` (puro), `src/api` (datos), `src/components/radar/*` (secciones del Radar),
  `src/components/opportunities/*` (piezas reutilizables en Explorar), `src/views/DiscoverView.vue` (composición).
  Componentes ≤ 200 líneas (estándares §4).

## Alternativas rechazadas

- **Filtrar en la API** — rechazada: solo acepta una etapa y no filtra por hueco, y el radar necesita la lista entera
  (D5).
- **Recalcular el hueco LATAM desde `audience_mix.latam_es`** — rechazada: mezcla España (CLAUDE.md §7). Se usa
  `latam_gap`.
- **Tooltip de shadcn-vue para `lifecycle_reason`** — rechazada por tiempo: `title` nativo en el chip del ranking, y el
  texto completo en el panel.

## Plan de implementación

Cada paso termina en un commit. Añade ` [HECHO]` al título del paso en ese mismo commit. Los pasos 1–5 son lógica con
tests; los 6–11, componentes con verificación manual. Antes del paso 6, lee `DESIGN.md` entero y abre la referencia
visual del contexto verificado.

### Paso 1 — Tipos generados del contrato, fixture y enums comprobados [HECHO]

- **Archivos:** `frontend/src/types/api.ts`, `data/fixtures/opportunities.json`, `frontend/src/lib/radarQuery.ts`
- **Cambio:**
  1. Si `main` ya contiene `backend/app/api/routes/opportunities.py`, genera desde `main`. Si no, desde
     `origin/data/opportunity-routes`:
     ```bash
     SRC="$(mktemp -d)/routes"
     git worktree add --detach "$SRC" origin/data/opportunity-routes
     (cd "$SRC/backend" && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))") > "$SRC/openapi.json"
     (cd frontend && OPENAPI_URL="$SRC/openapi.json" pnpm gen:api)
     git worktree remove --force "$SRC"
     ```
     Si el import de `app.main` pide variables de entorno, pásale valores ficticios tomados de `.env.example` (no se
     conecta a nada). Comprueba que `src/types/api.ts` contiene `Opportunity`, `OpportunityList`, `Lifecycle` y la ruta
     `/api/v1/opportunities`.
  2. `git show origin/intel/engine:data/fixtures/opportunities.json > data/fixtures/opportunities.json` (o desde
     `main`, si ya está). Sin editarlo.
  3. En `radarQuery.ts`, tipa `Period`, `Lifecycle` y `Confidence` desde `Schemas` y declara los arrays con
     `as const satisfies readonly Schemas['Lifecycle'][]` (ídem para el resto). Actualiza el comentario de las líneas
     3–5: ya no está "pendiente del PR #7".
- **Test primero:** no aplica (generado). `pnpm type-check` tiene que pasar.
- **Verificación:** `cd frontend && pnpm type-check && pnpm test`
- **Commit:** `Generate the Opportunity types and add the shared fixture`

### Paso 2 — La URL del Radar admite varias etapas, hueco y orden [HECHO]

- **Archivos:** `frontend/src/lib/radarQuery.ts`, `frontend/src/composables/__tests__/useRadarQuery.spec.ts`
- **Cambio:** D5. `lifecycle: Lifecycle[]` (lista separada por comas, descarta valores fuera del enum y duplicados),
  `gap: boolean` (`'1'` ↔ `true`; cualquier otro valor → `false`), `sort: RankingSort` (`RANKING_SORTS =
  ['opportunity', 'acceleration'] as const`, por defecto `'opportunity'`, omitido al serializar). Añade `gap` y `sort` a
  `RADAR_QUERY_KEYS`.
- **Test primero:** actualiza los casos existentes al nuevo estado por defecto (`lifecycle: []`, `gap: false`,
  `sort: 'opportunity'`) y añade:
  - `?lifecycle=emerging,bogus,peaking,emerging` → `['emerging', 'peaking']`;
  - `?gap=1&sort=acceleration` se lee y se vuelve a escribir igual;
  - `update({ lifecycle: [], gap: false, sort: 'opportunity' })` quita los tres params y conserva los ajenos.
- **Verificación:** `cd frontend && pnpm test useRadarQuery`
- **Commit:** `Support several stages, the LATAM gap and sorting in the radar URL`

### Paso 3 — Formateo y estilos de etapa [HECHO]

- **Archivos:** `frontend/src/lib/opportunityFormat.ts`, `frontend/src/lib/lifecycle.ts`,
  `frontend/src/lib/__tests__/opportunityFormat.spec.ts`
- **Cambio:** las funciones de "Diseño de módulos" con las reglas de D7 y D8. **`src/lib/lifecycle.ts` ya existe**
  (se adelantó en la fase 0 para paralelizar): úsalo, no lo reescribas.
- **Test primero** (`it.each` con nombres legibles; los valores esperados salen de D7, D8 y DESIGN.md, no del código):
  - `formatAcceleration`: `0.86` → "↑ +86 %", `-0.3` → "↓ −30 %", `0.004` → "→ 0 %".
  - `formatOutliers`: `(2, 6.1)` → "2 · máx. 6,1×", `(2, null)` → "2", `(0, 2.2)` → "0".
  - `fitBand` / `formatFit`: `67` → "Alto · 67", `66` → "Medio · 66", `34` → "Medio · 34", `33` → "Bajo · 33",
    `null` → "no disponible".
  - `formatScore(null)` → "no disponible"; `formatScore(74.2)` → "74".
  - `pulsePeriodSeconds`: aceleración `1.0` → 1.4, `0.5` → 2.0, `0.21` → 2.8, `0.2` → 3.6, `0.01` → 3.6,
    `0` → `null`, `-0.3` → `null`, `unknown` con `1.0` → `null`.
  - `bubbleSize(74)` → 43; `bubbleSize(0)` → 18.
  - `audienceReading`: un caso por regla de D7, más el caso de frontera `tech 0.6 · business 0.3` (→ no cumple la
    regla 1).
  - `latamGapLabel`: `true` / `false` / `null`.
- **Verificación:** `cd frontend && pnpm test opportunityFormat`
- **Commit:** `Add opportunity formatting and lifecycle styles`

### Paso 4 — Datos: `useOpportunities` con fixtures explícitos [HECHO]

- **Archivos:** `frontend/src/api/opportunities.ts`, `frontend/env.d.ts`, `frontend/vite.config.ts`,
  `frontend/tsconfig.app.json` (y `tsconfig.vitest.json` si hace falta), `frontend/src/api/__tests__/opportunities.spec.ts`
- **Cambio:**
  - `env.d.ts`: `interface ImportMetaEnv { readonly VITE_USE_FIXTURES?: string; readonly VITE_API_BASE_URL?: string }`.
  - `vite.config.ts`: alias `@fixtures` → `../data/fixtures` (con `fileURLToPath`) y `server.fs.allow` con la raíz
    del repo (`fileURLToPath(new URL('..', import.meta.url))`), para que el dev server pueda servir el JSON. Alias
    equivalente en `paths` de TS.
  - `opportunities.ts`: `USING_FIXTURES = import.meta.env.VITE_USE_FIXTURES === 'true'`. Con fixtures,
    `(await import('@fixtures/opportunities.json')).default.opportunities` tipado como `OpportunityList` (cast con un
    comentario de una línea: el JSON ya se generó contra el schema y el test lo vigila). Sin fixtures,
    `api.GET('/api/v1/opportunities', { params: { query: { period } } })`: `error` → `throw new Error('GET /opportunities falló')`;
    `data === null` → `null`. Sin fallback a fixtures.
- **Test primero** (`opportunities.spec.ts`):
  - el fixture está marcado (`_fixture` empieza por "MOCK" y todos los `topic` empiezan por "[MOCK]");
  - cada `lifecycle`, `recommendation`, `growth_status` y `confidence` del fixture está en su enum;
  - cada score no nulo está entre 0 y 100.
- **Verificación:** `cd frontend && pnpm test opportunities && pnpm type-check`
- **Commit:** `Load opportunities from the API or from the marked fixture`

### Paso 5 — View-model puro del Radar [HECHO]

- **Archivos:** `frontend/src/lib/radarView.ts`, `frontend/src/lib/__tests__/radarView.spec.ts`
- **Cambio:** `buildRadarView` según "Diseño de módulos", más `radarHeadline(view, query)` y
  `radarSubline(view, query)` con los textos de D12.
- **Test primero** (con los items del fixture como datos de entrada; los valores esperados se escriben a mano a partir
  del fixture):
  - sin filtros: `total 5`, `rank` 1..5 en el orden de la API, `plotted` sin `opp_005`, `unevaluatedCount 1`;
  - `lifecycle: ['peaking', 'saturated']` → `visible` = `opp_003` y `opp_004`, con su `rank` original; el resto de
    `plotted` en `dimmedIds`; `counts` sobre lo visible;
  - `gap: true` → solo `latam_gap === true` (`opp_001`);
  - `sort: 'acceleration'` → `visible` ordenado por aceleración descendente, con el `rank` intacto;
  - `selected`: id válido → ese; id inexistente o `null` → `rank 1`; seleccionada filtrada → no está en `dimmedIds`;
  - `highlight` no vacío → lo no resaltado se atenúa;
  - `list === null` → vacío, `selected: null`;
  - textos: "5 oportunidades esta semana", "2 de 5 temas", "Hay 5 temas con datos suficientes esta semana.", "Filtro:
    etapa en pico o saturado." y "1 oportunidad esta semana".
- **Verificación:** `cd frontend && pnpm test radarView`
- **Commit:** `Build the radar view model from the opportunity list and the URL`

### Paso 6 — Piezas: chips, anillo de score y barra de métrica [HECHO]

- **Archivos:** `frontend/src/components/opportunities/{LifecycleChip,RecommendationChip,ScoreRing,MetricBar}.vue`
- **Cambio:** DESIGN.md §4. `ScoreRing` recibe `score: number | null`, cuenta hasta el valor con `useTransition` de
  VueUse (450 ms, ease-out; con movimiento reducido, sin transición) y muestra "no disponible" si es nulo (anillo
  vacío). `MetricBar` crece con `scaleX` (`transform-origin: left`). Clases de Tailwind con los tokens de
  `main.css`; colores de etapa con `var(--lc-*)`.
- **Test primero:** verificación manual: se ven en el paso 9.
- **Verificación:** `cd frontend && pnpm lint && pnpm type-check`
- **Commit:** `Add lifecycle and recommendation chips, score ring and metric bar`

### Paso 7 — Cabecera, filtros y periodo [HECHO]

- **Archivos:** `frontend/src/components/radar/{RadarHero,RadarFilters}.vue`,
  `frontend/src/components/layout/{AppHeader,PeriodControl}.vue`
- **Cambio:**
  - `RadarHero`: H1 y frase (paso 5) más tres contadores.
  - `RadarFilters`: segmented multi de etapas, con el punto de color (hace de leyenda), toggle "Hueco en LATAM",
    "Filtros activos" y "Restablecer vista" (`update({ lifecycle: [], gap: false, highlight: [] })`). Botones reales con
    `aria-pressed` y `data-agent` (D11).
  - `PeriodControl` en `AppHeader`, solo si `route.name === RouteName.Discover`, más el aviso de D1 (recibe el
    `period` de la respuesta por prop o lo lee del caché de la query).
  - Chip "Datos de ejemplo" (#FFF0DC / #8A4B00) en `AppHeader` si `USING_FIXTURES`.
- **Test primero:** verificación manual.
- **Verificación:** `cd frontend && pnpm lint && pnpm type-check`
- **Commit:** `Add the radar header, filter row and period control`

### Paso 8 — El radar

- **Archivos:** `frontend/src/lib/radarChart.ts`, `frontend/src/lib/__tests__/radarChart.spec.ts`,
  `frontend/src/components/radar/{OpportunityRadar,RadarSelectionLayer,RadarSweep}.vue`, `frontend/src/lib/echarts.ts`
- **Cambio:** D9.
  - `OpportunityRadar`: la tarjeta, el título "Radar" con su nota, los nombres de los ejes, los cuadrantes y su lavado,
    el `VChart` y la nota de sin evaluar (D3).
  - `RadarSelectionLayer`: mira, lecturas, anillos de selección y hover, ping y tarjeta flotante (chip de etapa, tema,
    "Oportunidad 74 · ↑ +86 %").
  - `RadarSweep`: el haz CSS.
  - Eventos del chart: `click` → `update({ selected })`, `mouseover` / `mouseout` → emite `hover`.
  - Limpia `lib/echarts.ts` (D9).
- **Test primero** (`radarChart.spec.ts`, con una paleta fija):
  - una burbuja que crece y no está atenuada va en `effectScatter` con su `rippleEffect.period`;
  - una atenuada va en `scatter` con `opacity 0.16` y sin label;
  - `reducedMotion: true` → no hay serie `effectScatter` y `animation: false`;
  - `unknown` → relleno blanco con borde discontinuo;
  - `sweepDelaySeconds(100, 100)` → 0.35 s; `sweepDelaySeconds(0, 0)` → 1.26 s (φ ≈ 60.64°; redondeado a 2 decimales).
- **Verificación:** `cd frontend && pnpm test radarChart && pnpm lint && pnpm type-check`
- **Commit:** `Draw the opportunity radar with sweep, pulse and selection layers`

### Paso 9 — Panel de detalle y bento

- **Archivos:** `frontend/src/components/radar/{OpportunityDetail,AudienceMixCard,WhyItMattersCard}.vue`
- **Cambio:**
  - `OpportunityDetail`: criterio 10, con `data-agent="detail"`.
  - `AudienceMixCard`: barra apilada Tech · Negocio · En español, tres cifras y `audienceReading`, con
    `data-agent="mix"`.
  - `WhyItMattersCard`: `why_it_matters` y "Qué no sabemos" con la lista de `limitations` (`data-agent="limit"`). Si
    la lista está vacía: "El análisis no registró limitaciones."
  - Textos con fundido y 4 px de subida al cambiar de selección.
- **Test primero:** verificación manual.
- **Verificación:** `cd frontend && pnpm lint && pnpm type-check`
- **Commit:** `Add the opportunity detail panel and the audience and why cards`

### Paso 10 — Ranking

- **Archivos:** `frontend/src/components/radar/OpportunityRanking.vue`
- **Cambio:** criterio 11.
  - Filas `<button>` de 56 px con `aria-pressed`. La seleccionada lleva lavado de señal y el puesto en negrita.
  - Hover enlazado por emit. Orden "Oportunidad · Aceleración" ligado a `?sort`.
  - `overflow-x: auto` con ancho mínimo de 1000 px.
  - Entrada escalonada de 40 ms por fila.
  - `data-agent="ranking"`.
  - Vacío tras filtrar (D12).
- **Test primero:** verificación manual.
- **Verificación:** `cd frontend && pnpm lint && pnpm type-check`
- **Commit:** `Add the opportunity ranking table`

### Paso 11 — Composición de la vista, estados y nota al pie

- **Archivos:** `frontend/src/views/DiscoverView.vue`, `frontend/src/components/radar/RadarStates.vue` (skeletons,
  vacío y error), `frontend/src/components/radar/RadarFootnote.vue`
- **Cambio:**
  - `DiscoverView` une `useRadarQuery`, `useOpportunities(period)`, `buildRadarView` y el hover local, con el layout de
    DESIGN.md §5 (radar `flex: 999 1 680px`, panel `flex: 1 1 380px`, bento 1 : 2).
  - Estados de D12.
  - `RadarFootnote` con `monitoring_started_at` (`formatUtcTimestamp`) y las lecturas de DESIGN.md §9.
- **Test primero:** verificación manual con `cd frontend && VITE_USE_FIXTURES=true pnpm dev`. Comprueba:
  - criterios 1–15 con el fixture, incluido `opp_005` fuera del radar y en el ranking;
  - `?lifecycle=peaking,saturated&gap=1&sort=acceleration&selected=opp_003` reproduce la vista al recargar;
  - 24 h → aparece el aviso de periodo;
  - con el modo de movimiento reducido del sistema, nada se anima;
  - a 390 px de ancho no hay scroll horizontal de página;
  - sin el flag y sin API → estado de error, no los fixtures.
- **Verificación:** `cd frontend && pnpm lint && pnpm type-check && pnpm test && pnpm build`
- **Commit:** `Compose the radar view with loading, empty and error states`

### Paso 12 — Docs [HECHO]

- **Archivos:** `README.md` (sección frontend), `.claude/rules/frontend.md` (tabla "Librerías y recursos de UI")
- **Cambio:**
  - README: cómo arrancar con fixtures (`VITE_USE_FIXTURES=true pnpm dev`) y aviso de que se ven con el chip "Datos de
    ejemplo".
  - `frontend.md`: fila nueva "Utilidades de composición | `@vueuse/core` (v14, la misma copia que Reka UI) | tamaño de
    elementos, movimiento reducido, transiciones numéricas, portapapeles".
- **Test primero:** no aplica.
- **Verificación:** `cd frontend && pnpm lint`
- **Commit:** `Document the fixture mode and VueUse`

## Estrategia de test

- **Seams:**
  - `buildRadarView` y `buildRadarOption`, ambas puras: lo que la vista y el chart reciben.
  - `parseRadarQuery`/`serializeRadarQuery` a través de `useRadarQuery`, como el spec existente.
  - El formateo.
- **Prior art:** `frontend/src/composables/__tests__/useRadarQuery.spec.ts` (montar un probe con router de memoria) y
  `frontend/src/lib/__tests__/format.spec.ts` (funciones puras).
- **Casos que entran:** los listados en los pasos 2, 3, 4, 5 y 8. Cada uno sale de un criterio de aceptación, de una
  regla de DESIGN.md o CLAUDE.md, o de un dato real del fixture (fit nulo, `latam_gap` nulo, aceleración negativa,
  `unknown`).
- **Casos descartados por ruido:** snapshots de componentes, tests de estilos o clases, tests de ECharts renderizando
  en jsdom, y animaciones.
- **Parametrización:** `it.each` en formateo (bandas, latido, aceleración) con descripciones legibles.

## Verificación final

```bash
cd frontend
pnpm lint
pnpm type-check
pnpm test
pnpm build
VITE_USE_FIXTURES=true pnpm dev   # revisión manual del paso 11; pega lo comprobado
```

## Riesgos

- **El import de `app.main` falla en el worktree temporal (paso 1)** — falta una variable de entorno o una
  dependencia → valores ficticios de `.env.example`. Si sigue fallando, para y anótalo en "Preguntas abiertas"; no
  escribas tipos a mano.
- **#7 o #9 cambian el schema antes de mergear** — `pnpm gen:api` de nuevo cuando lleguen a `main`. Si un tipo cambia,
  `vue-tsc` lo señala.
- **`server.fs.allow` bloquea el JSON en dev** — error 403 en la consola al cargar con fixtures → revisa que la raíz
  del repo esté en `fs.allow`.
- **El tamaño de `OpportunityRadar` supera las 200 líneas** — saca más capas a `RadarSelectionLayer` o a un
  composable `useRadarGeometry`.
- **Va justo de tiempo** — orden de prioridad si hay que cortar: pasos 1–5, 8, 9, 11 y 7 (sin periodo); después 10 y
  12. Avisa en el informe de lo que quede.

## Historial de intentos

| Fecha | Qué bloqueó | Qué se decidió | Commits que quedaron |
| --- | --- | --- | --- |

## Preguntas abiertas

- (ninguna)
