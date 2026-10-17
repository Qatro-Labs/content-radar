# content-radar · 30X Signal

content-radar ayuda a líderes y equipos en Latinoamérica a producir contenido sobre IA buscando referentes y piezas que estén funcionando en LinkedIn, Instagram, TikTok y YouTube.

Radar de inteligencia editorial: detecta qué temas de IA están acelerando, por qué funcionan y si encajan con la audiencia de 30X, usando solo fuentes públicas. Plan, reglas y contratos en [CLAUDE.md](CLAUDE.md).

## Requisitos

- Docker
- [uv](https://docs.astral.sh/uv/) (instala Python 3.12 automáticamente)
- Node 20+ y pnpm (frontend)

## Backend: puesta en marcha

```bash
docker compose up -d --wait          # Postgres 17 + pgvector en localhost:5433
cp .env.example backend/.env         # completar YOUTUBE_API_KEY, etc.
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.jobs.seed_sources   # carga data/sources.yaml (idempotente)
uv run python -m app.jobs.collect        # backfill 14 días; --days 7 para refrescar métricas
uv run uvicorn app.main:app --reload # http://localhost:8000/health · docs en /docs
```

Tests y lint:

```bash
cd backend
uv run pytest        # usa una DB aparte (radar_test) en el mismo servidor
uv run ruff check . && uv run ruff format .
```

Nueva migración tras cambiar modelos:

```bash
uv run alembic revision --autogenerate -m "descripcion"
uv run alembic upgrade head
```

## Recolección periódica

Cada ejecución de `collect` es un snapshot de métricas; el historial de velocidad depende de que corra cada 2 h.

```bash
scripts/schedule-local.sh install    # launchd en macOS, cada 2 h (status / uninstall)
tail -f backend/logs/collect.log
```

- **Local (ahora):** requiere el Mac encendido y Docker levantado. Si el Mac duerme, la ejecución pendiente corre al despertar, pero ese hueco no se recupera.
- **Compartido (cuando exista Supabase):** `.github/workflows/collect.yml` corre cada 2 h al configurar los secrets `DATABASE_URL` (session pooler, puerto 5432) y `YOUTUBE_API_KEY`. Al activarlo, desinstalar el launchd local para tener una sola base de verdad.

## Estructura

```
backend/app/
  collectors/    conectores (YouTube, HN, RSS…) → ContentSignal
  schemas/       contratos Pydantic (signal.py = contrato del Signal Engine)
  models/        tablas SQLAlchemy
  services/      lógica de negocio compartida por API y MCP
  intelligence/  embeddings, clustering, scoring
  editorial/     análisis y briefs con LLM
  mcp/           servidor MCP
  api/routes/    FastAPI (delgado)
  jobs/          pipelines ejecutables por cron
frontend/        React + Vite (pendiente)
data/            fixtures, evaluaciones y perfiles de audiencia
```

## Estado

| Área | Estado |
|---|---|
| Esqueleto backend, DB y migración inicial | ✅ |
| Tablas `sources`, `content_items`, `metric_snapshots`, `pipeline_runs` | ✅ |
| `store_signals` (dedupe + historial de snapshots) y `GET /api/v1/sources/status` | ✅ |
| Lista inicial de fuentes (`data/sources.yaml`: 38 YouTube · 7 HN · 34 RSS) + loader `app.jobs.seed_sources` | ✅ |
| Collectors HN / RSS / YouTube + backfill 14 días (`app.jobs.collect`) | ✅ datos reales: 737 HN · 346 RSS · 405 YouTube (38 canales) |
| Job periódico de snapshots: launchd local cada 2 h (`scripts/schedule-local.sh`) · GitHub Actions listo para Supabase | ✅ |
