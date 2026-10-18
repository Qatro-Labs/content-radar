# 30X Signal

Radar de inteligencia editorial para el reto **30X · Media**. Responde a una pregunta:

> ¿Cuáles son los 10 temas de IA que más están creciendo esta semana, por qué funcionan y cómo los adapta 30X para ejecutivos y equipos de Latinoamérica?

Convierte señales públicas de Internet (YouTube, Hacker News, medios y blogs por RSS, TikTok, Reddit e Instagram) en oportunidades editoriales con evidencia enlazada. Se consultan desde un dashboard en Vue o desde un asistente de IA (Claude, ChatGPT, Grok) vía MCP. Si hay menos de 10 temas con datos suficientes, enseña los que hay: no inventa ninguno.

- **Por qué y para quién:** [docs/brief.md](docs/brief.md)
- **Decisiones, reglas y contratos:** [CLAUDE.md](CLAUDE.md)
- **Arquitectura y coste de operación medido:** [docs/architecture.md](docs/architecture.md) · [docs/costs.md](docs/costs.md)
- **Algoritmo de priorización:** [docs/scoring.md](docs/scoring.md)

## En vivo

| Qué | URL |
|---|---|
| Dashboard (Vercel) | <!-- TODO Melkin: URL de Vercel --> _pendiente_ |
| API REST | https://content-radar-production-9453.up.railway.app/api/v1/opportunities |
| Documentación de la API (OpenAPI) | https://content-radar-production-9453.up.railway.app/docs |
| Servidor MCP | https://content-radar-production-9453.up.railway.app/mcp |
| Estado de las fuentes (piezas por fuente) | https://content-radar-production-9453.up.railway.app/api/v1/sources/status |

## Cómo funciona

```
Colectores (YouTube, HN, RSS, ScrapeCreators) → normalizar, deduplicar y guardar snapshots → PostgreSQL + pgvector
analyze: Jev clasifica cada pieza → embeddings → clustering → scores en Python → audience fit y textos con el LLM
Servicios de dominio (Python) → API REST /api/v1 (dashboard Vue) y servidor MCP /mcp (asistentes), con el mismo ranking
```

- `collect` corre cada 2 h en GitHub Actions y `analyze` corre después de cada recolección correcta. La API y el MCP sirven la última ejecución correcta, o la fijada con `DEMO_RUN_ID`.
- Los scores se calculan en Python, de forma determinista. El LLM evalúa y redacta; no calcula. Jev (TypeSafe) responde preguntas tipadas sobre cada pieza.
- Detalle: [docs/architecture.md](docs/architecture.md) (arquitectura) y [docs/scoring.md](docs/scoring.md) (motor).

## Fuentes

| Fuente | Acceso |
|---|---|
| YouTube | Data API v3 oficial |
| Hacker News | API de Algolia |
| Medios y blogs (tech, negocio, LATAM) | RSS |
| TikTok · Reddit | ScrapeCreators, un proveedor de datos públicos: búsquedas por palabra clave y subreddits |
| Instagram | ScrapeCreators, solo los reels de perfiles elegidos a mano (no descubre temas) |
| LinkedIn · X | **Fuera del MVP.** Sin login no se puede buscar su contenido, y por Google llega poco y tarde. Sus referentes entran por sus canales abiertos (YouTube, newsletters, RSS) |

Solo guardamos metadatos, enlaces y métricas públicas, nunca datos personales. Límites, costes y vías oficiales del roadmap: [docs/sources.md](docs/sources.md). Fuentes dadas de alta: [`data/sources.yaml`](data/sources.yaml).

## Cómo se prioriza

- **Velocidad y aceleración, no popularidad.** Cuenta cuántas piezas nuevas salen al día en los últimos 3 días frente a los 3 anteriores, con un ajuste por volumen. El total de views nunca entra en un score.
- **Outliers.** Una pieza es outlier si rinde 3× o más sobre la referencia de su canal o fuente. El "por qué funcionó" que se deriva de los outliers es una hipótesis, no una causa.
- **Etapa del tema** (emerging → saturated), validación entre fuentes independientes, saturación, **para quién importa** (tech, negocio, español) y **LATAM Opportunity Gap**.
- **Opportunity Score** = 0,30·momentum + 0,25·audience fit + 0,20·cross-source + 0,15·(100 − saturación) + 0,10·accionabilidad. La confianza se muestra aparte. Cada oportunidad trae una recomendación (`publish_now`, `find_angle`, `wait_for_case` o `discard`) junto con la regla que la produjo.

Fórmulas, umbrales y reglas, tal como están en el código: [docs/scoring.md](docs/scoring.md). Jev: [docs/jev.md](docs/jev.md).

## Conectar el MCP

Solo lectura, sin autenticación y con datos públicos. Tiene seis tools: oportunidades en tendencia, análisis de una oportunidad, búsqueda de señales, comparación de audience fit, coste de operación y brief editorial.

```bash
claude mcp add --transport http 30x-signal https://content-radar-production-9453.up.railway.app/mcp
```

Claude web, MCP Inspector y otros clientes, qué clientes se han probado y sus limitaciones: [docs/mcp.md](docs/mcp.md).

## Coste de operación

Cada llamada a una API externa (YouTube, ScrapeCreators, Jev, LLM) queda registrada en `usage_events`, con su coste calculado a partir de [`data/pricing.yaml`](data/pricing.yaml). Ahí está cada precio con su fuente y su fecha. `GET /api/v1/costs` y la tool MCP `get_operating_cost` dan el coste medido y la proyección mensual por separado. La proyección es una estimación. Coste medido y su lectura: [docs/costs.md](docs/costs.md).

## Limitaciones y pendiente

- **En curso:** deduplicación de notas de prensa replicadas (de momento, una regla de similitud) y verificación con Jev de las afirmaciones del LLM.
- La saturación y el LATAM Gap son relativos a las fuentes que monitoreamos, no a todo Internet ni a todo el mercado LATAM.
- El audience fit es una evaluación editorial asistida por IA, no una medición.
- La velocidad de una pieza necesita dos snapshots o más. Sin ellos, la evidencia se marca `estimated` o `preliminary`. El historial empieza el 17/10.
- TikTok y Reddit solo traen el top de la semana en curso, y una pieza solo se vuelve a medir si sigue saliendo en la búsqueda.
- El MCP no tiene autenticación, y su cupo de briefs es compartido por todos los clientes.

## Equipo

| Persona | Área |
|---|---|
| Steven | Data & Backend: conectores, DB, jobs, API, despliegue |
| Melkin | AI & Intelligence: clustering, scoring, Jev, LLM, MCP |
| <!-- TODO Melkin: nombre del frontend lead --> Frontend lead | Product & Frontend: Vue, visualizaciones, UX, demo |

---

## Puesta en marcha

**Requisitos:** Docker · [uv](https://docs.astral.sh/uv/) (instala Python ≥ 3.12 si hace falta) · Node ≥ 20.19 y pnpm 11 (frontend).

### Backend

```bash
docker compose up -d --wait          # Postgres 17 + pgvector en localhost:5433
cp .env.example backend/.env         # completar las claves (tabla de abajo)
cd backend
uv sync                              # todo, incluido torch (grupo ml) para analyze
uv run alembic upgrade head
uv run python -m app.jobs.seed_sources   # carga data/sources.yaml (idempotente; --dry-run para revisar)
uv run python -m app.jobs.collect        # backfill de 14 días; --days 7 para refrescar, --platform youtube para una sola
uv run python -m app.jobs.analyze        # Jev → embeddings → clustering → scores → LLM
uv run uvicorn app.main:app --reload     # http://localhost:8000/health · /docs · /mcp
```

- Sin `YOUTUBE_API_KEY`, `seed_sources` y `collect` se saltan YouTube. Sin `SCRAPECREATORS_API_KEY`, se saltan TikTok, Reddit e Instagram.
- Sin `TYPESAFE_API_KEY`, `LLM_API_KEY` o `LLM_MODEL`, `analyze` corre igual, pero sin filtro de Jev y con el audience fit y el Opportunity Score en `null`.
- La primera ejecución de `analyze` descarga el modelo de embeddings de Hugging Face.
- Solo API y MCP, sin torch: `uv sync --no-group ml` (es lo que instala la imagen de Docker).

Tests y lint:

```bash
cd backend
uv run pytest        # crea y usa radar_test en el mismo servidor (cambiar con TEST_DATABASE_URL)
uv run ruff check . && uv run ruff format .
uv run pyright <archivos>
```

Nueva migración tras cambiar modelos: `uv run alembic revision --autogenerate -m "descripcion"` y `uv run alembic upgrade head`.

### Variables de entorno

Solo en el backend (`backend/.env`; plantilla en [`.env.example`](.env.example)). Ninguna clave va al frontend ni al repo.

| Variable | Para qué | ¿Obligatoria? |
|---|---|---|
| `DATABASE_URL` | Postgres con el driver asyncpg | Sí (por defecto, el Docker local) |
| `YOUTUBE_API_KEY` | Colector de YouTube | Para YouTube |
| `SCRAPECREATORS_API_KEY` | TikTok, Reddit e Instagram (se paga por llamada) | Para esas fuentes |
| `TYPESAFE_API_KEY` · `JEV_MODEL` | Jev: clasificación por pieza (versión fijada, `jev-1.13.0`) | Para `analyze` completo |
| `LLM_API_KEY` · `LLM_MODEL` | Clave de Anthropic y modelo (`claude-haiku-5-5`, con precio en `pricing.yaml`) | Para `analyze` completo, briefs y agente |
| `CORS_ALLOWED_ORIGINS` | Orígenes del frontend, separados por coma | En producción |
| `MCP_PUBLIC_URL` | URL pública exacta del MCP; con otro `Host`, responde 421 | En producción |
| `APP_ENV` | `local`, `ci` o `production` | No |
| `DEMO_RUN_ID` | Ejecución de `analyze` fijada para la demo; vacía = la última correcta | No |
| `BRAVE_API_KEY` | Reservada: Brave aún no tiene colector | No |

Tests: `TEST_DATABASE_URL` (opcional). Frontend: `VITE_API_BASE_URL` y `VITE_USE_FIXTURES` (ver abajo).

### Frontend

```bash
cd frontend
pnpm install
pnpm dev                 # http://localhost:5173 · proxy de /api a http://localhost:8000
```

- **Con datos de ejemplo, sin backend:** `VITE_USE_FIXTURES=true pnpm dev`. Los datos salen de `data/fixtures/opportunities.json` (marcado MOCK), y la cabecera muestra el chip "Datos de ejemplo". Sin el flag, los datos salen solo de la API, y si la API falla se ve el error, nunca los fixtures.
- **API en otro puerto:** `API_DEV_TARGET=http://localhost:8001 pnpm dev`.
- **Tipos de la API (nunca a mano):** con la API levantada, `pnpm gen:api` regenera `src/types/api.ts`. Sin la API, desde un JSON: `OPENAPI_URL=ruta/openapi.json pnpm gen:api`.
- **Antes de un PR:** `pnpm lint && pnpm type-check && pnpm test && pnpm build`.
- **En Vercel:** `frontend/vercel.json` reenvía `/api` a Railway. Para llamar a otra API, se pone su URL en `VITE_API_BASE_URL` (ver `frontend/.env.example`).

## Recolección periódica y despliegue

- **Recolección:** `.github/workflows/collect.yml` corre cada 2 h contra Supabase, con los secrets `DATABASE_URL` (session pooler, puerto 5432), `YOUTUBE_API_KEY` y `SCRAPECREATORS_API_KEY`. ScrapeCreators solo se consulta a las 00 y a las 12 UTC. En local, `scripts/schedule-local.sh install` programa la recolección con launchd (macOS) contra el Docker local.
- **Análisis:** `.github/workflows/analyze.yml` corre después de cada recolección correcta. Necesita además `TYPESAFE_API_KEY` y `LLM_API_KEY`; si falta alguna, no se ejecuta, para no publicar oportunidades sin filtro ni score. Las respuestas de Jev y del LLM se cachean en la DB.
- **API y MCP (Railway):** una sola imagen sin torch (`backend/Dockerfile`, configurada en `railway.json`). Migra al arrancar y usa `/health` como healthcheck. Variables: `DATABASE_URL`, `APP_ENV=production`, `CORS_ALLOWED_ORIGINS`, `MCP_PUBLIC_URL`, `LLM_API_KEY` y `LLM_MODEL` (briefs y agente) y, si se fija, `DEMO_RUN_ID`. Jev solo corre en `analyze`. Railway inyecta `PORT`.
- **DB (Supabase):** activar la extensión `vector` y usar la URL del session pooler con `postgresql+asyncpg://`. Los datos locales se migran con `pg_dump -Fc` / `pg_restore --no-owner --no-acl`, que conserva el historial de snapshots.
- **Imagen en local:** `docker build -f backend/Dockerfile -t radar-api . && docker run -p 8000:8000 --env-file backend/.env radar-api`. Dentro de Docker, la DB local está en `host.docker.internal:5433`.

## Estructura

```
backend/app/
  collectors/    YouTube, HN, RSS, ScrapeCreators → ContentSignal
  intelligence/  embeddings, clustering, velocidad, outliers, lifecycle, ranking, Jev
  editorial/     audience fit, explicaciones y briefs con el LLM (prompts versionados)
  services/      lógica de negocio compartida por la API y el MCP
  api/routes/    FastAPI (delgado)  ·  mcp/  servidor MCP  ·  agent/  agente del Radar
  schemas/ models/ db/ jobs/
frontend/src/    Vue 3 + Vite: Radar, Explorar, expediente del tema y Crear
data/            sources.yaml, pricing.yaml, audiences/, evaluations/, fixtures/ (MOCK)
docs/            brief, fuentes, Jev, MCP
```

## Cómo trabajamos

- Una rama por tarea (`data/…`, `intel/…`, `fe/…`), con PRs pequeños. `main` siempre desplegable. Cualquiera del equipo mergea con los tests en verde; Claude nunca mergea.
- Antes de coger una tarea, pasa el filtro de valor ([CLAUDE.md §12](CLAUDE.md#12-prioridades)). Los cambios de contrato (`Opportunity`, `Evidence`, OpenAPI) se avisan antes, y las decisiones se escriben en `CLAUDE.md`.
- Para tareas de 1 h o más con un contrato claro: `/spec` y después `/build`. Estándares de código: [`.claude/rules/engineering-standards.md`](.claude/rules/engineering-standards.md).
