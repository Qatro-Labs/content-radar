# Coste de operación medido

> Cuánto cuesta operar 30X Signal, medido con lo que registra `usage_events` y no estimado a mano.
> Cómo se registra el consumo: [`architecture.md`](architecture.md) ("Coste de operación") y
> CLAUDE.md §4. Los precios, con su fuente, están en [`data/pricing.yaml`](../data/pricing.yaml).

## Cómo se midió

- **Cuándo:** 17/10/2026 a las 21:57 UTC (23:57 ESP · 16:57 COL).
- **Cómo:** con el servicio que usan `GET /api/v1/costs` y la tool MCP `get_operating_cost`
  (`backend/app/services/costs.py:197`), en una transacción de solo lectura contra Supabase. No se
  ejecutó `collect` ni `analyze` ni se llamó a ninguna API de pago.
- **Desde cuándo hay registro:** el primer evento de `usage_events` es del 17/10 a las 16:53 UTC.
  Lo medido cubre unas **5 horas**, no el gasto total del proyecto: no incluye las recolecciones
  anteriores (los snapshots empiezan el 17/10 a las 02:48 UTC) ni las llamadas de las validaciones
  de `data/evaluations/`.
- `period=7d` y `period=30d` dan exactamente lo mismo: todo el consumo registrado cae dentro de los
  dos periodos.
- Precios revisados el 17/10/2026 (`checked_at` de `data/pricing.yaml`). Ningún consumo quedó sin
  precio conocido.

## Coste medido

Consumo real entre el 17/10 a las 16:53 UTC y el momento de la medición, con el coste calculado al
registrar cada evento.

| Proveedor | Operación | Llamadas | Unidades | Coste medido |
|---|---|---:|---:|---:|
| Jev (TypeSafe) | Batería de pieza (`analyze`) | 3.353 | 7.486.044 tokens de entrada | 0,3144 $ |
| LLM (`claude-haiku-5-5`) | `evaluate_topic`: audience fit (`analyze`) | 155 | 1.552.101 tokens | 0,2331 $ |
| LLM (`claude-haiku-5-5`) | `explain_opportunity`: «por qué importa» (`analyze`) | 120 | 600.955 tokens | 0,1015 $ |
| LLM (`claude-haiku-5-5`) | Agente del Radar (preguntas de usuarios) | 10 | 45.556 tokens | 0,0052 $ |
| ScrapeCreators | Instagram, Reddit y TikTok (`collect`) | 16 | 16 créditos | 0,0301 $ |
| YouTube Data API | `channels.list`, `playlistItems.list`, `videos.list` (`collect`) | 704 | 704 unidades de cuota | 0 $ |
| Hacker News (Algolia) | `search_by_date` (`collect`) | 54 | 54 peticiones | 0 $ |
| RSS | Lectura de feeds (`collect`) | 281 | 281 peticiones | 0 $ |
| **Total medido** | | | | **0,6842 $** |

Por proveedor: Jev 0,3144 $ · LLM 0,3397 $ · ScrapeCreators 0,0301 $ · YouTube, HN y RSS 0 $. El
coste del LLM incluye entrada y salida; el reparto queda en el detalle de cada evento.

**Sin consumo registrado** (no es lo mismo que 0 $):

- **Brave Search:** no tiene colector.
- **Briefs** (`POST /editorial/brief` y la tool MCP `generate_editorial_brief`): no hay ningún
  evento en el periodo.

## Proyección mensual (estimación)

Lo que devuelve el servicio. **Es una estimación, no una medición.**

| Perfil | Fijo (planes, precio de lista) | Variable (proyectado) | Total |
|---|---:|---:|---:|
| `demo` (lo que usamos en la hackathon) | 5,00 $ | 20,53 $ | 25,53 $ |
| `production` (lo que necesitaría 30X para uso comercial) | 50,00 $ | 20,53 $ | 70,53 $ |

Cómo se calcula y por qué hay que leerla con cuidado:

- **Variable:** el coste medido × 30 / días observados, menos el crédito gratis mensual de cada
  proveedor (`backend/app/services/costs.py:153`). Con menos de un día de registro, el servicio
  toma un día como mínimo (`backend/app/services/costs.py:27`). Aquí hubo unas 5 horas, así que los
  20,53 $ son **5 horas de consumo contadas como un día y multiplicadas por 30**.
- **Lo medido incluye carga que no se repite cada día.** Jev hizo 3.353 llamadas, más del doble de
  las ~1.600 piezas del corpus: la clasificación inicial de todo el backfill y, lo más probable, una
  segunda pasada al cambiar de versión de batería (la caché va por versión). Con la caché llena,
  cada `analyze` solo clasifica las piezas nuevas. Lo mismo vale para el LLM, que también cachea
  cada tema. Además, en el momento de la medición había un `analyze` en curso.
- No hacemos una proyección "corregida" a mano: haría falta medir varios días con la caché llena.
- **Fijo:** suma de los precios de lista de los planes de `data/pricing.yaml`. El uso real de
  Railway, Supabase, Vercel y GitHub Actions **no se mide**; tampoco el exceso sobre los 5 $ de uso
  que incluye Railway Hobby.

| Plan | `demo` | `production` | Fuente |
|---|---:|---:|---|
| Railway Hobby | 5,00 $ | 5,00 $ | [railway.com/pricing](https://railway.com/pricing) |
| Supabase | 0 $ (Free) | 25,00 $ (Pro) | [supabase.com/pricing](https://supabase.com/pricing) |
| Vercel | 0 $ (Hobby, no comercial) | 20,00 $ (Pro, por usuario) | [vercel.com/pricing](https://vercel.com/pricing) |
| GitHub Actions | 0 $ (repositorio público) | 0 $ | [docs.github.com](https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions) |

## Precios usados

| Proveedor | Precio | Fuente |
|---|---|---|
| Jev (TypeSafe) | 0,042 $ por millón de tokens de entrada; la salida es gratis | [docs.typesafe.ai/models](https://docs.typesafe.ai/models) |
| LLM `claude-haiku-5-5` | 0,10 $ por millón de tokens de entrada · 0,50 $ por millón de salida | [platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| ScrapeCreators | 0,00188 $ por llamada (47 $ por 25.000 créditos) | [scrapecreators.com](https://scrapecreators.com) |
| YouTube Data API v3 | 0 $ (cupo diario) | [developers.google.com](https://developers.google.com/youtube/v3/getting-started#quota) |
| Hacker News (Algolia) | 0 $ | [hn.algolia.com/api](https://hn.algolia.com/api) |
| RSS | 0 $ | — |
| Brave Search | 5 $ por 1.000 consultas, 5 $ de crédito gratis al mes (sin uso) | [brave.com/search/api](https://brave.com/search/api/) |

El precio del LLM corresponde a un modelo concreto: si `LLM_MODEL` no coincide con el de
`pricing.yaml`, el consumo se registra sin coste (`null`) en vez de con un precio equivocado
(`backend/app/services/costs.py:32`).

## Cómo repetir la medición

- `GET /api/v1/costs?period=7d` (o `30d`) en la API desplegada.
- La tool MCP `get_operating_cost` con `period`.

Las dos devuelven el coste medido por proveedor y la proyección por separado, con sus limitaciones.
No comparamos con el coste de los servicios de scraping que usa 30X hoy: solo tenemos su cifra
("miles de dólares al año"), no una medición nuestra.
