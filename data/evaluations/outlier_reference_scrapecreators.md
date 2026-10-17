# Referencia de outliers en TikTok, Instagram y Reddit (ScrapeCreators)

Pregunta (Steven a Melkin, PRs #36 y #41): Instagram y TikTok usan views/día contra la mediana de su perfil o búsqueda; ¿debería TikTok usar el p90, como HN? Y, con el mismo método, ¿qué pasa con Instagram y con Reddit?

**Respuesta corta:** hoy no se puede medir, porque no hay datos. No se cambia ninguna constante.
- **TikTok:** 0 piezas en la DB.
- **Reddit:** 0 piezas en la DB.
- **Instagram:** 20 reels con un solo snapshot cada uno, y ninguno tiene referencia con el código actual.

Cuando lleguen datos, la regla de decisión de más abajo dice qué medir y cuándo cambiar.

## Método

- **Script:** `data/evaluations/outlier_reference_scrapecreators.py`. Solo lee: abre una transacción `READ ONLY` y no llama a ninguna API.
- **Funciones de `analyze`:** usa las mismas, `load_pieces`, `keep_about_ai` con los juicios de Jev en caché y `outlier_ratios`. Para probar otro cuantil sustituye `outliers.MEDIAN`, que `outlier_ratios` lee en cada llamada en todas las plataformas salvo HN.
- **Comparaciones:** mediana, p75 y p90. HN se muestra como control con su p90 actual.
- **Ejecución:** `as_of = 2026-10-17T21:45:00+00:00`, contra la DB compartida (Supabase).

```bash
cd backend
PYTHONPATH=. uv run python ../data/evaluations/outlier_reference_scrapecreators.py \
    --as-of 2026-10-17T21:45:00+00:00
```

## Qué hay en la DB

| Plataforma | Fuentes activas | Piezas cargadas (14 días) | Tras `keep_about_ai` | Snapshots por pieza |
|---|---|---|---|---|
| TikTok | 4 búsquedas | 0 | 0 | — |
| Reddit | 5 subreddits | 0 | 0 | — |
| Instagram | 3 perfiles | 20 | 12 | 1 |
| HN (control) | — | 728 | 632 | — |

- **TikTok y Reddit:** ningún `collect` de la DB compartida los incluye. Las ejecuciones con éxito 17, 21, 22, 24, 27 y 30 no tienen ninguna clave `tiktok:` ni `reddit:` en `per_source`, y su `skipped_platforms` está vacío.
- **`usage_events`:** solo tiene una fila de ScrapeCreators, `/v1/instagram/user/reels`, con 4 llamadas el 17/10 a las 21:27 UTC.
- **Las 167 piezas del PR #36:** se recolectaron en una DB local, no en la compartida.

## Resultados con las reglas actuales (lo que calcularía `analyze`)

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

## Decisión por plataforma

| Plataforma | Referencia actual | Decisión | Motivo |
|---|---|---|---|
| **TikTok** | views/día vs. mediana de la misma búsqueda | **Sin cambio por ahora.** Es la primera candidata a un cuantil alto | n = 0. **Hipótesis:** la referencia es una búsqueda con muchos autores distintos, como en HN, y no un perfil. Si es así, la mediana de la búsqueda mezcla cuentas de cientos de views con cuentas de millones, y es probable que marque demasiados outliers |
| **Instagram** | views/día vs. mediana del mismo perfil | **Se queda la mediana** | Es el caso de YouTube: la referencia es una sola cuenta, sin cola larga entre autores. En lo poco medido, el p90 apaga la señal (0 destacados frente a 1). Lo que la limita es el tamaño de la referencia, no el cuantil |
| **Reddit** | score (`points`) bruto vs. mediana del mismo subreddit | **Sin cambio por ahora** | n = 0. El colector solo guarda el top de la semana con score ≥ 10 (`MIN_REDDIT_SCORE`), así que la referencia ya es la cabeza de la distribución, no la cola larga de HN. Con el p90, un outlier tendría que triplicar el p90 del top semanal, y saldría casi nunca. Como en HN, el score no se ajusta por edad |

### Regla para revisarlo cuando haya datos

Después de las primeras recolecciones de TikTok y Reddit en la DB compartida (al menos 2 corridas), hay que volver a ejecutar el script de arriba con un `as_of` nuevo.
- **Cuándo pasar a un cuantil alto:** si con la mediana la tasa de piezas ≥3× queda muy por encima del 3–6 % de HN (por ejemplo, más del 15 %) y los títulos marcados parecen vídeos normales, la plataforma pasa a un cuantil con nombre, como `HN_REFERENCE_QUANTILE`. Primero se prueba el p75 y después el p90, y se queda el que deje la tasa en ese rango con títulos que de verdad destaquen.
- **Qué dejar escrito:** la tasa medida y la `n`, en el comentario de la constante y en CLAUDE.md §7.

## Para Steven (colectores, no se tocan aquí)

1. **TikTok y Reddit nunca se han recolectado en la DB compartida.** Puede faltar `SCRAPECREATORS_API_KEY` en el cron o en el entorno, o puede que solo se haya lanzado `collect --platform instagram`. Sin esas piezas no hay ni temas ni outliers de esas plataformas.
2. **Instagram, si se quieren ratios antes:** la referencia del perfil se queda corta por la combinación del filtro de Jev, `MIN_REFERENCE_AGE` de 2 días y `MIN_REFERENCE` de 5. El cron recolecta con `--days 7` (`collect.yml`), así que el colector se queda con los reels de la última semana. Una pasada con `--days 14` daría más reels de referencia por perfil, si el endpoint devuelve más de una semana (no está comprobado).
3. **Opción del lado de inteligencia (Melkin), no aplicada:** calcular la referencia de un perfil antes del filtro de Jev. Mide el rendimiento típico de la cuenta, sea cual sea el tema. Es un cambio de diseño de `outlier_ratios` que afecta también a YouTube, así que queda fuera de este PR.
