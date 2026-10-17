# Referencia de outliers en TikTok, Instagram y Reddit (ScrapeCreators)

Pregunta (Steven a Melkin, PRs #36 y #41): Instagram y TikTok usan views/día contra la mediana de su perfil o búsqueda; ¿debería TikTok usar el p90, como HN? Y, con el mismo método, ¿qué pasa con Instagram y con Reddit?

## Medición con datos reales (17/10, 22:04 UTC)

**Respuesta corta:**
- **TikTok pasa al p90** (`TIKTOK_REFERENCE_QUANTILE = 0.9` en `intelligence/outliers.py`). Con la mediana, un 33 % de los vídeos salía ≥3×; con el p90, un 6 %, el rango de HN.
- **Reddit se queda con la mediana.** Da un 10 % ≥3×, por debajo del umbral del 15 % que fijamos antes de medir.
- **Instagram no cambia.** Sigue sin referencia: ningún perfil llega a 5 reels con 2+ días.
- **YouTube no se toca aquí**, pero da un 19 % con la mediana: queda anotado más abajo.

El ranking cambia en el próximo `analyze`. La ejecución fijada con `DEMO_RUN_ID` no cambia hasta que alguien vuelva a ejecutar `analyze` y fije la nueva.

### Método

- **Script:** `data/evaluations/outlier_reference_scrapecreators.py`. Solo lee: abre una transacción `READ ONLY`, no llama a ninguna API y usa los juicios de Jev en caché.
- **Mismas reglas que `analyze`:** `load_pieces`, `keep_about_ai`, `_performance` (views/día en TikTok, Instagram y YouTube; score en Reddit y HN), `MIN_REFERENCE_AGE` y `MIN_REFERENCE`. Solo cambia el cuantil, que el script pasa explícito.
- **Dos modos de referencia**, para que la decisión valga con y sin el PR #48:
  - `main`: la referencia son las piezas que pasan el filtro de Jev, como hace `analyze` hoy.
  - `#48`: la referencia son todas las piezas cargadas; el ratio solo se da a las que pasan el filtro.
- **Ejecución**, contra la DB compartida (Supabase):

```bash
cd backend
PYTHONPATH=. uv run python ../data/evaluations/outlier_reference_scrapecreators.py \
    --as-of 2026-10-17T22:04:38+00:00
```

### Qué hay en la DB

| Plataforma | Cargadas (14 días) | Tras `keep_about_ai` |
|---|---|---|
| TikTok | 74 | 72 |
| Reddit | 105 | 101 |
| Instagram | 20 | 12 |
| YouTube | 409 | 372 |
| HN (control) | 736 | 638 |

### Tasas (modo `main`)

`n` = piezas con métrica tras el filtro de Jev. Los porcentajes son sobre las piezas con referencia.

| Plataforma | Referencia | n | Sin referencia | ≥2× | ≥3× |
|---|---|---|---|---|---|
| **TikTok** | mediana | 72 | 0 | 29 (40 %) | 24 (33 %) |
| **TikTok** | p75 | 72 | 0 | 14 (19 %) | 12 (17 %) |
| **TikTok** | **p90 (elegido)** | 72 | 0 | 5 (7 %) | **4 (6 %)** |
| **Reddit** | **mediana (se queda)** | 101 | 0 | 18 (18 %) | **10 (10 %)** |
| Reddit | p75 | 101 | 0 | 11 (11 %) | 6 (6 %) |
| Reddit | p90 | 101 | 0 | 4 (4 %) | 2 (2 %) |
| HN (control) | mediana | 638 | 1 | 185 (29 %) | 145 (23 %) |
| HN (control) | p75 | 638 | 1 | 114 (18 %) | 99 (16 %) |
| HN (control) | **p90 (actual)** | 638 | 1 | 49 (8 %) | **33 (5 %)** |
| YouTube | mediana (actual) | 372 | 43 | 89 (27 %) | 61 (19 %) |
| YouTube | p75 | 372 | 43 | 48 (15 %) | 31 (9 %) |
| YouTube | p90 | 372 | 43 | 26 (8 %) | 20 (6 %) |
| Instagram | cualquiera | 12 | 12 | — | — |

El control de HN reproduce lo documentado en CLAUDE.md §7: un 22–23 % con la mediana y un 5 % con el p90.

**Con el PR #48 (referencia = todas las cargadas)** TikTok da exactamente lo mismo: las 2 piezas que quita Jev tienen menos de 2 días y no entraban en la referencia. Reddit se mueve una pieza: 10 (10 %) con la mediana, 7 (7 %) con el p75 y 3 (3 %) con el p90. HN da 22 % / 15 % / 5 %. La decisión vale con o sin #48.

### Referencias por fuente (modo `main`)

Views/día en TikTok, score en Reddit. "En referencia" = piezas con edad suficiente (2 días en TikTok, 6 h en Reddit).

| Fuente | Piezas | En referencia | Mediana | p75 | p90 | Máx / mediana |
|---|---|---|---|---|---|---|
| TikTok · AI agents | 24 | 10 | 1.723 | 23.224 | 51.762 | 40,0 |
| TikTok · AI for business | 17 | 9 | 1.710 | 4.598 | 15.007 | 14,4 |
| TikTok · agentes de IA (CO) | 15 | 12 | 4.347 | 24.115 | 102.747 | 27,9 |
| TikTok · inteligencia artificial empresas (MX) | 16 | 13 | 7.033 | 92.989 | 127.267 | 86,2 |
| r/AI_Agents | 22 | 22 | 22 | 38 | 52 | 3,8 |
| r/ClaudeAI | 17 | 17 | 1.204 | 1.577 | 2.641 | 13,7 |
| r/LocalLLaMA | 20 | 20 | 688 | 830 | 1.258 | 6,6 |
| r/OpenAI | 22 | 22 | 304 | 471 | 1.054 | 5,3 |
| r/artificial | 20 | 20 | 240 | 474 | 2.829 | 14,3 |

Ninguna búsqueda ni subreddit se queda sin referencia. Los perfiles de Instagram siguen por debajo de 5 (4, 3 y 2 reels con 2+ días).

### TikTok: por qué el p90

- **Muchos autores por búsqueda.** 63 autores distintos en 72 vídeos. Es el caso de HN, no el de un canal de YouTube: la búsqueda mezcla cuentas de cientos de views/día con cuentas de cien mil, y el máximo de una búsqueda llega a ser 14–86 veces su mediana.
- **El p75 no basta.** Deja un 17 %, por encima del umbral del 15 %. El p90 deja un 6 %, en el 3–6 % de HN.
- **Lo que marca cada opción.** Con la mediana salen 24 vídeos, y muchos son virales genéricos dentro de la búsqueda, por ejemplo:
  - 45,6× · agentes de IA (CO) · "Este hombre estaba en una entrevista de trabajo y se dió cuenta que lo estaba entrevistand…"
  - 36,2× · AI agents · "ECC just replaced your entire engineering team with 64 AI agents that plan, build, secure,…"
  - 26,2× · inteligencia artificial empresas (MX) · "El aire se le está saliendo a la Burbuja de las IAs #IA #MemoriaRam #Gamer #Gaming #PCGame"
  - 21,3× · inteligencia artificial empresas (MX) · "En esta entrevista de trabajo nadie tenía demasiadas ganas de trabajar. La empresa utilizó…"

  Con el p90 quedan 4, que superan por 3× o más a casi todo lo de su búsqueda:
  - 5,3× · inteligencia artificial empresas (MX) · "#Loret. Anthropic advierte que la inteligencia artificial podría replicarse sola en dispos…"
  - 3,7× · agentes de IA (CO) · "¿Los actores se quedarán sin trabajo por la IA? La inteligencia artificial alcanza un real…"
  - 3,5× · AI for business · "claude code seo loop: give it your site, type /loop, and it audits one page, writes a chan…"
  - 3,4× · agentes de IA (CO) · "🤖 Un youtuber envió a su inteligencia artificial a una entrevista laboral con otra IA 👉 El…"
- **Views/día frente a edad es justo aquí.** Todos los vídeos tienen menos de 7 días (p10/p50/p90 de edad: 0,5 / 2,2 / 5,4 días; máximo 6,9). Las medianas de views/día por edad son parecidas: 2.884 (0–2 días, n = 28), 4.432 (2–4 días, n = 28) y 2.217 (4–7 días, n = 16). Los vídeos de menos de 2 días no salen inflados: el mínimo de un día de `age_adjusted` los frena, y además no entran en la referencia.
- **Limitación.** Cada búsqueda tiene solo 9–13 vídeos con edad suficiente para la referencia, así que su p90 queda cerca del segundo valor más alto, y un solo viral lo mueve. Por eso los ratios de TikTok se leen como orden de magnitud, no como precisión.

### Reddit: por qué se queda la mediana

- **No cumple la regla.** Con la mediana sale un 10 % ≥3×. Está por encima del 3–6 % de HN, pero por debajo del 15 % que fijamos como umbral antes de tener datos (sección de abajo). Cambiar ahora sería ajustar el umbral al resultado.
- **La referencia ya es la cabeza.** El colector guarda el top de la semana con score ≥ 10, así que la distribución por subreddit es estrecha (máximo entre 3,8 y 14 veces la mediana, frente a 14–86 en TikTok). El p90 deja 2 posts en 101, y apaga la señal.
- **Lo que se ve raro no lo arregla el cuantil.** Entre los 10 marcados con la mediana hay posts de humor: "The Internet is wild😂😂" (13,1×), "R.I.P." (12,2×) y "Damage control (by @CaptainInsightX)" (14,7×). Siguen marcados con el p75, y "Damage control" incluso con el p90. Son *standouts* reales de su subreddit en score; el problema es de contenido (memes que Jev deja pasar como "trata de IA"), no de referencia. Los otros sí se leen como noticias que destacan:
  - 14,8× · r/artificial · "Claude Opus 5.5 decompiles a PS2-era game overnight, and hundreds of them now run in brows…"
  - 6,7× · r/LocalLLaMA · "It's been too quiet on the other side of the Pacific"
  - 5,5× · r/OpenAI · "Fields Medalist on the OpenAI Math Release"
  - 4,7× · r/artificial · "A solo developer rebuilt Word, Excel and PowerPoint as free open-source apps using Claude…"
- **Cuándo revisarlo.** Si con más corridas la tasa con la mediana pasa del 15 %, se prueba el p75 (hoy daría un 6–7 %).

### YouTube: anotado, sin cambio

Con la mediana del canal sale un 19 % ≥3× (61 de 329 con referencia); con el p75, un 9 %; con el p90, un 6 %. La referencia es un solo canal, y muchos de los marcados son lanzamientos o episodios que de verdad destacan en su canal ("Introducing GPT-6 in ChatGPT with Intelligent UI" en OpenAI, 26,5×). Pero la referencia no es la de CLAUDE.md §7 (los últimos 20 vídeos del canal), sino los vídeos del canal cargados en los últimos 14 días que pasan el filtro de Jev. Cambiar YouTube movería todo el ranking de la demo y queda fuera de este análisis: hay que revisarlo aparte.

### Para Steven

- Nada que cambiar en los colectores por esta decisión.
- Instagram sigue sin referencia (4, 3 y 2 reels con 2+ días por perfil); lo de `--days 14` de la sección de abajo sigue abierto.

## Medición anterior, sin datos (sustituida; 17/10, 21:45 UTC)

> Esta sección es la del PR #45 original, con `as_of = 2026-10-17T21:45:00+00:00`, cuando la DB compartida no tenía piezas de TikTok ni de Reddit. La sustituye la medición de arriba. Se conserva por la regla de revisión, que es la que se aplicó. Dos cosas ya no valen: el script ya no sustituye `outliers.MEDIAN` (pasa el cuantil explícito), y el punto 1 de "Para Steven" está resuelto, porque TikTok y Reddit ya se recolectan en la DB compartida.

**Respuesta corta (entonces):** hoy no se puede medir, porque no hay datos. No se cambia ninguna constante.
- **TikTok:** 0 piezas en la DB.
- **Reddit:** 0 piezas en la DB.
- **Instagram:** 20 reels con un solo snapshot cada uno, y ninguno tiene referencia con el código actual.

Cuando lleguen datos, la regla de decisión de más abajo dice qué medir y cuándo cambiar.

### Método

- **Script:** `data/evaluations/outlier_reference_scrapecreators.py`. Solo lee: abre una transacción `READ ONLY` y no llama a ninguna API.
- **Funciones de `analyze`:** usa las mismas, `load_pieces`, `keep_about_ai` con los juicios de Jev en caché y `outlier_ratios`. Para probar otro cuantil sustituye `outliers.MEDIAN`, que `outlier_ratios` lee en cada llamada en todas las plataformas salvo HN.
- **Comparaciones:** mediana, p75 y p90. HN se muestra como control con su p90 actual.
- **Ejecución:** `as_of = 2026-10-17T21:45:00+00:00`, contra la DB compartida (Supabase).

```bash
cd backend
PYTHONPATH=. uv run python ../data/evaluations/outlier_reference_scrapecreators.py \
    --as-of 2026-10-17T21:45:00+00:00
```

### Qué hay en la DB

| Plataforma | Fuentes activas | Piezas cargadas (14 días) | Tras `keep_about_ai` | Snapshots por pieza |
|---|---|---|---|---|
| TikTok | 4 búsquedas | 0 | 0 | — |
| Reddit | 5 subreddits | 0 | 0 | — |
| Instagram | 3 perfiles | 20 | 12 | 1 |
| HN (control) | — | 728 | 632 | — |

- **TikTok y Reddit:** ningún `collect` de la DB compartida los incluye. Las ejecuciones con éxito 17, 21, 22, 24, 27 y 30 no tienen ninguna clave `tiktok:` ni `reddit:` en `per_source`, y su `skipped_platforms` está vacío.
- **`usage_events`:** solo tiene una fila de ScrapeCreators, `/v1/instagram/user/reels`, con 4 llamadas el 17/10 a las 21:27 UTC.
- **Las 167 piezas del PR #36:** se recolectaron en una DB local, no en la compartida.

### Resultados con las reglas actuales (lo que calcularía `analyze`)

| Plataforma | Referencia | n con métrica | Sin referencia | ≥2× | ≥3× |
|---|---|---|---|---|---|
| TikTok | mediana / p75 / p90 | 0 | — | — | — |
| Reddit | mediana / p75 / p90 | 0 | — | — | — |
| Instagram | mediana / p75 / p90 | 12 | 12 | — | — |
| HN (control) | p90 (actual) | 632 | 1 | 46 (7 %) | 33 (5 %) |

El control de HN reproduce el rango documentado en CLAUDE.md §7: un 3–6 % de outliers con el p90.

### Por qué ningún reel de Instagram tiene referencia

Un reel necesita 5 reels de referencia en su perfil (`MIN_REFERENCE`). Cada uno de ellos tiene que tener al menos 2 días (`MIN_REFERENCE_AGE`) y haber pasado el filtro de Jev. A las 21:45 UTC del 17/10, los perfiles quedan así:

| Perfil | Reels cargados | Tras `keep_about_ai` | Con 2+ días (referencia) | views/día de la referencia: mediana · p90 · máx. |
|---|---|---|---|---|
| @evolving.ai | 12 | 6 | 4 | 348.180 · 645.437 · 670.272 |
| @platzi | 5 | 4 | 3 | 2.243 · 2.529 · 2.601 |
| @therundownai | 3 | 2 | 2 | 4.911 · 6.976 · 7.492 |

- **El PR #41 no cuadra con el código.** Dice que @evolving.ai ya tiene sus 5 reels de referencia, pero con el filtro de Jev y la edad mínima le quedan 4.
- **El filtro de Jev retrasa los ratios.** Quitó 6 de los 12 reels de @evolving.ai, porque es un perfil amplio (Tesla, cine, videojuegos). En un perfil así hace falta el doble de reels para llegar a 5 de referencia. Por eso tarda Instagram en dar ratios, más que por el cuantil elegido.

### Hipótesis: sin la edad mínima (no es lo que calcula `analyze`)

El script repite el cálculo con un `as_of` lejano. `outlier_ratios` solo usa `as_of` para la edad mínima de la referencia, así que solo se levanta esa regla y `MIN_REFERENCE` sigue aplicándose.

| Plataforma | Referencia | n | Sin referencia | ≥2× | ≥3× |
|---|---|---|---|---|---|
| Instagram | mediana | 12 | 6 | 1 de 6 | 0 de 6 |
| Instagram | p75 | 12 | 6 | 0 de 6 | 0 de 6 |
| Instagram | p90 | 12 | 6 | 0 de 6 | 0 de 6 |

- **Con referencia:** solo los 6 reels de @evolving.ai, con 5 de referencia cada uno. @platzi y @therundownai siguen por debajo de `MIN_REFERENCE`.
- **El único destacado** con la mediana es "🤖💀 A man sent his AI to a job interview, only to find out the company had sent an AI inter…", a 2,1×. Con el p75 o el p90 no queda ninguno.
- **Nota cualitativa, por debajo de `MIN_REFERENCE`:** el reel de @platzi "Sin cámaras, sin actores, sin estadio. Solo IA ⚽" tiene 660.422 views. Sus otros 4 reels tienen entre 5.246 y 12.666. Se lee como un *standout* de verdad, pero el código no le da ratio, porque al perfil le faltan reels.

Con muestras así, ningún cuantil se puede calibrar. Lo único que muestran es que, dentro de un perfil, el p90 apaga la señal.

### Decisión por plataforma

| Plataforma | Referencia actual | Decisión | Motivo |
|---|---|---|---|
| **TikTok** | views/día vs. mediana de la misma búsqueda | **Sin cambio por ahora.** Es la primera candidata a un cuantil alto | n = 0. **Hipótesis:** la referencia es una búsqueda con muchos autores distintos, como en HN, y no un perfil. Si es así, la mediana de la búsqueda mezcla cuentas de cientos de views con cuentas de millones, y es probable que marque demasiados outliers |
| **Instagram** | views/día vs. mediana del mismo perfil | **Se queda la mediana** | Es el caso de YouTube: la referencia es una sola cuenta, sin cola larga entre autores. En lo poco medido, el p90 apaga la señal (0 destacados frente a 1). Lo que la limita es el tamaño de la referencia, no el cuantil |
| **Reddit** | score (`points`) bruto vs. mediana del mismo subreddit | **Sin cambio por ahora** | n = 0. El colector solo guarda el top de la semana con score ≥ 10 (`MIN_REDDIT_SCORE`), así que la referencia ya es la cabeza de la distribución, no la cola larga de HN. Con el p90, un outlier tendría que triplicar el p90 del top semanal, y saldría casi nunca. Como en HN, el score no se ajusta por edad |

### Regla para revisarlo cuando haya datos

Después de las primeras recolecciones de TikTok y Reddit en la DB compartida (al menos 2 corridas), hay que volver a ejecutar el script de arriba con un `as_of` nuevo.
- **Cuándo pasar a un cuantil alto:** si con la mediana la tasa de piezas ≥3× queda muy por encima del 3–6 % de HN (por ejemplo, más del 15 %) y los títulos marcados parecen vídeos normales, la plataforma pasa a un cuantil con nombre, como `HN_REFERENCE_QUANTILE`. Primero se prueba el p75 y después el p90, y se queda el que deje la tasa en ese rango con títulos que de verdad destaquen.
- **Qué dejar escrito:** la tasa medida y la `n`, en el comentario de la constante y en CLAUDE.md §7.

### Para Steven (colectores, no se tocan aquí)

1. **TikTok y Reddit nunca se han recolectado en la DB compartida.** Puede faltar `SCRAPECREATORS_API_KEY` en el cron o en el entorno, o puede que solo se haya lanzado `collect --platform instagram`. Sin esas piezas no hay ni temas ni outliers de esas plataformas.
2. **Instagram, si se quieren ratios antes:** la referencia del perfil se queda corta por la combinación del filtro de Jev, `MIN_REFERENCE_AGE` de 2 días y `MIN_REFERENCE` de 5. El cron recolecta con `--days 7` (`collect.yml`), así que el colector se queda con los reels de la última semana. Una pasada con `--days 14` daría más reels de referencia por perfil, si el endpoint devuelve más de una semana (no está comprobado).
3. **Opción del lado de inteligencia (Melkin), no aplicada:** calcular la referencia de un perfil antes del filtro de Jev. Mide el rendimiento típico de la cuenta, sea cual sea el tema. Es un cambio de diseño de `outlier_ratios` que afecta también a YouTube, así que queda fuera de este PR.
