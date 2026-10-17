# intel-phase1-llm-fit — Audience fit de cada tema con el LLM

> Plan generado con `/spec`. Parte C de la fase 1. Depende de la parte A (contrato
> `audience_fit_criteria` y `score_breakdown`) y usa como pistas las etiquetas de la parte B (Jev).

## Metadatos

- **Slug:** `intel-phase1-llm-fit` · **Issue:** ninguno
- **Owner (CLAUDE.md §3):** Melkin
- **Prioridad (CLAUDE.md §12):** P0 ("audience fit con el LLM") · **Checkpoint que desbloquea
  (§13):** MVP P0 end-to-end, dom 00:30 ESP
- **Valor:** eje X del Radar, `opportunity_score` no nulo y `publish_now` posible · **Pregunta de
  `docs/brief.md` §4:** #3
- **Repo:** `/Users/melandres8/Documents/Projects/content-radar`
- **Rama base:** `main` @ `f3eaeae` (ya incluye las partes A y B, PR #19)
- **Rama de trabajo:** `intel/llm-topic-fit`
- **Fecha:** 2026-10-17 17:15 ESP
- **Contratos tocados:** ninguno nuevo (usa `audience_fit_criteria` de la parte A)
- **Auditoría tras `/build`:** sí
- **Estado del gate:** `LISTO` (perfil y rúbrica en borrador; se pueden editar sin tocar código)

## Alcance acordado (CLAUDE.md §7 tras el merge de #8)

- `evaluate_topic` (LLM, SDK oficial del proveedor, salida Pydantic): para cada uno de los 6
  criterios, primero `justification` citando `evidence_urls` del tema y después `level` entero 0–5.
- Entrada: etiqueta del tema, hasta 10 piezas representativas (título + descripción corta,
  **delimitadas** como datos; sin las piezas con `injection > 0.5` de la parte B), `audience_mix`,
  conteos de las pistas de Jev ("8 de 20 piezas muestran un caso real") y el perfil
  `data/audiences/30x.yaml`.
- Python: valida que cada URL citada pertenece al tema (si no, descarta la cita y lo anota),
  `audience_fit_score = mean(level)/5·100` (pesos iguales, constante con nombre), y
  `actionability_score = level(actionable_content)/5·100`. Rellena `score_breakdown`.
- Comprueba `stop_reason` (rechazo o `max_tokens`) antes de leer la respuesta; si falla → null y
  una limitación.
- Caché en Postgres por hash de la entrada + versión del prompt + modelo. `UsageRecorder` de la
  parte B con `provider` del LLM.
- Prompt versionado en `backend/app/editorial/prompts/evaluate_topic.v1.md`.
- Fuera: `why_it_matters` redactado, verificación con Jev, lift, briefs, `recommendation_reason`
  y las reglas nuevas de `recommendation` (propuestas en §7, pendientes de decisión).

## Decisiones tomadas (2026-10-17 19:20 ESP)

- **D1 · Modelo:** `claude-haiku-5-5` con el SDK oficial `anthropic` (versión publicada hace ≥ 7 días,
  fijada en `pyproject.toml`). `LLM_API_KEY` y `LLM_MODEL` ya están en `backend/.env`; nunca se
  imprimen. Salida estructurada validada con Pydantic (tool use con el schema, o structured outputs
  si la versión del SDK lo soporta). Comprobar `stop_reason` antes de leer: `refusal` o `max_tokens`
  → fit null y una limitación "No se pudo evaluar el encaje con la audiencia".
- **D2 · Perfil:** `data/audiences/30x.yaml` (borrador sacado de la web pública de 30X; Melkin lo
  revisa contra Instagram). El código lo carga tal cual y lo pasa al prompt como datos. `status:
  borrador` no bloquea la evaluación.
- **D3 · Rúbrica:** `backend/app/editorial/prompts/audience_fit_rubric.v1.yaml` (6 criterios, ids =
  `FitCriterion`, niveles 0–5 descritos). El prompt incluye la pregunta y los 6 niveles de cada
  criterio.
- **D4 · Pistas de Jev:** conteos por tema desde `jev_judgments` (batería v2) con
  `to_piece_judgment`: `business_use`, `dev_audience`, `business_case`, `tech_jargon`,
  `latam_context`, `launch` y formato. Se pasan como "N de M piezas clasificadas" (los inciertos no
  cuentan y se dice cuántos lo son). Piezas con `excluded_from_llm` no entran en el prompt.
- **D5 · Filtro `about_ai`:** antes del clustering se quitan las piezas con `about_ai` = False
  (seguro). Las inciertas y las sin clasificar se quedan. Registrar en `run_row.stats` cuántas se
  quitaron. Va en esta rama porque toca `compute_opportunities`.
- **D6 · Cálculo:** `audience_fit_score = mean(levels)/5·100` (pesos iguales, constante con nombre),
  `actionability_score = level(actionable_content)/5·100`, y con ellos `score_breakdown`,
  `opportunity_score` y `recommendation` (reglas actuales de `ranking.py`, sin las propuestas de
  David). Las URLs citadas que no son del tema se descartan y se anota en `limitations`.
  `audience_fit_criteria` se rellena con justificación, URLs válidas y nivel.
- **D7 · Caché:** tabla nueva `llm_evaluations` (migración) con clave sha256 de la entrada
  canónica + versión del prompt + versión de la rúbrica + hash del perfil + modelo. Guarda la salida
  validada y los tokens.
- **D8 · Coste:** `UsageMeter.add(Provider.LLM_TEXT, "evaluate_topic", …)` con tokens de entrada y
  salida. Si `VariablePrice` no lee `input_price_per_unit`/`output_price_per_unit` de `llm_text`,
  arreglarlo en `services/costs.py` con test (aviso a Steven en el informe).
- **D9 · Concurrencia:** `asyncio.Semaphore(4)`; un fallo por tema (error del SDK, validación)
  deja ese tema con fit null y una limitación, y el job sigue.
- **D10 · Seguridad (regla 6):** títulos y descripciones van dentro de un bloque delimitado
  (`<evidence>` con un `id` por pieza) y el system prompt dice que es texto no confiable. Nada de
  texto externo en el system prompt.
- **D11 · Tests:** el cliente del LLM detrás de un `Protocol` (`TopicEvaluator`) con un fake en los
  tests; nada de llamadas reales en pytest. Casos: niveles → scores (ejemplo trabajado a mano),
  URL citada ajena al tema, `stop_reason` max_tokens/refusal, caché (segunda ejecución 0 llamadas),
  sin clave → todo null y el job sigue, filtro `about_ai`.
- **D12 · Verificación real:** `analyze` contra la DB local (`DATABASE_URL` sobrescrita a
  `postgresql+asyncpg://radar:radar@localhost:5433/radar`), nunca contra Supabase en esta rama.
  Informar: nº de temas evaluados, fallidos, coste, distribución de recomendaciones y 3 ejemplos de
  criterios con su justificación.

## Pasos

El plan no traía pasos: `plan-implementer` los deriva de D1–D12, sin decisiones nuevas.

### Paso 1 — Precio de entrada y salida del LLM (D8)
### Paso 2 — Juicios de Jev por pieza y filtro `about_ai` (D4, D5)
### Paso 3 — Del nivel de cada criterio a los scores (D6)
### Paso 4 — Evaluador con el SDK de Anthropic y prompt v1 (D1, D2, D3, D10)
### Paso 5 — Caché `llm_evaluations` y servicio de evaluación (D7, D9, D11)
### Paso 6 — Integración en `analyze` y textos que dejan de ser ciertos
### Paso 7 — Verificación real contra la DB local (D12)

## Preguntas abiertas

- (ninguna; perfil y rúbrica en borrador, revisables sin tocar código)
