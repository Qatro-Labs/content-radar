# fe-dashboard-v2 — D2: Radar sin selección, expediente del tema y Explorar «Lo que está funcionando»

> Plan generado con `/spec`. Lo implementa `plan-implementer` con contexto limpio.
> El implementador NO ve la conversación que produjo este documento: todo lo que necesite tiene que
> estar escrito aquí.

## Metadatos

- **Slug:** `fe-dashboard-v2` · **Issue:** ninguno
- **Owner (CLAUDE.md §3):** Frontend lead
- **Prioridad (CLAUDE.md §12):** P0 (dashboard Vue con Radar y detalle; evidencias verificables) · **Checkpoint que
  desbloquea (§13):** MVP P0 end-to-end (dom 00:30 ESP) y revisión de frontend (dom 12:30 ESP)
- **Valor (filtro de CLAUDE.md §12):** "elegir una oportunidad → revisar scores y evidencia → entender por qué importa
  → obtener un brief" (hoy no existe el paso «revisar evidencia»: `/explore/:id` está vacío) · **Preguntas de
  `docs/brief.md` §4:** 1, 2, 3, 4 y 6
- **Repo:** `/Users/dacorredor/projects/personal/qatro_labs/content-radar`
- **Rama base:** `main` @ `2f546a2`
- **Rama de trabajo:** `fe/dashboard-v2` (integración). Ramas de cada parte: `fe/dashboard-v2-radar`,
  `fe/dashboard-v2-dossier`, `fe/dashboard-v2-explore` (ver «Cómo se ejecuta»)
- **Fecha:** 2026-10-17 22:50 ESP
- **Contratos tocados:** ninguno. Solo consume `GET /opportunities`, `GET /opportunities/{id}`, `/evidence` y
  `/timeline`, que ya están en `frontend/src/types/api.ts`. No se regenera `api.ts`.
- **Auditoría tras `/build`:** sí (`code-standards-auditor`): son las vistas de la demo
- **Estado del gate:** `LISTO`

## Cómo se ejecuta (paralelo)

1. **Fase 0 (coordinador, en `fe/dashboard-v2`):** pasos 0.1–0.4. Archivos compartidos por varias partes. Se
   commitean antes de abrir las partes.
2. **Tres partes en paralelo**, cada una en su worktree y su rama, creadas desde `fe/dashboard-v2` tras la fase 0.
   Cada parte toca **solo** sus archivos (tabla «Propiedad de archivos»). Un `plan-implementer` por parte, con la
   instrucción «implementa solo la Parte N; no edites el plan».
3. **Integración (coordinador):** merge `--no-ff` en `fe/dashboard-v2` en el orden **Parte 2 → Parte 1 → Parte 3**
   (prioridad de la demo: el expediente es «revisar evidencia»). Paso I.1 y verificación final. Después,
   `code-standards-auditor` sobre `main...fe/dashboard-v2` y un solo PR. Si una parte no llega a tiempo, el PR sale
   con las que hay y la que falta va en un segundo PR.
4. El coordinador marca `[HECHO]` en este archivo al mergear cada parte. Los implementadores **no** lo editan.

En cada worktree, antes de nada: `cd frontend && pnpm install --frozen-lockfile` (solo pnpm; nunca npm, npx ni yarn).

## Problema

El Radar actual (artboard E) selecciona el n.º 1 por defecto, muestra un panel de detalle con barras y un bento
«Para quién importa / Por qué importa» que repite datos, y sus botones llevan a `/explore/:id`, que está vacío. Quien
hace la demo no puede «revisar la evidencia» de un tema: no hay expediente con el desglose del score, la evolución,
los criterios de encaje con sus citas ni la lista de piezas con su rendimiento frente al canal. Tampoco hay una vista
que responda «qué piezas están funcionando». El diseño D2 (aprobado el 17/10) resuelve las tres cosas y está
documentado en `DESIGN.md` y `.claude/rules/frontend.md` (PR #37).

## Criterios de aceptación

Se verifican con datos reales (`pnpm dev` contra la API) y con `VITE_USE_FIXTURES=true pnpm dev`.

**Parte 1 — Radar (`/`)**

1. Sin `?selected=` válido no hay tema seleccionado: sin mira, sin lecturas en los ejes, sin ping, y el panel lateral
   muestra «Esta semana».
2. Cabecera: H1 «38 temas esta semana» (con filtro: «3 de 38 temas»), frase y, a la derecha, cuatro contadores-filtro
   (Publicar ya · Acelerando · Emergentes · Sin etapa) con **totales fijos** y **selección única**; pulsar el activo lo
   quita. Con filtro aparece «Restablecer vista». Ya no hay fila de filtros ni filtro «Hueco en LATAM».
3. Fila principal: a la izquierda la tarjeta del radar (leyenda de etapas en su cabecera, nota del latido debajo) y el
   ranking; a la derecha el panel lateral sticky.
4. Panel «Esta semana»: los temas `publish_now` en orden del ranking (botones que seleccionan), la línea «N piezas
   rinden 3× o más que su canal · Ver ›» (→ `/explore`) y «Qué no sabemos» con las cifras de etapa contadas desde la
   API (D7).
5. Panel con selección: vista previa (D8) con «← Esta semana», «Ver expediente →» (→ `/explore/:id`) y «Generar
   brief» (→ `/create?opportunity=:id`). Clic en la burbuja o fila ya seleccionada la deselecciona.
6. Ranking: columnas Puesto · Tema · Etapa · 6 días · Aceleración · Oportunidad; 10 filas y «Ver los N temas» / «Ver
   menos» si hay más de 10; mini barras de 6 periodos de 24 h desde `/timeline` (escala común, 5 piezas llenan la
   barra). Se conservan «Encaje no disponible» y la etiqueta Observado · Estimado · Preliminar.
7. Etiquetas de burbuja solo en los temas `publish_now` y solo sin selección. Tarjeta flotante solo en hover.
8. La primera selección tras el barrido responde al instante (bug actual: espera el retardo del barrido).

**Parte 2 — Expediente (`/explore/:id`)**

9. Cabecera con «Radar» (→ `/?selected=:id`), chip de etapa, tema, línea de estado, recomendación y su motivo; a la
   derecha «Cómo se compone»: anillo, «Oportunidad · puesto R de N», penalizaciones y los 5 componentes de
   `score_breakdown` con barra, cifra y peso.
10. «Evolución»: ventana anterior y actual lado a lado (3 barras cada una), aceleración, velocidad y
    `lifecycle_reason`, rotulado como periodos de 24 h que terminan a la hora de `last_updated`.
11. «Por qué importa» completo y los 6 criterios de encaje con su nivel, justificación y chips de las piezas citadas.
    Pulsar un chip resalta su pieza en la evidencia (el resto a opacidad 0.4) y hace scroll hasta ella.
12. «Evidencia»: piezas en el orden de la API (outliers primero), filtro por plataforma, «Para quién importa» en su
    cabecera, y en cada pieza la barra «Rendimiento frente a su canal» (marcas 1× y 3×, escala hasta 6×).
13. «Siguiente paso» (recomendación, «Generar brief», «Copiar enlace») junto a «Qué no sabemos» (`limitations`).
14. Estados: carga con skeletons, id inexistente (404) con mensaje propio, error inline con «Reintentar».

**Parte 3 — Explorar sin tema (`/explore`)**

15. H1 «Lo que está funcionando», frase con cifras reales y contadores Outliers · YouTube · Hacker News (filtros de
    selección única en `?filter=`) más RSS (no interactivo, «sin métricas públicas»). **Sin gráfico.**
16. Tabla «Piezas» con las piezas de la evidencia de todos los temas, ordenada por ratio (sin ratio al final), 25 filas
    y «Ver 25 más», filtro de texto por título o fuente.
17. Panel lateral sticky: «Dónde está funcionando» (temas y fuentes con más outliers + «Qué no sabemos») o, con una
    pieza seleccionada, su detalle con «Ver original ↗» y «Abrir el tema» (→ `/explore/:id`).

**Todas**

18. Ningún dato ausente se muestra como 0 o guion: se escribe «no disponible» o el texto de D10.
19. `pnpm lint && pnpm type-check && pnpm test && pnpm build` en verde (desde `frontend/`).

## No-objetivos

- La barra del agente y su presencia (tarea aparte, después de Explorar). Se mantienen y mueven las marcas
  `data-agent`.
- La cabecera de la app (iconos de nav, buscador ⌘K, «90 fuentes»), salvo el estado activo de «Explorar» (paso 0.1).
- La vista Crear. «Generar brief» solo enlaza a `/create?opportunity=:id`.
- El gráfico de dispersión «Rendimiento por fecha» de Explorar: **se quita** (decisión de David, D3).
- Cambios de backend o de contrato: conteos diarios en `GET /opportunities`, endpoint de todas las piezas, `id` de
  pieza, campo `recommendation` en `RadarPatch`. Se piden en el canal; aquí no se tocan.
- Componentes shadcn-vue nuevos, dependencias nuevas, tema oscuro, regenerar `src/types/api.ts`.
- Botón de orden del ranking (el orden por aceleración se queda solo en la URL, D6).

## Reglas de CLAUDE.md §2 en juego

- **Regla 3 (nunca inventar datos):** todas las cifras (temas `publish_now`, outliers, «Sin etapa», piezas por
  plataforma) se cuentan desde la API, nunca fijas como en el canvas. Un dato ausente se escribe «no disponible» o el
  texto de D10. Las piezas sin ratio no se dibujan como 0. Las mini barras sin datos dicen «no disponible».
- **Regla 4 / estándares §9 (el frontend no calcula scores):** solo se cuenta, agrupa, ordena y formatea. Los únicos
  umbrales del front son de presentación y ya están fijados en `CLAUDE.md` §7 (`≥ 3×` outlier, `≥ 2×` destacada) o
  en `DESIGN.md` (escala de 6× y de 5 piezas/día). `is_outlier` se lee de la API, no se recalcula.
- **Regla 5 (tipo de evidencia):** la etiqueta Observado · Estimado · Preliminar va en el ranking, la vista previa, la
  cabecera y la evolución del expediente.
- **Regla 6 (texto externo no confiable):** títulos, fuentes, `why_it_matters`, justificaciones y `limitations` se
  pintan con interpolación de Vue. **Nunca `v-html`.** Los enlaces a piezas llevan `target="_blank"` y
  `rel="noopener noreferrer"`.

## Contexto verificado del código

| Qué | Dónde | Estado actual |
| --- | --- | --- |
| Rutas | `frontend/src/router/index.ts:5-26` | `RouteName` Discover · Explore · Create; `/explore/:id?` → `ExploreView` (una sola ruta) |
| Explorar | `frontend/src/views/ExploreView.vue:1` | Placeholder de 9 líneas |
| Nav activa | `frontend/src/components/layout/AppHeader.vue:35` | `aria-current` si `route.name === view.name` |
| Selección por defecto | `frontend/src/lib/radarView.ts:91-92` | `?? ranked.at(0)`; el test `radarView.spec.ts:84-88` la espera |
| Contadores | `frontend/src/lib/radarView.ts:26,77-83` | `{accelerating, emerging, latamGap}` de lo visible |
| Filtro | `frontend/src/lib/radarView.ts:47-56` | etapas + `gap`; sin recomendación |
| Estado URL | `frontend/src/lib/radarQuery.ts:33-103` | `RadarQuery` (period, lifecycle[], confidence, topic, selected, highlight, gap, sort); claves = nombres de param |
| Vista Radar | `frontend/src/views/DiscoverView.vue:46-82` | Gate `data && view.selected`; filtros, radar+detalle, bento, ranking, nota |
| Panel actual | `frontend/src/components/radar/OpportunityDetail.vue:133-148` | «Ver evidencia» → `RouteName.Explore` con `id`; «Generar brief» → Create |
| Retardo de la 1.ª selección | `frontend/src/components/radar/RadarSelectionLayer.vue:59-77` | `isFirstSelection` añade el retardo del barrido a la primera selección, sea cuando sea |
| Etiquetas de burbuja | `frontend/src/lib/radarChart.ts:178-181` | `isLabelShown` |
| Anillo | `frontend/src/components/opportunities/ScoreRing.vue:10-11,37` | Fijo a 112 px (`size-28`) |
| Nota al pie | `frontend/src/components/radar/RadarFootnote.vue:1` | «Datos desde…», latido, tamaño, saturación, encaje |
| Datos | `frontend/src/api/opportunities.ts:1-34` | Solo `useOpportunities(period)`; fixtures con `USING_FIXTURES` |
| Caché | `frontend/src/api/queryClient.ts:4` | `staleTime` 60 s, `retry: 1` |
| `useQueries` | `@tanstack/vue-query` 5.104.1, `build/modern/useQueries.d.ts:181` | Acepta `queries` reactivo y `combine` |
| Formato | `frontend/src/lib/opportunityFormat.ts` | `formatAcceleration`, `isDeclining`, `formatShare`, `formatDecimal`, `formatOutliers`, `formatScore`, `formatFit`, `fitBand`, `audienceReading`, `latamGapLabel`, `RECOMMENDATION_LABEL`, `GROWTH_LABEL`, `CONFIDENCE_LABEL`, `SCORE_MAX` |
| Fechas | `frontend/src/lib/format.ts:11` | Solo `formatUtcTimestamp` → «17/10, 02:50 UTC» |
| Etapas | `frontend/src/lib/lifecycle.ts:39` | `LIFECYCLE_STYLE` (label, colores) |
| Tokens | `frontend/src/assets/main.css` | DESIGN.md §11; no hay token para #C9CED6 ni #D5D9DF |
| Fixture | `data/fixtures/opportunities.json` | `{_fixture, opportunities, evidence: {opp_00X: Evidence[]}, timeline: {opp_00X: OpportunityTimeline}}`; `opp_005` sin breakdown ni criterios |
| `Opportunity` | `frontend/src/types/api.ts:470-525` | `score_breakdown?` (null si no hay score), `audience_fit_criteria?`, `recommendation_reason?`, `why_it_matters`, `limitations` |
| `ScoreBreakdown` | `frontend/src/types/api.ts:630` | `components` (siempre 5, orden fijo: `momentum`, `audience_fit`, `cross_source`, `freshness`, `actionability`; `value` 0–100, `weight` 0–1), `penalties` (`single_source` \| `small_sample`, `points`), `total` |
| `AudienceFitCriterion` | `frontend/src/types/api.ts:192` | `criterion` (`business_impact` · `org_application` · `exec_readability` · `latam_relevance` · `pillar_fit` · `actionable_content`), `justification`, `evidence_urls: string[]`, `level` 0–5 |
| `Evidence` | `frontend/src/types/api.ts:275-320` | `url, source, platform, segment, title, published_at, observed_at, language?, metrics{views, likes, comments, points, shares}, velocity?{value, unit: string}, outlier_ratio?, is_outlier?, collection`. **Sin `id`**: la clave es `url` |
| `OpportunityTimeline` | `frontend/src/types/api.ts:540,722` | `{opportunity_id, window_days: 3, points: [{date, count, window: 'current'\|'previous'}]}` (6 puntos) |
| API: detalle | `GET /api/v1/opportunities/{opportunity_id}` | 404 «Oportunidad no encontrada» si el id no está en la ejecución servida |
| API: evidencia | `GET /api/v1/opportunities/{id}/evidence` | Ya ordenada: outliers primero por ratio descendente, luego sin ratio por fecha. Máximo 25 piezas por tema |
| Referencia visual | `/private/tmp/claude-501/-Users-dacorredor-projects-personal-qatro-labs-content-radar/70164a8d-6132-4e1b-ab6e-18067fbcad26/scratchpad/artifact-files/3161aba0-86e1-4001-9cc5-67fd96d5d7b7/project/` | `Dash.dc.html` (Parte 1), `Expediente.dc.html` (Parte 2), `Evidencia.dc.html` (Parte 3). Prototipos HTML con **datos fijos del run #29**: sirven para layout, textos y movimiento; las cifras se cuentan desde la API. Su barra del agente no entra. Si la ruta ya no existe, basta `DESIGN.md` + este plan |

**Datos reales del run servido (17/10, 19:09 UTC)**, para comprobar a mano: 38 temas; `publish_now` 3 (`opp_911`,
`opp_1272`, `opp_171`); `accelerating` 12, `emerging` 3, `unknown` 19 (8 de ellos `preliminary`); Σ `outlier_count`
= 27; 356 piezas de evidencia, **356 URLs únicas** (ninguna repetida entre temas); por plataforma: YouTube 96 (13 sin
ratio), Hacker News 145 (0 sin ratio; 138 con `0 puntos/h`), RSS 115 (todas sin métricas ni ratio); 27 piezas
`is_outlier`; 1 tema con 25 piezas (el tope). Ningún tema tiene `score_breakdown`, criterios ni
`recommendation_reason` nulos, pero el fixture `opp_005` sí: sirve para los estados vacíos.
`monitoring_started_at = 2026-10-16T00:00:00Z`. HN mide el ratio contra el p90 de su búsqueda; YouTube contra la
mediana del canal (ajustada por edad).

## Decisiones tomadas

### D1 — Paralelo con fase 0 compartida; merge 2 → 1 → 3; un PR

- **Elegido:** fase 0 del coordinador con lo que comparten las partes; tres worktrees con archivos disjuntos; merge
  `--no-ff` por prioridad de la demo.
- **Por qué:** quedan ~1 h 40 min para el MVP de las 00:30; el expediente es el paso que falta en la demo.
- **Descartado:** solo el expediente ahora *(David eligió las tres en paralelo)*.

### D2 — Contadores-filtro: totales fijos, selección única, «Publicar ya» en la URL

- **Elegido:** los contadores cuentan **todos** los temas (no lo filtrado). Selección única: pulsar uno aplica
  `resetViewPatch()` + su filtro; pulsar el activo aplica `resetViewPatch()`. «Acelerando», «Emergentes» y «Sin etapa»
  escriben `lifecycle: [etapa]`; «Publicar ya» escribe el param nuevo `recommendation=publish_now`. Un contador está
  pulsado solo si el estado de filtros es exactamente el suyo. Si el agente (o la URL) pone otra combinación (varias
  etapas, `gap`), ningún contador queda pulsado y la frase describe el filtro como hoy. `DESIGN.md` §5 se corrige
  (paso 0.4).
- **Por qué:** es lo aprobado en el canvas; con selección única, contar lo filtrado dejaría los demás contadores a 0.
- **Descartado:** contar lo filtrado *(DESIGN.md antiguo)*. El nombre del param sigue el patrón del código
  (`RADAR_QUERY_KEYS` = nombres de param), así que es `recommendation`, no `rec`.

### D3 — Explorar sin gráfico

- **Elegido:** Explorar sin tema = cabecera + contadores + tabla de piezas + panel lateral. Sin dispersión. Se quita
  de `DESIGN.md` §5 y §8 y de `.claude/rules/frontend.md` (paso 0.4). `src/lib/echarts.ts` no se toca.
- **Por qué:** David: «no aporta valor». La tabla ordenada por ratio ya responde «qué piezas funcionan».

### D4 — «Qué no sabemos» de «Esta semana», contado desde la API

- **Elegido:** «**Qué no sabemos.** {u} de {N} temas no tienen etapa: {p} por falta de datos y {u − p} porque ninguna
  regla se cumple. Datos desde el {formatUtcTimestamp(monitoring_started_at)}.» con `u` = temas `lifecycle ===
  'unknown'` y `p` = de esos, `growth_status === 'preliminary'` (CLAUDE.md §7: `preliminary` = datos insuficientes).
  Si `p = 0` u `u − p = 0`, se omite esa parte («19 de 38 temas no tienen etapa: ninguna regla se cumple.»); si
  `u = 0`, «Todos los temas tienen etapa.». Singular con 1 («1 de 38 temas no tiene etapa»).
- **Por qué:** la frase del canvas («no tienen datos suficientes») es falsa para 11 de los 19.

### D5 — Datos: un composable por recurso, y versiones múltiples con `useQueries`

- **Elegido:** en `src/api/opportunities.ts`: `useOpportunity(id)`, `useOpportunityEvidence(id)`,
  `useOpportunityTimeline(id)`, `useOpportunityTimelines(ids)` y `useOpportunitiesEvidence(ids)`. Las múltiples usan
  `useQueries` con las **mismas `queryKey`** que las individuales (caché compartida). Mini barras: una llamada a
  `/timeline` por fila **visible** (10, o todas con «Ver los N»). Explorar: una llamada a `/evidence` por tema (38;
  HTTP/2, ~0,4 s cada una).
- **Por qué:** no existe un endpoint de conteos ni de piezas; pedirlos es contrato (no-objetivo).

### D6 — Ranking: columnas de D2, sin botón de orden

- **Elegido:** columnas Puesto · Tema · Etapa · 6 días · Aceleración · Oportunidad (grid
  `52px minmax(240px,2fr) 128px 84px 104px 150px`, gap 14px, ancho mínimo 780 px con scroll dentro de la tarjeta).
  Bajo el tema, «Encaje no disponible» si `audience_fit_score` es nulo; bajo la aceleración, la etiqueta de
  `growth_status` (regla 5). Se quitan las columnas Outliers, Fuentes y Acción y el segmented de orden; `sort` sigue
  en la URL y en `buildRadarView` (lo usa el agente). `DESIGN.md` §6 pasa de 1000 a 780 px (paso 0.4).

### D7 — Selección: sin defecto, con toggle

- **Elegido:** `selected` = la oportunidad de `?selected=` si existe; si no, `null`. Clic en la burbuja o fila
  seleccionada → `selected: null`. «← Esta semana» → `selected: null`. Hover sigue siendo estado local.

### D8 — Vista previa del tema (panel con selección)

- **Elegido**, de arriba abajo: botón secundario «Esta semana» con `ChevronLeft` (`@lucide/vue`) · `LifecycleChip` ·
  tema (Bricolage 28px) · «{Observado} · confianza {media} · {N} fuentes» («1 fuente») · `ScoreRing` de 104 px +
  «Oportunidad · puesto R de N» + `RecommendationChip` · `recommendation_reason` (14px; se omite si es nulo) ·
  `why_it_matters` con `line-clamp-3` (sin «Leer completo»: el texto entero vive en el expediente) · tres baldosas
  Aceleración (`formatAcceleration`, color Negativo si `isDeclining`) · Encaje (`formatFit`) · Outliers
  (`outlier_count`) · primario «Ver expediente →» y secundario «Generar brief». `data-agent="detail"`.

### D9 — «Esta semana» con 0 temas `publish_now`

- **Elegido:** «Ningún tema cumple hoy las condiciones de «Publicar ya». Los primeros del ranking:» y los 3 primeros
  por puesto, con su `RecommendationChip`. Con 1+ temas: «{n} temas para publicar ya: crecen y encajan con la
  audiencia de 30X.» («1 tema para publicar ya: crece y encaja…»).

### D10 — Piezas sin ratio y rótulos de rendimiento

- **Elegido:** sin `outlier_ratio`: «Sin métricas públicas» si la plataforma es `rss` o todas sus métricas son nulas;
  si no, «Sin línea base del canal» (`docs/brief.md` §7: «sin línea base»). Etiqueta del ratio: `is_outlier === true`
  → «Outlier»; ratio ≥ 2 → «Destacada» (CLAUDE.md §7); menos → sin etiqueta. Leyenda: «1× = mediana del canal
  (YouTube, ajustada por la edad de la pieza) o p90 de la búsqueda (Hacker News). 3× = outlier. La barra llega hasta
  6×.» Velocidad: «Velocidad entre la primera y la última medición.» `0 puntos/h` se muestra tal cual (es una
  medición real).
- **Por qué:** 13 piezas de YouTube tienen métricas pero no referencia: «la fuente no publica métricas» sería falso.

### D11 — Citas de los criterios: un chip por pieza, resaltado por `url`

- **Elegido:** cada `evidence_urls[i]` es un chip con el nombre corto de la fuente de esa pieza (`source` cortado en
  el primer « · » o «:»; sin pieza que coincida, el host de la URL). Pulsarlo resalta **solo esa pieza** (por `url`),
  quita el filtro de plataforma, baja el resto de filas a opacidad 0.4 y hace `scrollIntoView({block: 'center'})`
  (`behavior: 'smooth'` salvo movimiento reducido). Pulsarlo otra vez, o «Quitar resaltado», lo quita. Estado local,
  no URL. Criterio sin citas: «Sin piezas citadas».
- **Descartado:** chip por fuente *(encendería piezas de la misma fuente que no se citan)*.

### D12 — Barras HTML, no ECharts

- **Elegido:** mini barras del ranking y barras de la evolución en HTML/CSS con `transform: scaleY`/altura fija en
  px calculada (sin animar `height`). Tokens nuevos `--window-previous: #C9CED6` y `--window-empty: #D5D9DF`
  (paso 0.3).
- **Por qué:** seis barras no necesitan un canvas; HTML es accesible (`aria-label`) y ya es el patrón de las mini
  barras de `DESIGN.md` §4.

### D13 — Navegación

- **Elegido:** rutas `/explore` (`RouteName.Explore`, `ExploreView`) y `/explore/:id` (`RouteName.Dossier`,
  `DossierView`). «Explorar» en la nav está activo en las dos. «Radar» del expediente → `{name: Discover, query:
  {selected: id}}`. «Ver ›» de «Esta semana» → `{name: Explore}`.

### D14 — Textos

- De usted, como en el canvas («Elija una burbuja o una fila para ver el tema.», «Pulse una pieza…»). Formato de
  `DESIGN.md` §9 (coma decimal, «+80 %», «17/10, 19:09 UTC»). Números con separador de miles siempre («1.363»):
  `Intl.NumberFormat('es-ES', { useGrouping: 'always' })` (es-ES no agrupa 4 cifras por defecto).

## Diseño de módulos

- **Seam de datos:** `src/api/opportunities.ts` (composables de TanStack Vue Query; los componentes no llaman a
  `fetch`). Fixtures solo con `USING_FIXTURES`; nunca se cae a fixtures si la API falla.
- **Seams de presentación (puros, con tests):** `src/lib/radarView.ts` (Parte 1), `src/lib/dossierView.ts`
  (Parte 2), `src/lib/exploreView.ts` (Parte 3), `src/lib/evidenceFormat.ts` (compartido). Entra la respuesta de la
  API, sale lo que se pinta. Sin reloj implícito.
- **Componentes:** ≤ 200 líneas cada uno; una carpeta por vista (`components/radar`, `components/dossier`,
  `components/explore`) y `components/evidence` para lo compartido.

### Propiedad de archivos (disjunta)

| Quién | Archivos (todo bajo `frontend/`) |
| --- | --- |
| Fase 0 | `src/router/index.ts`, `src/components/layout/AppHeader.vue`, `src/views/DossierView.vue` (placeholder), `src/components/radar/OpportunityDetail.vue` (solo el enlace), `src/api/opportunities.ts`, `src/lib/format.ts`, `src/lib/evidenceFormat.ts` + test, `src/components/evidence/PerformanceBar.vue`, `src/assets/main.css`, `DESIGN.md`, `.claude/rules/frontend.md` |
| Parte 1 | `src/views/DiscoverView.vue`, `src/components/radar/**` (incluye borrar `RadarFilters.vue`, `AudienceMixCard.vue`, `WhyItMattersCard.vue` y sustituir `OpportunityDetail.vue`), `src/lib/radarView.ts`, `src/lib/radarQuery.ts`, `src/lib/radarChart.ts`, `src/composables/useRadarQuery.ts` y sus tests, `src/components/opportunities/ScoreRing.vue` (prop de tamaño) |
| Parte 2 | `src/views/DossierView.vue`, `src/components/dossier/**` (nuevo), `src/lib/dossierView.ts` + test (nuevo) |
| Parte 3 | `src/views/ExploreView.vue`, `src/components/explore/**` (nuevo), `src/lib/exploreView.ts` + test (nuevo) |
| Integración | Borrar `src/components/opportunities/MetricBar.vue` si quedó sin uso; `README`/docs si algo cambió |

Todo lo demás es **solo lectura** para las partes (`opportunityFormat.ts`, `lifecycle.ts`, chips, `motion.ts`,
`components/ui/**`, `evidenceFormat.ts`, `PerformanceBar.vue`, `api/opportunities.ts`). Si una parte necesita un
helper nuevo, lo crea en su propio `lib/…View.ts` o en su carpeta de componentes, no en un archivo compartido. La
Parte 2 **no** importa nada de `components/radar/` (la Parte 1 borra lo que ya no usa).

## Plan de implementación

### Fase 0 — Coordinador

#### Paso 0.1 — Rutas del expediente y de Explorar [HECHO]

- **Archivos:** `src/router/index.ts`, `src/views/DossierView.vue` (nuevo), `src/components/layout/AppHeader.vue`,
  `src/components/radar/OpportunityDetail.vue`
- **Cambio:** `RouteName.Dossier = 'dossier'`. Rutas `{ path: '/explore', name: Explore, component: () =>
  import('@/views/ExploreView.vue') }` y `{ path: '/explore/:id', name: Dossier, component: () =>
  import('@/views/DossierView.vue') }`. `DossierView.vue` = `ViewHeader` «Expediente» (placeholder). En `AppHeader`,
  «Explorar» lleva `aria-current="page"` si `route.name` es `Explore` o `Dossier` (lista de nombres por vista). En
  `OpportunityDetail.vue:134`, el enlace pasa a `{ name: RouteName.Dossier, params: { id } }` (mantiene `main`
  desplegable hasta que la Parte 1 lo sustituya).
- **Test primero:** verificación manual: `/explore` y `/explore/opp_911` cargan sus vistas y «Explorar» queda activo.
- **Verificación:** `cd frontend && pnpm type-check && pnpm lint`
- **Commit:** `Split explore routes into overview and dossier`

#### Paso 0.2 — Composables de datos del tema [HECHO]

- **Archivos:** `src/api/opportunities.ts`
- **Cambio:** factorías `opportunityQueryOptions(id)`, `evidenceQueryOptions(id)`, `timelineQueryOptions(id)` con
  claves `['opportunity', id]`, `['opportunity', id, 'evidence']`, `['opportunity', id, 'timeline']`, y:
  - `useOpportunity(id: MaybeRefOrGetter<string>)` → `Opportunity | null` (`null` si la respuesta es 404:
    `response.status === 404`; otro error lanza `Error('GET /opportunities/{id} falló')`). Fixture: el item con ese
    `id` o `null`.
  - `useOpportunityEvidence(id)` → `Evidence[]`. Fixture: `fixture.evidence[id] ?? []`.
  - `useOpportunityTimeline(id)` → `OpportunityTimeline | null` (404 → `null`). Fixture: `fixture.timeline[id] ??
    null`.
  - `useOpportunityTimelines(ids: MaybeRefOrGetter<string[]>)` y `useOpportunitiesEvidence(ids)` → `useQueries` con
    `queries` reactivo y las mismas opciones; devuelven `ComputedRef<ReadonlyMap<string, QueryState<T>>>` con
    `QueryState<T> = { data: T | undefined; isPending: boolean; isError: boolean }`, más un `refetchFailed()` en
    `useOpportunitiesEvidence` que reintenta solo las que fallaron.
  - El fixture se importa una vez con un helper `loadFixture()` (el `import()` dinámico ya existente).
- **Test primero:** `src/api/__tests__/opportunities.spec.ts` — añadir: cada `fixture.timeline[id]` tiene 6 puntos, 3
  `previous` seguidos de 3 `current`; cada lista de `fixture.evidence[id]` tiene URLs únicas y `platform` del enum
  (`satisfies` contra `Schemas['Platform']`). (Los composables se verifican con type-check y en el navegador.)
- **Verificación:** `cd frontend && pnpm test -- opportunities && pnpm type-check`
- **Commit:** `Add opportunity detail, evidence and timeline queries`

#### Paso 0.3 — Formato de evidencia, barra de rendimiento y tokens [HECHO]

- **Archivos:** `src/lib/format.ts`, `src/lib/evidenceFormat.ts` (nuevo), `src/lib/__tests__/evidenceFormat.spec.ts`
  (nuevo), `src/components/evidence/PerformanceBar.vue` (nuevo), `src/assets/main.css`
- **Cambio:**
  - `format.ts`: `formatUtcDay(iso)` → «07/10» (UTC) y `formatUtcTime(iso)` → «19:09».
  - `evidenceFormat.ts`: `PLATFORM_LABEL: Record<Platform, string>` (YouTube · Hacker News · RSS · Brave · LinkedIn ·
    Instagram · TikTok) · `SEGMENT_LABEL: Record<Segment, string>` (Tech · Negocio · En español) · `formatCount(n)`
    (D14) · `formatMetrics(metrics): string | null` (orden vistas, puntos, me gusta, comentarios, compartidos; omite
    nulos; todos nulos → `null`) · `formatVelocity(velocity): string | null` (≥ 10 → entero con miles; < 10 →
    `formatDecimal`; unidad con `VELOCITY_UNIT_LABEL` `views/h` → «vistas/h», `points/h` → «puntos/h», otra → tal
    cual) · `formatRatio(r)` → «26,9×» · `ratioLabel(evidence): 'Outlier' | 'Destacada' | null` (D10) ·
    `missingRatioLabel(evidence)` (D10) · `performanceFraction(r) = min(r / PERFORMANCE_SCALE_MAX, 1)` con
    `PERFORMANCE_SCALE_MAX = 6` · `PERFORMANCE_MARKS = [1, 3]` · `HIGHLIGHT_RATIO_MIN = 2` (comentario: CLAUDE.md §7) ·
    `PERFORMANCE_LEGEND` y `VELOCITY_NOTE` (textos de D10) · `shortSourceName(source)` (D11).
  - `PerformanceBar.vue` (props `{ evidence: Evidence }`): con ratio, pista de 6 px (radio completo) con marcas en
    1× (`bg-reference-mark`) y 3× (Tinta), relleno con `scaleX(fraction)` y `transform-origin: left` (Tinta si
    `is_outlier`, `bg-reference-mark` si no) y badge «5,1×» (Lima señal + Tinta si outlier; `bg-neutral-action` si no);
    `aria-label` «5,1 veces su referencia». Sin ratio, solo el texto de `missingRatioLabel` en Apagado 13px. El título
    («Rendimiento frente a su canal») lo pone quien lo usa.
  - `main.css`: `--window-previous: #C9CED6`, `--window-empty: #D5D9DF`, `--reference-mark: #8A919C` y sus
    `--color-*` en `@theme inline` (clases `bg-window-previous`, `bg-window-empty`, `bg-reference-mark`).
- **Test primero:** `evidenceFormat.spec.ts`: `formatCount(1363)` → «1.363»; `formatMetrics` con todo nulo → `null`
  y con vistas + me gusta → «213.269 vistas · 4.367 me gusta»; `formatVelocity({value: 0, unit: 'points/h'})` →
  «0 puntos/h» y `{value: 1363.4, unit: 'views/h'}` → «1.363 vistas/h»; `formatRatio(26.9)` → «26,9×»;
  `performanceFraction(26.9)` → 1 y `(3)` → 0.5; `missingRatioLabel` RSS → «Sin métricas públicas» y YouTube con
  vistas → «Sin línea base del canal»; `ratioLabel` con 2.4 no outlier → «Destacada», con 1.2 → `null`;
  `shortSourceName('Xataka · Inteligencia artificial')` → «Xataka», `('The AI Daily Brief: Artificial Intelligence
  News')` → «The AI Daily Brief», `('midudev')` → «midudev».
- **Verificación:** `cd frontend && pnpm test -- evidenceFormat && pnpm type-check && pnpm lint`
- **Commit:** `Add shared evidence formatting and performance bar`

#### Paso 0.4 — Docs de las decisiones

- **Archivos:** `DESIGN.md`, `.claude/rules/frontend.md`
- **Cambio:** `DESIGN.md` §4 (contador-filtro: totales fijos y selección única, D2; tokens de ventana, D12) · §5
  (quitar «los contadores cuentan solo lo filtrado»; Explorar sin gráfico, D3) · §6 (ranking: ancho mínimo 780 px) ·
  §8 (quitar «Rendimiento por fecha»; las barras del timeline son HTML, D12) · §11 (tokens nuevos). `frontend.md`:
  Explorar sin tema sin dispersión.
- **Test primero:** n/a (docs).
- **Verificación:** `git diff --stat`
- **Commit:** `Document D2 decisions: fixed counters, explore without chart`

### Parte 2 — Expediente (`fe/dashboard-v2-dossier`)

#### Paso 2.1 — View-model puro del expediente

- **Archivos:** `src/lib/dossierView.ts`, `src/lib/__tests__/dossierView.spec.ts`
- **Cambio:**
  - `rankOf(list: OpportunityList | null | undefined, id): { rank: number; total: number } | null` (índice + 1 en
    `items`; `null` si no está).
  - `splitTimeline(timeline): { previous: Bar[]; current: Bar[]; previousLabel; currentLabel; scaleMax; cutoffTime }`
    con `Bar = { date, label: 'dd/mm', count }`; rótulos «Ventana anterior · 12–14/10» y «Ventana actual · 15–17/10»
    (si cambia el mes: «30/09–02/10»); `scaleMax = max(1, max count)`; `cutoffTime` = `formatUtcTime(last_updated)`
    (lo recibe como argumento).
  - `COMPONENT_LABEL: Record<ScoreComponentName, string>` (Momentum · Encaje con 30X · Fuentes independientes ·
    Frescura · Accionabilidad) y `componentRows(breakdown)` → `{ label, value, display, weightLabel: 'peso 30 %' }`
    en el orden de la API (`audience_fit` con `formatFit`, el resto con `formatScore`).
  - `PENALTY_LABEL` (single_source «Una sola fuente», small_sample «Muestra pequeña») y `describePenalties(list)` →
    «sin penalizaciones» o «Una sola fuente −10 · Muestra pequeña −10» (signo menos U+2212).
  - `CRITERION_LABEL: Record<FitCriterion, string>`: Impacto en decisiones empresariales · Aplicación real en
    organizaciones · Comprensible para directivos no técnicos · Relevancia para LATAM · Encaje con los pilares de
    30X · Convertible en contenido accionable.
  - `citationChips(criterion, evidence): { url, label, isInEvidence }[]` (D11).
  - `platformCounts(evidence)` → `[{ platform | 'all', label, count }]` solo con las plataformas presentes, «Todas»
    primero.
- **Test primero:** `dossierView.spec.ts` con el fixture y casos a mano: `rankOf` encuentra `opp_003` → 3 de 5 y un id
  ausente → `null`; `splitTimeline` del fixture `opp_001` → rótulos «12–14/10» y «15–17/10», `scaleMax` 6; un
  timeline todo a 0 → `scaleMax` 1; `describePenalties([])` → «sin penalizaciones»; con las dos → texto con «−10»;
  `citationChips` con una URL que no está en la evidencia → label = host; `componentRows` conserva el orden y pinta
  «peso 30 %».
- **Verificación:** `cd frontend && pnpm test -- dossierView`
- **Commit:** `Add dossier view model`

#### Paso 2.2 — Cabecera y «Cómo se compone»

- **Archivos:** `src/components/dossier/DossierHeader.vue`, `src/components/dossier/ScoreComposition.vue`,
  `src/views/DossierView.vue`
- **Cambio:** `DossierView` lee `route.params.id` y usa `useOpportunity`, `useOpportunityEvidence`,
  `useOpportunityTimeline` y `useOpportunities(DEFAULT_PERIOD)` (puesto y `monitoring_started_at`). Layout de
  `DESIGN.md` §5 «Expediente» y del artboard `Expediente.dc.html`. Cabecera (izquierda, `flex: 999 1 640px`): botón
  secundario «Radar» con `ChevronLeft` (→ D13), `LifecycleChip`, H1 = `topic` (Bricolage, `clamp`), línea «{GROWTH} ·
  confianza {c} · {n} fuentes independientes · {latamGapLabel} · actualizado el {formatUtcTimestamp(last_updated)}»,
  `RecommendationChip` + `recommendation_reason` (se omite si es nulo). Tarjeta derecha «Cómo se compone»
  (`flex: 1 1 440px`, `aria-label` «Cómo se compone la oportunidad»): `ScoreRing`, «Oportunidad · puesto R de N ·
  {penalizaciones}» («puesto no disponible» si `rankOf` es `null`), 5 filas (etiqueta 156px · barra 6px con `scaleX`
  · cifra · «peso 30 %») y la nota «Frescura = 100 − saturación ({saturation_score}, dentro de las fuentes
  monitoreadas).». `score_breakdown` nulo → «Sin desglose: falta el encaje con la audiencia, así que no hay
  puntuación de oportunidad.» Estados de la vista: cargando → skeletons con la forma de cada tarjeta; `null` (404) →
  tarjeta «Este tema no está en el análisis servido: los temas cambian entre ejecuciones.» + enlace «Volver al
  Radar»; error → inline con «Reintentar» (`refetch`).
- **Test primero:** verificación manual: `/explore/opp_911` (real) muestra puesto 3 de 38 y las 5 filas;
  `/explore/opp_005` (fixtures) muestra el texto sin desglose; `/explore/nada` muestra el estado 404.
- **Verificación:** `cd frontend && pnpm type-check && pnpm lint`
- **Commit:** `Add dossier header and score composition`

#### Paso 2.3 — Evolución

- **Archivos:** `src/components/dossier/DossierEvolution.vue`
- **Cambio:** tarjeta «Evolución»: a la izquierda, badge de `GROWTH_LABEL` y las dos baldosas de `splitTimeline`
  (anterior en `bg-window-previous`, actual en Tinta, cada barra con su cifra y «dd/mm»; 0 → trazo de 3px en
  `bg-window-empty`; altura proporcional a `count / scaleMax` sobre un máximo fijo en px), y la nota «Piezas nuevas
  del tema en periodos de 24 h que terminan a las {cutoffTime} UTC del día indicado.» A la derecha (300px):
  `formatAcceleration` grande (color Negativo si `isDeclining`) + «frente a la ventana anterior, ajustado por el
  volumen de las fuentes.»; «{formatDecimal(velocity)} piezas nuevas al día en la ventana actual.»; «Etapa
  «{LIFECYCLE_STYLE.label}»: {lifecycle_reason}». Timeline nulo o con error → «Evolución no disponible.» (la columna
  derecha se mantiene: viene de la oportunidad).
- **Test primero:** verificación manual con `opp_911`: anterior 1·1·1, actual 3·2·0 (el 0 como trazo), nota «… a las
  19:09 UTC …».
- **Verificación:** `cd frontend && pnpm type-check && pnpm lint`
- **Commit:** `Add dossier evolution windows`

#### Paso 2.4 — Por qué importa y criterios con citas

- **Archivos:** `src/components/dossier/WhyItMattersSection.vue`, `src/components/dossier/FitCriterion.vue`
- **Cambio:** `why_it_matters` completo (Geist 18px/1.55, ancho ≤ 720px). Columna izquierda: «Encaje con 30X»,
  `formatFit` grande, «Evaluación editorial, no una medición. Seis criterios de 0 a 5. Pulse una pieza para ver dónde
  está en la evidencia.» y, con un chip activo, el secundario «Quitar resaltado». Columna derecha: un `FitCriterion`
  por criterio en orden de la API: etiqueta, medidor de 5 segmentos (`level` en Tinta, el resto en `bg-track`;
  `role="img"`, `aria-label` «{level} de 5»), «{level} de 5», `justification`, «Se apoya en» + chips (`<button>`,
  `aria-pressed`) o «Sin piezas citadas». Emite `cite(url | null)`. Criterios nulos → «Encaje no disponible: el tema
  no se evaluó.»
- **Test primero:** verificación manual: pulsar un chip emite la URL; pulsarlo otra vez la quita.
- **Verificación:** `cd frontend && pnpm type-check && pnpm lint`
- **Commit:** `Add why-it-matters section with cited fit criteria`

#### Paso 2.5 — Evidencia

- **Archivos:** `src/components/dossier/EvidenceSection.vue`, `src/components/dossier/EvidenceRow.vue`,
  `src/components/dossier/AudienceMixBar.vue`, `src/views/DossierView.vue`
- **Cambio:** cabecera izquierda «{n} piezas · outliers primero» («1 pieza») + segmented de `platformCounts` (estado
  local; pista `#F2F3F5` dentro de la tarjeta). Cabecera derecha (420px): «Para quién importa», barra apilada de 12px
  (Tech Tinta · Negocio `bg-audience-business` · En español Lima, 3px entre segmentos, segmentos con `flex-grow` =
  proporción), leyenda «Tech 57 % · Negocio 0 % · En español 43 %» (`formatShare`) y la frase de `audienceReading`.
  Filas en el orden de la API (`data-evidence-url` = `url`): «{PLATFORM_LABEL} · {source} · {formatUtcDay} · ●
  {SEGMENT_LABEL}», título como enlace (`target="_blank" rel="noopener noreferrer"`), `formatMetrics` o «Métricas: no
  disponible»; columna derecha (300px) «Rendimiento frente a su canal» + `PerformanceBar` + `formatVelocity` o
  «Velocidad no disponible». Bajo la lista, `PERFORMANCE_LEGEND` y `VELOCITY_NOTE`; si hay 25 piezas, «Se muestran las
  25 primeras piezas del tema.». Sin piezas → «Este tema no tiene piezas en la evidencia servida.» Resaltado (D11):
  `DossierView` guarda `citedUrl`; al fijarlo pone el filtro en «Todas», marca la fila con `bg-signal/18` (como la fila seleccionada de `RankingRow.vue:47`)
  y baja el resto a opacidad 0.4 (transición 320ms) y hace scroll a la fila. Error de `/evidence` → inline con
  «Reintentar».
- **Test primero:** verificación manual con `opp_911`: 8 piezas, filtro «YouTube · 3», un chip de criterio resalta
  su pieza y baja hasta ella.
- **Verificación:** `cd frontend && pnpm type-check && pnpm lint`
- **Commit:** `Add dossier evidence list with audience mix`

#### Paso 2.6 — Siguiente paso, qué no sabemos y nota al pie

- **Archivos:** `src/components/dossier/NextStep.vue`, `src/views/DossierView.vue`
- **Cambio:** tarjeta de dos columnas: izquierda `RecommendationChip` + «El brief parte de esta evidencia y de los
  criterios de encaje.» + primario `RouterLink` «Generar brief» (→ `{name: Create, query: {opportunity: id}}`) +
  secundario «Copiar enlace» (`useClipboard` de VueUse con `window.location.href`; «Enlace copiado» durante 2 s).
  Derecha: bloque Aviso «Qué no sabemos» con un `<p>` por `limitations` (vacío → «No hay limitaciones registradas
  para este tema.»). Nota al pie de la página: «Datos desde el {formatUtcTimestamp(monitoring_started_at)}. La
  saturación se mide dentro de las fuentes monitoreadas. El encaje es una evaluación editorial, no una medición. Los
  enlaces abren la pieza original.» (sin la lista cargada, se omite la primera frase). `data-agent` en las secciones:
  `dossier-score`, `dossier-evolution`, `dossier-fit`, `dossier-evidence`, `limit`.
- **Test primero:** verificación manual del recorrido Radar → «Ver expediente» → «Generar brief».
- **Verificación:** `cd frontend && pnpm lint && pnpm type-check && pnpm test && pnpm build`
- **Commit:** `Add dossier next step and limitations`

### Parte 1 — Radar (`fe/dashboard-v2-radar`)

#### Paso 1.1 — URL y view-model: sin selección por defecto, contadores fijos y «Publicar ya»

- **Archivos:** `src/lib/radarQuery.ts`, `src/lib/radarView.ts`, sus tests y
  `src/composables/__tests__/useRadarQuery.spec.ts`
- **Cambio:**
  - `radarQuery.ts`: `RECOMMENDATIONS` (con `satisfies`), `RadarQuery.recommendation: Recommendation | null` (param
    `recommendation`), en `RADAR_QUERY_KEYS`, `parseRadarQuery`, `serializeRadarQuery` y `resetViewPatch` (→ `null`).
  - `radarView.ts`: `selected` sin fallback (D7). `matchesFilters` filtra también por `recommendation`. `counts` →
    `{ publishNow, accelerating, emerging, unknown }` sobre **todos** los temas (D2). Nuevo `activeCounter:
    CounterFilter | null` (`CounterFilter = 'publish_now' | 'accelerating' | 'emerging' | 'unknown'`) y
    `counterPatch(counter, query): Partial<RadarQuery>` (toggle de D2). `weekPicks` (los `publish_now` en orden de
    puesto; si no hay, los 3 primeros y `hasPublishNow: false`), `outlierPieces` (Σ `outlier_count`) y
    `describeStageUnknowns(ranked, monitoringStartedAt)` (D4). H1 «N temas esta semana» / «V de N temas»; frase sin
    filtro «Ordenados por oportunidad. Elija una burbuja o una fila para ver el tema.» (si N < 10, antes «Hay N temas
    con datos suficientes esta semana.»); con filtro «Filtro: {descripción}. El resto queda atenuado en el radar.»
    (la descripción incluye «para publicar ya»).
- **Test primero:** `radarView.spec.ts`: sin `selected` → `selected === null` (sustituye «falls back to rank 1»); con
  `recommendation=publish_now` solo quedan esos y los contadores no cambian; `counterPatch` sobre el activo → reset;
  `activeCounter` con dos etapas → `null`; `describeStageUnknowns` con u = 19 y p = 8 → la frase de D4, con p = 0 y
  con u = 0; `weekPicks` sin `publish_now` → 3 primeros. `useRadarQuery.spec.ts`/`radarQuery` tests: el param
  `recommendation` va y vuelve, valores inválidos → `null`.
- **Verificación:** `cd frontend && pnpm test -- radar`
- **Commit:** `Drop default selection and add fixed counter filters`

#### Paso 1.2 — Panel lateral: «Esta semana» y vista previa

- **Archivos:** `src/components/radar/RadarSidePanel.vue`, `src/components/radar/WeekSummary.vue`,
  `src/components/radar/OpportunityPreview.vue` (sustituye a `OpportunityDetail.vue`, que se borra),
  `src/components/opportunities/ScoreRing.vue`
- **Cambio:** panel: tarjeta blanca, `flex: 1 1 360px`, `sticky top-4 self-start`, padding 22px,
  `<aside aria-label="Panel del tema">`; cambia de estado con `<Transition>` (fundido + 6px, 280ms; sin movimiento con
  `prefers-reduced-motion`). `WeekSummary`: título «Esta semana», frase de D9, lista de `weekPicks` (botones: tema,
  chip «Publicar ya», aceleración, oportunidad 24px Bricolage; `select` y `hover`), línea «**{n} piezas** rinden 3× o
  más que su canal» + `RouterLink` «Ver ›» (→ `{name: Explore}`; con 0: «Ninguna pieza rinde 3× o más que su canal
  todavía.»), bloque Aviso con `describeStageUnknowns`. `OpportunityPreview`: D8. `ScoreRing`: prop `size` en px
  (por defecto 112) que fija `viewBox`, radio y tamaño; trazo 9px.
- **Test primero:** verificación manual: sin selección «Esta semana» con 3 temas reales; clic en uno → vista previa;
  «← Esta semana» vuelve.
- **Verificación:** `cd frontend && pnpm type-check && pnpm lint`
- **Commit:** `Add radar side panel with weekly summary and preview`

#### Paso 1.3 — Cabecera con contadores-filtro y tarjeta del radar

- **Archivos:** `src/components/radar/RadarHero.vue`, `src/components/radar/CounterFilter.vue` (nuevo),
  `src/components/radar/OpportunityRadar.vue`, `src/components/radar/RadarSelectionLayer.vue`,
  `src/components/radar/RadarFloatingCard.vue`, `src/lib/radarChart.ts` (+ test), borrar
  `src/components/radar/RadarFilters.vue`
- **Cambio:** `RadarHero`: H1 + frase a la izquierda; a la derecha 4 `CounterFilter` (baldosa blanca radio 16px,
  `min-width` 128px, cifra Bricolage 32px, muestra de color de 10px: Lima con anillo interior de Tinta al 15 % para
  «Publicar ya», relleno de etapa para las otras, blanca con anillo discontinuo `--lc-unknown` para «Sin etapa»;
  `aria-pressed`; activo con anillo de Tinta de 2px) y «Restablecer vista» si hay filtro. `data-agent`:
  `filter-rec-publish_now`, `filter-lc-accelerating`, `filter-lc-emerging`, `filter-lc-unknown`. `OpportunityRadar`:
  H2 «Radar» con las 5 etapas como chips no interactivos a la derecha de su cabecera; bajo el gráfico «Las burbujas
  que laten están creciendo: cuanto más rápido laten, más aceleran. El tamaño es la fuerza de la evidencia.» (y la
  nota de temas sin evaluar como hoy). `radarChart.isLabelShown`: solo `publish_now` y solo sin selección.
  `RadarSelectionLayer`: la tarjeta flotante sigue al hover (no a la selección, ni sobre la burbuja seleccionada),
  pasa a la izquierda si `fit > 62`, separación 22px; mira, lecturas, anillo y ping solo con selección; el retardo de
  detección solo se aplica si la selección llega **mientras dura el barrido** (bug de la tabla de contexto).
- **Test primero:** `radarChart.spec.ts`: etiqueta solo para `publish_now` sin selección y ninguna con selección.
- **Verificación:** `cd frontend && pnpm test -- radarChart && pnpm type-check && pnpm lint`
- **Commit:** `Add counter filters and stage legend to the radar`

#### Paso 1.4 — Ranking con mini barras de 6 días

- **Archivos:** `src/components/radar/OpportunityRanking.vue`, `src/components/radar/RankingRow.vue`,
  `src/components/radar/RankingSparkline.vue` (nuevo)
- **Cambio:** D6. Cabecera «Ranking» + nota «Barras: piezas nuevas por periodo de 24 h, del {dd/mm} al {dd/mm}»
  (fechas del primer timeline cargado; sin ninguno, sin fechas). 10 filas del filtro + «Ver los {n} temas» / «Ver
  menos» (solo si n > 10; vuelve a 10 al cambiar el filtro). `useOpportunityTimelines(ids de las filas mostradas)`.
  `RankingSparkline` (props `QueryState<OpportunityTimeline | null>`): 6 barras de 8px, gap 3px, alto 24px; alto =
  `min(count, SPARK_SCALE_MAX) / SPARK_SCALE_MAX · 24px` con `SPARK_SCALE_MAX = 5` (DESIGN.md §4); 0 → trazo de 2px en
  `bg-window-empty`; color por `window` (`bg-window-previous` / Tinta); `role="img"` y `aria-label` «Piezas nuevas
  por periodo de 24 h: 1, 1, 1, 3, 2, 0»; cargando → skeleton 66×24; error o `null` → «no disponible» (12px). Fila
  seleccionada en lavado de señal 0.18 y puesto en negrita; clic → toggle (D7).
- **Test primero:** verificación manual: 10 filas con barras reales; «Ver los 38 temas» carga el resto.
- **Verificación:** `cd frontend && pnpm type-check && pnpm lint`
- **Commit:** `Add six-day sparklines to the ranking`

#### Paso 1.5 — Composición de la vista y estados

- **Archivos:** `src/views/DiscoverView.vue`, `src/components/radar/RadarStates.vue`,
  `src/components/radar/RadarFootnote.vue`, borrar `src/components/radar/AudienceMixCard.vue` y
  `src/components/radar/WhyItMattersCard.vue`
- **Cambio:** sin el gate `view.selected`. Orden: `RadarHero` → fila (`flex flex-wrap items-start gap-4`): columna
  izquierda (`flex: 999 1 720px`, `flex-col gap-4`) con radar, ranking y nota al pie; `RadarSidePanel` a la derecha.
  `select(id)` hace toggle; `clearSelection()`. `RadarFootnote` se queda (con «Datos desde…», saturación y encaje;
  sin la frase del latido, que ya está bajo el radar). Skeleton de `RadarStates`: 4 contadores, sin fila de filtros
  ni bento, panel a la derecha y ranking en la columna izquierda.
- **Test primero:** verificación manual del criterio 1–8 con datos reales y con fixtures.
- **Verificación:** `cd frontend && pnpm lint && pnpm type-check && pnpm test && pnpm build`
- **Commit:** `Compose the D2 radar dashboard`

### Parte 3 — Explorar sin tema (`fe/dashboard-v2-explore`)

#### Paso 3.1 — View-model puro de Explorar

- **Archivos:** `src/lib/exploreView.ts`, `src/lib/__tests__/exploreView.spec.ts`
- **Cambio:** `ExploreFilter = 'outliers' | 'youtube' | 'hackernews'` y `parseExploreFilter(query)` (param
  `filter`; inválido → `null`). `buildExploreView({ opportunities, evidenceById, filter, text })` →
  - `pieces: Piece[]` con `Piece = Evidence & { opportunity: Opportunity; rank: number }`, deduplicadas por `url`
    (gana el tema de mejor puesto), ordenadas por `outlier_ratio` descendente, sin ratio al final; empates y sin ratio
    por `published_at` descendente;
  - `visible` = filtradas por `filter` (`is_outlier === true` · `platform`) y por `text` (incluye en `title` o
    `source`, sin mayúsculas ni tildes: `normalize('NFD')` y quitar diacríticos);
  - `counts = { total, outliers, youtube, hackernews, rss }` sobre todas (totales fijos, como D2);
  - `publishedRange: { from, to }` (`formatUtcDay` de la mínima y la máxima), `topicCount`, `isCapped` (algún tema
    con 25 piezas, `EVIDENCE_LIMIT = 25`);
  - `topTopics` = 5 temas con `outlier_count > 0` por `outlier_count` descendente (empate → puesto);
  - `topSources` = 5 `source` por número de piezas `is_outlier` (empate → orden alfabético `localeCompare('es')`),
    con `share = n / max`.
- **Test primero:** `exploreView.spec.ts` con datos construidos a mano: orden con nulos al final; dedupe por URL;
  filtro `outliers` y `youtube`; texto «inteligencia» encuentra «Inteligencia»; `topSources` desempata
  alfabéticamente; `topTopics` excluye temas sin outliers; `isCapped` con 25 piezas.
- **Verificación:** `cd frontend && pnpm test -- exploreView`
- **Commit:** `Add explore view model`

#### Paso 3.2 — Vista, cabecera y tabla de piezas

- **Archivos:** `src/views/ExploreView.vue`, `src/components/explore/ExploreHeader.vue`,
  `src/components/explore/PiecesTable.vue`, `src/components/explore/PieceRow.vue`
- **Cambio:** datos: `useOpportunities(DEFAULT_PERIOD)` → ids → `useOpportunitiesEvidence(ids)`; `filter` en la URL
  (`?filter=`, `router.replace`, conservando otros params); texto y pieza seleccionada en estado local (la selección
  por `url`). Cabecera: H1 «Lo que está funcionando»; frase «{total} piezas de los {topicCount} temas, publicadas
  entre el {from} y el {to}. {outliers} rinden 3× o más que su canal.» (+ « Hasta 25 piezas por tema.» si
  `isCapped`); contadores con el estilo de `CounterFilter` del Radar (copiado en `components/explore`, no importado):
  Outliers · YouTube · Hacker News (botones `aria-pressed`, selección única) y RSS (no interactivo, con «sin métricas
  públicas» debajo). Tabla «Piezas» + «mostrando {v} de {total}» + input «Filtrar por título o fuente» (con
  `<label>`). Columnas: Pieza (título en una línea con elipsis + fuente debajo) · Tema (punto de etapa + tema) ·
  Plataforma · Publicada (dd/mm) · Rendimiento (`PerformanceBar`). Ancho mínimo 900px con scroll dentro de la
  tarjeta. 25 filas y «Ver 25 más»; vuelve a 25 al cambiar filtro o texto. Clic en una fila → toggle de la selección
  (`bg-signal/18`). Sin resultados: «Ninguna pieza cumple estos filtros.». Estados: cargando → skeletons; lista `null` →
  «Todavía no hay análisis: el job `analyze` no ha corrido.»; temas cuya evidencia falló → aviso inline «No se pudo
  cargar la evidencia de {f} temas.» + «Reintentar» (`refetchFailed`) y se muestran el resto con las cifras de lo
  cargado.
- **Test primero:** verificación manual con datos reales: 356 piezas, 27 outliers, YouTube 96, Hacker News 145, RSS
  115; las primeras filas son los ratios más altos (26,9×…).
- **Verificación:** `cd frontend && pnpm type-check && pnpm lint`
- **Commit:** `Add explore pieces table with counter filters`

#### Paso 3.3 — Panel «Dónde está funcionando» y detalle de la pieza

- **Archivos:** `src/components/explore/ExploreSidePanel.vue`, `src/components/explore/WhereItWorks.vue`,
  `src/components/explore/PieceDetail.vue`, `src/views/ExploreView.vue`
- **Cambio:** panel sticky como el del Radar (`flex: 1 1 360px`, fundido + 6px). Sin selección: «Dónde está
  funcionando», «Temas y fuentes con más outliers.»; «Temas» (`topTopics`: punto de etapa, tema como `RouterLink` →
  Dossier, «{n} outliers» / «1 outlier»); «Fuentes» (`topSources`: nombre, barra con `scaleX(share)`, cifra); sin
  outliers → «Todavía no hay outliers en las piezas servidas.»; bloque Aviso «Qué no sabemos»: «Que una pieza rinda
  3× su referencia no explica por qué funcionó: es una señal para revisarla, no una causa. En Hacker News la
  referencia es el p90 de la búsqueda, no un canal.» Con selección: «← Resumen» (secundario, `ChevronLeft`),
  `PerformanceBar` + rótulo («rinde 3× o más que su canal» si `ratioLabel` = Outlier; «rinde 2× o más que su canal» si
  Destacada; sin rótulo si no; sin ratio, el de `missingRatioLabel`), H2 título, «{PLATFORM_LABEL} · {source} ·
  publicada el {dd/mm}», baldosas «Métricas públicas» (`formatMetrics` o «no disponible») y «Velocidad»
  (`formatVelocity` o «no disponible»), bloque «Tema» (punto + tema + etiqueta de etapa), secundario «Ver original
  ↗» (`<a target="_blank" rel="noopener noreferrer">`) y primario «Abrir el tema» (→ Dossier).
- **Test primero:** verificación manual: top de fuentes real (Matthew Berman 5, …); seleccionar una pieza y abrir su
  tema.
- **Verificación:** `cd frontend && pnpm lint && pnpm type-check && pnpm test && pnpm build`
- **Commit:** `Add explore side panel with piece detail`

### Integración — Coordinador

#### Paso I.1 — Merge, limpieza y verificación

- **Archivos:** `src/components/opportunities/MetricBar.vue` (borrar si `grep -rn MetricBar frontend/src` no da
  usos), este plan (`[HECHO]`)
- **Cambio:** `git merge --no-ff` de `fe/dashboard-v2-dossier`, `fe/dashboard-v2-radar` y `fe/dashboard-v2-explore`
  (en ese orden) en `fe/dashboard-v2`, con la verificación final tras cada merge. Recorrido manual completo: Radar sin
  selección → «Ver ›» → Explorar → «Abrir el tema» → expediente → «Radar» → vista previa → «Ver expediente» →
  «Generar brief».
- **Verificación:** la de «Verificación final».
- **Commit:** `Remove unused metric bar` (si aplica) y los merge commits.

## Estrategia de test

- **Seams:** los view-models puros (`radarView`, `dossierView`, `exploreView`) y `evidenceFormat`. Componentes y
  composables, a mano en el navegador (estándares §8).
- **Prior art:** `frontend/src/lib/__tests__/radarView.spec.ts` y `opportunityFormat.spec.ts` (Vitest, fixture
  importado con `@fixtures/opportunities.json`).
- **Casos que entran:** los listados en cada paso. Todos salen del plan o de los datos reales (nulos de RSS, YouTube
  sin línea base, `0 puntos/h`, 0 `publish_now`, tema con 25 piezas, criterios sin citas, `opp_005` sin desglose).
- **Casos descartados por ruido:** snapshots de componentes, tests de los composables de datos contra un servidor
  mock, tests de estilos.
- **Parametrización:** `it.each` con nombres legibles para los rótulos de ratio y las frases de D4.

## Verificación final

```bash
cd /Users/dacorredor/projects/personal/qatro_labs/content-radar/frontend
pnpm lint && pnpm type-check && pnpm test && pnpm build
grep -rn "v-html" src && echo "FALLO: v-html" || echo "sin v-html"
VITE_USE_FIXTURES=true pnpm dev   # recorrido con fixtures: chip «Datos de ejemplo», opp_005 sin desglose
pnpm dev                          # recorrido con la API real (proxy /api → API_DEV_TARGET)
```

## Riesgos

- **Conflictos al mergear** — una parte tocó un archivo de otra o uno compartido → se revierte ese cambio en la parte
  y se repite el merge; nunca se resuelve reescribiendo la otra parte.
- **38 llamadas a `/evidence` lentas en Explorar** (~0,4 s cada una en paralelo) — si tarda más de 3 s en la demo,
  se pide a Steven el endpoint de piezas (ya en el mensaje del canal).
- **El run servido cambia** (ids de tema) — el expediente muestra el estado 404; fijar `DEMO_RUN_ID` antes de la demo.
- **La ruta del canvas en `/private/tmp` desaparece** — `DESIGN.md` y este plan bastan; el canvas está en
  https://claude.ai/artifact/76g911QRiq6PabeLYhyLPp (artboards `Dash`, `Evidencia`, `Expediente`).

## Historial de intentos

| Fecha | Qué bloqueó | Qué se decidió | Commits que quedaron |
| --- | --- | --- | --- |

## Preguntas abiertas

- (ninguna)
