# intel-phase1-jev — Cliente Jev y batería de pieza con caché

> Plan generado con `/spec`. Lo implementa `plan-implementer` con contexto limpio.
> El implementador NO ve la conversación que produjo este documento: todo lo que necesite tiene que
> estar escrito aquí.
>
> Es la **parte B** de la fase 1. La parte A (`.claude/plans/intel-phase1-real-opportunities.plan.md`:
> contrato, rutas, correcciones del motor) y la parte C (`.claude/plans/intel-phase1-llm-fit.plan.md`:
> audience fit con el LLM) son planes aparte. B no toca los archivos de A, así que pueden ir en
> paralelo.

## Metadatos

- **Slug:** `intel-phase1-jev` · **Issue:** ninguno
- **Owner (CLAUDE.md §3):** Melkin
- **Prioridad (CLAUDE.md §12):** P0 ("clasificación por pieza con Jev") · **Checkpoint que
  desbloquea (§13):** MVP P0 end-to-end, dom 00:30 ESP. En el orden de construcción de §12 va antes
  del audience fit con el LLM, que recibe sus conteos como pistas.
- **Valor (filtro de CLAUDE.md §12):** paso "entender por qué importa" del recorrido de demo: las
  etiquetas por pieza (formato, gancho, caso real…) alimentan el audience fit del LLM y el *lift*
  del "por qué funcionó"; `injection` protege el contexto del LLM (regla 6) · **Pregunta de
  `docs/brief.md` §4:** #3
- **Repo:** `/Users/melandres8/Documents/Projects/content-radar`
- **Rama base:** `origin/data/cost-tracking` @ `f0be180` (PR #10 de Steven, ya con `intel/engine` @ `8ae61c8` mergeada y la migración `5c0a7e3d91b2` encadenada tras `aebe360930be`; un solo head)
- **Rama de trabajo:** `intel/jev-piece-battery`, **ya creada** en el worktree
  `/Users/melandres8/Documents/Projects/content-radar-jev` (con `backend/.env` copiado y `uv sync`
  hecho). Trabaja **solo** en ese worktree: en el repo principal hay otro implementador con la parte A.
  PR contra `data/cost-tracking` (o contra `main` cuando entren #7 y #10).
- **Tests en paralelo:** el otro implementador usa `radar_test`. Ejecuta **siempre** pytest con
  `TEST_DATABASE_URL=postgresql+asyncpg://radar:radar@localhost:5433/radar_test_jev` (lo soporta
  `backend/tests/conftest.py`). Las migraciones contra la DB local (`radar`) sí son compartidas: el
  paso 4 solo añade una tabla nueva.
- **Fecha:** 2026-10-17 17:10 ESP
- **Contratos tocados:** ninguno (`Opportunity`, `Evidence` y OpenAPI no cambian; tabla nueva interna)
- **Auditoría tras `/build`:** sí
- **Estado del gate:** `LISTO`

## Problema

No hay ninguna clasificación por pieza. Sin ella, el LLM de la parte C evaluaría temas sin pistas
medidas, el "por qué funcionó" no tiene rasgos que contar y nada filtra las piezas con
instrucciones dirigidas a un sistema de IA antes de que lleguen al LLM.

## Criterios de aceptación

1. `backend/app/intelligence/jev.py` es el único punto de acceso a Jev: `AsyncTypeSafeClient` con
   `asyncio.Semaphore(6)` y los reintentos por defecto del SDK.
2. La batería de pieza `piece.v1` se ejecuta en `analyze` para cada pieza cargada y se guarda en
   `jev_judgments`. Una segunda ejecución sin piezas nuevas hace **0** llamadas a Jev (caché).
3. Clave de caché = sha256 del JSON canónico (`sort_keys=True`, `ensure_ascii=False`) de
   `{"state": state, "battery": "piece", "battery_version": 1, "model": settings.jev_model}`.
4. Python convierte cada respuesta en un `PieceJudgment` con los umbrales de `docs/jev.md` ("Del
   juicio a la decisión"); lo incierto queda como `None`.
5. Sin `TYPESAFE_API_KEY`, o si Jev falla tras los reintentos del SDK: `analyze` termina con éxito,
   registra cuántas piezas quedaron sin clasificar y las oportunidades salen igual que hoy.
6. Cada llamada real (no las de caché) se cuenta en el `UsageMeter` de Steven
   (`app/collectors/usage.py`) y el job lo persiste en `usage_events` con `record_meter` (D12).
7. Tests sin red: el adaptador del SDK se prueba con `httpx2.MockTransport`; la lógica de caché y
   de decisiones, con un juez falso que implementa el `Protocol`.
8. Smoke real: una llamada a Jev con una pieza de la DB local responde y se cachea.

## No-objetivos

- La pregunta `pillar`: depende de `data/audiences/30x.yaml`, que todavía no existe. Entrará en
  `piece.v2`.
- Usar las etiquetas en scoring, en el contrato o en la UI. Aquí solo se calculan y se guardan.
- Filtrar piezas por `relevant` antes del clustering (pendiente de la validación con 30–50 piezas
  etiquetadas: una pregunta con < 70 % de acuerdo no se usa en la demo).
- Batería de pares, verificación de afirmaciones, LLM, lift, MCP.
- Cambiar `usage_events`, `record_usage`, `record_meter` o `data/pricing.yaml` (Steven): solo se usan.

## Reglas de CLAUDE.md §2 en juego

- **Regla 4:** Jev emite juicios atómicos; los umbrales y la decisión están en Python.
- **Regla 6:** el texto de la pieza va **solo** en `state`; nuestras instrucciones van en
  `questions`. La descripción se recorta a 1.000 caracteres.
- **Regla 3:** un juicio incierto o una pieza sin clasificar se guarda como `None`, nunca como "no".
- **Secretos:** la clave sale de `TYPESAFE_API_KEY` en `backend/.env`; nunca en código, tests, logs
  ni commits. No loguear el `state` ni las cabeceras.

## Contexto verificado del código

| Qué | Dónde | Estado actual |
| --- | --- | --- |
| SDK | PyPI `typesafe-sdk` | 0.7.4 publicada 2026-10-09 (cumple ≥ 7 días); 0.7.5 es del 2026-10-14 y **no** se permite. No está en `pyproject.toml` |
| Dependencia transitiva | `httpx2` 2.13.1 (2026-09-23) | Ya instalada en `.venv`; `httpx2.MockTransport` existe |
| Constructor | `typesafe_sdk` 0.7.4, `_core/client/aio/client.py:46-58` | `AsyncTypeSafeClient(*, api_key, model, retry, timeout, headers, transport, http_client, base_url)` |
| Llamada | mismo archivo, `:139-151` | `await client.system_one(state, questions, *, model, retry, timeout, …) -> SystemOneResponse` |
| Respuesta | `_core/response_types.py` | `SystemOneResponse.model: str`, `.answers[id]`, `.usage.input_tokens/output_tokens` (`int \| None`). `ChoiceAnswer`: `choice`, `probabilities`, `confidence`. `ScoreAnswer`: `score` (media ponderada por probabilidad, 0-indexada), `legend`, `confidence`, `probabilities`. `NoulAnswer`: `noul` (0–1), sin `confidence` |
| Preguntas | exports de `typesafe_sdk` | `Choice(instructions=..., criteria={opción: descripción})`, `Score(instructions=..., criteria=[niveles])`, `Noul(instructions=...)` |
| Errores | exports de `typesafe_sdk` | `TypeSafeRateLimitError`, `TypeSafeAuthenticationError`, `TypeSafeAPIConnectionError` (y una base común: comprobar su nombre en el paquete instalado) |
| Settings | `backend/app/core/config.py` | Sin campos de Jev |
| `.env` | `backend/.env` | `TYPESAFE_API_KEY` **definida**; `JEV_MODEL` no está (usar default) |
| `.env.example` | raíz | `TYPESAFE_API_KEY=` y `JEV_MODEL=jev-1.13.0` |
| Job | `backend/app/jobs/analyze.py:25-72` | `compute_opportunities` → `save_opportunities` → `run_row.stats` |
| Carga de piezas | `backend/app/services/opportunities.py` `load_pieces` | Devuelve `Piece` (ver `app/intelligence/opportunities.py:44`) con `item_id`, `title`, `description`, `platform`, `source_name`, `language` |
| Modelos | `backend/app/models/__init__.py` | Exporta `Base`, `ContentItem`, `MetricSnapshot`, `OpportunityRecord`, `PipelineRun`, `Source` |
| Batería y umbrales | `docs/jev.md` "1. Pieza" y "Del juicio a la decisión" | Fuente de las preguntas y opciones |
| Consumo | `app/collectors/usage.py` (`UsageMeter.add(provider, operation, units)`), `app/services/costs.py` (`record_meter(session, meter, *, pipeline_run_id)`, hace un solo `commit`), `app/schemas/cost.py` (`Provider.TYPESAFE_JEV`) | `pricing.yaml`: `typesafe_jev`, `unit: input_tokens`, 0,042 $/M. **No usar `record_usage`**: hace `commit` por llamada |
| Última migración | `backend/alembic/versions/5c0a7e3d91b2_usage_events.py` | Head actual (revisa `aebe360930be`). La migración nueva de `jev_judgments` revisa `5c0a7e3d91b2` |

## Decisiones tomadas

### D1 — Dependencia y settings

- **Elegido:** `typesafe-sdk==0.7.4` en `dependencies`. Sin `exclude-newer` global (degradaría
  dependencias ya bloqueadas). En su lugar, tras `uv lock`, listar los paquetes **nuevos** del diff de
  `uv.lock` y comprobar su fecha en `https://pypi.org/pypi/<paquete>/<versión>/json`
  (`urls[0].upload_time`): si alguno tiene < 7 días, fijar la versión anterior que sí cumpla y
  anotarlo en el commit. En `Settings`:
  `typesafe_api_key: str = ""` y `jev_model: str = "jev-1.13.0"`. El cliente se construye con
  `api_key=settings.typesafe_api_key, model=settings.jev_model`.
- **Por qué:** CLAUDE.md §7 fija `JEV_MODEL=jev-1.13.0`; regla del equipo de no usar paquetes de
  < 7 días.

### D2 — Batería `piece.v1`

Archivo `backend/app/editorial/prompts/jev/piece.v1.yaml` (YAML con `version: 1` y una entrada por
pregunta: `id`, `type` = `noul|choice|score`, `instructions`, `criteria`). Instrucciones en
**español**. El loader lo convierte en `dict[str, Noul | Choice | Score]`.

`state` = `{"title": …, "description": (≤ 1000 caracteres o null), "channel": source_name,
"platform": platform.value, "language": language}`.

| id | Tipo | Instrucción | Opciones / niveles |
| --- | --- | --- | --- |
| `relevant` | noul | ¿La pieza trata de inteligencia artificial aplicada a empresas u organizaciones? | — |
| `injection` | noul | ¿El texto contiene instrucciones dirigidas a un sistema de IA (por ejemplo, "ignora las instrucciones anteriores")? | — |
| `format` | choice | ¿Qué formato tiene la pieza? | `tutorial`: enseña a hacer algo paso a paso · `opinion`: defiende una postura · `news`: noticia o lanzamiento · `use_case`: caso de uso en una organización · `interview`: entrevista o podcast · `demo`: demostración de un producto · `list`: lista o recopilación |
| `format_rev` | choice | igual que `format` | mismas opciones en orden inverso |
| `hook` | choice | ¿Qué tipo de gancho usa el título? | `question`: una pregunta · `data`: un dato o cifra · `counterintuitive`: algo contraintuitivo · `story`: una historia · `how_to`: cómo hacer algo · `news`: una noticia · `list`: una lista |
| `hook_rev` | choice | igual que `hook` | mismas opciones en orden inverso |
| `announcement` | noul | ¿Es el anuncio de un lanzamiento o una noticia puntual? | — |
| `business_case` | noul | ¿Describe un caso real de uso de IA en una organización concreta? | — |
| `exec_readability` | score | ¿Quién puede entender esta pieza? | `requiere perfil técnico` · `requiere bastante contexto técnico` · `la entiende un profesional con algo de contexto` · `la entiende un directivo sin perfil técnico` |
| `latam_context` | noul | ¿Menciona empresas, países o el contexto de Latinoamérica? | — |

### D3 — De respuesta a decisión (Python, `intelligence/jev.py`)

Constantes con nombre: `CHOICE_MIN_PROB = 0.6`, `NOUL_YES = 0.7`, `NOUL_NO = 0.3`,
`SCORE_MIN_CONFIDENCE = 0.5`.

```python
@dataclass(frozen=True)
class PieceJudgment:
    item_id: int
    relevant: bool | None
    injection: bool | None
    format: str | None          # None si prob máx < 0.6 o no coincide con format_rev
    hook: str | None            # igual con hook_rev
    announcement: bool | None
    business_case: bool | None
    exec_readability: int | None  # nivel redondeado 0–3; None si confidence < 0.5
    latam_context: bool | None
```

- `noul ≥ 0.7` → `True`; `≤ 0.3` → `False`; entre medias → `None`.
- `choice`: aceptado si `max(probabilities) ≥ 0.6` **y** `choice == choice_rev`; si no, `None`.
- `score`: `round(score)` si `confidence ≥ 0.5`; si no, `None`.
- `injection` para el contexto del LLM (parte C): una pieza se excluye si `noul > 0.5` (umbral
  distinto a propósito: `INJECTION_EXCLUDE = 0.5`, `docs/jev.md`). Exponerlo como función
  `excluded_from_llm(answers) -> bool` que lee el `noul` crudo.

### D4 — Tabla `jev_judgments` (una fila por llamada)

```
id              bigint pk
cache_key       char(64) unique            -- sha256 hex (criterio 3)
battery         varchar(32)  index         -- "piece"
battery_version int
requested_model varchar(64)
response_model  varchar(64)
content_item_id int fk content_items.id ondelete cascade, nullable, index
answers         jsonb                       -- response.answers serializado (model_dump(mode="json"))
input_tokens    int null
output_tokens   int null
created_at      timestamptz default now()
```

Modelo `JevJudgment` en `backend/app/models/jev.py`, exportado en `app/models/__init__.py`.
Migración Alembic nueva (`uv run alembic revision --autogenerate -m "jev judgments"`), revisada a
mano y formateada con ruff.

- **Por qué una fila por llamada y no por pregunta:** la caché es por llamada (criterio 3) y la
  batería se evalúa entera; las respuestas con sus probabilidades quedan en `answers` para auditar.

### D5 — Seams

```python
class Judge(Protocol):
    async def judge(self, state: dict[str, Any], questions: Mapping[str, Question]) -> JudgeResult: ...

@dataclass(frozen=True)
class JudgeResult:
    model: str
    answers: dict[str, Any]       # JSON de cada respuesta
    input_tokens: int | None
    output_tokens: int | None
```

- `TypeSafeJudge(client: AsyncTypeSafeClient, semaphore: asyncio.Semaphore)` implementa `Judge`
  (adaptador del SDK; único sitio que importa `typesafe_sdk`).
- `build_judge(settings) -> Judge | None`: `None` si `typesafe_api_key` está vacía.

### D6 — Servicio y job

- `backend/app/services/classification.py`:
  `async def classify_pieces(session, pieces, judge: Judge | None, meter: UsageMeter) -> ClassificationStats`
  1. Si `judge is None` → `ClassificationStats(classified=0, cached=0, failed=len(pieces), skipped_reason="sin TYPESAFE_API_KEY")`.
  2. Calcula `state` y `cache_key` de cada pieza; carga en **una** query las filas existentes
     (`JevJudgment.cache_key.in_(keys)`).
  3. Lanza en paralelo (`asyncio.gather`, el semáforo limita a 6) solo las que faltan. Una
     excepción de `typesafe_sdk` en una pieza cuenta como `failed` y no aborta el resto
     (`except` de la excepción base del SDK, con log; nunca `except Exception: pass`).
  4. Inserta las nuevas en bloque, hace `meter.add(Provider.TYPESAFE_JEV, "piece_battery", units=input_tokens or 0)`
     por cada llamada real (D12) y hace `commit`.
  5. Devuelve `ClassificationStats(classified, cached, failed, skipped_reason)` (dataclass).
- `analyze.py`: tras cargar las piezas y antes de `save_opportunities`, crea un `UsageMeter`, llama a
  `classify_pieces`, persiste con `await record_meter(session, meter, pipeline_run_id=run_row.id)` y añade `"jev": asdict(stats)` a `run_row.stats`; imprime una línea
  `jev: N clasificadas · M de caché · K fallidas`. Para no duplicar la carga de piezas,
  `compute_opportunities` pasa a aceptar `pieces` ya cargadas **o** el job llama a
  `load_pieces` y se las pasa: elegir lo que menos toque; si exige cambiar la firma de
  `compute_opportunities`, mantener compatible el call site existente.
- Una pieza ya clasificada no se vuelve a clasificar mientras su `state` no cambie.

### D12 — Consumo con el `UsageMeter` de Steven

- Sustituye el `UsageRecorder` de D5. `classify_pieces` recibe un `UsageMeter`
  (`app/collectors/usage.py`) y por cada llamada **real** hace
  `meter.add(Provider.TYPESAFE_JEV, "piece_battery", units=input_tokens or 0)`. El job persiste
  con `await record_meter(session, meter, pipeline_run_id=run_row.id)` al final.
- **Por qué no `record_usage`:** hace `commit` en cada llamada (~1.100 commits en la primera
  ejecución) y confirma también lo que el job tenga pendiente en la sesión.
- `pricing.yaml` ya tiene `typesafe_jev` con `unit: input_tokens` (0,042 $/M).
- Cambia el test `test_usage_recorded_only_for_real_calls`: comprobar `meter.counts` (3 llamadas,
  suma de tokens) y 0 tras la segunda ejecución.

## Diseño de módulos

- **Seam:** `Judge` en `intelligence/jev.py`. Todo lo de arriba (decisiones, caché, servicio) se
  prueba con un juez falso; solo `TypeSafeJudge` conoce el SDK.
- **Ubicación (CLAUDE.md §10):** `intelligence/jev.py` (cliente, umbrales, `PieceJudgment`),
  `editorial/prompts/jev/piece.v1.yaml` + loader en `intelligence/jev.py`,
  `services/classification.py`, `models/jev.py`, `jobs/analyze.py`, `core/config.py`.
- **Consumo:** ver D12.
- **Modos de error:** sin clave → `None`; error del SDK en una pieza → `failed` y sigue; error de DB
  → se propaga (el job ya marca la ejecución como `failed`).

## Acceso a datos

- Una query para leer la caché (`in_`), un `insert` en bloque para las nuevas
  (`insert(JevJudgment).values([...]).on_conflict_do_nothing(index_elements=["cache_key"])`).
- Migración nueva; no toca datos existentes.

## Plan de implementación

### Paso 1 — Dependencia, settings y smoke real [HECHO]

- **Archivos:** `backend/pyproject.toml`, `backend/uv.lock`, `backend/app/core/config.py`.
- **Cambio:** D1.
- **Verificación:** `cd backend && uv lock && uv sync` sin errores, y un smoke en el scratchpad (no
  en el repo) que construya el cliente desde `Settings` y haga `system_one` con
  `state={"title": "test"}` y una pregunta `Noul`. Pegar en el informe `response.model` y los tokens,
  **nunca** la clave.
- **Commit:** `Add typesafe-sdk 0.7.4 and Jev settings`

### Paso 2 — Batería y decisiones

- **Archivos:** `backend/app/editorial/prompts/jev/piece.v1.yaml`, `backend/app/intelligence/jev.py`,
  `backend/tests/test_jev.py`.
- **Cambio:** D2, D3, loader de la batería, `piece_state(piece)`, `cache_key(...)`,
  `to_piece_judgment(item_id, answers)`.
- **Test primero** (`test_jev.py`, sin red):
  - `test_battery_loads_all_questions`: ids exactos de D2; `format_rev` tiene las opciones de
    `format` en orden inverso (lo mismo con `hook`).
  - `test_noul_thresholds`: parametrizado `0.71 → True`, `0.29 → False`, `0.5 → None`
    (`ids=["yes", "no", "uncertain"]`).
  - `test_choice_needs_agreement_with_rev`: `format=use_case 0.8` y `format_rev=use_case` →
    `"use_case"`; `format_rev=news` → `None`; `format=use_case 0.55` → `None`.
  - `test_score_needs_confidence`: `2.6, conf 0.7 → 3`; `conf 0.4 → None`.
  - `test_injection_excludes_above_half`: `0.51 → True`, `0.5 → False`.
  - `test_state_trims_description_and_key_is_stable`: descripción de 1.500 caracteres → 1.000; misma
    pieza → misma clave; cambiar el modelo → clave distinta.
- **Verificación:** `cd backend && uv run pytest tests/test_jev.py -q`
- **Commit:** `Add the Jev piece battery and its decision thresholds`

### Paso 3 — Adaptador del SDK

- **Archivos:** `backend/app/intelligence/jev.py`, `backend/tests/test_jev.py`.
- **Cambio:** D5 (`TypeSafeJudge`, `build_judge`).
- **Test primero:** `test_typesafe_judge_parses_response`: `AsyncTypeSafeClient(api_key="test",
  transport=httpx2.MockTransport(handler))`, donde `handler` devuelve el JSON de una respuesta de
  `system_one` con un `noul` y un `choice` (sacar la forma exacta del wire de
  `typesafe_sdk/_core` en `.venv`, p. ej. los modelos de `wire`). Comprobar que `JudgeResult`
  trae `model`, las dos respuestas y los tokens, y que el handler recibió el `state` y las
  preguntas. `test_build_judge_without_key_is_none`.
- **Verificación:** `cd backend && uv run pytest tests/test_jev.py -q`
- **Commit:** `Wrap the TypeSafe SDK behind a Judge protocol`

### Paso 4 — Tabla `jev_judgments` (la migración revisa `5c0a7e3d91b2`)

- **Archivos:** `backend/app/models/jev.py`, `backend/app/models/__init__.py`,
  `backend/alembic/versions/<nuevo>_jev_judgments.py`.
- **Cambio:** D4.
- **Verificación:** `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`
- **Commit:** `Add the jev_judgments table`

### Paso 5 — Servicio de clasificación con caché

- **Archivos:** `backend/app/services/classification.py`, `backend/tests/test_classification.py`.
- **Cambio:** D6 (servicio).
- **Test primero** (DB `radar_test`, juez falso que cuenta llamadas y devuelve respuestas fijas;
  hacen falta `Source` y `ContentItem` reales por la FK):
  - `test_second_run_uses_cache`: 3 piezas → 3 llamadas; repetir → 0 llamadas, `cached == 3`.
  - `test_changed_state_is_reclassified`: cambiar el título de una pieza → 1 llamada.
  - `test_failure_in_one_piece_does_not_abort`: el juez lanza la excepción base del SDK para una
    pieza → `classified == 2`, `failed == 1`, sin excepción.
  - `test_without_judge_nothing_is_called`: `judge=None` → `failed == len(pieces)` y
    `skipped_reason` no vacío.
  - `test_usage_counted_only_for_real_calls`: juez falso con `input_tokens=100`; 3 llamadas
    reales → `meter.counts[(Provider.TYPESAFE_JEV, "piece_battery")]` con `calls == 3` y
    `units == 300`; segunda ejecución con un `UsageMeter` nuevo → sin entradas.
- **Verificación:** `cd backend && uv run pytest tests/test_classification.py -q`
- **Commit:** `Classify pieces with Jev and cache judgments in Postgres`

### Paso 6 — Integración en `analyze`

- **Archivos:** `backend/app/jobs/analyze.py` (y `services/opportunities.py` solo si hace falta
  para no cargar las piezas dos veces; mantener compatible la firma existente).
- **Cambio:** D6 (job). Actualizar el docstring del módulo: ya no es "sin LLM ni Jev".
- **Verificación:** `cd backend && uv run python -m app.jobs.analyze` dos veces seguidas con la DB
  local. Primera: `jev: N clasificadas` con N ≈ nº de piezas. Segunda: `0 clasificadas · N de
  caché`. Pegar las dos salidas y el coste aproximado (`Σ input_tokens` × 0,042 $/M).
- **Commit:** `Run the Jev piece battery in analyze`

## Estrategia de test

- **Seams:** `Judge` (juez falso) para servicio y caché; `httpx2.MockTransport` solo para el
  adaptador; funciones puras de decisión sin DB.
- **Prior art:** `backend/tests/test_store_signals.py` (tests de servicio contra `radar_test`) y
  `backend/tests/test_collectors.py` (mock del borde HTTP).
- **Casos que entran:** umbrales de D3 (spec de `docs/jev.md`), acuerdo con `_rev` (sesgo de
  primera opción documentado), caché (criterio 2), fallo parcial y sin clave (criterio 5), consumo
  (criterio 6, D12).
- **Casos descartados por ruido:** cada opción de `format`/`hook` por separado, contenido exacto de
  las instrucciones, reintentos del SDK (los cubre el SDK).
- **Parametrización:** umbrales de `noul` y de `injection` con `ids=`.

## Verificación final

```bash
cd /Users/melandres8/Documents/Projects/content-radar-jev/backend
uv run ruff check . && uv run ruff format --check .
uv run pyright app
TEST_DATABASE_URL=postgresql+asyncpg://radar:radar@localhost:5433/radar_test_jev uv run pytest -q
uv run python -m app.jobs.analyze
uv run python -m app.jobs.analyze
```

## Riesgos

- **Rate limit con ~1.100 piezas en la primera ejecución** — muchas `failed` por 429 → bajar el
  semáforo a 3 (constante `JEV_CONCURRENCY`) y repetir; la caché conserva lo ya hecho.
- **Una transitiva nueva tiene < 7 días y no hay versión anterior compatible** → anotarlo en
  "Preguntas abiertas", gate `BLOQUEADO` y parar.
- **Respuestas en español peor calibradas** — no se corrige aquí; lo mide la validación de
  `data/evaluations/` (frontend etiqueta las piezas).

## Historial de intentos

| Fecha | Qué bloqueó | Qué se decidió | Commits que quedaron |
| --- | --- | --- | --- |
| 2026-10-17 16:50 | Sin `TYPESAFE_API_KEY` y fit asignado a Jev | Tras #8 el fit pasa al LLM (parte C); la clave ya está en `backend/.env` | — |
| 2026-10-17 17:50 | Migración de Steven con head duplicado | Steven la encadenó (`0b34f85`); consumo con `UsageMeter` + `record_meter` (D12) | — |

## Preguntas abiertas

- (ninguna)
