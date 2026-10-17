# intel-dedup-replicas — Notas replicadas: que no inflen fuentes, saturación ni confianza

> Plan generado con `/spec`. Lo implementa `plan-implementer` con contexto limpio.
> El implementador NO ve la conversación que produjo este documento: todo lo que necesite tiene que
> estar escrito aquí.

## Metadatos

- **Slug:** `intel-dedup-replicas` · **Issue:** ninguno
- **Owner (CLAUDE.md §3):** Melkin
- **Prioridad (CLAUDE.md §12):** P0-adyacente (evidencias verificables; `docs/brief.md` §8 "Las
  republicaciones no inflan la diversidad de fuentes") · orden de construcción §12, punto 2,
  "batería de pares" · **Checkpoint que desbloquea (§13):** revisión de MCP y frontend (Dom 12:30
  ESP) y lista de verificación de la entrega antes del feature freeze (Dom 15:00 ESP)
- **Valor (filtro de CLAUDE.md §12):** paso "revisar scores y evidencia" del recorrido de demo:
  `source_count`, `cross_source_score`, saturación y confianza dejan de contar copias de la misma
  nota como validación cruzada, y la evidencia dice "republicada en N medios" · **Pregunta de
  `docs/brief.md` §4:** #1 (¿cómo se detecta una tendencia temprana? → validación cruzada entre
  fuentes independientes)
- **Repo:** `/Users/melandres8/Documents/Projects/content-radar`
- **Rama base:** `main` @ `551cf78`
- **Rama de trabajo:** `intel/dedup-replicas`
- **Fecha:** 2026-10-18 01:00 ESP
- **Contratos tocados:** `Evidence` (dos campos nuevos con default, aceptado por Melkin el 18/10) →
  OpenAPI, `frontend/src/types/api.ts` (regenerado), fixture `data/fixtures/opportunities.json`,
  `Evidence` dentro de las tools MCP (`analyze_opportunity`) — **avisado en el canal:** pendiente
  (Melkin) — el PR no se mergea antes del aviso. `Opportunity` no cambia de forma (solo la
  `description` de `source_count`).
- **Auditoría tras `/build`:** sí (toca scoring, contrato y datos)
- **Estado del gate:** `LISTO`

## Problema

La misma nota aparece en varios sitios: una story de HN o un post de Reddit que enlaza el artículo
de Ars Technica con el mismo título, WIRED que publica en inglés y en WIRED en Español, Platzi que
sube el mismo vídeo a YouTube y a Instagram, OpenAI que publica en su blog y en su canal. Hoy cada
copia cuenta como una fuente independiente (`outlet_key`, `app/intelligence/cross_source.py:17`),
así que un tema con una sola nota replicada parece validado por 3 medios: sube `source_count`,
`cross_source_score`, `evidence_strength` y la confianza, puede pasar a `accelerating` (regla
"≥ 3 fuentes independientes") y su volumen infla la saturación. Quien revisa la evidencia ve tres
"fuentes" que son una sola pieza, y nada se lo dice. Es un dato presentado como más fuerte de lo que
es (CLAUDE.md §2, regla 3; `docs/brief.md` §7 "Fuentes independientes: tras quitar las
republicaciones").

## Criterios de aceptación

1. Dentro de cada tema, dos piezas de medios distintos (`outlet_key` distinto) son la **misma nota**
   si se cumple una de estas condiciones (D2–D5):
   - Comparten enlace (`url` o `target_url`, normalizado). No se pregunta a Jev.
   - Jev, con la batería `pair.v1`, responde con seguridad el nivel "la misma nota replicada".
   - Jev no responde o duda, y tienen el mismo título normalizado (≥ 5 palabras) o similitud coseno
     ≥ `FALLBACK_MIN_SIMILARITY` (0.90).
2. Un "no" seguro de Jev (niveles 0–2, incluido "mismo acontecimiento contado por separado") deja
   el par como independiente aunque la regla de similitud diga lo contrario.
3. Las piezas unidas por esos pares se agrupan en **notas** (componentes conexos, union-find). La
   representante es la publicada antes (desempate por `item_id` menor). Las demás son
   republicaciones.
4. `source_count`, `cross_source_score`, `evidence_strength`, la confianza, la etapa (`classify`) y
   la penalización del score cuentan solo medios y piezas **originales** (no republicaciones). La
   saturación usa el número de notas del tema en las dos ventanas, no el de piezas. Velocidad,
   aceleración, momentum, timeline, outliers y `audience_mix` no cambian (siguen por pieza).
5. `score_breakdown` da el mismo `item_count` antes y después del audience fit (`apply_fit` usa el
   número de notas, no `len(result.pieces)`).
6. `Evidence` tiene `replica_of` (URL de la representante, `null` si la pieza es original o única) y
   `replica_count` (en la representante: medios distintos del suyo que republican la nota; `0` en
   el resto). Los dos tienen default: las ejecuciones guardadas, incluida la de `DEMO_RUN_ID`, se
   siguen validando.
7. En la evidencia guardada, las republicaciones van después de todas las piezas originales, así
   que cada `replica_of` apunta a una URL que también está en la evidencia del tema.
8. Si el tema tiene republicaciones, `limitations` lo dice con el número. Si alguna se decidió solo
   con la regla (sin un sí de Jev), lo dice también. La `description` cuenta fuentes independientes
   tras quitar republicaciones.
9. Las llamadas a Jev de pares se cachean en `jev_judgments` (clave por hash del par canónico +
   batería + versión + modelo), se limitan a `MAX_PAIR_JUDGMENTS_PER_RUN` (250) llamadas nuevas por
   ejecución y registran su consumo en `usage_events` (operación `pair_battery`).
10. Sin `TYPESAFE_API_KEY`, o si Jev falla en un par, el job sigue: esos pares los decide la regla.
    Sin embeddings ni clusters (0 piezas), no hay pares y nada cambia.
11. `analyze` imprime y guarda en `stats` un resumen de pares (candidatos, juzgados, de caché,
    fallidos, fuera de presupuesto, republicaciones y cuántas por regla).
12. `frontend/src/types/api.ts` regenerado con los dos campos; `pnpm type-check` y `pnpm build` en
    verde.
13. `docs/jev.md` (§2 "Par" y "Del juicio a la decisión") y `CLAUDE.md` §7 "Cross-source" describen
    lo implementado.

## No-objetivos

- **UI:** pintar "republicada en N medios" o agrupar republicaciones en Explore es del Frontend lead
  (CLAUDE.md §3). Este plan solo entrega el contrato, el fixture y los tipos regenerados.
- Velocidad, aceleración, `momentum_score`, percentil de velocidad, timeline, outliers y
  `audience_mix` siguen contando piezas. Cambiarlos movería el ranking entero horas antes del
  freeze. Queda como seguimiento en el informe.
- No se toca `MIN_RECENT_ITEMS` (filtro de tema activo) ni el clustering.
- No se deduplica entre temas distintos (los clusters son disjuntos) ni dentro del mismo medio (un
  medio ya cuenta una vez).
- `EvidenceLink` y `top_evidence` del MCP (`app/mcp/tools.py:89-101`) no cambian.
  `analyze_opportunity` ya expone `Evidence` completo con los campos nuevos.
- Sin migración de Alembic (D9).
- No se corre `analyze` contra Supabase ni contra ninguna DB que no sea la de tests. Calibrar de
  nuevo o fijar `DEMO_RUN_ID` lo decide Melkin después.
- La batería de verificación de afirmaciones y el *lift* del "por qué funcionó" no entran.

## Reglas de CLAUDE.md §2 en juego

- **Regla 3 (nunca inventar datos):** es el motivo de la tarea. Las republicaciones dejan de
  presentarse como validación independiente. Lo decidido solo por similitud se marca en
  `limitations` como no verificado por Jev. Un par sin decisión segura de Jev no se inventa: cae a
  la regla determinista y documentada.
- **Regla 4 (el LLM no calcula):** Jev solo emite un juicio `score` atómico. Python convierte su
  respuesta en sí/no/incierto con umbrales con nombre (D4), arma las notas y recalcula los scores.
- **Regla 5 (tipo de evidencia):** `growth_status` no cambia. La procedencia de cada republicación
  (regla o Jev) queda en `limitations`.
- **Regla 6 (texto externo no confiable):** títulos y descripciones van solo en `state` del par.
  Nuestras instrucciones van en la pregunta de la batería YAML. Los logs no llevan el `state` ni el
  mensaje de error (mismo patrón que `app/services/classification.py:55-56`).
- **Regla 1:** el `state` del par lleva título, descripción recortada y nombre público de la
  fuente. Sin autores.

## Contexto verificado del código

| Qué | Dónde | Estado actual |
| --- | --- | --- |
| Orden del job | `backend/app/jobs/analyze.py:56-71` | `load_pieces` → `classify_pieces` (piezas) → `record_meter` (`:61`) → `load_judgments` → `compute_opportunities` (`:64`) → fit y explicación → `rank` |
| `compute_opportunities` | `backend/app/services/opportunities.py:128-157` | Docstring "No escribe nada." (`:135`). Hace `keep_about_ai` → `embed` → `cluster` → `representative` → `build_opportunities`. Los vectores y los clusters no salen de la función. No la llama ningún test |
| `_to_piece` | `backend/app/services/opportunities.py:78-101` | No copia `item.target_url` |
| `ContentItem.target_url` | `backend/app/models/signals.py:60` | `Text`, nullable. Lo rellenan HN (`collectors/hackernews.py:68`) y Reddit (`collectors/scrapecreators.py:168`) |
| `Piece` | `backend/app/intelligence/opportunities.py:72-88` | Dataclass. Sin `target_url`. Último campo con default: `region` |
| `TopicResult` | `backend/app/intelligence/opportunities.py:100-107` | `opportunity, evidence, timeline, stage, pieces` |
| `_evidence` | `backend/app/intelligence/opportunities.py:158-173` | Construye `Evidence` por pieza |
| `_limitations` | `backend/app/intelligence/opportunities.py:187-207` | Notas en texto. La explicación del LLM conserva las de Python (`app/intelligence/explanation.py:45-46`) |
| `_active_topics` | `backend/app/intelligence/opportunities.py:217-233` | `counts` por pieza. Alimenta velocidad y saturación |
| `_score_topic` | `backend/app/intelligence/opportunities.py:265-295` | `source_count = len(outlets)`, `item_count = len(topic.group)` → `classify`, `score_breakdown`, `confidence` |
| `_topic_facts` | `backend/app/intelligence/opportunities.py:307-315` | `outlets` = `outlet_key` de **todas** las piezas del grupo |
| `_score_fields` | `backend/app/intelligence/opportunities.py:358-377` | `source_count` (`:373`) y `evidence_strength(len(topic.group), …)` (`:374`) |
| `_description` | `backend/app/intelligence/opportunities.py:380-385` | "N piezas de M fuentes independientes" |
| `_ranked` | `backend/app/intelligence/opportunities.py:425-438` | Outliers → recientes → `item_id`. El orden decide la evidencia guardada (`MAX_EVIDENCE = 25`, `:64`) y lo que recibe el LLM (`TopicResult.pieces`) |
| `build_opportunities` | `backend/app/intelligence/opportunities.py:441-479` | Saturación por `counts.current + counts.previous` (`:458`). El archivo ya tiene 492 líneas |
| `outlet_key` | `backend/app/intelligence/cross_source.py:17-20` | HN y TikTok cuentan como un medio cada uno. El resto, `platform:source_name` |
| `evidence_strength`, `confidence` | `backend/app/intelligence/ranking.py:50-54`, `:126-131` | Usan `item_count` y `source_count` |
| Acoplamiento oculto | `backend/app/intelligence/audience_fit.py:85-93` | `apply_fit` rehace `score_breakdown` con `item_count=len(result.pieces)` (`:92`) |
| Texto al LLM | `backend/app/editorial/explanation.py:110` | "Fuentes independientes: {o.source_count}." (recoge el valor deduplicado sin cambios) |
| Cliente Jev | `backend/app/intelligence/jev.py:95-116` | `Judge` Protocol (`:89-92`), `TypeSafeJudge` con `Semaphore(6)`, `build_judge` → `None` sin clave |
| Clave de caché | `backend/app/intelligence/jev.py:148-157` | `cache_key(state, model)` fijada a `piece_battery()` (`:149`) |
| Carga de baterías | `backend/app/intelligence/jev.py:119-130` | `load_battery(name, path)` admite `type: score` (`QUESTION_CLASSES`, `:49-53`) |
| Caché de piezas | `backend/app/services/classification.py:60-104` | `_cached_keys`, `_save` (insert `on_conflict_do_nothing` por `cache_key`), `content_item_id` = pieza (`:84`). Consumo: `meter.add(Provider.TYPESAFE_JEV, "piece_battery", units=input_tokens)` (`:142`) |
| `jev_judgments` | `backend/app/models/jev.py:14-28` | `content_item_id` nullable (`:23-25`). `cache_key` único |
| Respuesta `score` del SDK | `typesafe_sdk/_core/response_types.py:44-58` (`typesafe-sdk` 0.7.4) | `ScoreAnswer`: `score` (media ponderada), `confidence`, `legend: dict[int, …]`, `probabilities: dict[int, float]`. Niveles desde 0 en el orden de `criteria` (`question_types.py:121-131`). Guardado con `model_dump(mode="json")` (`jev.py:105`), así que en `answers` las claves de `legend` y `probabilities` son **strings** |
| `Evidence` | `backend/app/schemas/opportunity.py:76-93` | Sin campos de republicación. `TopicEvidence` hereda (`:96-99`) |
| `source_count` | `backend/app/schemas/opportunity.py:181` | `description="Fuentes independientes"` |
| Test de payload viejo | `backend/tests/test_opportunity_fixture.py:82-95` | Quita campos nuevos y valida |
| Fixture | `data/fixtures/opportunities.json` | `opp_003` tiene 2 evidencias (YouTube latam_es + RSS latam_es) |
| DB de tests | `backend/tests/conftest.py:1-55` | `create_all` desde los modelos: sin migraciones. `TEST_DATABASE_URL` en el entorno |
| Prior art de tests | `backend/tests/test_classification.py:19-60` (`FakeJudge`), `backend/tests/test_build_opportunities.py:15-43` (`piece()`), `backend/tests/test_jev.py` | Estilo a imitar |
| Tipos del front | `frontend/package.json:19` | `gen:api` acepta `OPENAPI_URL` (ruta de archivo vale). `type-check` y `build` existen |
| Doc de diseño de la batería | `docs/jev.md:83-96` (Par), `:113-121` (umbrales) | Niveles de `same_story`. "Los niveles intermedios se marcan como inciertos" (D4 lo cambia) |
| Pendiente en CLAUDE.md | `CLAUDE.md:227` | "Pendiente: deduplicar notas de prensa replicadas…" |
| `docs/scoring.md` | — | **No existe en `main`.** No se cita ni se crea |

### Calibración (18/10, solo lectura, datos reales)

Se corrió en local, en solo lectura (`set transaction read only`): `load_pieces` + `load_judgments`
→ `keep_about_ai` → `embed` → `cluster`, con `as_of` = ahora. Resultado: 1.826 piezas, 1.616 tras el
filtro, 71 temas, 634 piezas en temas. Hay 2.106 pares de medios distintos dentro de un mismo tema.

| Similitud coseno | Pares | Piezas | Temas |
| --- | --- | --- | --- |
| ≥ 0.95 | 3 | 6 | 3 |
| ≥ 0.90 | 8 | 16 | 8 |
| ≥ 0.85 | 21 | 38 | 15 |
| ≥ 0.80 | 44 | 70 | 22 |
| ≥ 0.75 | 89 | 117 | 29 |
| ≥ 0.70 | 221 | 224 | 43 |

Qué hay en cada tramo (ejemplos reales):
- **≥ 0.90: los 8 pares son la misma pieza.** HN y r/OpenAI con el mismo título (1.000). WIRED · AI
  y WIRED en Español traducidos (0.90, 0.92, 0.93). Platzi en YouTube y en Instagram (0.92, 0.95).
  EDteam en YouTube y TikTok (0.98). OpenAI News (RSS) y el canal de YouTube de OpenAI ("Sophos cuts
  threat … 96%", 0.90).
- **0.85–0.90: mezcla.** Son republicaciones Ars Technica ↔ HN con el mismo título (0.885 y 0.899)
  y OpenAI News ↔ HN "GPT-6 and Intelligent UI for everyone" (0.865). Son **coberturas
  independientes del mismo hecho** The Verge ↔ TechCrunch sobre Meta (0.867, 0.890) y El País ↔
  Expansión sobre la detención del FBI (0.861). Es un **falso positivo** Expansión ↔ MoureDev sobre
  ciberseguridad (0.885).
- **0.75–0.85:** sobre todo coberturas independientes (El País ↔ Clarín 0.804; Fortune ↔ r/OpenAI
  0.761). También hay republicaciones con título idéntico que el coseno puntúa bajo, porque la story
  de HN no tiene descripción y el embedding incluye hasta 300 caracteres de ella: Simon Willison ↔
  HN "OpenAI 'rogue' agent activities…" (0.838) y OpenAI News ↔ HN "Sharing AI progress in
  mathematics" (0.784).
- **Título normalizado idéntico entre medios distintos:** 12 pares, todos republicaciones (HN o
  Reddit enlazando el artículo), con un coseno entre 0.65 y 1.00. Con 4 palabras aparece "Claude
  Haiku 5.5" (HN ↔ Simon Willison), que es ambiguo. Con un mínimo de 5 palabras desaparece.
- **Enlace compartido:** 10 piezas con `target_url` igual a la `url` de otra pieza. Ninguna URL
  aparece en dos fuentes.

Conclusión: el coseno solo no separa "la misma nota" de "el mismo hecho contado por otro medio". Por
eso la regla de respaldo usa 0.90, que da precisión 8/8 en la muestra, más el título idéntico, y Jev
decide la franja dudosa desde 0.70. El implementador **no** repite la calibración.

## Decisiones tomadas

### D1 — Qué cuenta como "la misma nota"

- **Elegido:** cuenta como republicación una copia, traducción o reenvío de la misma pieza: el mismo
  artículo enlazado desde HN o Reddit, la versión en otro idioma del mismo medio, o el mismo
  autor/marca publicándola en otro canal (YouTube ↔ Instagram, blog ↔ YouTube). Dos medios que
  cuentan por separado el mismo acontecimiento **no** son republicación: eso sí es validación
  cruzada.
- **Por qué:** `docs/brief.md` §7: "Medios distintos, no copias de la misma nota". La cobertura
  independiente es justo la señal que mide `cross_source_score`.
- **Descartado:** colapsar todo "mismo acontecimiento" *(destruiría la validación cruzada, que es la
  señal principal)*. Tratar la story de HN como fuente independiente del artículo que enlaza *(es
  conversación sobre la misma pieza, no un medio que la cuenta. La conversación sigue pesando en
  outliers y velocidad, que no cambian)*.

### D2 — Capas de decisión por par y su orden

- **Elegido:** dentro de un tema, para cada par de piezas con `outlet_key` distinto:
  1. **Enlace compartido** (`_link(a.url) == _link(b.url)`, o el `target_url` de una igual a la
     `url` de la otra, o los dos `target_url` iguales y no nulos) → republicación, base
     `SAME_LINK`. No se pregunta a Jev: es un hecho.
  2. Si no, es **candidato a Jev** cuando tiene similitud ≥ `JEV_MIN_SIMILARITY` (0.70) o el mismo
     título normalizado.
  3. Un veredicto seguro de Jev manda: `True` → republicación, base `JEV`. `False` → independiente.
  4. Sin veredicto (sin clave, fallo, incierto o fuera de presupuesto) → **regla de respaldo**:
     mismo título normalizado (base `SAME_TITLE`) o similitud ≥ `FALLBACK_MIN_SIMILARITY` (0.90,
     base `SIMILARITY`) → republicación. Si no, independiente.
- **Por qué:** la calibración. El enlace es inequívoco. El título idéntico acierta 12/12, aunque Jev
  puede corregirlo. 0.90 es el codo de precisión. Por debajo hay coberturas independientes que solo
  Jev distingue. Que Jev mande en las dos direcciones permite que deshaga The Verge ↔ TechCrunch.
- **Descartado:** solo coseno con un umbral *(0.85 colapsa coberturas independientes y 0.90 pierde
  las republicaciones de HN)*. Mandar a Jev también los pares con enlace compartido *(gasto sin
  información nueva)*. Candidatos desde 0.75 *(89 pares; deja fuera republicaciones de 0.70–0.75 y
  el coste de 0.70 es despreciable, D8)*.

### D3 — Normalización de título y enlace

- **Elegido:** `normalize_title(t)` aplica `unicodedata.normalize("NFKC", t).casefold()`, cambia
  todo lo que no sea `\w` ni espacio por un espacio (`re.sub(r"[^\w\s]", " ", …)`) y colapsa los
  espacios. Cuenta como "mismo título" si son iguales y tienen ≥ `MIN_TITLE_WORDS` (5) palabras.
  `_link(url)` quita el fragmento (`#…`) y la barra final. Sin más normalización (query, http/https).
- **Por qué:** comillas tipográficas (“ ” vs " ") y guiones diferían en los pares reales. Con 4
  palabras entra "Claude Haiku 5.5", que es ambiguo.
- **Descartado:** fuzzy matching de títulos *(sin datos que lo justifiquen; Jev cubre la franja
  dudosa)*. Normalizar parámetros de URL *(ninguna URL se repite entre fuentes en los datos)*.

### D4 — De la respuesta `same_story` de Jev a sí/no/incierto

- **Elegido:** la batería `pair.v1.yaml` tiene una sola pregunta, `same_story`, de tipo `score`, con
  4 niveles en este orden (0–3): temas distintos · mismo tema, hechos distintos · mismo
  acontecimiento contado por separado · la misma nota replicada. En `same_story_verdict(answer)`:
  - `None` si falta la respuesta o `confidence < SAME_STORY_MIN_CONFIDENCE` (0.5, de
    `docs/jev.md:119`).
  - Si no, `level = round(answer["score"])`. `True` si `level >= SAME_STORY_LEVEL` (3), `False` si
    es menor.
  - No se lee `probabilities` ni `legend` (sus claves son strings en el JSON guardado).
- **Por qué:** el nivel 2 ("mismo acontecimiento contado por separado") es cobertura independiente,
  y por D1 es un "no". Si los niveles intermedios fueran "inciertos", como dice hoy `docs/jev.md:95`,
  el nivel 2 caería a la regla de respaldo y colapsaría justo lo que debe quedar independiente. La
  incertidumbre se mide con `confidence`. `docs/jev.md` se actualiza (paso 8).
- **Descartado:** exigir además `probabilities["3"] ≥ 0.6` *(sin validación que lo respalde. Se
  puede afinar cuando haya pares etiquetados)*.

### D5 — Notas (story clusters) y representante

- **Elegido:** union-find sobre las aristas de republicación, solo dentro de cada tema. La
  representante de cada nota con ≥ 2 piezas es la de `published_at` mínimo (desempate `item_id`
  menor). Las demás son republicaciones de esa representante.
- **Por qué:** lo primero publicado suele ser el original. Union-find es determinista y basta con
  aristas de alta precisión.
- **Descartado:** representante = mayor `outlier_ratio` *(mezcla "original" con "la que más rindió";
  el outlier ya se muestra aparte)*. Clustering jerárquico de notas *(sobreingeniería)*.
- **Riesgo aceptado:** con A~B y B~C, A y C quedan juntas aunque no se parezcan. Con aristas de
  precisión alta, el riesgo es bajo.

### D6 — Qué cuenta tras deduplicar

- **Elegido:** "originales" = piezas del tema que no son republicaciones (representantes + piezas
  sin par). Con ellas se calculan:
  - `outlets` → `source_count`, `cross_source_score`, `evidence_strength` y `classify(source_count=…)`.
  - `story_count = len(originales)` → `classify(item_count=…)`, `confidence(…, item_count)`,
    `evidence_strength(item_count, …)` y `score_breakdown(item_count=…)`, tanto en
    `build_opportunities` como en `apply_fit`.
  - Saturación: `saturation_scores` con `window_counts` de los `published_at` de las originales
    (`current + previous`).
  - `_description`: "N piezas (K republicaciones) de M fuentes independientes (…)". Sin "(K
    republicaciones)" cuando K = 0.

  Siguen por pieza: velocidad, aceleración, percentil de velocidad, momentum, timeline, outliers,
  `audience_mix`, `latam_gap`, `MIN_RECENT_ITEMS` y `_stable_id`.
- **Por qué:** el reto pide que las republicaciones no inflen diversidad ni saturación, y la
  confianza depende de las dos. Tocar la velocidad movería el momentum y el ranking entero antes del
  freeze. La velocidad mide actividad de publicación, y una republicación sí es actividad.
- **Descartado:** `item_count` por pieza en `classify` y `confidence` *(5 copias de una nota darían
  "datos suficientes")*.

### D7 — Forma del contrato

- **Elegido:** dos campos en `Evidence`, los dos con default:
  - `replica_of: HttpUrl | None = Field(default=None, description="URL de la pieza original si esta
    republica la misma nota; None = original o sin republicaciones")`
  - `replica_count: int = Field(default=0, ge=0, description="En la pieza original: medios
    distintos del suyo que republican la misma nota en este tema")`

  `replica_count` cuenta `outlet_key` distintos entre las republicaciones, sin contar el de la
  representante. Se calcula en el backend sobre el tema completo, no sobre las 25 evidencias
  guardadas. `Opportunity` no recibe campos nuevos. Solo cambia la `description` de `source_count`
  a "Fuentes independientes, sin contar republicaciones de la misma nota".
- **Por qué:** es lo mínimo para que la UI diga "republicada en N medios" en la original y enlace la
  original desde la copia. El frontend no calcula (CLAUDE.md §9). Si lo contara él, lo haría sobre
  una evidencia truncada. Los defaults mantienen válidas las ejecuciones guardadas.
- **Descartado:** `story_id` *(la URL de la representante ya identifica la nota)*. Un
  `replica_count` en `Opportunity` *(la `description` y `limitations` ya lo cuentan, y es un campo
  más del contrato)*. Añadir los campos a `EvidenceLink` del MCP *(no hace falta para la demo)*.

### D8 — Presupuesto y coste de Jev

- **Elegido:** candidatos ordenados por similitud descendente (desempate por ids). Solo se llama a
  Jev por los no cacheados, hasta `MAX_PAIR_JUDGMENTS_PER_RUN = 250` por ejecución. Los que pasan
  del tope van a la regla de respaldo y se cuentan en `over_budget`. Mismo `Judge` y semáforo que la
  batería de pieza (concurrencia 6).
- **Por qué:** en los datos actuales hay ~221 candidatos ≥ 0.70 más los de título idéntico. Con
  ~800 tokens por llamada y 0,042 $/M, una ejecución sin caché cuesta ~0,01 $. El tope protege
  latencia y rate limits, no dinero. Con la caché, cada ejecución solo paga los pares nuevos.
- **Descartado:** sin tope *(un tema amplio crece de forma cuadrática)*.

### D9 — Caché sin migración

- **Elegido:** las filas de pares van a `jev_judgments` con `battery="pair"`, `battery_version=1`,
  `content_item_id=None` y `cache_key` = sha256 de `{state, battery, battery_version, model}`, con
  el **state canónico**: `a` = la pieza de `item_id` menor. Se lee solo por `cache_key`, igual que
  la de pieza.
- **Por qué:** `content_item_id` ya es nullable y la tabla ya guarda todo lo demás. Una migración
  obligaría a correr `alembic upgrade` en Supabase horas antes del freeze.
- **Coste aceptado:** desde una fila no se sabe a qué par corresponde sin recalcular el `state`, y
  el `ON DELETE CASCADE` no limpia filas de pares. Va al informe como deuda.
- **Descartado:** columna `pair_item_id` o tabla `jev_pair_judgments` *(migración en producción)*.
  `content_item_id = min(a, b)` *(mezcla significados en la columna)*.

### D10 — `state` del par y batería

- **Elegido:** `pair_state(a, b)` devuelve `{"a": {...}, "b": {...}}`, ordenado por `item_id`. Cada
  lado lleva `title`, `source` (= `source_name`) y `description` recortada a
  `MAX_PAIR_DESCRIPTION_CHARS = 500`. Sin descripción, se omite la clave (como `piece_state`,
  `jev.py:140-144`). Nunca lleva segmento, región, URL ni métricas. Las instrucciones y los
  criterios de `same_story` están en español (como `piece.v3.yaml`) y dicen de forma explícita que
  una traducción, un reenvío que enlaza el artículo o el mismo autor en otro canal es nivel 3, y que
  dos medios que cuentan el mismo hecho con su propio texto es nivel 2.
- **Por qué:** es lo que diseña `docs/jev.md:88`. La fuente ayuda a reconocer "WIRED" frente a
  "WIRED en Español". 500 caracteres mantienen ~800 tokens. El orden canónico hace que (A,B) y (B,A)
  compartan caché.
- **Descartado:** mandar la URL *(Jev contestaría por el dominio, como pasaba con el segmento en la
  batería de pieza)*.

### D11 — Dónde vive cada cosa y orden en `analyze`

- **Elegido:**
  - **Puro** en `app/intelligence/replicas.py`: constantes, `normalize_title`, `same_link`,
    `CandidatePair`, `candidate_pairs`, `same_story_verdict`, `decide_pair`, `group_stories`,
    `StoryAssignment`.
  - **Jev** en `app/intelligence/jev.py`: `pair_battery()`, `pair_state()` y una clave de caché
    parametrizada por batería.
  - **Async con DB y red** en `app/services/replicas.py`: `detect_replicas`.
  - `compute_opportunities` pasa a orquestar `keep_about_ai → embed → cluster → detect_replicas →
    build_opportunities(stories=…)` y recibe `judge` y `meter`. Su docstring dice que solo escribe
    la caché de pares en `jev_judgments`.
  - En `analyze._evaluate`, el `meter` de Jev cubre las dos baterías y `record_meter` se mueve
    después de `compute_opportunities`.
- **Por qué:** los vectores y los clusters solo existen dentro de `compute_opportunities`, así que
  el par va entre clustering y scores sin sacarlos fuera. El scoring sigue puro (recibe
  `StoryAssignment`), igual que recibe `judgments`.
- **Descartado:** devolver vectores y clusters a `analyze` y orquestar allí *(más superficie para el
  mismo resultado)*. Meter la lógica de pares en `jev.py` *(pasaría de 300 líneas y mezclaría
  agrupación con cliente)*.

### D12 — Orden de la evidencia y del contexto del LLM

- **Elegido:** `_ranked` pone primero las originales y después las republicaciones. Dentro de cada
  grupo se mantiene el orden actual. Como `TopicResult.pieces` sale de ese orden, las
  republicaciones también van al final de lo que recibe el LLM.
- **Por qué:** garantiza el criterio 7 (con `MAX_EVIDENCE = 25`, si entra una republicación ya
  entraron todas las originales) y no gasta contexto del LLM en copias. Las cachés del LLM de los
  temas con republicaciones cambian de clave y se reevalúan una vez (céntimos).
- **Descartado:** quitar las republicaciones de la evidencia *(son evidencia verificable de
  alcance)*.

### D13 — Notas en `limitations`

- **Elegido:** si el tema tiene K > 0 republicaciones: `f"{K} piezas son republicaciones de la misma
  nota: no cuentan como fuentes independientes ni para la saturación."` (con K = 1: "1 pieza es una
  republicación…"). Si alguna republicación del tema tiene solo aristas `SAME_TITLE` o
  `SIMILARITY`, se añade `REPLICAS_UNVERIFIED_NOTE = "Algunas republicaciones se detectaron por
  título o similitud de texto, sin verificar con Jev."`. `SAME_LINK` y `JEV` cuentan como
  verificadas.
- **Por qué:** regla 3 y regla 5: quien lee distingue lo comprobado de lo inferido.

## Diseño de módulos

- **Seam:** `build_opportunities(..., stories: StoryAssignment | None = None)`. Lo puro recibe la
  asignación ya decidida. `detect_replicas` es el único que habla con Jev y con la DB para pares.
- **Interfaz (`app/intelligence/replicas.py`):**

  ```python
  JEV_MIN_SIMILARITY = 0.70        # candidatos a Jev (calibración del 18/10)
  FALLBACK_MIN_SIMILARITY = 0.90   # regla de respaldo: precisión 8/8 en datos reales
  MIN_TITLE_WORDS = 5
  SAME_STORY_LEVEL = 3             # "la misma nota replicada"
  SAME_STORY_MIN_CONFIDENCE = 0.5  # docs/jev.md, "Del juicio a la decisión"

  class ReplicaBasis(StrEnum): SAME_LINK, SAME_TITLE, JEV, SIMILARITY
  VERIFIED_BASES = {ReplicaBasis.SAME_LINK, ReplicaBasis.JEV}

  def normalize_title(title: str) -> str: ...
  def same_title(a: Piece, b: Piece) -> bool: ...   # normalizados iguales y ≥ MIN_TITLE_WORDS
  def same_link(a: Piece, b: Piece) -> bool: ...

  @dataclass(frozen=True)
  class CandidatePair:
      a: Piece               # item_id menor
      b: Piece
      similarity: float
      same_title: bool

  @dataclass(frozen=True)
  class ReplicaEdge:
      a: int; b: int; basis: ReplicaBasis

  def topic_pairs(
      pieces: Sequence[Piece], clusters: Sequence[Sequence[int]], vectors: np.ndarray
  ) -> tuple[list[ReplicaEdge], list[CandidatePair]]:
      """Aristas por enlace compartido y candidatos a Jev, dentro de cada cluster y entre
      medios distintos. Candidatos ordenados por similitud desc., luego (a.item_id, b.item_id)."""

  def same_story_verdict(answer: Mapping[str, Any] | None) -> bool | None: ...
  def decide_pair(pair: CandidatePair, verdict: bool | None) -> ReplicaBasis | None: ...

  @dataclass(frozen=True)
  class StoryAssignment:
      representative_of: Mapping[int, int]  # republicación → representante (solo republicaciones)
      unverified: frozenset[int]            # republicaciones sin ninguna arista verificada
      @property
      def replica_ids(self) -> frozenset[int]: ...

  NO_REPLICAS = StoryAssignment({}, frozenset())

  def group_stories(pieces: Sequence[Piece], edges: Sequence[ReplicaEdge]) -> StoryAssignment: ...
  ```

  **Import circular (obligatorio):** `opportunities.py` importa de `replicas.py` y `replicas.py`
  necesita `Piece`, que vive en `opportunities.py`. Para que no haya ciclo en tiempo de ejecución,
  `replicas.py` empieza con `from __future__ import annotations` e importa `Piece` solo bajo
  `if TYPE_CHECKING:`. `replicas.py` lee atributos de `Piece`, pero nunca construye uno ni lo usa en
  `isinstance`. No se mueve `Piece` de sitio. `outlet_key` se importa de `cross_source.py`, que no
  tiene ciclo. `services/replicas.py` y `jev.py` ya importan `Piece` desde `opportunities.py` sin
  problema.

  Invariantes:
  - `topic_pairs` nunca empareja una pieza consigo misma ni dos del mismo `outlet_key`
    (`cross_source.outlet_key(p.platform.value, p.source_name)`).
  - Un par con enlace compartido sale solo como arista `SAME_LINK`, nunca como candidato.
  - `vectors[i]` corresponde a `pieces[i]` y está normalizado: similitud = producto escalar.
  - `group_stories` es determinista y sin aristas devuelve `NO_REPLICAS`.
  - Una republicación es `unverified` cuando todas las aristas que la tocan son `SAME_TITLE` o
    `SIMILARITY` (ninguna `SAME_LINK` ni `JEV`). La representante nunca aparece en
    `representative_of` ni en `unverified`.
  - Sin clusters o con `len(vectors) == 0` → `([], [])`.
- **Interfaz (`app/intelligence/jev.py`):**

  ```python
  PAIR_BATTERY = "pair"
  PAIR_BATTERY_FILE = …/"editorial/prompts/jev/pair.v1.yaml"
  MAX_PAIR_DESCRIPTION_CHARS = 500
  SAME_STORY_QUESTION = "same_story"

  def battery_cache_key(battery: Battery, state: dict[str, Any], model: str) -> str: ...
  def cache_key(state, model) -> str: return battery_cache_key(piece_battery(), state, model)  # firma actual intacta
  @lru_cache
  def pair_battery() -> Battery: ...
  def pair_state(a: Piece, b: Piece) -> dict[str, Any]: ...   # ordena por item_id
  ```

  `battery_cache_key` reproduce el payload actual (`state`, `battery`, `battery_version`, `model`):
  las claves de pieza ya guardadas tienen que seguir siendo iguales. Lo comprueba un test.
- **Interfaz (`app/services/replicas.py`):**

  ```python
  PAIR_BATTERY_OPERATION = "pair_battery"
  MAX_PAIR_JUDGMENTS_PER_RUN = 250

  @dataclass
  class ReplicaStats:
      candidates: int
      judged: int        # llamadas nuevas con respuesta
      cached: int
      failed: int        # JudgeError
      over_budget: int
      replicas: int      # piezas marcadas como republicación
      unverified: int
      skipped_reason: str | None = None   # SKIPPED_WITHOUT_KEY si judge is None

  async def detect_replicas(
      session: AsyncSession,
      pieces: Sequence[Piece],
      clusters: Sequence[Sequence[int]],
      vectors: np.ndarray,
      *,
      judge: Judge | None,
      meter: UsageMeter,
  ) -> tuple[StoryAssignment, ReplicaStats]: ...
  ```

  Flujo:
  1. `topic_pairs`.
  2. Claves de caché de todos los candidatos y lectura en bloque de `JevJudgment.cache_key,
     answers` con `cache_key.in_(…)`.
  3. Si `judge` existe, se llama, en orden, por los no cacheados hasta el tope, con
     `asyncio.gather` y `JudgeError` capturado por par. El log no lleva el state.
  4. Insert en bloque `on_conflict_do_nothing(index_elements=["cache_key"])` y `meter.add(
     Provider.TYPESAFE_JEV, PAIR_BATTERY_OPERATION, units=input_tokens or 0)` por respuesta. Después
     `session.commit()`.
  5. `verdict = same_story_verdict(answers.get(SAME_STORY_QUESTION))` y `decide_pair`, y se suman
     aristas.
  6. `group_stories`.

  Sin candidatos no hace queries. Sin `judge` sigue leyendo la caché: los pares ya juzgados
  conservan su veredicto.
- **Cambios en `app/intelligence/opportunities.py`:**
  - `Piece.target_url: str | None = None`, al final.
  - `TopicResult.replica_ids: frozenset[int] = field(default_factory=frozenset)`, al final, con la
    property `story_count -> len(pieces) - len(replica_ids & {p.item_id for p in pieces})`.
  - `build_opportunities(..., stories: StoryAssignment | None = None)`. `None` equivale a
    `NO_REPLICAS`: los tests actuales no cambian.
  - `_TopicFacts` gana `story_count`, `replica_count` y `unverified`. `outlets` sale solo de las
    originales.
  - La saturación usa un `story_counts: WindowCounts` por tema, calculado sobre las originales.
  - `_evidence(p, ratio, *, replica_of: str | None, replica_count: int)`.
  - `_ranked(group, ratios, replica_ids)`.
  - `_limitations(..., replicas: int, unverified: bool)`.

  Para no pasar de 500 líneas, los helpers nuevos de republicación (conteo de medios por
  representante, notas de `limitations`) van en `replicas.py`, y `opportunities.py` solo los llama.
  Si aun así pasa de 500, se anota como deuda en el informe. No se parte el archivo en este plan.
- **`app/intelligence/audience_fit.py:92`:** `item_count=result.story_count`.
- **Ubicación (CLAUDE.md §10):** `intelligence/replicas.py` (puro), `intelligence/jev.py`
  (batería), `services/replicas.py` (DB + Jev), `services/opportunities.py` (orquestación),
  `jobs/analyze.py` (stats). Sin cambios en `api/routes/` ni en `mcp/`.

## Acceso a datos

- **Lectura de caché:** `select(JevJudgment.cache_key, JevJudgment.answers).where(
  JevJudgment.cache_key.in_(keys))`, una sola query. Sin relaciones ni lazy loading.
- **Escritura:** `insert(JevJudgment).values(rows).on_conflict_do_nothing(index_elements=
  ["cache_key"])`, en bloque. Las filas llevan `battery="pair"`, `battery_version`,
  `requested_model=get_settings().jev_model`, `response_model=result.model`, `content_item_id=None`,
  `answers`, `input_tokens` y `output_tokens`.
- **`_to_piece`:** añade `target_url=item.target_url`. Ya se carga en la misma query.
- **Migración:** ninguna (D9). Los datos existentes no cambian. Las filas de pieza conservan su
  clave (lo comprueba un test).

## Alternativas rechazadas

- **Solo la regla de coseno** (lo que dice hoy CLAUDE.md como mientras tanto): el coseno no separa
  republicación de cobertura independiente (calibración).
- **Deduplicar antes del clustering, sobre todo el corpus:** cruzaría temas y cambiaría los
  clusters. CLAUDE.md §7 lo plantea dentro del tema.
- **Jev para todos los pares del tema:** 2.106 pares en la muestra, casi todos obvios.

## Plan de implementación

Antes de empezar: `git switch -c intel/dedup-replicas` desde `main` @ `551cf78` (si `main` avanzó,
desde el `main` actual, y anótalo). Comprueba que las referencias de "Contexto verificado" siguen
valiendo. Postgres de tests: `docker compose up -d db` desde la raíz (puerto 5433). Todos los
comandos de backend se corren desde `backend/`.

### Paso 1 — Contrato `Evidence` y fixture [HECHO]

- **Archivos:** `backend/app/schemas/opportunity.py`, `data/fixtures/opportunities.json`,
  `backend/tests/test_opportunity_fixture.py`
- **Cambio:**
  - `replica_of` y `replica_count` en `Evidence` (D7), después de `collection`.
  - Nueva `description` de `source_count` (`:181`).
  - En el fixture (MOCK), `opp_003` gana una tercera evidencia MOCK que republica la de RSS:
    - otra fuente mock, otro `segment`/`platform` (p. ej. `hackernews`);
    - `replica_of` = la URL de la de RSS;
    - `outlier_ratio`/`is_outlier` a `null`;
    - título con `[MOCK]`.
  - La de RSS lleva `replica_count: 1`.
  - Comprueba que `test_fixture_is_internally_consistent` sigue en verde (`outlier_count` y
    `top_outlier_ratio` no cambian con un ratio `null`).
- **Test primero:**
  - `test_old_payload_still_validates`: quitar también `replica_of` y `replica_count` y comprobar
    `e.replica_of is None` y `e.replica_count == 0`.
  - Nuevo `test_fixture_replicas_point_inside_their_topic`: en cada tema, todo `replica_of` es la
    URL de una evidencia del mismo tema que no es republicación y tiene `replica_count ≥ 1`.
- **Verificación:** `uv run pytest tests/test_opportunity_fixture.py -q && (cd ../frontend && pnpm test)`.
  Los tests del front importan el fixture (`frontend/src/lib/__tests__/dossierView.spec.ts:3`,
  `radarView.spec.ts:3`, `exploreView.spec.ts:3`, `searchPalette.spec.ts:3`). Ninguno cuenta la
  evidencia de `opp_003` (comprobado), pero se confirma aquí y no en el paso 7.
- **Commit:** `Add replica fields to the Evidence contract and fixture`

### Paso 2 — Lógica pura de republicaciones [HECHO]

- **Archivos:** `backend/app/intelligence/replicas.py` (nuevo), `backend/tests/test_replicas.py`
  (nuevo)
- **Cambio:** todo lo de "Interfaz (`app/intelligence/replicas.py`)". Más dos helpers para el paso
  4:
  - `replica_outlets(group: Sequence[Piece], stories: StoryAssignment) -> dict[int, int]`:
    representante → nº de `outlet_key` distintos del suyo entre sus republicaciones del grupo.
  - `replica_notes(replicas: int, unverified: bool) -> list[str]` (D13).

  `same_story_verdict` lee `answer["confidence"]` y `answer["score"]`. Si falta la clave, es `None`.
- **Test primero** (`tests/test_replicas.py`, vectores `numpy` a mano y piezas con un helper como
  `piece()` de `test_build_opportunities.py`):
  - `test_normalize_title_ignores_case_quotes_and_punctuation`: `OpenAI “rogue” agent activities
    found on Wikimedia projects` = `OpenAI "rogue" agent activities found on Wikimedia projects`.
  - `test_short_equal_titles_are_not_same_title`: "Claude Haiku 5.5" en dos medios → `False`.
  - `test_same_link_by_url_target_or_both_targets` (parametrizado, `ids=`): url = url;
    target_url = url de la otra; target_url = target_url; los dos target `None` → `False`; barra
    final y `#frag` ignorados.
  - `test_pairs_skip_same_outlet`: dos stories de HN con queries distintas (mismo `outlet_key`
    "hackernews") y similitud 1.0 → ni arista ni candidato.
  - `test_shared_link_is_an_edge_not_a_candidate`.
  - `test_candidates_from_similarity_or_equal_title`: 0.71 → candidato; 0.69 con título distinto →
    nada; 0.40 con título igual ≥ 5 palabras → candidato con `same_title=True`.
  - `test_candidates_sorted_by_similarity_then_ids`.
  - `test_pairs_never_cross_clusters`.
  - `test_no_clusters_or_vectors_gives_nothing`: `clusters=[]` y `vectors` vacío → `([], [])`.
  - `test_verdict` (parametrizado): `None` → `None`; confidence 0.4 → `None`; score 2.8, conf 0.9
    → `True`; score 2.4, conf 0.9 → `False` (nivel 2 = cobertura independiente); score 0.1 →
    `False`.
  - `test_decide_pair` (parametrizado): verdict `True` → `JEV`; `False` con sim 0.99 y título igual
    → `None`; `None` y sim 0.91 → `SIMILARITY`; `None` y título igual con sim 0.5 → `SAME_TITLE`;
    `None` y sim 0.85 → `None`.
  - `test_group_stories_picks_earliest_as_representative` y `…_ties_by_item_id`.
  - `test_group_stories_is_transitive`: A~B, B~C → B y C apuntan a la representante A.
  - `test_all_pieces_replicas_of_one_story`: 5 piezas, una nota → 4 republicaciones y 1
    representante.
  - `test_unverified_only_when_no_verified_edge`: arista `SIMILARITY` → `unverified`; con `JEV` o
    `SAME_LINK` también → no.
  - `test_replica_outlets_counts_distinct_outlets_other_than_representative`: dos republicaciones
    del mismo medio cuentan 1; una del mismo medio que la representante no cuenta.
  - `test_replica_notes` (0 → `[]`; 1 → singular; 3 sin verificar → dos notas).
- **Verificación:** `uv run pytest tests/test_replicas.py -q && uv run pyright app/intelligence/replicas.py && uv run python -c "import app.intelligence.replicas, app.intelligence.opportunities"`
  (repite el import en el paso 4, cuando `opportunities.py` ya importa de `replicas.py`)
- **Commit:** `Add pure replica detection and story grouping`

### Paso 3 — Batería de pares de Jev [HECHO]

- **Archivos:** `backend/app/editorial/prompts/jev/pair.v1.yaml` (nuevo),
  `backend/app/intelligence/jev.py`, `backend/tests/test_jev.py`
- **Cambio:**
  - YAML `version: 1` con la pregunta `same_story`, `type: score`, `instructions` y 4 `criteria`
    en orden 0–3 (D4, D10). Cabecera de comentario con el porqué, como `piece.v3.yaml`.
    Instrucciones propuestas:
    - instrucción: "¿Las piezas `a` y `b` son la misma nota?";
    - 0: "tratan temas distintos";
    - 1: "mismo tema, pero cuentan hechos distintos";
    - 2: "el mismo acontecimiento, contado por separado por cada medio con su propio texto,
      fuentes o enfoque";
    - 3: "la misma nota replicada: una es copia, traducción o reenvío de la otra (un enlace al
      mismo artículo, la versión en otro idioma del mismo medio o el mismo autor publicándola en
      otro canal)".
  - En `jev.py`: `battery_cache_key`, `cache_key` delegando (firma intacta), `pair_battery()` y
    `pair_state()` (D10). Actualiza el docstring del módulo ("baterías de pieza y de par").
- **Test primero:**
  - `test_pair_battery_loads_same_story_score`: una pregunta, `Score`, 4 criterios.
  - `test_piece_cache_key_is_unchanged`: `cache_key(state, m) == sha256` del payload actual
    calculado a mano en el test (`json.dumps({...}, sort_keys=True, ensure_ascii=False)`).
  - `test_pair_state_is_canonical`: `pair_state(a, b) == pair_state(b, a)` y misma clave.
  - `test_pair_state_trims_and_omits_description`.
  - `test_pair_state_never_carries_url_segment_or_region`.
- **Verificación:** `uv run pytest tests/test_jev.py -q && uv run pyright app/intelligence/jev.py`
- **Commit:** `Add the Jev pair battery for replicated stories`

### Paso 4 — Scores con notas deduplicadas [HECHO]

- **Archivos:** `backend/app/intelligence/opportunities.py`,
  `backend/app/intelligence/audience_fit.py`, `backend/tests/test_build_opportunities.py`,
  `backend/tests/test_audience_fit.py`
- **Cambio:** lo de "Cambios en `app/intelligence/opportunities.py`" (D6, D7, D12, D13) y
  `audience_fit.py:92` → `item_count=result.story_count`. Cuando hay republicaciones, `_description`
  añade "(K republicaciones)". `TopicResult.replica_ids` = republicaciones del grupo.
- **Test primero** (en `test_build_opportunities.py`, con `stories=group_stories(...)` construido a
  mano):
  - `test_without_stories_nothing_changes`: `build_opportunities(..., stories=NO_REPLICAS) ==
    build_opportunities(...)`.
  - `test_replicas_do_not_count_as_independent_sources`:
    - 3 piezas HN (un medio) + 3 RSS de 3 medios, y 2 de los RSS republican al tercero;
    - `source_count` baja de 4 a 2;
    - `cross_source_score` y `evidence_strength` bajan en consecuencia (valores esperados a mano
      con `POINTS_PER_EXTRA_SOURCE`/`_PLATFORM` y la fórmula de `ranking.py:50-54`).
  - `test_replicas_do_not_raise_saturation`: dos temas con el mismo nº de piezas, uno con
    republicaciones → su `saturation_score` es menor que el del otro.
  - `test_all_replicas_single_story_is_low_confidence`: 5 piezas de 5 medios, una nota →
    `source_count == 1`, `lifecycle` `unknown`, `confidence` `low`.
  - `test_single_source_with_stories_unchanged`: tema de una sola fuente sin pares → igual que hoy.
  - `test_evidence_marks_replicas_and_count`: la representante lleva `replica_count` = medios
    distintos; cada republicación lleva `replica_of` = URL de la representante.
  - `test_replicas_go_after_originals_in_evidence`: incluido un caso en el que la republicación es
    outlier y la original no.
  - `test_replica_limitations` (verificadas → solo la nota de conteo; con `unverified` → las dos).
  - `test_velocity_and_timeline_still_count_pieces`: velocidad, aceleración y suma del timeline
    iguales con y sin `stories`.
  - En `test_audience_fit.py`: `test_breakdown_item_count_uses_stories`. Un tema con
    republicaciones y una muestra pequeña: la penalización `small_sample` de `apply_fit` coincide
    con la que daría `score_breakdown(item_count=story_count, …)` y no con `len(pieces)`.
- **Verificación:** `uv run pytest tests/test_build_opportunities.py tests/test_audience_fit.py -q && uv run pyright app/intelligence/opportunities.py app/intelligence/audience_fit.py`
- **Commit:** `Count independent sources and saturation by story, not by copy`

### Paso 5 — Servicio de detección con caché y presupuesto [HECHO]

- **Archivos:** `backend/app/services/replicas.py` (nuevo),
  `backend/tests/test_replicas_service.py` (nuevo)
- **Cambio:** `detect_replicas` y `ReplicaStats` según el diseño (D8, D9).
- **Test primero** (contra `radar_test`, con `FakePairJudge` al estilo de
  `test_classification.py:19-33`, que devuelve `{"same_story": {"type": "score", "score": s,
  "confidence": c, "legend": {...}, "probabilities": {...}}}` según los títulos; las piezas pueden
  ser `Piece` en memoria, porque `content_item_id=None` no necesita filas en `content_items`):
  - `test_jev_yes_marks_replica_and_is_cached`: segunda llamada → 0 llamadas nuevas y
    `cached == 1`; la fila tiene `battery == "pair"` y `content_item_id is None`.
  - `test_jev_no_overrides_similarity_rule`: sim 0.95 y Jev nivel 2 seguro → sin republicaciones.
  - `test_without_judge_uses_fallback_rule`: `judge=None`, sim 0.95 → republicación `unverified`,
    `skipped_reason == SKIPPED_WITHOUT_KEY`; sim 0.80 → nada.
  - `test_without_judge_still_reads_cache`: con una fila de par ya guardada, `judge=None` aplica su
    veredicto.
  - `test_judge_failure_falls_back`: `JudgeError` en un par → `failed == 1` y decide la regla.
  - `test_budget_caps_new_calls`: con `MAX_PAIR_JUDGMENTS_PER_RUN` parcheado a 1 (monkeypatch del
    módulo) y 2 candidatos → 1 llamada, `over_budget == 1`, y el par de mayor similitud es el
    juzgado.
  - `test_usage_is_metered_per_answer`: `meter.counts[(Provider.TYPESAFE_JEV, "pair_battery")]`
    suma `input_tokens`.
  - `test_no_candidates_makes_no_queries_or_calls`.
- **Verificación:** `TEST_DATABASE_URL=postgresql+asyncpg://radar:radar@localhost:5433/radar_test_dedup uv run pytest tests/test_replicas_service.py -q && uv run pyright app/services/replicas.py`
- **Commit:** `Detect replicated stories with cached Jev pair judgments`

### Paso 6 — Cableado en `compute_opportunities` y `analyze` [HECHO]

- **Archivos:** `backend/app/services/opportunities.py`, `backend/app/jobs/analyze.py`,
  `backend/tests/test_load_pieces.py`
- **Cambio:**
  - `_to_piece` copia `target_url`.
  - `compute_opportunities(session, as_of, *, pieces=None, judgments=None, judge: Judge | None,
    meter: UsageMeter)` llama a `detect_replicas(session, pieces, clusters, vectors, judge=…,
    meter=…)` después de `cluster` y pasa `stories=` a `build_opportunities`. Docstring: "Solo
    escribe la caché de pares de Jev (`jev_judgments`)."
  - `ComputedOpportunities.replicas: ReplicaStats`. Con 0 piezas →
    `ReplicaStats(0, 0, 0, 0, 0, 0, 0)` sin llamar al servicio.
  - En `analyze._evaluate` se construye `judge = build_judge(settings)` una vez y se pasa a
    `classify_pieces` y a `compute_opportunities` con el mismo `meter`. `record_meter(session,
    meter, …)` va después de `compute_opportunities`.
  - `_stats` gana `"replicas": asdict(e.computed.replicas)`.
  - `_print_summary` gana la línea `f"  republicaciones: {r.replicas} piezas ({r.unverified} sin
    verificar) · pares: {r.candidates} candidatos · {r.judged} jev · {r.cached} de caché ·
    {r.failed} fallidos · {r.over_budget} fuera de presupuesto"`.
  - Si `skipped_reason`, `f"  pares omitidos: {r.skipped_reason}"`.
- **Test primero:** `test_load_pieces_carries_target_url` en `tests/test_load_pieces.py` (estilo
  de los tests existentes del archivo). `compute_opportunities` y `analyze` no tienen tests: cargan
  el modelo de embeddings. Se verifican con pyright y la suite completa.
- **Verificación:** `TEST_DATABASE_URL=postgresql+asyncpg://radar:radar@localhost:5433/radar_test_dedup uv run pytest -q && uv run pyright app/services/opportunities.py app/jobs/analyze.py`
- **Prohibido:** correr `uv run python -m app.jobs.analyze`. `backend/.env` puede apuntar a
  Supabase.
- **Commit:** `Run replica detection between clustering and scoring in analyze`

### Paso 7 — Tipos del frontend

- **Archivos:** `frontend/src/types/api.ts`
- **Cambio:** regenerar desde el OpenAPI de la app sin levantar servidor. El archivo se escribe
  desde Python, no redirigiendo stdout: un log al importar `app.main` corrompería el JSON.
  `cd backend && uv run python -c "import json; from pathlib import Path; from app.main import app; Path('/tmp/openapi-dedup.json').write_text(json.dumps(app.openapi()))"`
  y después `cd frontend && OPENAPI_URL=/tmp/openapi-dedup.json pnpm gen:api`.
  - El diff de `api.ts` debe limitarse a `replica_of`, `replica_count` y la descripción de
    `source_count`. Si sale más, `main` tenía tipos desactualizados: anótalo en el informe y no lo
    arregles a mano.
  - No toques componentes.
- **Test primero:** no aplica (archivo generado). Verificación manual: el diff.
- **Verificación:** `cd frontend && pnpm type-check && pnpm lint && pnpm test && pnpm build`
- **Commit:** `Regenerate API types with Evidence replica fields`

### Paso 8 — Documentación

- **Archivos:** `docs/jev.md`, `CLAUDE.md`
- **Cambio:**
  - `docs/jev.md`:
    - §2 "Par" (`:83-96`): batería implementada (`pair.v1.yaml`), candidatos (≥ 0.70 o título
      igual; el enlace compartido no se pregunta), nivel 2 = independiente y 3 = republicación,
      regla de respaldo (título ≥ 5 palabras o ≥ 0.90) y tope de 250 llamadas.
    - Tabla "Del juicio a la decisión" (`:115-121`): fila `score` precisando que la incertidumbre
      es `confidence < 0.5` y que el nivel se redondea.
    - Tabla de reparto (`:24`): quitar el "mientras no esté".
    - Coste del par: medido ~800 tokens; quitar "~500 al día" si no aplica y poner "~220 pares en
      la primera ejecución; después, solo los nuevos".
  - `CLAUDE.md:227`: cambiar "Pendiente: deduplicar…" por una frase con lo implementado (enlace
    compartido, Jev en la franja dudosa, regla de respaldo, notas con representante la más antigua,
    qué cuenta tras deduplicar) y el puntero a `docs/jev.md`.
  - Sin cambios de §6 más allá de añadir a la línea de `Evidence` (`CLAUDE.md:166`):
    "`replica_of` (URL de la original o `null`), `replica_count` (en la original: medios que la
    republican)".
- **Verificación:** `git diff --stat` (solo esos dos archivos).
- **Commit:** `Document replicated-story detection`

## Estrategia de test

- **Seams:** `build_opportunities(stories=…)` (puro, el más alto sin modelo de embeddings),
  `detect_replicas` (servicio con DB de tests y `Judge` falso), funciones puras de
  `intelligence/replicas.py` y de `jev.py`.
- **Prior art:** `backend/tests/test_build_opportunities.py` (helper `piece()`, valores esperados a
  mano), `backend/tests/test_classification.py` (`FakeJudge`, caché), `backend/tests/test_jev.py`
  (batería y state).
- **Casos que entran:**
  - los de cada paso;
  - casos límite obligatorios: una sola fuente, todas las piezas republicaciones de una nota, sin
    clusters ni embeddings, sin clave de Jev, fallo de Jev, veredicto incierto, tope de llamadas;
  - 0 snapshots y métrica ausente: ya cubiertos por `test_zero_snapshots` y `test_missing_metric`,
    que no cambian con `stories=None`;
  - ventana anterior vacía: cubierta por `test_empty_previous_window`; con republicaciones, la
    saturación por notas no rompe nada.
  - Todos salen de los datos reales de la calibración o del plan.
- **Casos descartados por ruido:** precisión real de Jev en pares (necesita pares etiquetados; va
  al informe como validación pendiente). Rendimiento de `topic_pairs` (temas ≤ ~40 piezas).
- **Parametrización:** `same_link` (`ids=["url", "target-url", "both-targets", "no-targets",
  "trailing-slash"]`), `same_story_verdict` (`ids=["missing", "low-confidence", "level-3",
  "level-2", "level-0"]`), `decide_pair` (`ids=["jev-yes", "jev-no-beats-rule", "rule-similarity",
  "rule-title", "below-rule"]`).

## Verificación final

```bash
cd /Users/melandres8/Documents/Projects/content-radar && docker compose up -d db
cd /Users/melandres8/Documents/Projects/content-radar/backend
uv run ruff check . && uv run ruff format --check .
uv run pyright app/intelligence/replicas.py app/intelligence/jev.py app/intelligence/opportunities.py app/intelligence/audience_fit.py app/services/replicas.py app/services/opportunities.py app/jobs/analyze.py app/schemas/opportunity.py
TEST_DATABASE_URL=postgresql+asyncpg://radar:radar@localhost:5433/radar_test_dedup uv run pytest -q
wc -l app/intelligence/opportunities.py app/intelligence/replicas.py app/services/replicas.py
cd ../frontend && pnpm type-check && pnpm lint && pnpm test && pnpm build
cd .. && git log --oneline main..intel/dedup-replicas
```

No se corre `analyze` en ninguna DB. Melkin decide cuándo correrlo y si fija `DEMO_RUN_ID`.

## Riesgos

- **Jev pone en nivel 3 coberturas independientes** (lectura literal: el mismo hecho con titulares
  parecidos). Señal: tras la primera ejecución real, `source_count` baja en muchos temas de prensa
  en español (El País/Expansión/Clarín). → Melkin revisa 10 pares con `jev_judgments`
  (`battery='pair'`) y, si hace falta, sube `SAME_STORY_MIN_CONFIDENCE` o ajusta los criterios
  (`pair.v2`).
- **El ranking de la demo se mueve:** los temas inflados por copias bajan, algunos a `unknown` o
  `wait_for_case`. Es lo esperado (regla 3), pero hay que revisar el ranking a mano antes de fijar
  `DEMO_RUN_ID` (CLAUDE.md §13).
- **La caché del LLM cambia de clave** en los temas con republicaciones (D12): se reevalúan una vez.
  Señal: `llm: N evaluados` mayor de lo habitual en la primera ejecución. Coste de céntimos.
- **`opportunities.py` pasa de 500 líneas.** → Deuda en el informe. No se parte en este plan.
- **Choque con el plan en paralelo `intel-claim-verification`**
  (`.claude/plans/intel-claim-verification.plan.md`). Ese plan también toca `intelligence/jev.py`
  (otra batería y la misma `battery_cache_key(battery, state, model)`, con la misma firma y el
  mismo payload que aquí), `jobs/analyze.py`, `docs/jev.md` y CLAUDE.md §7. Señal: conflicto al
  rebasar. → Gana la `battery_cache_key` que ya esté en `main` (son idénticas). En `analyze.py`
  conserva los dos cambios. `frontend/src/types/api.ts` se **regenera** con el paso 7, no se
  resuelve a mano.
- **El frontend no pinta los campos** hasta que el Frontend lead lo haga. Sin riesgo de rotura: son
  opcionales con default.

## Historial de intentos

| Fecha | Qué bloqueó | Qué se decidió | Commits que quedaron |
| --- | --- | --- | --- |

## Preguntas abiertas

- (ninguna)
