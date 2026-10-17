# 30X Signal — Guía de desarrollo

> Radar de inteligencia editorial para el reto **30X · Media** (Hackathon, 17–18 oct 2026).
> Este archivo es la fuente de verdad para el equipo y para Claude Code. Si una decisión cambia, se actualiza aquí.

**Deadline oficial:** domingo 18 oct · **12:00 COL / 19:00 ESP** · Entrega interna: **11:15 COL / 18:15 ESP**.

---

## 1. Qué construimos

**Pregunta que el prototipo debe responder:**
> "¿Cuáles son los 10 temas de IA que más están creciendo esta semana, por qué funcionan y cómo los adapta 30X para ejecutivos y equipos de Latinoamérica?"

**Propuesta de valor:** 30X Signal convierte señales públicas de Internet en oportunidades editoriales **verificables y accionables**, accesibles desde un dashboard visual (Vue) o desde asistentes de IA (Claude, ChatGPT, Grok) vía **MCP**.

Flujo del producto: **Señal → Tendencia → Oportunidad → Evidencia → Contenido recomendado**

**Recorrido de demo** (lo que una persona hace de punta a punta; mide el valor de cada tarea, ver §12):
abrir el Radar → elegir una oportunidad → revisar scores y evidencia → entender por qué importa → obtener un brief → repetir la consulta desde un asistente vía MCP.

**Brief de producto:** [`docs/brief.md`](docs/brief.md) explica el problema de 30X, el usuario frente a la audiencia, el mapa de capacidades, qué podemos afirmar con los datos y la lista de verificación de la entrega. Léelo antes de planear una tarea o decidir su alcance, al redactar texto que lee una persona (UI, prompts del LLM, respuestas MCP, pitch) y al revisar la entrega.

Las tres preguntas del reto y cómo las respondemos:

| Pregunta del reto | Nuestra respuesta |
|---|---|
| ¿Cómo se detecta una tendencia temprana? | **Velocidad y aceleración, no popularidad** + **etapa del ciclo de vida** (emerging → saturated) + validación cruzada entre fuentes + saturación + **LATAM Opportunity Gap** |
| ¿Por qué funcionó una pieza? | **Outliers**: piezas que rinden ≥3× la mediana de su canal o fuente. Análisis contrastivo outlier vs. resto del tema por dimensiones observables (gancho, formato, tema, estructura, timing, autor, rendimiento relativo). Se presenta como **hipótesis**, nunca como causalidad |
| ¿Es relevante para nuestra audiencia? | **Para quién importa:** mezcla de audiencias que impulsan el tema (tech, negocio, LATAM en español) + **Audience Fit** estructurado (rúbrica 0–5 × 6 criterios) contra el perfil editorial de 30X |

---

## 2. Reglas no negociables

1. **Solo contenido público. Nada de datos personales.** Guardamos metadatos, enlaces y métricas públicas, no copias completas ni datos de usuarios.
2. **Nada de scraping de LinkedIn / Instagram / TikTok** ni nada detrás de un login o que viole ToS. Esas plataformas entran solo por **curación manual** (sensor editorial, ver §5).
3. **Nunca inventar datos.** No mostrar métricas, crecimiento o conclusiones no observadas como hechos. Si hay 7 oportunidades reales, se muestran 7, no 10. Un dato ausente se muestra como "no disponible", nunca como 0.
4. **El LLM explica, no calcula.** Los scores se calculan en Python, de forma determinista y reproducible. El LLM interpreta y redacta.
5. **Distinguir siempre el tipo de evidencia:** `observed` (≥2 mediciones) · `estimated` (1 medición vs. referencia) · `preliminary` (aparece, sin aceleración demostrada).
6. **El texto recuperado de Internet es no confiable** (riesgo de prompt injection). Va al LLM como dato, delimitado, nunca como instrucción.
7. **Prioridades del equipo, en orden:** Functional > perfect · Reliable > impressive · Integrated > isolated · Shipped > unfinished.

---

## 3. Equipo y ownership

| Persona | Ubicación | Área | Responsable de |
|---|---|---|---|
| **Steven** | Colombia (UTC-5) | Data & Backend | Conectores, normalización, snapshots, DB, jobs, API base, despliegue backend |
| **Melkin** | España (UTC+2) | AI & Intelligence | Embeddings, clustering, scoring, audience fit, análisis editorial LLM, **servidor MCP** |
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
Collectors (YouTube, HN, RSS, Brave, Manual)
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
| YouTube | Data API v3 (`search.list` ≈ 100 llamadas/día; preferir `playlistItems` de canales conocidos) | Vídeos, Shorts, views/likes/comments | P0 |
| Hacker News | Algolia HN Search API | Conversaciones tempranas | P0 |
| RSS / medios tech y LATAM | `feedparser` + `httpx` | Artículos y lanzamientos | P0 |
| Brave Search | API (crédito mensual gratis) | Descubrimiento web | P1 |
| Google Trends | RSS público | Demanda de búsqueda | P2 |
| LinkedIn / Instagram / TikTok | **Solo curación manual** (pegar URL + etiquetas + métricas vistas) · TikTok Creative Center como referencia | Referencias editoriales y formatos | P1 |

**Dos niveles de sensores:**
- **Automáticos:** YouTube, HN, RSS, Brave.
- **Editoriales:** el equipo o la comunidad de 30X pegan enlaces y los etiquetan. Es el enfoque de "comunidad como sensor" que propone el brief.

Todos los conectores implementan el protocolo `SignalCollector` (`backend/app/collectors/base.py`) y no escriben en la DB: la persistencia la hace `services.signals.store_signals`.
Cada `source` lleva un **`segment`** (`tech` | `business` | `latam_es`), además de `language` y `region`. Se asigna a mano al dar de alta la fuente o el canal; es lo que permite responder "para quién importa".

**Backfill:** al dar de alta una fuente, traer también las piezas de los últimos 14 días (HN y YouTube lo permiten por fecha). La velocidad **del tema** se calcula con `published_at` y no necesita snapshots, así que sí habrá tendencia de varios días el domingo. La velocidad **de una pieza** sí necesita snapshots.

Cada colector devuelve `ContentSignal` normalizado (fuente, url, título/descr., `published_at`, `observed_at`, formato, idioma, métricas públicas). Usar `tenacity` para reintentos. **Empezar a guardar snapshots cuanto antes**: sin historial no hay crecimiento observado.

Grupos para el **LATAM Opportunity Gap**:
- **A (internacional):** HN, YouTube y medios en inglés.
- **B (español / LATAM empresarial):** canales y medios de referencia, por ejemplo los perfiles de 30X y Andrés Bilbao.

---

## 6. Modelo de datos y contratos

**Tablas:** `sources` (con `segment`), `content_items`, `metric_snapshots` (siempre tabla aparte), `topics`, `topic_content`, `embeddings`, `opportunities` (+ historial de scores), `opportunity_evidence`, `audience_profiles`, `editorial_briefs`, `editorial_feedback`, `pipeline_runs`.

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
  "audience_fit_score": 0-100,
  "cross_source_score": 0-100,
  "saturation_score": 0-100,
  "actionability_score": 0-100,
  "opportunity_score": 0-100,
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
`Evidence`: `url`, `source`, `platform`, `segment`, `title`, `published_at`, `metrics` (tal cual la fuente), `observed_at`, `language`, `velocity` (tasa por hora con su unidad, p. ej. `views/h` o `points/h`; `null` sin 2 snapshots), `outlier_ratio`, `is_outlier`.

**Fuente de verdad de tipos:** modelos Pydantic → OpenAPI → `openapi-typescript` → `frontend/src/types/api.ts`. No escribir tipos TS a mano para la API.

**Endpoints REST (`/api/v1`):**
```
GET  /opportunities              ?period=24h|7d|30d&lifecycle=&confidence=&topic=
GET  /opportunities/{id}
GET  /opportunities/{id}/evidence
GET  /opportunities/{id}/timeline
GET  /topics · GET /signals · GET /sources/status
POST /editorial/brief            {opportunity_id, platform, goal, format}
POST /editorial/feedback
POST /signals/manual             (sensor editorial: URL + etiquetas)
GET  /health
```

**Herramientas MCP (solo lectura):** `get_trending_opportunities`, `analyze_opportunity`, `search_content_signals`, `compare_audience_fit`. P2: `generate_editorial_brief`. Las respuestas son estructuradas y siempre incluyen evidencia (URLs). Nunca exponer SQL arbitrario ni el sistema de archivos.

---

## 7. Motor de inteligencia y scoring

- **Embeddings:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (ES/EN en el mismo espacio, necesario para el LATAM Gap). Se calculan **solo en el job `analyze`** (GitHub Actions o local, torch CPU en un grupo de dependencias `ml`). La imagen de la API y el MCP no instala torch: sus búsquedas usan texto en Postgres, no embeddings de la consulta.
- **Clustering:** scikit-learn sobre similitud coseno. Nada de BERTopic ni HDBSCAN salvo que sobre tiempo. LLM solo para **nombrar** clusters.
- **Velocidad, no popularidad.** El total de views, likes o puntos **nunca** entra directamente en un score: solo tasas normalizadas dentro de cada fuente.
  - *Pieza:* `Δmétrica / Δhoras` entre snapshots (`views/h` en YouTube, `points/h` y `comments/h` en HN). Sin 2+ snapshots → `growth_status = estimated | preliminary`.
  - *Tema:* `velocity` = piezas nuevas por día en la ventana actual (por `published_at`, ponderadas por fuentes independientes).
  - *Aceleración:* `(v_actual − v_anterior) / max(v_anterior, 1)`. Ventanas por defecto de 3 días (actual) vs. 3 días (anterior), configurables. Es la señal principal de tendencia temprana.
  - `momentum_score` = combinación normalizada de velocidad del tema, aceleración y outliers. Pesos en `intelligence/momentum.py`.
- **Outliers (por pieza, estilo 1of10).** `outlier_ratio = rendimiento ajustado por edad / mediana de su referencia`.
  - YouTube: `views / días desde la publicación` vs. la mediana de los últimos 20 vídeos del mismo canal (`playlistItems` + `videos.list`).
  - HN: puntos vs. la mediana de las stories de la misma búsqueda y el mismo periodo.
  - `≥ 3×` = outlier, `≥ 2×` = destacado. Con una sola observación es `estimated`.
  - Los outliers alimentan el "por qué funcionó": el LLM compara outliers con las piezas normales **del mismo tema** (análisis contrastivo) en lugar de describir una pieza aislada.
- **Etapa de la tendencia (`lifecycle`, determinista, en `intelligence/lifecycle.py`).** Primera regla que se cumple, con umbrales ajustables:
  | Etapa | Regla inicial |
  |---|---|
  | `saturated` | saturation ≥ 75 y aceleración < 0 |
  | `peaking` | saturation ≥ 60 y \|aceleración\| < 0.2 |
  | `accelerating` | aceleración ≥ 0.5 y ≥ 3 fuentes independientes |
  | `emerging` | aceleración > 0, ≤ 3 fuentes independientes y saturation < 40 |
  | `unknown` | datos insuficientes (menos de 5 piezas o una sola fuente) |
  Guardar en `lifecycle_reason` qué regla se cumplió, para que la UI y el MCP puedan explicarlo.
- **Para quién importa (estilo SparkToro).** `audience_mix` = proporción de la evidencia de cada `segment`, ponderada por el engagement normalizado. Lectura editorial:
  - Mucho `tech`, poco `business` y fit alto → "todavía no llegó a ejecutivos: traducirlo a negocio".
  - `business` presente y `latam_es` bajo → candidato a **LATAM Opportunity Gap** (`latam_gap = true`).
  - `latam_es` alto → probablemente ya cubierto en la región: buscar otro ángulo.
- **Cross-source:** nº de fuentes **independientes** (deduplicar notas de prensa replicadas). Normalizar métricas dentro de cada fuente.
- **Saturation:** volumen de contenido similar en la ventana reciente **dentro de las fuentes monitoreadas** (decirlo así en la UI).
- **Audience Fit (LLM, salida Pydantic):** 6 criterios de 0 a 5, cada uno con su justificación:
  impacto en decisiones empresariales · aplicación real en organizaciones · comprensible para directivos no técnicos · relevancia LATAM · encaje con pilares 30X · convertible en contenido accionable.
- **Opportunity Score (heurística inicial, ajustable):**
  ```
  0.30·momentum + 0.25·audience_fit + 0.20·cross_source + 0.15·(100 − saturation) + 0.10·actionability
  − penalizaciones (datos pobres, fuentes duplicadas, muestra pequeña)
  ```
  La **confianza** se muestra aparte del score. Una oportunidad puede ser alta con evidencia débil.
- **"Por qué funcionó" (por pieza):** gancho · tema · formato · estructura · propuesta de valor · credibilidad · timing · autor · rendimiento relativo → hipótesis redactada por el LLM con su limitación explícita.
- **LLM:** vía el **SDK oficial del proveedor**, con salidas estructuradas (Pydantic). Sin capa multi-proveedor: un modelo y cuatro funciones no la justifican. El modelo se elige con `LLM_MODEL`. Proveedor y modelo: pendiente (Melkin). Funciones concretas (`classify_topic`, `evaluate_audience_fit`, `explain_opportunity`, `recommend_content_angles`). **Sin agentes autónomos.** Resultados cacheados en Postgres.
- **Perfil editorial de 30X:** en `data/audiences/30x.yaml` (audiencia, pilares, tono, formatos, qué no encaja). Se define en la Fase 2 a partir de los Instagram de 30X y Andrés Bilbao.

---

## 8. Stack

| Área | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic + asyncpg, httpx, tenacity |
| Datos / ML | Polars, NumPy, scikit-learn · sentence-transformers solo en el job `analyze` (grupo `ml`, torch CPU) |
| LLM | SDK oficial del proveedor + modelo económico con structured outputs |
| MCP | MCP Python SDK oficial, Streamable HTTP, montado en FastAPI |
| DB | PostgreSQL + pgvector (Supabase en la demo, Docker en local). Se migra con `pg_dump`/`pg_restore` desde la DB local para conservar el historial de snapshots (no repetir el backfill). Supabase y Railway en la misma región |
| Jobs | cron / GitHub Actions |
| Tooling | uv (Python), pnpm (frontend), Ruff, Pyright, pytest + respx, ESLint (`eslint-plugin-vue`), Prettier, `vue-tsc`, Vitest + Vue Testing Library |
| Deploy | Vue (build estático de Vite) → Vercel · API + MCP → Railway · DB → Supabase |

**Fuera de la hackathon:** Kubernetes, Kafka, Redis, Celery, LangChain/LangGraph, LiteLLM, Scrapy, Elasticsearch, GraphQL, microservicios, Streamlit, Next.js / SSR.

**Variables de entorno** (solo en el backend; ver `.env.example`):
`DATABASE_URL`, `YOUTUBE_API_KEY`, `BRAVE_API_KEY`, `LLM_API_KEY`, `LLM_MODEL`, `CORS_ALLOWED_ORIGINS`, `MCP_PUBLIC_URL`, `APP_ENV`.

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
│   │   ├── collectors/          # youtube.py, hackernews.py, rss.py, brave.py, manual.py
│   │   ├── intelligence/        # embeddings, clustering, velocity, outliers, momentum, lifecycle, saturation, audience_mix, relevance, ranking
│   │   ├── editorial/           # audience.py, analyzer.py, briefs.py, prompts/ (versionados)
│   │   ├── services/            # opportunities, signals, editorial  ← lógica de negocio ÚNICA
│   │   ├── mcp/                 # server.py, tools.py (usa services, nada más)
│   │   ├── db/ models/ schemas/ jobs/
│   │   └── main.py
│   ├── alembic/ · tests/ · pyproject.toml
├── frontend/
│   └── src/{components/{ui,radar,opportunities,evidence,editorial},views,composables,lib,api,types,router}
│       # components/ui = shadcn-vue · api = cliente openapi-fetch + composables de TanStack Vue Query · types/api.ts generado desde OpenAPI
├── data/{fixtures,evaluations,audiences}
└── docs/{brief,architecture,scoring,sources,mcp,design-resources}.md
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

- **P0:** datos reales de YouTube y al menos otra fuente · persistencia, snapshots y backfill de 14 días · clustering · velocidad y aceleración · outliers · etapa de la tendencia · audience mix por segmento · ranking · audience fit · evidencias verificables · dashboard Vue con Radar y detalle · despliegue.
- **P1:** servidor MCP con conexión demostrada · Content Studio (briefs) · timeline · sensor editorial manual · LATAM Opportunity Gap · comparación de oportunidades.
- **P2:** Topic Network · animaciones avanzadas · más fuentes · varias audiencias.

**Ningún P2 puede poner en riesgo un P0.**

**Fuera de alcance:** scraping de redes cerradas · entrenar modelos · auto-publicación · editor de contenido · multi-tenant · auth avanzada · facturación · causalidad o viralidad presentadas como certeza · igualar la cobertura de las herramientas de referencia (1of10, SparkToro, Exploding Topics…) · una base propia de comportamiento de audiencias · monitorizar todas las redes o todo el mercado LATAM · predicciones con poco historial.

Las ideas sin prioridad asignada están en `docs/brief.md` §8.

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

**Criterios de aceptación:** la lista de verificación de la entrega está en `docs/brief.md` §7. Se repasa en la revisión del domingo a las 12:30 y antes del code freeze.

**Guion de demo:** el problema (`docs/brief.md` §1) → el recorrido de demo (§1) → el impacto (sin cifras de ahorro que no hayamos medido).

**Entregables:** repo · app desplegada · MCP accesible (o demo local verificada con la limitación documentada) · README · arquitectura · fuentes y limitaciones · algoritmo de priorización · presentación · vídeo de respaldo.

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
