# 30X Signal — Guía de desarrollo

> Radar de inteligencia editorial para el reto **30X · Media** (Hackathon, 17–18 oct 2026).
> Este archivo es la fuente de verdad para el equipo y para Claude Code. Si una decisión cambia, se actualiza aquí.

**Deadline oficial:** domingo 18 oct · **12:00 COL / 19:00 ESP** · Entrega interna: **11:15 COL / 18:15 ESP**.

---

## 1. Qué construimos

**Pregunta que el prototipo debe responder:**
> "¿Cuáles son los 10 temas de IA que más están creciendo esta semana, por qué funcionan y cómo los adapta 30X para ejecutivos y equipos de Latinoamérica?"

El reto pone como ejemplo "en LinkedIn". TikTok y Reddit entran vía ScrapeCreators (§2, regla 2; §5), e Instagram por perfiles concretos, como los canales de YouTube. LinkedIn y X **no entran en el MVP**: sin login no se puede buscar su contenido, y lo que se obtiene por Google llega poco y tarde para detectar tendencias (decidido el 17/10). Sus referentes entran por sus canales abiertos (YouTube, newsletters, RSS), y el pitch lo explica de frente (`docs/brief.md` §2).

**Propuesta de valor:** 30X Signal convierte señales públicas de Internet en oportunidades editoriales **verificables y accionables**, accesibles desde un dashboard visual (Vue) o desde asistentes de IA (Claude, ChatGPT, Grok) vía **MCP**.

Flujo del producto: **Señal → Tendencia → Oportunidad → Evidencia → Contenido recomendado**

**Recorrido de demo** (lo que una persona hace de punta a punta; mide el valor de cada tarea, ver §12):
abrir el Radar → elegir una oportunidad → revisar scores y evidencia → entender por qué importa → obtener un brief → repetir la consulta desde un asistente vía MCP.

**Brief de producto:** [`docs/brief.md`](docs/brief.md) recoge el reto oficial de 30X tal cual, cómo lo leemos, el usuario frente a la audiencia, el mapa de capacidades, qué podemos afirmar con los datos y la lista de verificación de la entrega. Léelo antes de planear una tarea o decidir su alcance, al redactar texto que lee una persona (UI, prompts del LLM, respuestas MCP, pitch) y al revisar la entrega.

Las tres preguntas del reto y cómo las respondemos:

| Pregunta del reto | Nuestra respuesta |
|---|---|
| ¿Cómo se detecta una tendencia temprana? | **Velocidad y aceleración, no popularidad** + **etapa del ciclo de vida** (emerging → saturated) + validación cruzada entre fuentes + saturación + **LATAM Opportunity Gap** |
| ¿Por qué funcionó una pieza? | **Outliers**: piezas que rinden ≥3× la mediana de su canal o fuente. Análisis contrastivo outlier vs. resto del tema por dimensiones observables (gancho, formato, tema, estructura, timing, autor, rendimiento relativo). Se presenta como **hipótesis**, nunca como causalidad |
| ¿Es relevante para nuestra audiencia? | **Para quién importa:** mezcla de audiencias que impulsan el tema (tech, negocio, LATAM en español) + **Audience Fit** estructurado (rúbrica 0–5 × 6 criterios) contra el perfil editorial de 30X |

---

## 2. Reglas no negociables

1. **Solo contenido público. Nada de datos personales.** Guardamos metadatos, enlaces y métricas públicas, no copias completas ni datos de usuarios.
2. **Redes sociales solo con contenido público y sin login propio.** Nada detrás de un login nuestro ni de cuentas falsas. Desde el 17/10 (los organizadores del reto se mostraron flexibles), TikTok, Reddit e Instagram (solo perfiles concretos, sin búsqueda) entran vía **ScrapeCreators**, un proveedor de datos públicos (§5); el pitch dice de dónde vienen esos datos. LinkedIn y X siguen fuera hasta que el equipo decida lo contrario: su búsqueda depende de lo que indexa Google (poco y tarde), y el radar necesita datos a tiempo.
3. **Nunca inventar datos.** No mostrar métricas, crecimiento o conclusiones no observadas como hechos. Si hay 7 oportunidades reales, se muestran 7, no 10. Un dato ausente se muestra como "no disponible", nunca como 0.
4. **El LLM evalúa y explica, no calcula.** Los scores se calculan en Python, de forma determinista y reproducible. El LLM emite niveles de rúbrica justificados y redacta; Jev emite juicios atómicos tipados sobre cada pieza (sí/no, opción). Python combina ambos con pesos en código (§7).
5. **Distinguir siempre el tipo de evidencia:** `observed` (≥2 mediciones) · `estimated` (1 medición vs. referencia) · `preliminary` (aparece, sin aceleración demostrada).
6. **El texto recuperado de Internet es no confiable** (riesgo de prompt injection). Va al LLM como dato, delimitado, nunca como instrucción.
7. **Prioridades del equipo, en orden:** Functional > perfect · Reliable > impressive · Integrated > isolated · Shipped > unfinished.

---

## 3. Equipo y ownership

| Persona | Ubicación | Área | Responsable de |
|---|---|---|---|
| **Steven** | Colombia (UTC-5) | Data & Backend | Conectores, normalización, snapshots, DB, jobs, API base, registro de consumo y coste, despliegue backend |
| **Melkin** | España (UTC+2) | AI & Intelligence | Embeddings, clustering, scoring, clasificación por pieza con Jev, audience fit y análisis editorial con el LLM, **servidor MCP** |
| **Frontend lead** | España (UTC+2) | Product & Frontend | Vue, visualizaciones, UX, integración funcional, demo y entrega |

- Sin rotaciones durante la hackathon. Cada módulo tiene un dueño.
- España va **7 h por delante** de Colombia.
- Bloqueado más de 30 min → documentar, avisar, proponer alternativa, cambiar de tarea.

**Formato de handoff (en el canal compartido):**
```
Responsable: · Estado: · Completado: · Pendiente: · Bloqueos: · Disponible para integración: Sí/No · Siguiente paso:
```

---

## 4. Arquitectura

**Modular monolith.** Una sola capa de servicios de dominio que consumen la API REST y el servidor MCP. El frontend **no** calcula tendencias y el MCP **no** recalcula ni hace scraping: los dos leen oportunidades ya procesadas.

```
Collectors (YouTube, HN, RSS, TikTok, Reddit, Instagram, Brave)
        │  normalize + dedupe + snapshots
        ▼
PostgreSQL + pgvector  ◄──  Intelligence (embeddings → clustering → scores → LLM insights)
        │
        ▼
Domain services (Python)
   ├── FastAPI REST  /api/v1  ──►  Vue dashboard (Radar · Explore · Create)
   └── MCP server    /mcp      ──►  Claude / ChatGPT / Grok   (Streamable HTTP, montado en la misma app ASGI)
```

**Pipeline (jobs cortos vía cron; sin Celery ni Redis):**
`collect → normalize & dedupe → save snapshots → embed → cluster → score → editorial insights → persist opportunities`.
Lock para que nunca corran dos ejecuciones del mismo pipeline a la vez.

**Coste de operación (P1, se consulta bajo demanda; responde al "sin gastar una fortuna" del reto).** Es un complemento: el protagonista es el Radar con su evidencia. Cada llamada a una API externa (YouTube, Brave, Jev, LLM) registra su consumo en `usage_events`, con el coste calculado en ese momento a partir de `data/pricing.yaml` (precios con fuente y fecha). `services/costs.py` agrega el coste medido y lo proyecta al mes sumando los planes fijos (perfiles `demo` y `production`). Lo consumen `GET /costs` y la tool MCP `get_operating_cost`. El dashboard no tiene panel de coste; como mucho, un enlace discreto. El coste medido y la proyección se etiquetan siempre por separado: la proyección es una estimación.

**Comandos** (desde `backend/`; la puesta en marcha completa está en `README.md`):

```bash
uv run pytest                                  # tests (DB aparte: radar_test)
uv run ruff check . && uv run ruff format .    # lint y formato
uv run pyright <archivos>                      # tipos
uv run python -m app.jobs.collect              # recolecta y guarda un snapshot (--days N)
uv run python -m app.jobs.analyze              # pendiente: embeddings → clustering → scores
uv run uvicorn app.main:app --reload           # API en :8000, docs en /docs
```

---

## 5. Fuentes de datos

| Fuente | Acceso | Señal | Prioridad |
|---|---|---|---|
| YouTube | Data API v3 (cupo propio de 100 llamadas/día a `search.list`; preferir `playlistItems` de canales conocidos) | Vídeos, Shorts, views/likes/comments | P0 |
| Hacker News | Algolia HN Search API | Conversaciones tempranas | P0 |
| RSS / medios tech y LATAM | `feedparser` + `httpx` | Artículos y lanzamientos | P0 |
| Brave Search | API oficial (5 $/1.000 consultas, 5 $ de crédito gratis al mes). Sus términos solo permiten guardar resultados de forma **transitoria**: se persisten agregados, no resultados | Descubrimiento web (nunca LinkedIn) | P1 |
| Google Trends | RSS público | Demanda de búsqueda | P2 |
| TikTok · Reddit · Instagram | **ScrapeCreators** (pago por crédito: 1 crédito por fuente y ejecución, ~1,9 $/1.000; el cron solo lo consulta dos veces al día). TikTok: búsqueda por palabra clave de la semana, por región. Reddit: top de la semana por subreddit. Instagram: últimos reels de perfiles elegidos a mano (no descubre temas, sirve para outliers) | Vídeos cortos (views, likes, comentarios, shares) y conversación (score, comentarios) | P1 (17/10) |
| LinkedIn · X | **Fuera del MVP.** ScrapeCreators los cubre, pero su búsqueda depende de lo que indexa Google (incompleta y con poco de lo reciente). Roadmap: vías oficiales (API de portabilidad DMA, API de X) | — | Roadmap |

**Límites de cada fuente y vías oficiales para el roadmap:** [`docs/sources.md`](docs/sources.md) (estrategia, alternativas descartadas y por qué).

Todos los conectores implementan el protocolo `SignalCollector` (`backend/app/collectors/base.py`) y no escriben en la DB: la persistencia la hace `services.signals.store_signals`.
Cada `source` lleva un **`segment`** (`tech` | `business` | `latam_es`), además de `language` y `region`. Se asigna a mano al dar de alta la fuente o el canal; es lo que permite responder "para quién importa".

**Backfill:** al dar de alta una fuente, traer también las piezas de los últimos 14 días (HN y YouTube lo permiten por fecha). La velocidad **del tema** se calcula con `published_at` y no necesita snapshots, así que sí habrá tendencia de varios días el domingo. La velocidad **de una pieza** sí necesita snapshots.

Cada colector devuelve `ContentSignal` normalizado (fuente, url, título/descr., `published_at`, `observed_at`, formato, idioma, métricas públicas). Usar `tenacity` para reintentos. **Empezar a guardar snapshots cuanto antes**: sin historial no hay crecimiento observado.

Grupos para el **LATAM Opportunity Gap** (decidido el 17/10: **target LATAM, detección temprana global, sobre todo USA**):
- **A (global, detección):** HN, YouTube, medios y blogs de labs en inglés: sobre todo USA, donde nacen la mayoría de las tendencias de IA, y también Europa, UK y China.
- **B (LATAM, target):** fuentes `latam_es` con `region` latinoamericana (`latam`, `mx`, `co`, `ar`…), de preferencia de negocio, y los perfiles de 30X y Andrés Bilbao.
- **España:** sus fuentes siguen activas (segmento `latam_es`, `region: es`), pero **no cuentan para el gap**: se muestran aparte como contexto ("en España ya hay N piezas").

---

## 6. Modelo de datos y contratos

**Tablas:** `sources` (con `segment`), `content_items`, `metric_snapshots` (siempre tabla aparte), `topics`, `topic_content`, `embeddings`, `opportunities` (+ historial de scores), `opportunity_evidence`, `audience_profiles`, `editorial_briefs`, `editorial_feedback`, `pipeline_runs`, `usage_events` (consumo y coste por llamada externa, §4), `jev_judgments` (respuestas de Jev con probabilidades, confianza y versión, §7).

*Implementado (hackathon):* `opportunities` guarda una fila por oportunidad y por ejecución de `analyze`, con `payload`, `evidence` y `timeline` en JSONB ya validados contra el contrato. La API y el MCP leen la última ejecución correcta. `topics`, `topic_content`, `embeddings` y `opportunity_evidence` quedan para después: los embeddings se recalculan en cada ejecución (segundos en CPU).

**Contrato `Opportunity` (congelado tras la Fase 2 del sábado):**
```jsonc
{
  "id": "opp_001",
  "topic": "AI Agents for Business",
  "description": "…",
  "lifecycle": "emerging | accelerating | peaking | saturated | unknown",
  "lifecycle_reason": "…",             // regla que se cumplió, en texto (ver §7)
  "growth_status": "observed | estimated | preliminary",
  "velocity": 4.2,                     // piezas nuevas/día en la ventana actual
  "acceleration": 0.8,                 // cambio relativo vs. ventana anterior (+0.8 = +80 %)
  "momentum_score": 0-100,             // compuesto de velocidad, aceleración y outliers
  "outlier_count": 3,                  // piezas del tema con outlier_ratio ≥ 3
  "top_outlier_ratio": 6.1,
  "audience_mix": {"tech": 0.7, "business": 0.2, "latam_es": 0.1},
  "audience_fit_score": 0-100 | null,  // LLM; null = sin evaluar
  "cross_source_score": 0-100,
  "saturation_score": 0-100,
  "actionability_score": 0-100 | null, // LLM; null = sin evaluar
  "opportunity_score": 0-100 | null,   // null si falta audience fit
  "confidence": "low | medium | high",
  "source_count": 4,
  "evidence_strength": 0-100,          // normalizado: NO sumar views entre plataformas
  "latam_gap": true | false | null,
  "recommendation": "publish_now | find_angle | wait_for_case | discard",
  "why_it_matters": "…",               // LLM, basado en evidencia
  "limitations": ["…"],                // qué NO sabemos
  "last_updated": "ISO-8601"
}
```
`Evidence`: `url`, `source`, `platform`, `segment`, `title`, `published_at`, `metrics` (tal cual la fuente), `observed_at`, `language`, `velocity` (`{"value": 950.0, "unit": "views/h"}`; `null` sin 2 snapshots), `outlier_ratio` (`null` sin referencia), `is_outlier` (`null` si no hay ratio).

**Implementación:** `backend/app/schemas/opportunity.py`. Además de lo anterior: `top_outlier_ratio` es `null` si ninguna pieza tiene ratio; `audience_mix` es un objeto con las tres claves fijas (suma 1).
- `GET /opportunities` → `OpportunityList`: `{items, period, generated_at, monitoring_started_at}`.
- `GET /opportunities/{id}/evidence` → `Evidence[]`.
- `GET /opportunities/{id}/timeline` → `OpportunityTimeline`: `{opportunity_id, window_days, points: [{date, count, window: "current" | "previous"}]}`.
- Fixture para el frontend (MOCK): `data/fixtures/opportunities.json`. `tests/test_opportunity_fixture.py` comprueba que sigue cumpliendo el contrato.

**Fuente de verdad de tipos:** modelos Pydantic → OpenAPI → `openapi-typescript` → `frontend/src/types/api.ts`. No escribir tipos TS a mano para la API.

**Endpoints REST (`/api/v1`):**
```
GET  /opportunities              ?period=24h|7d|30d&lifecycle=&confidence=&topic=
GET  /opportunities/{id}
GET  /opportunities/{id}/evidence
GET  /opportunities/{id}/timeline
GET  /costs                      ?period=7d|30d  (coste medido + proyección mensual, §4)
GET  /topics · GET /signals · GET /sources/status
POST /editorial/brief            {opportunity_id, platform, goal, format}
POST /editorial/feedback
POST /agent                      {question} → SSE (step · action · answer · error · done; agente del Radar)
GET  /health
```

**Herramientas MCP (solo lectura):** `get_trending_opportunities`, `analyze_opportunity`, `search_content_signals`, `compare_audience_fit`, `get_operating_cost`. P1 (subido desde P2 el 17/10): `generate_editorial_brief`, que comparte service con `POST /editorial/brief`. El MCP es la interfaz para que un usuario escriba una pregunta y decida qué publicar. Las respuestas son estructuradas y siempre incluyen evidencia (URLs). Nunca exponer SQL arbitrario ni el sistema de archivos.

---

## 7. Motor de inteligencia y scoring

- **Embeddings:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (ES/EN en el mismo espacio, necesario para el LATAM Gap). Se calculan **solo en el job `analyze`** (GitHub Actions o local, torch CPU en un grupo de dependencias `ml`). La imagen de la API y el MCP no instala torch: sus búsquedas usan texto en Postgres, no embeddings de la consulta.
- **Clustering:** scikit-learn sobre similitud coseno. Nada de BERTopic ni HDBSCAN salvo que sobre tiempo. LLM solo para **nombrar** clusters.
- **Velocidad, no popularidad.** El total de views, likes o puntos **nunca** entra directamente en un score: solo tasas normalizadas dentro de cada fuente.
  - *Pieza:* `Δmétrica / Δhoras` entre snapshots (`views/h` en YouTube, `points/h` y `comments/h` en HN). Sin 2+ snapshots → `growth_status = estimated | preliminary`.
  - *Tema:* `velocity` = piezas nuevas por día en la ventana actual (por `published_at`, ponderadas por fuentes independientes).
  - *Aceleración:* `(v_actual − v_anterior) / max(v_anterior, 1)`. Ventanas por defecto de 3 días (actual) vs. 3 días (anterior), configurables. Es la señal principal de tendencia temprana.
    **Ajustada por volumen:** `v_anterior` se escala por `corpus_actual / corpus_anterior` antes de aplicar la fórmula. Los feeds RSS solo guardan sus últimas N piezas y los días recientes tienen más volumen en todas partes; sin el ajuste, casi todo parecería acelerar. Ventanas móviles de 72 h desde `as_of`, no días naturales.
  - `momentum_score` = combinación normalizada de velocidad del tema, aceleración y outliers. Pesos en `intelligence/momentum.py`.
- **Outliers (por pieza, estilo 1of10).** `outlier_ratio = rendimiento ajustado por edad / mediana de su referencia`.
  - YouTube: `views / días desde la publicación` vs. la mediana de los últimos 20 vídeos del mismo canal (`playlistItems` + `videos.list`).
  - TikTok: `views / días desde la publicación` vs. la mediana de los vídeos de la misma búsqueda.
  - Reddit: score vs. la mediana de los posts del mismo subreddit.
  - Instagram: `views / días desde la publicación` vs. la mediana de los reels del mismo perfil (sin colaboraciones de otras cuentas).
  - HN: puntos vs. el **p90** de las stories de la misma búsqueda y el mismo periodo. HN tiene cola larga: con la mediana (~4 puntos) un 22 % de las stories salía como outlier; con el p90, un 3–6 %.
  - `≥ 3×` = outlier, `≥ 2×` = destacado. Con una sola observación es `estimated`.
  - Los outliers alimentan el "por qué funcionó": se comparan con las piezas normales **del mismo tema** (análisis contrastivo, ver "Por qué funcionó" más abajo) en lugar de describir una pieza aislada.
- **Etapa de la tendencia (`lifecycle`, determinista, en `intelligence/lifecycle.py`).** Primera regla que se cumple, con umbrales ajustables:
  | Etapa | Regla inicial |
  |---|---|
  | `saturated` | saturation ≥ 75 y aceleración < 0 |
  | `peaking` | saturation ≥ 60 y \|aceleración\| < 0.2 |
  | `accelerating` | aceleración ≥ 0.5 y ≥ 3 fuentes independientes |
  | `emerging` | aceleración > 0, ≤ 3 fuentes independientes y saturation < 40 |
  | `unknown` | datos insuficientes (menos de 5 piezas o una sola fuente) |
  `growth_status` depende de los datos, no de la etapa: `preliminary` = datos insuficientes, `estimated` = ventana anterior vacía, `observed` = dos ventanas con datos. Un `unknown` porque ninguna regla se cumple sí tiene datos (recomendación `find_angle`); un `unknown` por datos insuficientes espera caso.
  `unknown` se evalúa **antes** que las demás: con datos insuficientes no se asigna etapa aunque otra regla se cumpla. Guardar en `lifecycle_reason` qué regla se cumplió, para que la UI y el MCP puedan explicarlo.
- **Para quién importa (estilo SparkToro).** `audience_mix` = proporción de la evidencia de cada `segment`, ponderada por el engagement normalizado. Lectura editorial:
  - Mucho `tech`, poco `business` y fit alto → "todavía no llegó a ejecutivos: traducirlo a negocio".
  - `business` presente y poca evidencia de fuentes latinoamericanas (grupo B de §5, sin contar España) → candidato a **LATAM Opportunity Gap** (`latam_gap = true`).
  - Mucha evidencia de fuentes latinoamericanas → probablemente ya cubierto en la región: buscar otro ángulo.
  - `latam_gap` calcula la proporción LATAM solo con piezas de `region` latinoamericana. El `latam_es` del `audience_mix` mezcla España y Latinoamérica, así que en la UI se rotula "en español".
- **Cross-source:** nº de fuentes **independientes**: un medio o canal cuenta una vez (todas las búsquedas de HN cuentan como una sola fuente). Normalizar métricas dentro de cada fuente. Pendiente: deduplicar notas de prensa replicadas (pares candidatos por embeddings y Jev decide si son la misma nota; mientras tanto, regla de similitud coseno ≥ umbral y fuente distinta).
- **Saturation:** volumen de contenido similar en la ventana reciente **dentro de las fuentes monitoreadas** (decirlo así en la UI).
- **Audience Fit (LLM, salida Pydantic):** el LLM evalúa el tema completo en 6 criterios. Para cada uno devuelve primero la justificación, citando ids de evidencia, y después un nivel entero de 0 a 5 (en ese orden, para que razone antes de puntuar). Recibe como pistas los conteos de las etiquetas de Jev por pieza (p. ej. "8 de 20 piezas muestran un caso real"), que la UI muestra como apoyo. Python combina los 6 niveles con pesos en código → `audience_fit_score`; la UI lo muestra como banda (bajo · medio · alto) junto a los 6 niveles, no como precisión al punto. `actionability_score` sale del criterio 6. Criterios:
  impacto en decisiones empresariales · aplicación real en organizaciones · comprensible para directivos no técnicos · relevancia LATAM · encaje con pilares 30X · convertible en contenido accionable.
- **Opportunity Score (heurística inicial, ajustable):**
  ```
  0.30·momentum + 0.25·audience_fit + 0.20·cross_source + 0.15·(100 − saturation) + 0.10·actionability
  − penalizaciones (datos pobres, fuentes duplicadas, muestra pequeña)
  ```
  La **confianza** se muestra aparte del score. Una oportunidad puede ser alta con evidencia débil.
  El ranking (API y MCP) ordena por `opportunity_score`; los `discard` van después y los temas sin score al final; momentum desempata.
- **`recommendation` (implementada en `intelligence/ranking.py`).** Primera regla que se cumple; `recommendation_reason` guarda en texto la regla cumplida, para que la UI y el MCP la expliquen:
  | Etiqueta | Regla |
  |---|---|
  | `discard` | `lifecycle` es `saturated` |
  | `wait_for_case` | datos insuficientes o `confidence` baja |
  | `wait_for_case` | criterio "aplicación real en organizaciones" ≤ 1: ninguna pieza muestra un caso real |
  | `find_angle` | `lifecycle` es `peaking`, o `unknown` porque ninguna regla se cumple |
  | `find_angle` | `latam_gap = false`: ya hay mucha cobertura en fuentes latinoamericanas |
  | `publish_now` | `emerging` o `accelerating`, y `audience_fit_score` ≥ 60 |
  | `find_angle` | cualquier otro caso (también mientras no haya audience fit) |
  Decidido el 17/10: un fit bajo **no** descarta (con fit < 40 se descartaban 22 de 37 temas, también los de más momentum); da `find_angle` y la UI muestra la banda de fit.
- **"Por qué funcionó" (por pieza):** gancho · tema · formato · estructura · propuesta de valor · credibilidad · timing · autor · rendimiento relativo → hipótesis redactada por el LLM con su limitación explícita. Jev clasifica el gancho y el formato de cada pieza, y Python calcula el *lift* de cada rasgo entre los outliers y el resto del tema (lift ≥ 2 en ≥ 2 outliers = "patrón observado"; si no, "anecdótico"). El LLM redacta la hipótesis a partir de esa tabla. Con pocos outliers por tema casi todo saldrá "anecdótico", y se dice así.
- **Los embeddings agrupan, Jev clasifica cada pieza, Python calcula, el LLM evalúa cada tema y redacta, y Jev verifica lo que escribe el LLM.** Cada modelo usa su SDK oficial; sin capa multi-proveedor. **Sin agentes autónomos.** Excepción: el agente del Radar (`POST /agent`) lo arranca el usuario, solo lee la ejecución servida, sus acciones solo cambian la vista (máx. 8 pasos) y sus citas se validan en Python contra lo que devolvieron sus tools; no pasa por Jev. Ámbito cerrado con `decline`, entradas y salidas saneadas, datos externos delimitados, canario y límites de tiempo, pasos y concurrencia. Resultados cacheados en Postgres.
- **Jev (TypeSafe; lo sugiere el reto): decisiones atómicas sobre piezas.** Modelo de decisión: no genera texto. Responde preguntas tipadas (`noul` sí/no, `choice` opción, `score` nivel) con probabilidades y, en `choice` y `score`, `confidence`. Las preguntas de una llamada corren en paralelo y el `state` se paga una vez, así que cada entidad se evalúa en **una llamada con todas sus preguntas** (una *batería*):
  - **Pieza** (`piece.v3.yaml`, una condición por pregunta): trata de IA (y si el título habla de IA: el filtro de ruido exige "no" en las dos), formato, gancho, lanzamiento e inyección de instrucciones, más pistas para el LLM (uso en organizaciones, público desarrollador, caso real, jerga técnica, contexto LATAM sin España, pilar de 30X). Formato y gancho van repetidos con las opciones en orden inverso para detectar el sesgo hacia la primera opción.
  - **Par:** ¿es la misma nota replicada? → fuentes independientes y saturación.
  - **Verificación:** cada afirmación del LLM contra la evidencia que cita; solo se publica lo respaldado con `confidence` ≥ 0,8 (regla 3). Como la evidencia es título y descripción, el LLM debe ceñirse a lo que dicen.
  - El juicio de conjunto sobre un tema (audience fit) no es de Jev: lee de forma literal, sus niveles de `score` no están calibrados como números y pierde precisión con contextos grandes.
  - Python convierte probabilidades en decisiones con umbrales, y lo incierto se muestra como tal. El texto externo va en `state` y nuestras instrucciones en `questions` (regla 6).
  - SDK `typesafe-sdk` (`AsyncTypeSafeClient`, concurrencia acotada), `JEV_MODEL=jev-1.13.0` fijado, y caché por hash del `state` + versión de la batería + versión del modelo en `jev_judgments`. Cuesta alrededor de 1 $ al mes. En cuanto haya clave, validarlo con 30–50 piezas etiquetadas a mano en `data/evaluations/`. **Acceso:** confirmar hoy la clave; si no la hay antes de las 19:00 ESP, el LLM hace la batería de pieza en lote con el mismo modelo Pydantic, y Jev la sustituye cuando llegue.
  - Preguntas, umbrales, paralelismo, validación y coste: [`docs/jev.md`](docs/jev.md).
- **LLM (evalúa cada tema y redacta):** salidas estructuradas validadas con Pydantic. Funciones: `evaluate_topic` (los 6 criterios del audience fit y, en la misma llamada, el nombre del tema: campo `topic_name`, prompt v2; si falta o pasa de 80 caracteres, el tema conserva el título de su pieza representativa), `explain_opportunity` (`why_it_matters` y `limitations`, en una llamada aparte después del fit y de la recomendación; Python descarta cada afirmación que no cite una pieza enviada o que traiga una cifra que no está en los datos ni en la evidencia; pendiente: la hipótesis de "por qué funcionó"), `recommend_content_angles` y briefs. Devuelve afirmaciones con el id de la evidencia que las respalda: Python comprueba que cada id pertenece al tema y Jev verifica el contenido. Recibe como datos los resultados de Python y Jev. Antes de leer la respuesta hay que comprobar `stop_reason` (rechazo o `max_tokens`). Modelo con `LLM_MODEL`; finalistas: Claude Haiku 5.5 y GPT-6 Luna (mismo precio), con Claude Sonnet 5.5 como techo de calidad para los briefs. Lo decide Melkin probando 3–5 temas reales.
- **Perfil editorial de 30X:** en `data/audiences/30x.yaml` (audiencia, pilares, tono, formatos, qué no encaja). Se define en la Fase 2 revisando a mano los Instagram que compartió 30X: @crece30x y @andresbilbao.

---

## 8. Stack

| Área | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic + asyncpg, httpx, tenacity |
| Datos / ML | Polars, NumPy, scikit-learn · sentence-transformers solo en el job `analyze` (grupo `ml`, torch CPU) |
| IA | **Jev** de TypeSafe (`typesafe-sdk`, versión fijada) para clasificar piezas y verificar · LLM económico vía SDK oficial del proveedor para evaluar temas y redactar |
| Coste | `usage_events` + `data/pricing.yaml` → `GET /costs` (§4) |
| MCP | MCP Python SDK oficial, Streamable HTTP, montado en FastAPI |
| DB | PostgreSQL + pgvector (Supabase en la demo, Docker en local). Se migra con `pg_dump`/`pg_restore` desde la DB local para conservar el historial de snapshots (no repetir el backfill). Supabase y Railway en la misma región |
| Jobs | cron / GitHub Actions |
| Tooling | uv (Python), pnpm (frontend), Ruff, Pyright, pytest + respx, ESLint (`eslint-plugin-vue`), Prettier, `vue-tsc`, Vitest + Vue Testing Library |
| Deploy | Vue (build estático de Vite) → Vercel · API + MCP → Railway · DB → Supabase |

**Fuera de la hackathon:** Kubernetes, Kafka, Redis, Celery, LangChain/LangGraph, LiteLLM, Scrapy, Elasticsearch, GraphQL, microservicios, Streamlit, Next.js / SSR.

**Variables de entorno** (solo en el backend; ver `.env.example`):
`DATABASE_URL`, `YOUTUBE_API_KEY`, `BRAVE_API_KEY`, `SCRAPECREATORS_API_KEY`, `TYPESAFE_API_KEY`, `JEV_MODEL`, `LLM_API_KEY`, `LLM_MODEL`, `CORS_ALLOWED_ORIGINS`, `MCP_PUBLIC_URL`, `APP_ENV`, `DEMO_RUN_ID`.

---

## 9. Frontend

### Stack base (P0)
**Vue 3 + TypeScript + Vite** (SPA con `<script setup>` y Composition API; sin Nuxt: no hace falta SSR y el backend ya es FastAPI) · Tailwind CSS v4 (`@tailwindcss/vite`) · **shadcn-vue** (sobre Reka UI) · `@lucide/vue` · **Apache ECharts + `vue-echarts`** · TanStack Vue Query (`@tanstack/vue-query`) · Vue Router · Pinia (P1, solo si el estado en la URL no alcanza).
El frontend habla **solo con la API REST**, nunca con el MCP. Cliente tipado con `openapi-typescript` + `openapi-fetch`, envuelto en composables de TanStack Vue Query en `src/api/`. Los filtros del Radar se guardan en la URL (query params de Vue Router) para poder compartir enlaces y repetir la demo.

### Vistas y dirección visual
Tres vistas: **Discover** (Radar de burbujas + ranking), **Explore** (evidencia, timeline, `audience_mix`, insights) y **Create** (Content Studio, P1). El detalle de las vistas, la dirección visual y las librerías de UI están en `.claude/rules/frontend.md`, que Claude carga al tocar `frontend/`. Referencias de inspiración para el equipo: `docs/design-resources.md`.

---

## 10. Estructura del repo (objetivo)

```
.
├── CLAUDE.md · DESIGN.md · README.md · docker-compose.yml · .env.example
├── .claude/{commands,agents,templates,plans}   # flujo /spec → /build (§11)
├── .claude/rules/{engineering-standards,frontend}.md   # se cargan al tocar código / frontend
├── backend/
│   ├── app/
│   │   ├── api/routes/          # FastAPI, delgado: solo llama a services
│   │   ├── collectors/          # youtube.py, hackernews.py, rss.py, brave.py
│   │   ├── intelligence/        # embeddings, clustering, velocity, outliers, momentum, lifecycle, saturation, audience_mix, relevance, ranking
│   │   ├── editorial/           # audience.py, analyzer.py, briefs.py, prompts/ (versionados)
│   │   ├── services/            # opportunities, signals, editorial, costs  ← lógica de negocio ÚNICA
│   │   ├── mcp/                 # server.py, tools.py (usa services, nada más)
│   │   ├── db/ models/ schemas/ jobs/
│   │   └── main.py
│   ├── alembic/ · tests/ · pyproject.toml
├── frontend/
│   └── src/{components/{ui,radar,opportunities,evidence,editorial},views,composables,lib,api,types,router}
│       # components/ui = shadcn-vue · api = cliente openapi-fetch + composables de TanStack Vue Query · types/api.ts generado desde OpenAPI
├── data/{fixtures,evaluations,audiences} · data/{sources,pricing}.yaml
└── docs/{brief,architecture,scoring,sources,jev,mcp,design-resources}.md
```

---

## 11. Convenciones

- **Contratos primero.** No se cambia un schema compartido sin avisar en el canal. Fixtures en `data/fixtures/` que cumplen el contrato, para que el frontend avance sin backend.
- Rutas delgadas → `services/` → `intelligence/` o `db/`. Ni la API ni el MCP duplican lógica.
- Las funciones de scoring (velocidad, outliers, lifecycle, audience mix, ranking) son puras, con umbrales como constantes con nombre, y tienen tests en pytest con casos límite (0 snapshots, una sola fuente, ventana anterior vacía). Los conectores se testean con `respx`, no contra la red.
- Prompts versionados en archivos. Salidas del LLM validadas con Pydantic. El contenido externo va delimitado en el prompt.
- Integrar en `main` pronto y a menudo; `main` siempre desplegable. Ramas cortas por área: `data/…`, `intel/…`, `fe/…`.
- Cualquiera del equipo puede mergear a `main` (mismo poder de decisión), con los tests en verde. Los cambios de contrato se avisan en el canal antes de mergear. Claude nunca mergea: abre el PR y la persona decide.
- Español en la UI y en el contenido editorial; inglés en el código.
- **Estándares de código:** [`.claude/rules/engineering-standards.md`](.claude/rules/engineering-standards.md). Comentarios, los necesarios (el *porqué*, nunca el *qué*); docstrings no por defecto.
- **Flujo `/spec` → `/build`** (opcional, para tareas de 1 h o más con un contrato claro: módulos de scoring, endpoints, tools MCP, migraciones). `/spec` investiga, pregunta y escribe un plan en `.claude/plans/`; `/build` lo implementa con `plan-implementer` en contexto limpio y, si toca, lo audita `code-standards-auditor`; `/spec <slug>` retoma un plan bloqueado o a medias. El plan es el estado vivo de su tarea (decisiones, pasos `[HECHO]`, historial, preguntas abiertas). No compensa para iteración visual de UI ni para arreglos rápidos.

---

## 12. Prioridades

**Filtro de valor.** Antes de empezar una tarea, una idea o un PR, la persona o Claude responde estas cuatro preguntas:
1. **¿Qué paso del recorrido de demo (§1) hace funcionar, hace más fiable o hace más convincente con datos reales?** Si no mejora ninguno, se aparca.
2. **¿Le toca ya por prioridad?** O es P0, o el P0 del que depende ya funciona.
3. **¿Se sostiene con datos reales y evidencia enlazada?** Si solo luce con datos de ejemplo, no aporta a la demo.
4. **¿Cabe antes del próximo checkpoint (§13)?** Si no, se recorta a la versión mínima que aporta, o se avisa.

- **P0:** datos reales de YouTube y al menos otra fuente · persistencia, snapshots y backfill de 14 días · clustering · velocidad y aceleración · outliers · etapa de la tendencia · audience mix por segmento · ranking · clasificación por pieza con Jev · audience fit con el LLM · evidencias verificables · dashboard Vue con Radar y detalle · despliegue.
- **P1:** servidor MCP con conexión demostrada · Content Studio (briefs) · timeline · LATAM Opportunity Gap · comparación de oportunidades · coste de operación bajo demanda (`GET /costs` y `get_operating_cost`, sin panel).
- **P2:** Topic Network · animaciones avanzadas · más fuentes · varias audiencias.

**Ningún P2 puede poner en riesgo un P0.**

**Orden de construcción.** No se recorta nada; se decide qué va primero para que la demo funcione aunque un extra no llegue a tiempo:
1. **Núcleo, para el MVP de las 00:30:** datos → embeddings y clustering → scores en Python → clasificación por pieza (Jev, o el LLM en lote) → audience fit y textos con el LLM → API → Radar y detalle en Vue.
2. **Después del núcleo:** verificación de afirmaciones con Jev, *lift* del "por qué funcionó", batería de pares (mientras tanto, la regla de similitud), MCP, briefs, LinkedIn por la API de portabilidad y Brave.

**Fuera de alcance:** scraping de redes cerradas · entrenar modelos · auto-publicación · editor de contenido · multi-tenant · auth avanzada · facturación · causalidad o viralidad presentadas como certeza · igualar la cobertura de las herramientas de referencia (1of10, SparkToro, Exploding Topics…) · una base propia de comportamiento de audiencias · monitorizar todas las redes o todo el mercado LATAM · predicciones con poco historial.

Las ideas sin prioridad asignada están en `docs/brief.md` §9.

---

## 13. Calendario y checkpoints

| Cuándo (ESP / COL) | Checkpoint |
|---|---|
| Sáb 08:30 / 01:30 | Steven: repo, DB y ≥2 fuentes con datos reales + handoff escrito |
| Sáb 10:30–12:00 / 03:30–05:00 | Melkin y Frontend: **contrato `Opportunity` congelado** y perfil 30X |
| Sáb 16:30 / 09:30 | Sync de los tres (30 min): mismo modelo de datos |
| Sáb 20:30 / 13:30 | Primera integración: datos reales → oportunidades → Vue |
| Dom 00:30 / Sáb 17:30 | **MVP P0 end-to-end** (recorrido de demo de §1 hasta el brief) |
| Dom 12:30 / 05:30 | Revisión de MCP y frontend |
| Dom 15:00 / 08:00 | **Feature freeze** |
| Dom 16:30 / 09:30 | **Code freeze** |
| Dom 17:30 / 10:30 | Demo ensayada y grabación de respaldo |
| Dom 18:15 / 11:15 | **Entrega interna** |
| Dom 19:00 / 12:00 | Deadline oficial |

**Criterios de aceptación:** la lista de verificación de la entrega está en `docs/brief.md` §8. Se repasa en la revisión del domingo a las 12:30 y antes del code freeze.

**Guion de demo:** el problema (`docs/brief.md` §1) → el recorrido de demo (§1). El coste medido de operar el radar no es un paso del guion: se responde si alguien lo pregunta, por MCP o con `GET /costs` (sin cifras de ahorro que no hayamos medido).

**La demo usa una ejecución de `analyze` congelada:** los clusters cambian entre ejecuciones, así que el ranking que se enseña es el de una ejecución fijada y revisada a mano. Se fija con `DEMO_RUN_ID` en Railway: la API y el MCP sirven esa ejecución (listado y detalle) aunque el cron siga corriendo `analyze`. Sin valor, sirven la última correcta.

**Entregables:** repo · app desplegada · MCP accesible (o demo local verificada con la limitación documentada) · README · arquitectura · fuentes y limitaciones · algoritmo de priorización · coste de operación medido · presentación · vídeo de respaldo.

---

## 14. Instrucciones para Claude

Actúa como **Technical Project Coordinator y Product Engineering Copilot** de 30X Signal.

- Pasa por el filtro de valor (§12) toda tarea antes de proponerla o empezarla, y di en una línea qué paso del recorrido de demo mejora. Si no pasa el filtro, dilo y propone la versión mínima que sí aporta, o recomienda aparcarla.
- Respeta el ownership de §3 al sugerir tareas o resolver dependencias.
- Prefiere soluciones simples y librerías maduras. Evita la sobreingeniería y las herramientas de la lista de "fuera de la hackathon".
- **Nunca** generes ni muestres datos ficticios como resultados reales. Los mocks viven solo en `data/fixtures/` y se marcan como tales.
- Frontend en Vue 3 + TypeScript con `<script setup>`, Composition API y composables, solo con las librerías de UI y de charts de §9.
- Antes de tocar UI, lee `DESIGN.md`. Antes de tocar contratos, avisa: rompen el trabajo de los demás.
- Avisa pronto si una decisión pone en riesgo un checkpoint.
- Cuando te pidan el estado, constrúyelo a partir de las fuentes, no de la memoria: cabeceras de `.claude/plans/*.plan.md` (owner, prioridad, gate, pasos `[HECHO]`), `gh pr list` y `git log` de `main`. Responde con esta tabla. Una tarea no está hecha porque haya pasado su horario; solo cuenta lo que el equipo confirme:

| Fase actual | Tiempo restante | Estado (En tiempo / En riesgo / Bloqueado) | Steven | Melkin | Frontend | Riesgos | Decisión recomendada |
|---|---|---|---|---|---|---|---|
