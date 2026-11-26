# Fuentes oficiales y abiertas — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** sumar tres fuentes de piezas sin scraping: búsquedas de YouTube Shorts, Google News RSS y GDELT. Así el radar deja de depender de TikTok para los outliers de vídeo corto y gana cobertura de noticias en cualquier tema, idioma y país.

**Architecture:** las tres implementan `SignalCollector` (`app/collectors/base.py`) y se dan de alta en `data/sources.yaml` como fuentes de tipo `query`. Dos cambios previos en `intelligence/` hacen que encajen sin inflar las métricas:
- **Independencia por tipo de fuente, no por plataforma.** Una búsqueda cuenta como un único medio por plataforma; hoy eso está escrito a mano para HN y TikTok.
- **Outliers por formato.** Un Short se compara con los Shorts de su canal, no con los vídeos largos.

**Tech Stack:** Python 3.12, httpx, feedparser, tenacity, pytest + respx. Frontend: solo etiquetas, más los tipos regenerados con `openapi-typescript`.

**Spec:** `docs/superpowers/specs/2026-11-26-radar-configurable-design.md` §10 (proyecto previo) y §5.3.

**Fuera de este plan:** las señales de demanda (Google Trends y Wikipedia Pageviews). No son piezas ni evidencia y necesitan un modelo de datos propio. Antes de planearlas hay que decidir cómo se pasa de un tema a un término de búsqueda o a un artículo, y cómo se muestran. Van en un diseño y un plan aparte.

## Global Constraints

- Owner: Steven (colectores, CLAUDE.md §3). Rama nueva desde `main`: `data/official-sources`, en un worktree aparte (en el checkout principal está `fe/ui-audit-polish` con cambios sin commitear). Claude abre el PR y no mergea.
- Los colectores no escriben en la DB. Usan `tenacity` para reintentos de transporte y registran su consumo en `UsageMeter` con un `Provider` propio que tenga entrada en `data/pricing.yaml` (precio `0`, con `source`).
- Ninguna métrica inventada. Google News y GDELT no traen métricas, así que `metrics` queda vacío (todo `None`), igual que RSS.
- Texto externo con `clean_html`, guardado como dato y nunca como instrucción (regla 6).
- **Google News RSS se da de alta con `active: false`.** Steven revisa sus términos de uso antes de activarlo (spec §10).
- Cupo de YouTube: `search.list` cuesta 100 unidades de 10.000 al día. Con 2 recolecciones al día, como máximo **20 búsquedas de Shorts** activas (`MAX_YOUTUBE_SEARCH_SOURCES = 20`, que equivale a 4.000 unidades al día).
- GDELT DOC API: como máximo 1 petición cada 5 segundos (`GDELT_MIN_INTERVAL_SECONDS = 5`).
- Tests sin red (`respx`). Verificación antes de cada commit: `uv run ruff check . && uv run ruff format --check . && uv run pyright <archivos> && uv run pytest`.
- `Platform` crece con dos valores (`google_news`, `gdelt`), y el enum llega al frontend. Hay que avisar en el canal antes de mergear (CLAUDE.md §11).

## Review Focus

1. **Una misma nota llega por RSS y por Google News.** Debe detectarse como réplica, no contar como dos piezas originales. Para que la regla de mismo título funcione, el título de Google News se guarda sin el sufijo " - Medio" (test en la Tarea 4).
2. **GDELT responde con texto plano** (consulta inválida o límite de peticiones) **o con un JSON sin `articles`.** El colector levanta `GDELTError` con un mensaje legible en el primer caso, y devuelve `[]` en el segundo, nunca una excepción de JSON (tests en la Tarea 5).
3. **Un canal con menos de 5 Shorts antiguos.** El ratio de sus Shorts es `None`; no se compara contra sus vídeos largos (test en la Tarea 2).
4. **Una búsqueda de Shorts trae vídeos de más de 3 minutos** (`videoDuration=short` admite hasta 4). Se descartan los de más de `SHORT_MAX_SECONDS` (test en la Tarea 3).
5. **Varias búsquedas de una misma plataforma en un tema.** Cuentan como un único medio para `source_count` y `cross_source_score` (test en la Tarea 1).

---

### Task 1: Independencia de fuentes por tipo

Hoy `outlet_key` trata como un solo medio a HN y TikTok porque están en una lista fija (`SEARCH_PLATFORMS`). Pasa a decidirlo el tipo de fuente: toda fuente `query` cuenta como un único medio por plataforma. El comportamiento actual no cambia, porque las únicas fuentes `query` hoy son HN y TikTok (`seed_sources.py`).

**Files:**
- Modify: `backend/app/intelligence/cross_source.py` (quitar `SEARCH_PLATFORMS`, cambiar `outlet_key`, actualizar el docstring del módulo)
- Modify: `backend/app/intelligence/opportunities.py:247`, `backend/app/intelligence/replicas.py:87` (pasar `p.source_kind.value`)
- Test: `backend/tests/test_intelligence.py` (sustituir las aserciones de las líneas 298–299)

**Interfaces:**
- Produces: `outlet_key(platform: str, source_name: str, source_kind: str) -> str`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize(
    ("platform", "name", "kind", "expected"),
    [
        ("hackernews", "HN · LLM", "query", "hackernews"),
        ("tiktok", "TikTok · agentes", "query", "tiktok"),
        ("youtube", "YouTube · búsqueda · agentes de IA", "query", "youtube"),
        ("youtube", "Fireship", "channel", "youtube:Fireship"),
        ("rss", "Xataka", "feed", "rss:Xataka"),
    ],
    ids=["hn", "tiktok", "yt-search", "yt-channel", "rss"],
)
def test_outlet_key_collapses_searches_per_platform(platform, name, kind, expected):
    assert outlet_key(platform, name, kind) == expected


def test_two_searches_of_one_platform_are_one_outlet():
    assert outlet_key("google_news", "Google News · a", "query") == outlet_key(
        "google_news", "Google News · b", "query"
    )
```

- [ ] **Step 2: Run it and check that it fails**
Run: `uv run pytest tests/test_intelligence.py -k outlet -v` → FAIL (`outlet_key` recibe 2 argumentos).

- [ ] **Step 3: Implement it.** `source_kind == SourceKind.QUERY` → `platform`; otherwise `f"{platform}:{source_name}"`. Update both callers.

- [ ] **Step 4: Run the whole suite**
Run: `uv run pytest` → PASS. `test_build_opportunities` and `test_replicas` should keep passing without changes. If they fail, something changed for HN or TikTok.

- [ ] **Step 5: Commit** — `Decide source independence by source kind instead of a platform list`

### Task 2: Outliers por formato y por tipo de fuente

**Files:**
- Modify: `backend/app/intelligence/opportunities.py`:
  - `Piece` gains `format: ContentFormat = ContentFormat.UNKNOWN`, the last field, so existing test constructors keep working.
  - `outlier_ratios` groups the reference by `(source_id, format)`.
- Modify: `backend/app/services/opportunities.py` (`_to_piece` passes `ContentFormat(item.format)`)
- Modify: `backend/app/intelligence/outliers.py`:
  - `reference_quantile` by kind; `REFERENCE_QUANTILE` becomes `SEARCH_REFERENCE_QUANTILE = 0.9`.
  - Keep the measurement comments for HN and TikTok and add why: "una búsqueda mezcla autores".
- Test: `backend/tests/test_intelligence.py` (the parametrized `test_reference_quantile_per_platform`), `backend/tests/test_build_opportunities.py`

**Interfaces:**
- Consumes: `SourceKind`, `ContentFormat` (`app/schemas/signal.py`)
- Produces: `reference_quantile(kind: SourceKind) -> float`, `Piece.format`

- [ ] **Step 1: Write the failing tests**

```python
# test_intelligence.py
@pytest.mark.parametrize(
    ("kind", "quantile"),
    [(SourceKind.QUERY, 0.9), (SourceKind.CHANNEL, 0.5), (SourceKind.FEED, 0.5)],
    ids=["query-p90", "channel-median", "feed-median"],
)
def test_reference_quantile_per_kind(kind, quantile):
    assert reference_quantile(kind) == quantile

# test_build_opportunities.py — same channel, 6 long videos at 1.000 views/day
# and 6 Shorts at 10.000/day, all older than MIN_REFERENCE_AGE
def test_short_is_compared_with_shorts_of_its_channel():
    # one Short at 30.000/day → ratio 3.0 (against the Shorts' median of 10.000), not 30.0
    assert ratios[short_id] == 3.0

def test_channel_without_enough_shorts_has_no_short_ratio():
    # 10 long videos and 3 Shorts → the Shorts' ratio is None (MIN_REFERENCE = 5)
    assert ratios[short_id] is None
```

- [ ] **Step 2: Run it and check that it fails**
Run: `uv run pytest tests/test_intelligence.py tests/test_build_opportunities.py -v` → the new tests FAIL.

- [ ] **Step 3: Implement** as described in **Files**. The call in `outlier_ratios` becomes `out.reference_quantile(p.source_kind)`.

- [ ] **Step 4: Run the whole suite** → PASS. `test_hn_outlier_ratios_use_p90_of_same_query` should keep passing without changes.

- [ ] **Step 5: Commit** — `Compare outliers within the same format and use p90 for every search source`

### Task 3: Búsquedas de YouTube Shorts

`YouTubeCollector` handles two kinds of source: `channel` (today) and `query` (new). The mapping from video to `ContentSignal` is shared.

**Files:**
- Modify: `backend/app/collectors/youtube.py`:
  - Update the module docstring: `search.list` is now used, with a budget.
  - Extract `_video_signal(video: dict, source: Source, observed_at: datetime) -> ContentSignal | None` from the current loop. It returns `None` for live streams and for pieces the AI filter drops.
  - Add the client method and the branch by `source.kind`.
- Modify: `backend/app/jobs/seed_sources.py`:
  - `YouTubeSearchSeed(_Common)` with `query: str`, `region: str | None`, `language: str | None`.
  - A `youtube_search: list[YouTubeSearchSeed] = []` key in `SeedFile`, plus `_seed_youtube_search`.
  - `external_id = f"{query}|{region or 'global'}"`, `kind=query`, `name=f"YouTube Shorts · {query}" + region`, `config={"query", "region", "language", "ai_filter"}`.
  - It fails with a clear message if there are more than `MAX_YOUTUBE_SEARCH_SOURCES` active seeds.
- Test: `backend/tests/test_collectors.py`, `backend/tests/test_seed_sources.py`

**Interfaces:**
- Produces:
  - `YouTubeClient.search_short_video_ids(query: str, *, since: datetime, region: str | None, language: str | None) -> list[str]`
    - `search.list` with `part=id`, `type=video`, `videoDuration=short`, `publishedAfter`, `maxResults=50`, and `regionCode` and `relevanceLanguage` only if present.
    - One page: 100 units.
  - `MAX_YOUTUBE_SEARCH_SOURCES = 20` in `youtube.py`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_youtube_search_keeps_only_shorts_up_to_three_minutes():
    # respx: search → ids [a, b]; videos → a lasts PT45S, b lasts PT3M30S
    signals = await YouTubeCollector(client).collect(make_search_source("agentes de IA", region="MX"))
    assert [s.external_id for s in signals] == ["a"]
    assert signals[0].format == ContentFormat.SHORT_VIDEO
    assert search_route.calls.last.request.url.params["regionCode"] == "MX"
    assert usage.total(Provider.YOUTUBE) == 100 + 1  # search + videos

def test_seed_rejects_more_youtube_searches_than_the_budget(tmp_path):
    # YAML with 21 active youtube_search entries → ValueError that mentions MAX_YOUTUBE_SEARCH_SOURCES
```

(Use the `UsageMeter` helper that `test_youtube_collects_recent_uploads_with_metrics` already uses to read the units. If it doesn't exist, check `usage.events`.)

- [ ] **Step 2: Run it and check that it fails** → FAIL.
- [ ] **Step 3: Implement** according to **Interfaces**. `test_youtube_collects_recent_uploads_with_metrics` should not change.
- [ ] **Step 4: Run** `uv run pytest tests/test_collectors.py tests/test_seed_sources.py -v` → PASS.
- [ ] **Step 5: Commit** — `Add YouTube Shorts keyword search sources within the daily quota`

### Task 4: Google News RSS

**Files:**
- Create: `backend/app/collectors/google_news.py`
- Modify:
  - `backend/app/schemas/signal.py`: `Platform.GOOGLE_NEWS = "google_news"`.
  - `backend/app/schemas/cost.py`: `Provider.GOOGLE_NEWS = "google_news"`.
  - `data/pricing.yaml`: `google_news: {unit: requests, price_per_unit: 0}`.
  - `backend/app/jobs/collect.py` (`build_collectors`, no API key needed).
  - `backend/app/jobs/seed_sources.py`:
    - `GoogleNewsSeed(_Common)`: `query`, `hl` (e.g. `es-419`) and `gl` (e.g. `CO`).
    - `external_id = f"{query}|{hl}|{gl}"`, `kind=query`, `name=f"Google News · {query} ({gl})"`.
    - `url` = the feed URL.
- Test: `backend/tests/test_collectors.py`, `backend/tests/test_seed_sources.py`

**Interfaces:**
- Produces:
  - `google_news_feed_url(query: str, *, hl: str, gl: str, days: int) -> str`, returning `https://news.google.com/rss/search?q=<query quoted> when:<days>d&hl=<hl>&gl=<gl>&ceid=<gl>:<hl language part>`.
  - `GoogleNewsCollector(client: httpx.AsyncClient, usage: UsageMeter | None = None)`.
- Mapping:
  - `title` without the trailing `" - " + entry.source.title`.
  - `author_name` = `entry.source.title` (the outlet).
  - `url` = `entry.link`, the Google News link that redirects to the outlet.
  - `description` = `clean_html(entry.summary)`.
  - `format=ARTICLE`, empty `metrics`, `language` from `hl` (first two letters).
  - It applies `ai_filter` the same way as `RSSCollector`.

- [ ] **Step 1: Write the failing tests**

```python
def test_google_news_feed_url():
    assert google_news_feed_url("agentes de IA", hl="es-419", gl="CO", days=14) == (
        "https://news.google.com/rss/search?q=agentes+de+IA+when%3A14d&hl=es-419&gl=CO&ceid=CO%3Aes-419"
    )

async def test_google_news_strips_outlet_suffix_and_keeps_outlet_as_author():
    # entry title "Bancolombia lanza agente de IA - El Tiempo", <source>El Tiempo</source>
    assert signal.title == "Bancolombia lanza agente de IA"
    assert signal.author_name == "El Tiempo"
    assert signal.metrics.views is None

async def test_google_news_keeps_title_when_suffix_is_not_the_outlet():
    # title "IA - lo que viene", source "Semana" → the title stays as it is
    assert signal.title == "IA - lo que viene"
```

(Before writing the expected `ceid` value, check what Google News uses by opening a real Google News URL in the browser. If it's `CO:es-419`, put that in the test and in the docstring.)

- [ ] **Step 2: Run it and check that it fails** → FAIL.
- [ ] **Step 3: Implement** following the `RSSCollector` pattern (same `_fetch` with retries and `USER_AGENT`; import them instead of duplicating them).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `Add Google News RSS search collector`

### Task 5: GDELT

**Files:**
- Create: `backend/app/collectors/gdelt.py`
- Modify:
  - `Platform.GDELT = "gdelt"` and `Provider.GDELT = "gdelt"`.
  - `data/pricing.yaml` (`gdelt`, requests, `0`, source `https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/`).
  - `collect.py`.
  - `seed_sources.py`:
    - `GDELTSeed(_Common)`: `query`, `source_country: str | None` (FIPS code, e.g. `CO`) and `source_lang: str | None` (e.g. `spanish`).
    - `external_id = f"{query}|{source_country or 'global'}|{source_lang or 'any'}"`, `kind=query`.
- Test: `backend/tests/test_collectors.py`, `backend/tests/test_seed_sources.py`

**Interfaces:**
- Produces: `GDELTCollector(client: httpx.AsyncClient, usage: UsageMeter | None = None)` and `GDELTError(Exception)`.
- Request: `GET https://api.gdeltproject.org/api/v2/doc/doc` with:
  - `query = <query> [sourcecountry:<c>] [sourcelang:<l>]`
  - `mode=ArtList`, `format=json`, `maxrecords=250`, `timespan=<backfill_days>d`, `sort=DateDesc`.
- Pacing: one `asyncio.Lock` per instance, plus `time.monotonic()`, so requests from the same collector are at least `GDELT_MIN_INTERVAL_SECONDS` apart. The job runs sources in parallel (`CONCURRENCY = 8`).
- Mapping:
  - `external_id` = url (sha256 if > 512, like `rss._external_id`).
  - `published_at` from `seendate` (`%Y%m%dT%H%M%SZ`, UTC).
  - `author_name` = `domain`, `format=ARTICLE`, `description=None`, empty `metrics`.
  - `language` from a constant `GDELT_LANGUAGE = {"Spanish": "es", "English": "en", "Portuguese": "pt"}`; any other value gives `None`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_gdelt_maps_articles_without_metrics():
    # respx: {"articles": [{"url": "...", "title": "...", "seendate": "20261125T143000Z",
    #          "domain": "eltiempo.com", "language": "Spanish", "sourcecountry": "Colombia"}]}
    assert s.published_at == datetime(2026, 11, 25, 14, 30, tzinfo=UTC)
    assert s.author_name == "eltiempo.com" and s.language == "es"
    assert s.metrics.views is None

async def test_gdelt_without_articles_returns_empty():
    # respx: {} → []

async def test_gdelt_plain_text_error_raises_readable_error():
    # respx: 200 with text "Please limit requests to one every 5 seconds" → GDELTError with that text

async def test_gdelt_spaces_requests_from_one_collector(monkeypatch):
    # two collect() calls in parallel; patch the sleep and check it was called with ≈ GDELT_MIN_INTERVAL_SECONDS
```

- [ ] **Step 2: Run it and check that it fails** → FAIL.
- [ ] **Step 3: Implement it.**
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `Add GDELT DOC search collector with request pacing`

### Task 6: Alta de fuentes, frontend y documentación

**Files:**
- Modify: `data/sources.yaml`. Add these entries and comment on the ownership and the quota:
  - **`youtube_search`:** 6 entries, the HN queries already in use, in Spanish with `region: MX/CO/AR` and in English global.
  - **`google_news`:** 6 entries (the same topics, `es-419` for CO, MX and AR, plus `en-US`), all with `active: false` (Global Constraints).
  - **`gdelt`:** 4 entries (Spanish in CO, MX and AR, plus English global).
  - Segments: Spanish and Latin American searches → `latam_es` with their `region`; English → `tech`.
- Modify: `frontend/src/lib/evidenceFormat.ts` (`PLATFORM_LABEL`: `google_news: 'Google News'`, `gdelt: 'GDELT'`), after regenerating `frontend/src/types/api.ts` with `pnpm gen:api` (with the API running on :8000).
- Modify:
  - `docs/sources.md`: one section per source, with limits (no metrics in Google News and GDELT; Shorts by duration; quota).
  - `CLAUDE.md` §5: three rows in the sources table.
  - `CLAUDE.md` §7: the outliers note for YouTube searches (p90) and Shorts by format.

- [ ] **Step 1:** `uv run python -m app.jobs.seed_sources --dry-run` → validates the YAML with no errors.
- [ ] **Step 2:** `uv run python -m app.jobs.seed_sources` against the local DB, then `uv run python -m app.jobs.collect --platform youtube --platform gdelt --days 3` → no errors in the new sources, and pieces from both.
- [ ] **Step 3:** In `frontend/`: `pnpm gen:api && pnpm lint && pnpm type-check && pnpm test && pnpm build` → PASS. `type-check` fails until both labels are added; that's the expected red.
- [ ] **Step 4:** `uv run python -m app.jobs.analyze` locally → the run finishes, and in the output the new platforms appear in the evidence of some topic. Note in the PR how many pieces each source brought and how many outliers came from Shorts.
- [ ] **Step 5: Commit** — `Seed Shorts, Google News and GDELT sources and document them`
- [ ] **Step 6:** Push the branch and open a PR against `main` with the results from step 4, plus the note that Google News stays inactive until its terms are reviewed. Don't merge.
