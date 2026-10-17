# content-radar · 30X Signal

Radar de inteligencia editorial para 30X: detecta qué temas de IA están acelerando, por qué funcionan y si encajan con su audiencia de líderes y equipos de Latinoamérica. Convierte señales públicas (YouTube, Hacker News, medios y RSS, más enlaces de LinkedIn, Instagram o TikTok curados a mano) en oportunidades editoriales con evidencia verificable, consultables desde un dashboard o desde asistentes de IA vía MCP.

- **Por qué y para quién:** [docs/brief.md](docs/brief.md)
- **Plan, reglas y contratos:** [CLAUDE.md](CLAUDE.md)

## Cómo trabajamos

1. **Al empezar un bloque:** `git pull` y leer el último handoff del canal.
2. **Antes de coger una tarea:** pasarla por el filtro de valor (`CLAUDE.md` §12). Si no mejora ningún paso del recorrido de demo, se aparca.
3. **Una rama por tarea** (`data/…`, `intel/…`, `fe/…`), PRs pequeños y mergeados pronto. `main` siempre desplegable.
4. **Elegir el modo de trabajo:**
   - Tarea de 1 h o más con un contrato claro (scoring, endpoints, tools MCP, migraciones): `/spec` para planearla y `/build` para implementarla. `/spec <slug>` retoma un plan bloqueado o a medias.
   - Todo lo demás (UI, arreglos, ajustes): directo con Claude, sin plan.
5. **Contratos** (`Opportunity`, `Evidence`, `ContentSignal`, OpenAPI): se avisan en el canal antes de cambiarlos. Los tipos del frontend se generan desde la API, nunca a mano.
6. **Decisiones:** se hablan en el canal y se escriben en `CLAUDE.md` con un PR. Si no está ahí, Claude no la conoce.
7. **Merge:** cualquiera puede mergear a `main` (mismo poder de decisión) con los tests en verde. Claude nunca mergea.
8. **Al cerrar un bloque:** handoff en el canal con el formato de `CLAUDE.md` §3.
9. **Estado:** pregunta a Claude "¿cómo vamos?"; lo calcula a partir de los planes, los PRs y `git log`.
10. **Bloqueado más de 30 min:** avisa, propón una alternativa y cambia de tarea.

Estándares de código: [`.claude/rules/engineering-standards.md`](.claude/rules/engineering-standards.md).

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
frontend/        Vue 3 + Vite (pendiente)
data/            fixtures, evaluaciones y perfiles de audiencia
docs/            brief de producto y documentación de la entrega
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
