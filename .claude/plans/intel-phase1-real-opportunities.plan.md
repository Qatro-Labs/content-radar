# intel-phase1-real-opportunities — Contrato aditivo, rutas de oportunidades y correcciones del motor

> Plan generado con `/spec`. Lo implementa `plan-implementer` con contexto limpio.
> El implementador NO ve la conversación que produjo este documento: todo lo que necesite tiene que
> estar escrito aquí.
>
> Es la **parte A** de la fase 1. La parte B (cliente Jev, `jev_judgments`, baterías y
> `audience_fit_score`) está en `.claude/plans/intel-phase1-jev.plan.md` y no se toca aquí.

## Metadatos

- **Slug:** `intel-phase1-real-opportunities` · **Issue:** ninguno
- **Owner (CLAUDE.md §3):** Melkin
- **Prioridad (CLAUDE.md §12):** P0 · **Checkpoint que desbloquea (§13):** primera integración, sáb
  20:30 ESP (datos reales → oportunidades → frontend)
- **Valor (filtro de CLAUDE.md §12):** Radar y detalle con evidencia del recorrido de demo: el
  frontend deja de leer el fixture y lee oportunidades reales por REST, con el desglose del score
  visible · **Pregunta de `docs/brief.md` §4:** #1 y #2 (qué destaca, qué crece y con qué evidencia)
- **Repo:** `/Users/melandres8/Documents/Projects/content-radar`
- **Rama base:** `intel/engine` @ `8ae61c8`
- **Rama de trabajo:** `intel/phase1-real-opportunities`, creada así:
  `git checkout -b intel/phase1-real-opportunities origin/data/opportunity-routes && git merge --no-edit origin/intel/engine`
  (las rutas de Steven, PR #9, + `intel/engine` @ `8ae61c8`; no comparten archivos, merge limpio
  comprobado a las 17:40). La PR va contra `intel/engine`, después de la #9.
- **Fecha:** 2026-10-17 16:45 ESP (revisado 17:05 tras mergear #8: el audience fit pasa al LLM)
- **Contratos tocados:** `Opportunity` / `Evidence` / OpenAPI (cambio aditivo: todo opcional o con
  default) — **avisado en el canal:** sí (2026-10-17, antes de lanzar `/spec`)
- **Auditoría tras `/build`:** sí
- **Estado del gate:** `LISTO`

## Problema

- El frontend no puede pasar a datos reales: `backend/app/api/routes/` solo tiene `sources.py` y
  las funciones de lectura de oportunidades de `services/opportunities.py` no están expuestas.
- El equipo de media no puede ver **por qué** una oportunidad tiene su score: el contrato solo da
  el total.
- El motor tiene tres fallos que distorsionan los outliers y la reproducibilidad:
  1. `load_pieces` no respeta `as_of`: entra contenido publicado después y snapshots posteriores,
     así que un `analyze` con `as_of` en el pasado no es reproducible.
  2. `outlier_ratios` incluye la propia pieza en su referencia (sin leave-one-out).
  3. Las piezas muy recientes entran en la referencia con rendimiento todavía bajo y deprimen la
     mediana o el p90, lo que infla los ratios del resto.

## Criterios de aceptación

1. `Opportunity` tiene `score_breakdown` (null si `opportunity_score` es null) y
   `audience_fit_criteria` (null = sin evaluar). `Evidence` tiene `collection`
   (`automatic | manual`, default `automatic`). Payloads guardados antes del cambio siguen validando.
2. Cuando `opportunity_score` no es null, `score_breakdown.total == opportunity_score` y es
   `clamp(Σ value·weight − Σ penalizaciones, 0, 100)` redondeado a 1 decimal.
3. `GET /api/v1/opportunities`, `/opportunities/{id}`, `/opportunities/{id}/evidence` y
   `/opportunities/{id}/timeline` responden con los modelos del contrato y aparecen en `/docs`.
   Id desconocido → 404. Sin ninguna ejecución de `analyze` → 503 en el listado.
4. `load_pieces` excluye piezas con `published_at > as_of` y snapshots con `observed_at > as_of`.
5. `outlier_ratios` calcula la referencia de cada pieza sin ella misma y sin las piezas más jóvenes
   que `MIN_REFERENCE_AGE` de su plataforma. Las piezas jóvenes **sí** reciben ratio.
6. Tests de casos límite (0 snapshots, una sola fuente, ventana anterior vacía, métrica ausente)
   pasan. `pytest`, `ruff` y `pyright` en verde.
7. Tasa de outliers de HN con datos reales entre el 3 % y el 6 % (hoy 4,5 %), medida antes y
   después del cambio.
8. `data/fixtures/opportunities.json` cumple el contrato nuevo y sigue marcado como MOCK.

## No-objetivos

- Jev, `jev_judgments`, baterías, LLM `evaluate_topic`, `30x.yaml`, `audience_fit_score` y `actionability_score` reales
  (parte B). En esta parte `audience_fit_criteria` siempre es null en datos reales.
- `latam_gap` por región: ya hecho en `intel/engine` (`8ae61c8`, `latam_share` en `audience_mix.py`).
- LLM generativo, `why_it_matters` redactado, verificación de afirmaciones, lift, test de Poisson.
- MCP, backtest, loader del CSV manual, `usage_events` (Steven).
- Filtros de `period` y `segment` en el listado: se aceptan sin error pero no filtran (ver D4).
- Regenerar `frontend/src/types/api.ts`: lo hace el frontend lead con el OpenAPI nuevo.
- Cambiar pesos, umbrales de lifecycle o el orden del ranking.

## Reglas de CLAUDE.md §2 en juego

- **Nunca inventar datos:** `score_breakdown` es null cuando falta el score; `audience_fit_criteria`
  es null mientras Jev no evalúa. Los componentes ausentes no se rellenan con 0.
- **El LLM explica, no calcula:** el desglose sale de `intelligence/ranking.py`, determinista.
- **Distinguir el tipo de evidencia:** `Evidence.collection` dice si la pieza vino de un sensor
  automático o de curación manual.
- **Reproducibilidad:** el filtro de `as_of` hace que el mismo `as_of` dé el mismo resultado.
- Texto externo no confiable: no aplica (no hay LLM en esta parte).

## Contexto verificado del código

| Qué | Dónde | Estado actual |
| --- | --- | --- |
| Contrato `Evidence` | `backend/app/schemas/opportunity.py:68-82` | Sin `collection` |
| Contrato `Opportunity` | `backend/app/schemas/opportunity.py:85-113` | Sin `score_breakdown` ni `audience_fit_criteria` |
| Comentario erróneo | `backend/app/schemas/opportunity.py:98` | "Los calcula el LLM (rúbrica de §7)…": debe decir Jev |
| `SourceKind.MANUAL` | `backend/app/schemas/signal.py:35` | Ya existe (`"manual"`) |
| Pesos y penalizaciones | `backend/app/intelligence/ranking.py:13-21` | `W_MOMENTUM=0.30`, `W_FIT=0.25`, `W_CROSS=0.20`, `W_FRESHNESS=0.15`, `W_ACTION=0.10`, `PENALTY_SINGLE_SOURCE=10`, `PENALTY_SMALL_SAMPLE=10`, `SMALL_SAMPLE=8` |
| `opportunity_score` | `backend/app/intelligence/ranking.py:47-73` | Devuelve `float \| None`; None si falta fit o actionability |
| `outlier_ratios` | `backend/app/intelligence/opportunities.py:77-93` | Referencia = todas las piezas de la misma fuente, incluida ella misma; sin `as_of` |
| `Piece` | `backend/app/intelligence/opportunities.py:44-59` | Sin `source_kind`; termina en `snapshots` y `region` (ambos con default) |
| `_evidence` | `backend/app/intelligence/opportunities.py:104-118` | Sin `collection` |
| `_limitations` | `backend/app/intelligence/opportunities.py:132-145` | Dice "Audience fit y análisis editorial pendientes (sin LLM todavía)." |
| `build_opportunities` | `backend/app/intelligence/opportunities.py:148-` | Llama a `outlier_ratios(pieces)` y `opportunity_score(...)` con `audience_fit=None` |
| Constantes de outliers | `backend/app/intelligence/outliers.py:14-18` | `OUTLIER_RATIO=3.0`, `MIN_REFERENCE=5`, `MEDIAN=0.5`, `HN_REFERENCE_QUANTILE=0.9` |
| `load_pieces` | `backend/app/services/opportunities.py:43-77` | Filtra `published_at > as_of - LOOKBACK` pero no `≤ as_of`; carga todos los snapshots con `selectinload` |
| Lecturas ya hechas | `backend/app/services/opportunities.py` (`list_opportunities`, `get_opportunity`, `get_evidence`, `get_timeline`) | Devuelven `None` si no hay datos; `list_opportunities` acepta `lifecycle`, `confidence`, `topic` |
| Router existente | `backend/app/api/routes/sources.py` | Patrón: `APIRouter(prefix=…, tags=…)`, `Annotated[AsyncSession, Depends(get_session)]` |
| Montaje | `backend/app/main.py:22-24` | `api_v1.include_router(sources.router)` |
| Fixture | `data/fixtures/opportunities.json` + `backend/tests/test_opportunity_fixture.py` | Claves `_fixture`, `opportunities`, `evidence`, `timeline` |
| Prior art de tests | `backend/tests/test_build_opportunities.py:13-31` | Helper `piece(i, *, hours_ago, platform, source, points, seg)` con `AS_OF = 2026-10-17 12:00 UTC` |
| Tests de DB | `backend/tests/conftest.py:17-40` | Fixtures `engine` y `session` contra `radar_test` (drop/create de `Base.metadata`) |

## Decisiones tomadas

### D1 — Forma de `score_breakdown`

- **Elegido:**
  ```python
  class ScoreComponentName(StrEnum):
      MOMENTUM = "momentum"; AUDIENCE_FIT = "audience_fit"; CROSS_SOURCE = "cross_source"
      FRESHNESS = "freshness"; ACTIONABILITY = "actionability"

  class ScorePenaltyName(StrEnum):
      SINGLE_SOURCE = "single_source"; SMALL_SAMPLE = "small_sample"

  class ScoreComponent(BaseModel):
      name: ScoreComponentName
      value: Score            # 0–100; freshness = 100 − saturation
      weight: float = Field(ge=0, le=1)

  class ScorePenalty(BaseModel):
      name: ScorePenaltyName
      points: float = Field(ge=0)

  class ScoreBreakdown(BaseModel):
      components: list[ScoreComponent]   # siempre los 5, en el orden del enum
      penalties: list[ScorePenalty]      # solo las aplicadas
      total: Score                       # == Opportunity.opportunity_score
  ```
  `Opportunity.score_breakdown: ScoreBreakdown | None = Field(default=None, description="None si opportunity_score es None")`.
- **Por qué:** el frontend puede pintar barras por componente sin recalcular nada, y la UI dice
  qué penalización bajó el score.
- **Descartado:** un dict `{nombre: valor}` *(no tipado en OpenAPI; regla "nada de diccionarios anónimos")*.

### D2 — Forma de `audience_fit_criteria`

- **Elegido:**
  ```python
  class FitCriterion(StrEnum):
      BUSINESS_IMPACT = "business_impact"        # impacto en decisiones empresariales
      ORG_APPLICATION = "org_application"        # aplicación real en organizaciones
      EXEC_READABILITY = "exec_readability"      # comprensible para directivos no técnicos
      LATAM_RELEVANCE = "latam_relevance"        # relevancia LATAM
      PILLAR_FIT = "pillar_fit"                  # encaje con pilares 30X
      ACTIONABLE_CONTENT = "actionable_content"  # convertible en contenido accionable

  class AudienceFitCriterion(BaseModel):
      criterion: FitCriterion
      justification: str = Field(description="Por qué ese nivel, citando la evidencia")
      evidence_urls: list[HttpUrl] = Field(description="Evidencias del tema que cita la justificación")
      level: int = Field(ge=0, le=5, description="Nivel de la rúbrica 0–5 (LLM)")
  ```
  `justification` va antes que `level` a propósito: es el orden en que el LLM los genera, para
  que razone antes de puntuar (CLAUDE.md §7). Las evidencias se citan por URL porque `Evidence`
  no tiene otro id estable.
  `Opportunity.audience_fit_criteria: list[AudienceFitCriterion] | None = Field(default=None, description="None = sin evaluar")`.
- **Por qué:** es lo que devolverá `evaluate_topic` (LLM, CLAUDE.md §7 tras el merge de #8) en
  la parte B; fijarlo ya evita un segundo aviso de contrato.
- **Descartado:** dejarlo para la parte B *(obligaría a avisar dos veces en el canal)*.

### D3 — `Evidence.collection`

- **Elegido:** `class Collection(StrEnum): AUTOMATIC = "automatic"; MANUAL = "manual"`.
  `Evidence.collection: Collection = Field(default=Collection.AUTOMATIC, description="Sensor automático o curación manual")`.
  Se deriva de `Source.kind`: `MANUAL` si `kind == SourceKind.MANUAL`, `AUTOMATIC` en otro caso.
  `Piece` gana el campo `source_kind: SourceKind` (sin default, así que va **antes** de
  `snapshots` y `region`, que sí tienen default; actualizar el helper `piece()` de los tests con
  `source_kind=SourceKind.QUERY`).
- **Por qué:** `SourceKind.MANUAL` ya existe y el loader del CSV de Steven creará fuentes con ese
  kind. El default mantiene válidos los payloads ya guardados en `opportunities`.
- **Descartado:** derivarlo de `platform` *(LinkedIn/IG/TikTok solo son manuales hoy, pero YouTube
  puede llegar por los dos caminos)*.

### D4 — Rutas

- **Elegido:** `backend/app/api/routes/opportunities.py`, `APIRouter(prefix="/opportunities", tags=["opportunities"])`,
  montado en `main.py` junto a `sources`. Las rutas solo llaman a `services.opportunities`.
  - `GET ""` → `OpportunityList`. Query params: `lifecycle: Lifecycle | None`,
    `confidence: Confidence | None`, `topic: str | None`, `period: Period | None`. `period` se
    acepta para no romper al frontend pero **no filtra**: la respuesta siempre dice `period: "7d"`
    (ventanas 3 + 3 días), que es la verdad. Si el service devuelve `None` →
    `HTTPException(503, "Todavía no hay ninguna ejecución de analyze")`.
  - `GET "/{opportunity_id}"` → `Opportunity`; `None` → 404 `"Oportunidad no encontrada"`.
  - `GET "/{opportunity_id}/evidence"` → `list[Evidence]`; `None` → 404.
  - `GET "/{opportunity_id}/timeline"` → `OpportunityTimeline`; `None` → 404.
- **Por qué:** las lecturas ya existen en el service; las rutas son delgadas (CLAUDE.md §11). 503 y
  no 200 vacío porque `OpportunityList.generated_at` es obligatorio y no hay un valor real que poner.
- **Owner:** las hace Melkin (antes eran de Steven en §3 "API base"); ya avisado en el canal.
- **`recommendation_reason`** y las reglas nuevas de `recommendation` propuestas en CLAUDE.md §7
  quedan **fuera** de esta parte: pendientes de decisión de Melkin.

### D5 — Desglose en `ranking.py`

- **Elegido:** nueva función pura `score_breakdown(*, momentum, audience_fit, cross_source,
  saturation, actionability, source_count, item_count) -> ScoreBreakdown | None`, con la misma
  lógica que hoy tiene `opportunity_score`. `opportunity_score` pasa a ser
  `b = score_breakdown(...); return None if b is None else b.total` (misma firma, mismo
  comportamiento: los tests actuales no cambian). `build_opportunities` calcula el breakdown una vez
  y rellena `opportunity_score=b.total if b else None` y `score_breakdown=b`.
- **Por qué:** una sola fuente de verdad para el total y su desglose.

### D6 — Filtro de `as_of`

- **Elegido:** en `load_pieces`, añadir `ContentItem.published_at <= as_of` al `where` y cargar
  snapshots con `selectinload(ContentItem.snapshots.and_(MetricSnapshot.observed_at <= as_of))`.
  Ordenar los snapshots por `observed_at` en Python antes de usarlos (no confiar en el orden de la
  relación). `observed_at` de la pieza = `observed_at` del último snapshot kept; sin snapshots,
  `min(item.last_observed_at, as_of)`. `metrics` = las del último snapshot kept o `Metrics()`.
- **Por qué:** reproducibilidad y backtest futuro. Los snapshots nunca se borran ni se modifican.

### D7 — Leave-one-out y edad mínima de referencia

- **Elegido:** `outlier_ratios(pieces, as_of)` (nuevo argumento obligatorio, keyword o posicional).
  Para cada pieza con rendimiento, la referencia es el rendimiento de las **otras** piezas de su
  misma `source_id` cuya edad en `as_of` (`as_of − published_at`) sea ≥ `MIN_REFERENCE_AGE` de su
  plataforma. La pieza recibe ratio aunque sea joven. Constantes nuevas en
  `app/intelligence/outliers.py`:
  ```python
  # Las piezas recién publicadas aún no han acumulado métricas: dentro de la referencia hunden la
  # mediana (o el p90) y disparan los ratios del resto. Solo salen de la referencia; sí se puntúan.
  MIN_REFERENCE_AGE = {Platform.YOUTUBE: timedelta(days=2), Platform.HACKERNEWS: timedelta(hours=6)}
  ```
  Plataforma sin entrada → sin mínimo. `MIN_REFERENCE=5` se aplica tras las exclusiones.
- **Por qué:** con ventana actual de 3 días, quitar el ratio a las piezas jóvenes dejaría sin
  outliers la ventana que más importa para la detección temprana. HN acumula casi todos sus puntos
  en las primeras horas (6 h); YouTube tarda días (2 d).
- **Descartado:** ratio `None` para piezas jóvenes *(colapsa `outlier_count` y `momentum`)*.

### D8 — Texto de limitaciones

- **Elegido:** no cambiar el texto: "Audience fit y análisis editorial pendientes (sin LLM
  todavía)." sigue siendo cierto (el fit lo evalúa el LLM). Sin cambios de texto en esta parte.

### D9 — Ids estables anclados a la pieza más antigua (decidido por Melkin, 17:20)

- **Elegido:** `oid = f"opp_{anchor.item_id}"`, con `anchor = min(group, key=lambda p: (p.published_at, p.item_id))`.
  Se elimina el parámetro `id_prefix` de `build_opportunities` (`app/intelligence/opportunities.py:156,177`)
  y su uso en `app/services/opportunities.py:91`. El formato sigue siendo un `str`: el contrato no
  cambia.
- **Por qué:** el frontend y el MCP pueden guardar el id entre ejecuciones sin migración. Es estable
  mientras esa pieza siga en el cluster y dentro de los 14 días de `LOOKBACK`.
- **Aceptado:** si un tema se parte, la mitad sin el ancla cambia de id; un id viejo cuyo tema
  desapareció sigue respondiendo con su última versión (`_record` ordena por `run_id` desc) y su
  `last_updated` lo delata.
- **Descartado:** emparejar con la ejecución anterior por solape *(migración y más código)*; dejarlo
  como está *(frontend y MCP guardan ids)*.

### D10 — Volver a partir los clusters grandes o poco cohesionados (decidido por Melkin, 17:20)

- **Elegido:** en `app/intelligence/clustering.py`, después del clustering a `DISTANCE_THRESHOLD`:
  ```python
  # Con average linkage a 0.5 aparecen clusters que solo comparten el término de la búsqueda
  # ("AI agents" en HN: 36 piezas, similitud media 0.555 el 17/10). Se vuelven a partir una vez.
  SPLIT_MIN_SIZE = 25
  SPLIT_MIN_COHESION = 0.6
  SPLIT_THRESHOLD = 0.4
  ```
  `cohesion(embeddings, members) -> float` = media de la similitud coseno entre pares distintos (los
  embeddings ya vienen normalizados: `embeddings.py:26`). Un cluster con `len > SPLIT_MIN_SIZE` **o**
  `cohesion < SPLIT_MIN_COHESION` se vuelve a agrupar (mismo `AgglomerativeClustering`, solo sus
  miembros) con `SPLIT_THRESHOLD`; se quedan los subclusters con ≥ `MIN_CLUSTER_SIZE`. Un solo nivel
  de partición. El resultado final se ordena de mayor a menor como hoy.
  `cluster()` mantiene su firma. Nueva función pura `is_broad(embeddings, members) -> bool`
  (`len > SPLIT_MIN_SIZE and cohesion < SPLIT_MIN_COHESION`, tras la partición). `build_opportunities`
  gana el keyword `broad: Sequence[bool] | None = None` (uno por cluster); `services` lo calcula y se
  lo pasa. Un tema amplio añade a `limitations`: "Tema amplio: las piezas comparten poco más que el
  término de búsqueda; tómalo como categoría, no como historia concreta."
- **Por qué:** el #1 de Steven es un cajón de sastre (58 piezas de 22 fuentes) y no sirve
  editorialmente.
- **Descartado:** bajar el umbral global *(fragmenta los temas buenos que cruzan ES/EN)*; solo
  marcarlo *(sigue sin servir)*.

### D11 — Temas en descenso explicados en `lifecycle_reason` (decidido por Melkin, 17:20)

- **Elegido:** en `app/intelligence/lifecycle.py:67-71`, cuando ninguna regla se cumple y
  `acceleration < 0`, el texto pasa a
  `f"En descenso: aceleración {acceleration:+.0%}, saturación {saturation:.0f}, {source_count} fuentes. Ninguna etapa aplica."`.
  La etapa sigue siendo `unknown`, `insufficient` sigue en `False` y la recomendación sigue siendo
  `find_angle`. Con `acceleration ≥ 0` el texto actual no cambia.
- **Por qué:** 6 de 10 `unknown` locales son temas que se enfrían; la UI y el MCP pueden decirlo sin
  cambiar el enum del contrato.
- **Descartado:** etapa `declining` *(cambia el contrato)*; ocultarlos *(esconde datos reales)*.

## Diseño de módulos

- **Seam:** el contrato (`schemas/opportunity.py`) es la interfaz con frontend y MCP. El scoring
  sigue en `intelligence/` (puro), la lectura en `services/opportunities.py`, y la ruta solo
  traduce `None` a 404/503.
- **Interfaz:**
  - `score_breakdown(...) -> ScoreBreakdown | None`: None si `audience_fit` o `actionability` es
    None. Componentes siempre los 5, en el orden de `ScoreComponentName`; `freshness = 100 −
    saturation`; penalizaciones solo las aplicadas; `total` con clamp 0–100 y `round(…, 1)`.
  - `outlier_ratios(pieces, as_of) -> dict[int, float | None]`: None si la pieza no tiene métrica o
    su referencia tiene < 5 piezas o cuantil ≤ 0.
- **Ubicación (CLAUDE.md §10):** `schemas/opportunity.py`, `intelligence/ranking.py`,
  `intelligence/outliers.py`, `intelligence/opportunities.py`, `services/opportunities.py`,
  `api/routes/opportunities.py`, `main.py`.

## Acceso a datos

- `load_pieces`: una query con `join(Source)` y `selectinload` filtrado de snapshots (D6). Sin lazy
  loading. Hay que importar `MetricSnapshot` desde `app.models`.
- Sin migración: el cambio de contrato vive en el JSONB de `opportunities`. Los payloads antiguos
  validan gracias a los defaults (`None` / `automatic`).

## Plan de implementación

### Paso 1 — Medir la tasa de outliers de HN antes del cambio

- **Archivos:** ninguno (script en el scratchpad o `uv run python -c`).
- **Cambio:** con la DB local, correr `uv run python -m app.jobs.analyze` y calcular, sobre la
  evidencia guardada de la última ejecución, `% de piezas HN con is_outlier == True` entre las HN
  con ratio no nulo. Anotar el número en el informe (esperado ≈ 4,5 %).
- **Verificación:** número anotado.
- **Commit:** ninguno.

### Paso 2 — Contrato aditivo y fixture [HECHO]

- **Archivos:** `backend/app/schemas/opportunity.py`, `data/fixtures/opportunities.json`,
  `backend/tests/test_opportunity_fixture.py`.
- **Cambio:** añadir D1, D2 y D3 al schema. Corregir el comentario de la línea 98 a
  "Los calcula Jev (rúbrica de §7) y Python los combina. None = todavía sin evaluar; nunca un valor
  inventado." En el fixture: `collection: "automatic"` en cada evidencia (y `"manual"` en una
  si hay alguna de LinkedIn/IG/TikTok); para cada oportunidad con `opportunity_score` no nulo, un
  `score_breakdown` coherente; para cada una con `audience_fit_score` no nulo, 6
  `audience_fit_criteria` con `mean(level)/5·100 ≈ audience_fit_score` y cuyas `evidence_urls`
  estén entre las URLs de la evidencia de esa oportunidad. Mantener `_fixture` con
  "MOCK".
- **Test primero:** en `test_opportunity_fixture.py`:
  - `test_breakdown_matches_score`: si `score_breakdown` no es null, `total == opportunity_score`
    y `total == clamp(Σ value·weight − Σ points)` (`pytest.approx(…, abs=0.1)`); si
    `opportunity_score` es null, `score_breakdown` es null.
  - `test_fit_criteria_match_fit_score`: si hay criterios, son los 6 distintos,
    `mean(level)/5·100 == approx(audience_fit_score, abs=0.5)` y cada `evidence_urls` está en la
    evidencia de la oportunidad.
  - `test_old_payload_still_validates`: un `Opportunity` y un `Evidence` sin los campos nuevos
    validan, con `score_breakdown is None`, `audience_fit_criteria is None`,
    `collection is Collection.AUTOMATIC`.
- **Verificación:** `cd backend && uv run pytest tests/test_opportunity_fixture.py -q`
- **Commit:** `Add score breakdown, fit criteria and collection to the Opportunity contract`

### Paso 3 — Desglose del score en `ranking.py` [HECHO]

- **Archivos:** `backend/app/intelligence/ranking.py`, `backend/app/intelligence/opportunities.py`,
  `backend/tests/test_intelligence.py`.
- **Cambio:** D5. En `build_opportunities`, rellenar `score_breakdown`. Hoy siempre será None
  (fit None hasta la parte B), y eso es correcto.
- **Test primero:** `test_score_breakdown_worked_example`: momentum 80, fit 60, cross 50,
  saturation 30, actionability 40, 1 fuente, 5 piezas → componentes
  `[(momentum,80,0.30),(audience_fit,60,0.25),(cross_source,50,0.20),(freshness,70,0.15),(actionability,40,0.10)]`,
  penalizaciones `single_source 10` y `small_sample 10`, total = 24 + 15 + 10 + 10.5 + 4 − 20 =
  **43.5**. `test_score_breakdown_is_none_without_fit` (fit None → None; actionability None → None).
- **Verificación:** `cd backend && uv run pytest tests/test_intelligence.py -q`
- **Commit:** `Compute the opportunity score breakdown in ranking`

### Paso 4 — `collection` en la evidencia [HECHO]

- **Archivos:** `backend/app/intelligence/opportunities.py`, `backend/app/services/opportunities.py`,
  `backend/tests/test_build_opportunities.py`.
- **Cambio:** D3: `Piece.source_kind`, `load_pieces` lo rellena con `SourceKind(source.kind)`,
  `_evidence` pone `collection`. Actualizar el helper `piece()` (parámetro `kind=SourceKind.QUERY`).
- **Test primero:** `test_manual_source_is_marked_manual_in_evidence`: un tema con una pieza de
  `SourceKind.MANUAL` produce una evidencia con `collection is Collection.MANUAL` y las demás
  `AUTOMATIC`.
- **Verificación:** `cd backend && uv run pytest tests/test_build_opportunities.py -q`
- **Commit:** `Mark manual-sensor evidence in opportunities`

### Paso 5 — Leave-one-out y edad mínima de referencia [HECHO]

- **Archivos:** `backend/app/intelligence/outliers.py`, `backend/app/intelligence/opportunities.py`,
  `backend/tests/test_build_opportunities.py`.
- **Cambio:** D7. `build_opportunities` pasa `as_of` a `outlier_ratios`.
- **Test primero** (recalcular a mano los esperados de `test_hn_outlier_ratios_use_p90_of_same_query`
  con leave-one-out: 10 piezas de 10 puntos + una de 100; referencia de la de 100 = diez de 10 →
  p90 = 10 → ratio 10.0; referencia de una de 10 = nueve de 10 + una de 100 → p90 =
  `np.quantile([10]*9+[100], 0.9)` = 19.0 → ratio 0.53. Ajustar el assert de `ratios[0]`):
  - `test_piece_is_excluded_from_its_own_reference`: el caso anterior.
  - `test_young_pieces_are_scored_but_not_in_reference`: 6 HN de 10 puntos con 10 h + 5 HN de
    1 punto con 2 h + una HN de 100 puntos con 2 h. La de 100 tiene ratio = 100 / p90(seis de 10)
    = 10.0 (las de 2 h no están en su referencia); cada pieza de 2 h tiene ratio no nulo.
  - `test_youtube_reference_needs_two_days`: canal con 4 vídeos de ≥ 2 días y 3 de 1 día → la
    referencia tiene 4 < 5 → todos `None`.
- **Verificación:** `cd backend && uv run pytest tests/test_build_opportunities.py -q`
- **Commit:** `Use leave-one-out references and a minimum reference age for outliers`

### Paso 6 — Filtro de `as_of` en `load_pieces` [HECHO]

- **Archivos:** `backend/app/services/opportunities.py`, `backend/tests/test_load_pieces.py` (nuevo).
- **Cambio:** D6.
- **Test primero** (DB `radar_test`, fixture `session`): `test_load_pieces_ignores_the_future`:
  una fuente activa HN con tres items: uno publicado antes de `as_of` con snapshots en
  `as_of − 2 h` y `as_of + 1 h`; uno publicado después de `as_of`; uno publicado antes sin
  snapshots. Esperado: 2 piezas; la primera con 1 snapshot y `metrics` del de `as_of − 2 h` y
  `observed_at == as_of − 2 h`; la tercera con `metrics == Metrics()` y `snapshots == []`.
- **Verificación:** `cd backend && uv run pytest tests/test_load_pieces.py -q`
- **Commit:** `Respect as_of when loading pieces and snapshots`

### Paso 7 — Casos límite del motor [HECHO]

- **Archivos:** `backend/tests/test_build_opportunities.py`.
- **Cambio:** solo tests (arreglar el código si alguno falla por un bug real y decirlo en el commit).
- **Test primero**, parametrizado con `ids=` donde solo cambia el input:
  - `zero_snapshots`: tema HN cuyas piezas no tienen snapshots ni métricas → evidencias con
    `velocity is None`, `outlier_ratio is None`, `is_outlier is None`; `outlier_count == 0`;
    `top_outlier_ratio is None`.
  - `single_source`: tema con ≥ 5 piezas de una sola fuente → `lifecycle is Lifecycle.UNKNOWN`,
    `confidence is Confidence.LOW`, una limitación con "una plataforma".
  - `empty_previous_window`: ≥ 5 piezas, todas en las últimas 72 h, de ≥ 3 fuentes →
    `growth_status is GrowthStatus.ESTIMATED`.
  - `missing_metric`: pieza HN con `Metrics(points=None)` dentro de un grupo con referencia →
    su ratio es `None` y no rompe el resto.
- **Verificación:** `cd backend && uv run pytest tests/test_build_opportunities.py -q`
- **Commit:** `Cover scoring edge cases: no snapshots, single source, empty window, missing metric`

### Paso 8 — Rutas de oportunidades [HECHO por Steven, PR #9]

- No implementar: `backend/app/api/routes/opportunities.py` y `backend/tests/test_opportunity_routes.py`
  ya están en la rama base. **Diferencia con D4:** sin ejecuciones de `analyze`, el listado devuelve
  `200` con `null` (no 503); se queda así (gana el código existente).
- Solo comprobar que sus tests siguen en verde tras los pasos 2 y 9 (el fixture conserva los ids
  `opp_001…`).

### Paso 9 — Ids estables

- **Archivos:** `backend/app/intelligence/opportunities.py`, `backend/app/services/opportunities.py`,
  `backend/tests/test_build_opportunities.py`.
- **Cambio:** D9.
- **Test primero:** `test_id_is_anchored_to_the_oldest_piece`: un tema de 6 piezas → id
  `opp_<item_id de la más antigua>`; añadir una pieza más nueva al mismo cluster y repetir → mismo
  id; dos piezas con el mismo `published_at` → gana el `item_id` menor.
- **Verificación:** `cd backend && uv run pytest tests/test_build_opportunities.py -q`
- **Commit:** `Anchor opportunity ids to the oldest piece of each topic`

### Paso 10 — Partir clusters cajón de sastre

- **Archivos:** `backend/app/intelligence/clustering.py`, `backend/app/intelligence/opportunities.py`,
  `backend/app/services/opportunities.py`, `backend/tests/test_clustering.py` (nuevo),
  `backend/tests/test_build_opportunities.py`.
- **Cambio:** D10.
- **Test primero** (embeddings sintéticos normalizados, sin modelo):
  - `test_large_cluster_is_split`: dos grupos de 15 vectores, cada uno a ≤ 0.02 de distancia coseno
    de su centro, con los dos centros a distancia coseno 0.45 → a 0.5 se unirían (30 > 25) → salen
    2 clusters de 15.
  - `test_small_cohesive_cluster_is_kept`: un grupo de 10 vectores casi iguales → 1 cluster de 10.
  - `test_cohesion_of_identical_vectors_is_one` y `test_is_broad`: `is_broad` llamado
    directamente sobre 30 vectores ortogonales dos a dos en un espacio de 32 dimensiones
    (cohesión 0) → `True`; sobre el grupo de 10 casi iguales → `False`.
  - `test_broad_topic_has_limitation` en `test_build_opportunities.py`: `broad=[True]` → la nota
    "Tema amplio" está en `limitations`.
- **Verificación:** `cd backend && uv run pytest tests/test_clustering.py tests/test_build_opportunities.py -q`
- **Commit:** `Split catch-all clusters and flag broad topics`

### Paso 11 — Temas en descenso

- **Archivos:** `backend/app/intelligence/lifecycle.py`, `backend/tests/test_intelligence.py`.
- **Cambio:** D11.
- **Test primero:** `test_declining_topic_reason`: aceleración −0.52, saturación 22, 5 fuentes, 10
  piezas → `Lifecycle.UNKNOWN`, `insufficient is False`, `reason.startswith("En descenso: aceleración -52%")`.
  Con aceleración +0.43 y saturación 82 → el texto sigue empezando por "Ninguna regla se cumple".
- **Verificación:** `cd backend && uv run pytest tests/test_intelligence.py -q`
- **Commit:** `Explain declining topics in lifecycle_reason`

### Paso 12 — Verificación con datos reales

- **Archivos:** ninguno.
- **Cambio:** correr `analyze` en local, repetir la medición del paso 1 (tasa HN después) e
  imprimir el top 10 (topic, lifecycle, acceleration, outlier_count, momentum_score,
  opportunity_score) con `curl -s localhost:8000/api/v1/opportunities | python3 -m json.tool | head`
  o un script equivalente. Además: tamaño del cluster más grande (debe ser ≤ 25 o llevar "Tema
  amplio"), nº de `unknown` por motivo, y que dos ejecuciones seguidas de `analyze` repiten la
  mayoría de los ids (pegar cuántos coinciden). Si la tasa HN queda fuera del 3–6 %, **no** tocar umbrales: anotarlo en
  "Preguntas abiertas", poner el gate en `BLOQUEADO` y parar.
- **Verificación:** salida real pegada en el informe.
- **Commit:** ninguno.

## Estrategia de test

- **Seams:** funciones puras de `intelligence/` (`build_opportunities`, `outlier_ratios`,
  `score_breakdown`), `load_pieces` contra `radar_test`, y la app ASGI para las rutas.
- **Prior art:** `backend/tests/test_build_opportunities.py` (helper `piece`) y
  `backend/tests/test_intelligence.py`.
- **Casos que entran:** ids anclados (D9), partición y cohesión (D10, cajón de sastre real del
  17/10), texto de descenso (D11); los cuatro casos límite obligatorios (CLAUDE.md §11); leave-one-out y edad
  mínima (D7, bug real); `as_of` (D6, bug real); ejemplo trabajado del breakdown (D5); rutas
  feliz/404/503 y filtro (D4); compatibilidad de payloads antiguos (D3, datos ya guardados).
- **Casos descartados por ruido:** combinaciones de filtros del listado, validación de cada campo
  del schema por separado, orden de la evidencia (ya cubierto).
- **Parametrización:** casos límite del paso 7 con `ids=["zero_snapshots", "single_source",
  "empty_previous_window", "missing_metric"]` si comparten estructura; si no, tests separados.

## Verificación final

```bash
cd /Users/melandres8/Documents/Projects/content-radar/backend
uv run ruff check . && uv run ruff format --check .
uv run pyright app
uv run pytest -q
uv run python -m app.jobs.analyze
```

Más la tasa de outliers HN antes/después y el top 10 del paso 9.

## Riesgos

- **Tasa de outliers HN fuera del 3–6 % tras el leave-one-out** — el paso 9 lo mide → parar y
  preguntar; no ajustar `HN_REFERENCE_QUANTILE` ni `MIN_REFERENCE_AGE` sin decisión.
- **`selectinload(...and_(...))` no soportado en la versión de SQLAlchemy instalada** — error al
  importar o ejecutar → filtrar los snapshots en Python tras cargarlos (mismo resultado) y anotarlo.
- **El frontend usa tipos viejos** — avisar al frontend lead en el handoff para que regenere
  `src/types/api.ts` desde `/openapi.json`.

## Historial de intentos

| Fecha | Qué bloqueó | Qué se decidió | Commits que quedaron |
| --- | --- | --- | --- |

## Preguntas abiertas

- (ninguna)
