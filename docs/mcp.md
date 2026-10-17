# Servidor MCP de 30X Signal

El servidor MCP permite hacer las mismas consultas del dashboard desde un asistente de IA (Claude,
ChatGPT o Grok): "¿qué temas de IA están despegando esta semana y con qué evidencia?". Lee las
oportunidades que ya calculó `analyze` a través de `backend/app/services/`: no recalcula nada, no
hace scraping y no busca en la web. El ranking es el mismo que el del dashboard y la ejecución
servida también: `DEMO_RUN_ID` o, si no está fijada, la última ejecución correcta.

- **Endpoint:** `<URL de la API>/mcp`, sin barra final. Por ejemplo `http://localhost:8000/mcp` en
  local.
- **Transporte:** Streamable HTTP con el SDK oficial (`mcp` 2.3.0), sin estado y con respuestas
  JSON (sin SSE). Va montado en la misma app ASGI que la API REST (`backend/app/main.py`).
- **Sin autenticación:** solo expone datos públicos de solo lectura (metadatos, URLs y métricas
  públicas). Ver "Limitaciones".
- **Briefs:** `generate_editorial_brief` llama a un LLM. Tiene un límite de **20 briefs por hora y
  100 por día, compartido por todos los clientes MCP**, y genera como mucho 2 a la vez. Es un cupo
  aparte del de `POST /editorial/brief`.

Código: `backend/app/mcp/server.py` (servidor, transporte y límites), `backend/app/mcp/tools.py`
(tools) y `backend/app/schemas/mcp.py` (contrato de salida).

## Tools

Todas devuelven salida estructurada (JSON Schema en `tools/list`). Un `null` significa "no
disponible", nunca 0. Los errores previstos (sin datos, id desconocido, límite alcanzado, brief
rechazado) llegan como resultado con `is_error` y un mensaje en español que se puede mostrar.

| Tool | Para qué | Argumentos | Devuelve |
| --- | --- | --- | --- |
| `get_trending_opportunities` | Las oportunidades de la semana, en el orden del ranking del dashboard | `limit` (1–10, 10 por defecto), `lifecycle`, `confidence`, `topic` (texto del tema, ≤ 60) | Periodo (`7d`: ventanas de 3 + 3 días), `generated_at`, `matched`, y por oportunidad: etapa y su regla, `growth_status`, aceleración, scores, confianza, recomendación y hasta 3 URLs de evidencia (outliers primero). Nunca rellena: si hay 7, devuelve 7 |
| `analyze_opportunity` | El detalle de una oportunidad | `opportunity_id` (`opp_…`) | La `Opportunity` completa (por qué importa, limitaciones, desglose del score, los 6 criterios de encaje), hasta 15 evidencias (outliers primero) con el total y el timeline |
| `search_content_signals` | Buscar piezas concretas en las fuentes que monitoreamos | `query` (2–80 caracteres; todas las palabras deben aparecer), `platform`, `segment`, `days` (1–30, 14 por defecto), `limit` (1–20, 10 por defecto) | URL, fuente, fechas, métricas del último snapshot y los ids de las oportunidades del ranking que contienen cada pieza |
| `compare_audience_fit` | Comparar el encaje con la audiencia de 30X | `opportunity_ids` (de 2 a 5) | Por oportunidad, en el orden pedido: fit 0–100 y sus 6 criterios (nivel, justificación y URLs), `audience_mix`, `latam_gap`, recomendación y confianza |
| `get_operating_cost` | Coste de operar el radar | `period` (`7d` o `30d`) | Lo mismo que `GET /api/v1/costs`: coste medido por proveedor y la proyección mensual (una estimación) |
| `generate_editorial_brief` | Convertir una oportunidad en un brief | `opportunity_id`, `platform`, `goal`, `format` (opciones cerradas, sin texto libre) | Lo mismo que `POST /api/v1/editorial/brief`: ángulo, gancho, estructura, puntos clave con sus URLs y por qué encaja |

`generate_editorial_brief` es la única tool marcada como no de solo lectura: escribe en la caché de
briefs y en el registro de consumo (`usage_events`). El consumo del LLM queda registrado también
cuando el brief no supera la comprobación de evidencia.

### Preguntas de ejemplo

Las de `docs/validation-plan.md` §9:

| El usuario escribe | Tool |
| --- | --- |
| "¿Qué temas de IA están despegando esta semana?" | `get_trending_opportunities` |
| "¿Por qué está creciendo X? ¿Es fiable?" | `analyze_opportunity` |
| "¿Qué encaja mejor con ejecutivos LATAM, A o B?" | `compare_audience_fit` |
| "¿Hay algo sobre agentes en YouTube?" | `search_content_signals` |
| "Dame un post de LinkedIn sobre X para CEOs" | `generate_editorial_brief` |

## Despliegue (Steven)

- Fijar en Railway **`MCP_PUBLIC_URL=https://<dominio-de-railway>/mcp`**, con el dominio público
  exacto. El servidor solo acepta peticiones cuyo `Host` sea ese dominio o uno local (protección
  contra DNS rebinding del SDK): **sin `MCP_PUBLIC_URL`, el MCP responde 421 a todo** aunque el
  healthcheck pase. Si la URL está mal escrita (sin `https://`, por ejemplo), la app no arranca y
  el error nombra la variable.
- `DEMO_RUN_ID` fija la misma ejecución de `analyze` para el dashboard y para el MCP.
- No hace falta nada más: la imagen y el puerto son los de la API.

## Conectar un cliente

Sustituir `<dominio>` por el dominio público de la API en Railway, o usar
`http://localhost:8000/mcp` contra la API en local
(`uv run uvicorn app.main:app --port 8000` desde `backend/`).

### Claude Code

```bash
claude mcp add --transport http 30x-signal https://<dominio>/mcp
# Para tenerlo en todos los proyectos:
claude mcp add --transport http --scope user 30x-signal https://<dominio>/mcp
```

Para comprobarlo, `claude mcp list` en la terminal y `/mcp` dentro de Claude Code. Documentación:
<https://code.claude.com/docs/en/mcp>.

### Claude (web y escritorio): conector personalizado

Se añade como conector personalizado con la URL `https://<dominio>/mcp`. Los pasos no se
comprobaron en esta rama: ver la documentación oficial de conectores personalizados (remote MCP)
en el Centro de ayuda de Claude, <https://support.claude.com>. El conector necesita la URL pública:
no llega a `localhost`.

### MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

En la interfaz, transporte **Streamable HTTP** y URL `http://localhost:8000/mcp`. El comando sale
del plan y no se comprobó contra la documentación oficial del Inspector en esta rama:
<https://modelcontextprotocol.io/docs/tools/inspector>.

### ChatGPT y Grok

Sin probar y sin documentar aquí: cada uno conecta servidores MCP remotos a su manera. Ver su
documentación oficial.

### Cliente Python del SDK

```python
from mcp import Client

async with Client("http://localhost:8000/mcp") as c:
    tools = await c.list_tools()
    result = await c.call_tool("get_trending_opportunities", {"limit": 3})
```

## Clientes probados

Solo se afirma en la demo lo que está como "probado" (`docs/brief.md` §7).

| Cliente | Contra | Estado |
| --- | --- | --- |
| Cliente Python del SDK (`mcp` 2.3.0) | `localhost` con la DB local | Probado (2026-10-17, Claude Code para Melkin): las seis tools en `tools/list`, el listado en el mismo orden que `GET /api/v1/opportunities`, búsqueda y coste; `Host` ajeno → 421 |
| Cliente Python del SDK (`mcp` 2.3.0) | Railway (`https://content-radar-production-9453.up.railway.app/mcp`) | Probado (2026-10-18 ~00:40 ESP): las seis tools en `tools/list`; `get_trending_opportunities` con el mismo orden que `GET /api/v1/opportunities` (opp_1272, opp_1157, opp_519) y `top_evidence` con URLs; `analyze_opportunity` con 13 evidencias; `get_operating_cost` y `search_content_signals` responden. `generate_editorial_brief` no se llamó (gasta LLM) |
| Claude Code | Railway | Documentado, sin probar |
| Claude (conector personalizado) | Railway | Documentado, sin probar |
| MCP Inspector | `localhost` | Documentado, sin probar |
| ChatGPT | — | Sin probar |
| Grok | — | Sin probar |

## Limitaciones

- **Sin autenticación.** Cualquiera con la URL puede consultar el radar. Son datos públicos de solo
  lectura; los conectores de Claude piden OAuth para autenticar, y eso queda fuera de la hackathon.
- **Cupo de briefs compartido.** El MCP no tiene una IP de cliente fiable, así que el límite de
  briefs es uno para todos los clientes: un solo cliente abusivo puede agotar el cupo diario.
- **Búsqueda por palabras, no semántica.** `search_content_signals` exige que todas las palabras
  aparezcan en el título o la descripción; el corpus mezcla inglés y español, así que conviene
  probar la palabra en los dos idiomas. Solo busca en las piezas ya recolectadas de las fuentes
  activas. Puede devolver piezas más nuevas que la ejecución servida: `opportunity_ids` dice cuáles
  entran en el ranking.
- **LinkedIn y X no se monitorean**, e Instagram solo por perfiles concretos: no descubre temas
  (CLAUDE.md §2, regla 2).
- Saturación y LATAM Gap son relativos a las fuentes que monitoreamos; el audience fit es una
  evaluación editorial asistida por IA, no una medición.
