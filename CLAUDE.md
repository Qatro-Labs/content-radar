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
3. **Nunca inventar datos.** No mostrar métricas, crecimiento o conclusiones no observadas como hechos. Si hay 7 oportunidades reales, se muestran 7, no 10.
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

```bash
uv run python -m app.jobs.collect
uv run python -m app.jobs.analyze
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

Patrón común:
```python
class SignalCollector(Protocol):
    async def collect(self) -> list[ContentSignal]: ...
```
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
- **LLM:** vía el **SDK oficial del proveedor**, con un modelo económico y salidas estructuradas. Sin LiteLLM: un modelo y cuatro funciones no justifican la capa, y LiteLLM 1.82.7 y 1.82.8 fueron versiones maliciosas en PyPI (marzo de 2026). Proveedor y modelo: pendiente (Melkin). Funciones concretas (`classify_topic`, `evaluate_audience_fit`, `explain_opportunity`, `recommend_content_angles`). **Sin agentes autónomos.** Resultados cacheados en Postgres.
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
> Decisión del 17/10 (frontend lead): **Vue en lugar de React**, por facilidad de uso. Sustituye a la versión anterior de esta sección.

**Vue 3 + TypeScript + Vite** (SPA con `<script setup>` y Composition API; sin Nuxt: no hace falta SSR y el backend ya es FastAPI) · Tailwind CSS v4 (`@tailwindcss/vite`) · **shadcn-vue** (sobre Reka UI) · `@lucide/vue` · **Apache ECharts + `vue-echarts`** · TanStack Vue Query (`@tanstack/vue-query`) · Vue Router · Pinia (P1, solo si el estado en la URL no alcanza).
El frontend habla **solo con la API REST**, nunca con el MCP. Cliente tipado con `openapi-typescript` + `openapi-fetch`, envuelto en composables de TanStack Vue Query en `src/api/`. Los filtros del Radar se guardan en la URL (query params de Vue Router) para poder compartir enlaces y repetir la demo.

### Tres vistas
1. **Discover (Radar):** gráfico de burbujas de ECharts como protagonista y ranking sincronizado.
   - X = audience fit · Y = momentum · tamaño = evidence strength (normalizado) · color = lifecycle.
   - Cuadrante superior derecho = prioridad. Filtros: periodo, lifecycle, confianza, tema, segmento.
   - En el ranking, cada fila muestra la etapa (badge con `lifecycle_reason` en el tooltip), la aceleración (↑ +80 %) y el nº de outliers. Ordenar por aceleración, no por volumen. Si una métrica falta, la UI lo dice; no la rellena.
   - Avisar de forma visible que "el monitoreo comenzó el 16/10" para que nadie lea los periodos largos como históricos.
2. **Explore (Evidencia):** timeline de velocidad del tema (barras por día, ventana actual vs. anterior) con su confianza · **barra apilada de `audience_mix`** (para quién importa) · Evidence Explorer por plataforma (enlaces originales, fechas, métricas, velocidad y **badge de outlier `6.1×`**; outliers primero) · AI Insights (por qué funciona, patrones, **qué no podemos saber**, encaje con 30X).
3. **Create (Content Studio, P1):** oportunidad + plataforma + objetivo + formato → brief (ángulo, gancho, estructura, evidencias, por qué encaja). Se puede copiar. No es un editor.

P2: Topic Network con Vue Flow (`@vue-flow/core`) y animaciones avanzadas.

### Dirección visual
"Intelligence platform", no un admin dashboard. Tono tecnológico, editorial y minimalista: fondo oscuro, superficies neutras, acentos de color solo para estados (lifecycle o confianza). Los gráficos son el centro de la interfaz. Jerarquía: **score → evolución → explicación → acción**. Microinteracciones suaves al seleccionar y filtrar. Ningún gráfico decorativo.

**Regla de efectos:** como mucho un efecto llamativo por vista (por ejemplo, un fondo sutil en el Radar o number tickers en los scores). El Radar y la evidencia son el producto; los efectos de Inspira UI o Vue Bits no pueden tapar los datos ni bajar el rendimiento.

### Recursos de diseño (de nuestra lista de referencias)

| Uso | Recurso | Cómo lo usamos |
|---|---|---|
| Componentes base | [shadcn-vue](https://www.shadcn-vue.com) | Sistema de componentes principal (se instalan con el CLI de shadcn-vue, el código queda en el repo) |
| Tema / tokens | [tweakcn](https://tweakcn.com/) | Generar las variables CSS del tema oscuro (las mismas que usa shadcn-vue) |
| Ecosistema shadcn | [21st.dev](https://21st.dev), [shadcndesign.com](https://www.shadcndesign.com/) | **Son de React: solo referencia visual** de bloques (sidebars, paneles, tablas); se reimplementan con shadcn-vue. Mapa de LATAM (P2): con ECharts |
| Componentes animados | [Inspira UI](https://inspira-ui.com) (port Vue de Aceternity y Magic UI), [Vue Bits](https://vue-bits.dev) (port de React Bits) | Pocos y con intención (ver regla de efectos). Copiar el componente al repo, no instalar librerías enteras |
| Animación | `<Transition>` / `<TransitionGroup>` de Vue; Motion para Vue (`motion-v`) si no alcanza | Transiciones de panel, selección y entrada de listas |
| Gráficos | ECharts con `vue-echarts` (decidido) | No cambiar de librería de charts durante la hackathon |
| Inspiración UI | [Refero Styles](https://styles.refero.design), [Mobbin](https://mobbin.com), [Godly](https://godly.website), [minimal.gallery](https://minimal.gallery), [60fps.design](https://60fps.design), [beautifului.dev](https://www.beautifului.dev), [component.gallery](https://component.gallery), [navbar.gallery](https://www.navbar.gallery), [cta.gallery](https://www.cta.gallery) | Buscar referencias de dashboards de analítica o inteligencia y de paneles laterales de detalle |
| Principios | [Vercel Design Engineering](https://vercel.com/design/engineer) | Checklist de calidad de interacción |
| Assets | [3dicons.co](https://3dicons.co), [backgrounds.supply](https://www.backgrounds.supply) | Solo para landing o hero si sobra tiempo (P2) |

### Diseñar con agentes (Claude Code)
- Crear un **`DESIGN.md`** en la raíz (formato DESIGN.md de Google Stitch, con paleta, tipografía, espaciado, radios, estados y tono). Referencias: [designmd.supply](https://www.designmd.supply/) y [typeui.sh](https://www.typeui.sh/). Todo agente que toque UI debe leerlo primero.
- Skills útiles: `frontend-design`, [taste-skill](https://www.tasteskill.dev/) e [impeccable](https://impeccable.style/) (para evitar diseño genérico), y [emilkowalski/skills](https://github.com/emilkowalski/skills) (`/apple-design`, `/animation-performance`) para el pulido final.
- Si alguien tiene acceso, el **MCP de Mobbin** sirve para comparar pantallas con referencias reales.
- Antes de instalar una skill o un MCP de terceros, revisar su contenido.

---

## 10. Estructura del repo (objetivo)

```
.
├── CLAUDE.md · DESIGN.md · README.md · docker-compose.yml · .env.example
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
└── docs/{architecture,scoring,sources,mcp}.md
```

---

## 11. Convenciones

- **Contratos primero.** No se cambia un schema compartido sin avisar en el canal. Fixtures en `data/fixtures/` que cumplen el contrato, para que el frontend avance sin backend.
- Rutas delgadas → `services/` → `intelligence/` o `db/`. Ni la API ni el MCP duplican lógica.
- Las funciones de scoring (velocidad, outliers, lifecycle, audience mix, ranking) son puras, con umbrales como constantes con nombre, y tienen tests en pytest con casos límite (0 snapshots, una sola fuente, ventana anterior vacía). Los conectores se testean con `respx`, no contra la red.
- Prompts versionados en archivos. Salidas del LLM validadas con Pydantic. El contenido externo va delimitado en el prompt.
- Integrar en `main` pronto y a menudo; `main` siempre desplegable. Ramas cortas por área: `data/…`, `intel/…`, `fe/…`.
- Español en la UI y en el contenido editorial; inglés en el código.
- **Estándares de código:** [`docs/engineering-standards.md`](docs/engineering-standards.md). Comentarios, los necesarios (el *porqué*, nunca el *qué*); docstrings no por defecto.
- **Flujo `/spec` → `/build`** (opcional, para tareas de 1 h o más con un contrato claro: módulos de scoring, endpoints, tools MCP, migraciones). `/spec` investiga, pregunta y escribe un plan en `.claude/plans/`; `/build` lo implementa con `plan-implementer` en contexto limpio y, si toca, lo audita `code-standards-auditor`; `/spec <slug>` retoma un plan bloqueado o a medias. El plan es el estado vivo de su tarea (decisiones, pasos `[HECHO]`, historial, preguntas abiertas). No compensa para iteración visual de UI ni para arreglos rápidos.

---

## 12. Prioridades

- **P0:** datos reales de YouTube y al menos otra fuente · persistencia, snapshots y backfill de 14 días · clustering · velocidad y aceleración · outliers · etapa de la tendencia · audience mix por segmento · ranking · audience fit · evidencias verificables · dashboard Vue con Radar y detalle · despliegue.
- **P1:** servidor MCP con conexión demostrada · Content Studio (briefs) · timeline · sensor editorial manual · LATAM Opportunity Gap · comparación de oportunidades.
- **P2:** Topic Network · animaciones avanzadas · más fuentes · varias audiencias.

**Ningún P2 puede poner en riesgo un P0.**

**Fuera de alcance:** scraping de redes cerradas · entrenar modelos · auto-publicación · editor de contenido · multi-tenant · auth avanzada · facturación · causalidad o viralidad presentadas como certeza.

---

## 13. Calendario y checkpoints

| Cuándo (ESP / COL) | Checkpoint |
|---|---|
| Sáb 08:30 / 01:30 | Steven: repo, DB y ≥2 fuentes con datos reales + handoff escrito |
| Sáb 10:30–12:00 / 03:30–05:00 | Melkin y Frontend: **contrato `Opportunity` congelado** y perfil 30X |
| Sáb 16:30 / 09:30 | Sync de los tres (30 min): mismo modelo de datos |
| Sáb 20:30 / 13:30 | Primera integración: datos reales → oportunidades → Vue |
| Dom 00:30 / Sáb 17:30 | **MVP P0 end-to-end** (abrir → ver → seleccionar → evidencias → por qué → brief) |
| Dom 12:30 / 05:30 | Revisión de MCP y frontend |
| Dom 15:00 / 08:00 | **Feature freeze** |
| Dom 16:30 / 09:30 | **Code freeze** |
| Dom 17:30 / 10:30 | Demo ensayada y grabación de respaldo |
| Dom 18:15 / 11:15 | **Entrega interna** |
| Dom 19:00 / 12:00 | Deadline oficial |

**Criterios de aceptación:** 100–300 piezas públicas procesadas · ≥2 fuentes automáticas · ranking revisado a mano por el equipo · cada oportunidad con fuentes enlazadas · se distingue observado, estimado y preliminar · un cliente MCP consulta datos reales · funciona desde una sesión limpia (no solo en local).

**Guion de demo:** problema → Radar → detalle con evidencia → brief → la misma consulta desde Claude vía MCP → impacto (sin cifras de ahorro que no hayamos medido).

**Entregables:** repo · app desplegada · MCP accesible (o demo local verificada con la limitación documentada) · README · arquitectura · fuentes y limitaciones · algoritmo de priorización · presentación · vídeo de respaldo.

---

## 14. Instrucciones para Claude

Actúa como **Technical Project Coordinator y Product Engineering Copilot** de 30X Signal.

- Prioriza el MVP. No propongas funcionalidades nuevas salvo que aporten mucho y no pongan en riesgo el deadline.
- Respeta el ownership de §3 al sugerir tareas o resolver dependencias.
- Prefiere soluciones simples y librerías maduras. Evita la sobreingeniería y las herramientas de la lista de "fuera de la hackathon".
- **Nunca** generes ni muestres datos ficticios como resultados reales. Los mocks viven solo en `data/fixtures/` y se marcan como tales.
- Frontend en Vue 3 + TypeScript con `<script setup>`, Composition API y composables. No introduzcas React ni otra librería de UI o de charts además de las de §9.
- Antes de tocar UI, lee `DESIGN.md`. Antes de tocar contratos, avisa: rompen el trabajo de los demás.
- Avisa pronto si una decisión pone en riesgo un checkpoint.
- Cuando te pidan el estado, constrúyelo a partir de las fuentes, no de la memoria: cabeceras de `.claude/plans/*.plan.md` (owner, prioridad, gate, pasos `[HECHO]`), `gh pr list` y `git log` de `main`. Responde con esta tabla. Una tarea no está hecha porque haya pasado su horario; solo cuenta lo que el equipo confirme:

| Fase actual | Tiempo restante | Estado (En tiempo / En riesgo / Bloqueado) | Steven | Melkin | Frontend | Riesgos | Decisión recomendada |
|---|---|---|---|---|---|---|---|
