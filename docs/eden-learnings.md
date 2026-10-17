# Qué aprendemos de Eden (sin depender de Eden)

> Análisis del 17/10/2026. Decisión del equipo: **no usamos Eden como fuente de datos**. Solo copiamos ideas de método que encajan con nuestras reglas (CLAUDE.md §2 y §7).

## 1. De dónde sale este análisis

Eden publica la especificación de todas sus herramientas en `https://mcp.eden.so/v1/openapi.json`, y la skill `eden-mcp` describe cómo usarlas. Todo lo que sigue sale de esas descripciones públicas: **es lo que Eden documenta, no lo que hemos visto hacer a su backend**. No revisamos su código ni capturamos su tráfico.

Cómo llena Eden su índice de Instagram, TikTok y LinkedIn no aparece en ningún sitio. Tampoco nos sirve: esa parte queda fuera por la regla 2.

## 2. Lo que Eden documenta sobre su método

### 2.1 Línea base por creador y outlier score

- Cada creador tiene una **línea base** de rendimiento propio. `outlierScore` es "un múltiplo de la línea base del propio creador".
- Usa tres umbrales:
  - `≥ 1.2×` basta para que un post aparezca entre los ~8 mejores de un creador. Si no llega a ocho, completa la lista con posts recientes y lo dice.
  - `≥ 2×` sirve para buscar patrones: "el doble del post típico del creador".
  - `≥ 3×` es un "breakout real".
- El índice rápido solo guarda los posts **"3x+ su línea base o su propio top ~3 %"**. Es un umbral doble: un múltiplo de la mediana **o** un percentil propio, para que los creadores con cola larga no queden vacíos ni saturados.
- En sus analytics también expone `creatorPercentile`, la posición del post dentro de la distribución del propio creador.

### 2.2 "Diamantes": outliers de creadores medianos

Para buscar "qué está funcionando", la recomendación por defecto es `creatorTier: "mid"` (100k–1M seguidores) con `minOutlierScore: 2`. La idea: un pico en una cuenta mediana dice más del contenido que un pico en una cuenta gigante, donde casi todo rinde. Los tramos son `micro` 10k–100k, `mid` 100k–1M, `macro` 1M–10M y `mega` 10M+.

### 2.3 Honestidad sobre la cobertura

- "Coverage describes a limited candidate page, not every post on a topic."
- "Empty topical results remain empty": un resultado vacío no se rellena con posts populares sin relación.
- "Un error, un timeout o un fallo externo no es 'no hay posts'."
- La búsqueda profunda puede ser parcial. Cuando lo es, lo informa en `deepCoverage` y avisa antes de dar resultados por completos.
- Las métricas que todavía se están sincronizando (`metricsStatus: "syncing"`) no se leen como cero. Si un creador está a medio cargar, dice "tenemos N de ~M posts" y no lo presenta como el total.

### 2.4 Esqueletos de títulos (`eden_study_top_titles`)

Para cada título ganador (outlier ≥ 2× por defecto) devuelve:

- el **marco** con huecos: `After [studying N of a thing], here's how to [outcome]`;
- el título original, sin cambios;
- qué necesita cada hueco;
- el "movimiento" que hace que el título funcione;
- `doNotReuse`: los números, nombres e historia propios del original.

La regla es **reutilizar el marco y cambiar el contenido**. Hay un error que Eden prohíbe expresamente: leer el ganador, resumir el principio ("usa credibilidad y especificidad") y escribir un título nuevo desde ese principio. Así se pierde la estructura que funcionaba.

Solo aplica a títulos **escritos como empaque**: vídeos de YouTube, artículos de Substack y artículos de X. El formato corto (tweets, reels, LinkedIn) no tiene título: su primera línea es cuerpo. El gancho hablado dentro de un vídeo es otro artefacto y vive en la transcripción.

### 2.5 Otros patrones

- **Longevidad como prueba cuando no hay métricas.** Meta Ad Library no publica engagement, así que Eden usa `runDays` y `variationCount` ("las marcas pagan cada día por mantener el anuncio"). La idea de fondo: si no hay métricas, buscar una señal observable que sea cara de fingir.
- **Analytics:** totales del periodo con delta frente al periodo anterior, temas y formatos que rinden por encima, y benchmark contra un grupo de pares parecidos.
- **Errores estructurados:** `{ ok: false, status, message, errors? }`, y `status` dice qué hacer (`invalid` = corregir la entrada sin reintentar, `unreachable` = reintentar una vez, `auth-expired` = reconectar). Cada herramienta lleva `x-read-only` / `x-destructive`.

## 3. Estado de nuestro motor (comprobado el 17/10 sobre la DB local)

| Comprobación | Resultado |
|---|---|
| Piezas en la ventana de 14 días | 1080 (734 HN, 346 RSS) |
| YouTube en la DB local | **0 fuentes, 0 piezas**. No hay `YOUTUBE_API_KEY` en local. No se pudo medir el sesgo de YouTube. |
| HN con `outlier_ratio` | 732 de 734. Outliers ≥ 3×: 33 (4,5 %), dentro del 3–6 % esperado con el p90 |
| Snapshots | 738 snapshots para 738 piezas: una medición por pieza. Ninguna pieza tiene todavía velocidad propia (`views/h`, `points/h`) |

### Dos huecos en lo que ya prometimos (P0, no son ideas nuevas)

**A. La referencia de YouTube no es la de CLAUDE.md.** El §7 dice "mediana de los últimos 20 vídeos del mismo canal". Pero `outlier_ratios()` (`backend/app/intelligence/opportunities.py`) calcula la referencia con las piezas que carga `load_pieces()`, que son las de los últimos 14 días (`LOOKBACK`). Consecuencias:

- Un canal que publica menos de un vídeo cada ~3 días no llega a `MIN_REFERENCE = 5` y todas sus piezas quedan con `outlier_ratio = null`.
- Además, el filtro de IA (`ai_filter`) descarta vídeos del canal, así que la referencia queda todavía más corta.
- Es justo lo que Eden llama "línea base del creador".

Arreglo propuesto: el colector de YouTube guarda por fuente una **línea base** con la mediana de views/día de los últimos 20–50 vídeos del canal, sin pasar el filtro de IA. Cuesta 1 `playlistItems` + 1 `videos.list` por canal, unas 80 unidades de cuota en total. Se guarda en la fuente (por ejemplo en `sources.config` o en una tabla `source_baselines`), **no** como `content_items`: si se guardara así, los vídeos viejos entrarían en el clustering, en la saturación y en el conteo de ventanas. El colector es de Steven; `outliers.py` y `opportunities.py`, de Melkin.

**B. Sesgo por edad en `age_adjusted()`.** Las views se acumulan rápido al principio y luego se aplanan. Dividir por días de vida, con un mínimo de un día, infla los vídeos de 0 a 3 días, que son justo los de la ventana actual, y de ahí pasan a `outlier_count` y a `momentum_score`. **Si se arregla A sin arreglar B, hay más falsos outliers**, porque los vídeos viejos de la línea base tienen views/día bajas.

Arreglo más simple: un vídeo con menos de `MIN_AGE_DAYS` (2–3 días) no recibe `is_outlier` (queda `null`, "demasiado reciente para comparar"). Se compara por velocidad (`views/h` entre snapshots) cuando haya dos mediciones. Cuando haya datos de YouTube, hay que verificarlo: comparar la mediana del ratio de los vídeos de menos de 3 días con la de los de más de 3 días.

## 4. Evaluación crítica: ¿replicar, mejorar o descartar?

### 4.1 La diferencia de fondo

Eden y 30X Signal responden preguntas distintas:

- **Eden se centra en el creador y en el post:** "¿qué post rindió por encima de lo normal para *ese* creador?". Sus filtros de tiempo (`since: week | month | …`) ordenan por rendimiento dentro de una ventana fija. En lo que documenta públicamente **no aparece** ningún concepto de velocidad del tema, aceleración, etapa del ciclo de vida ni brecha entre regiones.
- **30X Signal se centra en el tema y en el tiempo:** "¿qué tema está creciendo *ahora*, quién lo empuja y llega ya a LATAM?". El outlier es para nosotros **una señal de entrada** (pesa el 20 % del momentum y alimenta el "por qué funcionó"), no el producto.

De ahí sale el criterio para todo lo demás. Copiar a Eden tal cual nos convertiría en un buscador de posts virales, que es justo lo que el §7 prohíbe ("velocidad, no popularidad"). Lo que vale la pena son las piezas de método que mejoran nuestras señales, ajustadas a un motor centrado en temas. En dos puntos ya somos mejores, y no hay que retroceder:

- **Delta contra el periodo anterior.** Eden documenta "deltas frente al periodo anterior". Nuestra aceleración ya va más lejos: se ajusta por el volumen del corpus en cada ventana. Sin ese ajuste, los feeds RSS (que solo guardan sus últimas N piezas) harían que casi todo pareciera acelerar.
- **Rellenar huecos.** Para la vitrina de un creador, Eden completa con posts recientes cuando hay pocos outliers (y lo avisa). Nosotros no rellenamos nunca: si hay 7 oportunidades, se muestran 7 (regla 3).

### 4.2 Veredicto por idea

**1. Línea base por creador → REPLICAR, con tres mejoras.**
Es la primitiva correcta y la usan todos los que hacen esto bien (Eden, 1of10, vidIQ). Además ya la prometimos en el §7. Pero tal como la documenta Eden ("múltiplo de la línea base") le faltan tres cosas que en nuestro caso importan:

- **Igualar la edad.** Comparar views/día de un vídeo de 1 día con las de vídeos de 3 semanas favorece siempre al nuevo. Eden no documenta cómo lo resuelve. Nosotros lo hacemos explícito: un vídeo de menos de `MIN_AGE_DAYS` no recibe veredicto de outlier, y cuando haya dos snapshots se compara velocidad con velocidad.
- **Sacar la pieza de su propia referencia (leave-one-out).** Hoy `outlier_ratios()` mete cada pieza en la mediana con la que se la compara. Con referencias cortas, eso aplasta el ratio de los outliers reales. Es un cambio de una línea.
- **No mezclar la línea base con el corpus de temas.** Los últimos 20 vídeos sirven de referencia y nada más. No entran en clustering, saturación ni ventanas (ver §3.A).

**2. Umbral doble ("≥ 3× o top ~3 %") → NO REPLICAR TAL CUAL. Quedarnos con la mitad útil.**
Eden usa el umbral doble para decidir **qué guarda en su índice rápido**, y para eso tiene sentido: garantiza que cada creador aporte algo. Como **etiqueta de outlier** sería un error para nosotros: con la rama "top 3 %", *toda* fuente produce outliers por definición, haya pasado algo o no. Ese ruido entraría directo en `outlier_count` y de ahí en el momentum, y un tema parecería acelerar solo por tener piezas de muchas fuentes.
Lo útil es usar un **percentil como referencia** cuando la mediana no discrimina, que es justo lo que ya hacemos con el p90 de HN. Mejora concreta: elegir el cuantil de referencia por fuente según la forma de su distribución (cola larga → p90, distribución normal → mediana) y mantener siempre el `≥ 3×` como única regla de etiqueta.

**3. "Diamantes" (creadores medianos) → DESCARTAR la forma, ADOPTAR la idea mejorada: amplitud de outliers.**
Los tramos de seguidores de Eden sirven para buscar en un corpus enorme y descubierto. Nosotros tenemos ~40 canales elegidos a mano: casi no hay "pequeños", y un peso por tamaño metería un sesgo arbitrario.
La intuición de fondo sí es valiosa: un pico que no se explica por la distribución del canal es más señal. En un motor centrado en temas, eso se traduce en **amplitud**. Hoy `outlier_count` cuenta piezas, así que un canal con 3 outliers pesa igual que 3 canales independientes con un outlier cada uno. El segundo caso es mucho mejor señal de tendencia temprana. Mejora: contar **fuentes independientes con al menos un outlier** (`outlier_source_count`) y usarlo en el momentum en lugar del número de piezas. Esto mejora a Eden en nuestro terreno, porque Eden puntúa posts, no temas.

**4. Esqueletos de títulos → REPLICAR LA FORMA, MEJORAR EL MÉTODO.**
El formato de salida de Eden es muy bueno y encaja con nuestras reglas: marco con huecos, título original al lado, `doNotReuse` y la prohibición de escribir "desde el principio". Además `doNotReuse` es una forma práctica de aplicar "nunca inventar" en el brief. Tiene dos debilidades que podemos corregir:

- **Sesgo de supervivencia.** Eden estudia solo a los ganadores. Si un marco ("X is all you need") aparece igual de seguido en las piezas que no destacaron, no explica nada. Mejora: extraer marcos de los outliers **y** de las piezas normales del mismo tema, y proponer solo los que aparecen más en los outliers. Es el análisis contrastivo del §7, aplicado al título. Si la muestra es pequeña (lo normal: 0–3 outliers por tema), el marco sale como **hipótesis**, con su limitación explícita.
- **Traducción a la audiencia.** Nuestra fuente de marcos es sobre todo inglés técnico, y el destino es un directivo de LATAM. Un marco no se traduce palabra por palabra. El brief debe pedir el marco **adaptado a español de negocio**, con el original visible para comparar.

Alcance: sirven los títulos de YouTube, de RSS (titulares de medios) y de HN (que suele conservar el titular original del artículo). Igual que Eden, no aplicamos esto a formato corto.

**5. Lenguaje de cobertura → REPLICAR TAL CUAL.** No hay nada que mejorar: es nuestra regla 3 bien redactada. "Muestra de las fuentes monitoreadas", "vacío = vacío", "un error no es 'sin datos'". Cuesta minutos y protege la demo frente a preguntas difíciles del jurado.

**6. Longevidad como prueba sin métricas → NO REPLICAR APARTE.** Para RSS, el equivalente sería "cuántos medios independientes repiten la historia y durante cuántos días". Eso ya lo miden `cross_source` y el timeline del tema. Un score adicional contaría dos veces la misma señal.

**7. Errores estructurados en el MCP → REPLICAR EN VERSIÓN MÍNIMA, P2.** El SDK oficial de MCP ya tiene `isError` y anotaciones `readOnlyHint`. Basta con un `status` corto (`not_found`, `invalid`, `no_data`) para que Claude no confunda "no hay datos" con un fallo. Para la demo aporta poco.

**8. Benchmarks contra pares, descubrimiento de creadores, corpus de anuncios, búsqueda profunda → DESCARTAR.** Necesitan un índice masivo que no tenemos ni vamos a construir, y no responden ninguna de las tres preguntas del reto.

### 4.3 Resumen

| # | Idea | Veredicto | Dónde | Dueño | Prioridad | Coste |
|---|---|---|---|---|---|---|
| 1 | Línea base del canal + igualar edad + leave-one-out | Replicar y mejorar | `collectors/youtube.py`, `intelligence/outliers.py`, `intelligence/opportunities.py` | Steven + Melkin | **P0** (lo prometimos) | ~1,5 h |
| 3 | Amplitud de outliers (`outlier_source_count`) en el momentum | Mejora propia inspirada en "diamantes" | `intelligence/opportunities.py`, `intelligence/ranking.py` | Melkin | P1 | 30 min + tests |
| 5 | Lenguaje de cobertura | Replicar tal cual | `_limitations()`, UI, MCP | Melkin + Frontend | P1 | 15 min |
| 4 | Esqueletos de títulos contrastivos y adaptados a LATAM | Replicar la forma, mejorar el método | `editorial/` (schema + prompt versionado) | Melkin; Frontend en Create | P1, tras conectar el LLM | ~2 h |
| 2 | Cuantil de referencia por forma de distribución | Mejorar; no copiar el "o top 3 %" | `intelligence/outliers.py` | Melkin | P2 | 30 min |
| 7 | `status` en errores MCP | Versión mínima | `mcp/` | Melkin | P2 | 20 min |
| 6, 8 | Longevidad, benchmarks, descubrimiento, anuncios | Descartar | — | — | — | — |

### 4.4 Conclusión

**No vale la pena replicar Eden como sistema.** Su valor está en un índice enorme de posts y creadores, y su pregunta es "qué post funcionó". Ni podemos tener ese índice (regla 2, plazo) ni es nuestra pregunta. **Sí vale la pena tomar tres piezas de método y mejorarlas para un motor centrado en temas**:

1. La línea base del creador, con igualación de edad.
2. La idea de "diamantes", convertida en amplitud de outliers entre fuentes.
3. El formato de esqueletos de títulos, con análisis contrastivo y adaptación a LATAM.

Las tres refuerzan lo que nos diferencia: tendencia temprana, verificable y traducida para ejecutivos de LATAM. Ninguna pone en riesgo un P0.

Orden si se implementa: #1 (cierra un hueco de lo prometido), #5, #3, y #4 cuando el LLM esté conectado. Antes del #1 hay que confirmar con Steven que YouTube ya recolecta en producción. En la DB local no hay datos de YouTube para validar el sesgo de edad.
