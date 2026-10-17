# Validación del radar: cómo demostrar que 30X Signal funciona

> Propuesta de Melkin (AI & Intelligence) para el equipo · 17 oct 2026.
> Objetivo: profundizar, no ampliar. No añade funcionalidades; añade pruebas de que lo que ya tenemos detecta tendencias reales y no ruido.
>
> **Enfoque (decidido el 17/10):** el **target es LATAM** y las **señales tempranas se buscan en fuentes globales**, sobre todo de USA, que marca la mayor parte de las tendencias de IA (también labs y comunidades de Europa, UK y China). España queda fuera: es un mercado seguidor, no un origen, y no es audiencia.

---

## 0. Resumen

**Qué resolvemos:** un usuario de 30X **escribe una pregunta** ("¿qué publico esta semana en LinkedIn para CEOs de LATAM?") y recibe una recomendación con evidencia verificable, su explicación y un brief. Todo sale de un análisis que podemos demostrar que no es ruido.

| Pieza | Decisión | Coste |
|---|---|---|
| Detección | Velocidad y aceleración ajustadas por volumen + test de Poisson + tope por outlet. Fuentes globales (sobre todo USA) | $0 |
| Target | LATAM (España fuera). LATAM Gap = acelera en las fuentes globales y todavía es bajo en LATAM | $0 |
| Redes sociales | YouTube (con Shorts) automático; LinkedIn, Instagram y TikTok por sensor editorial manual (CSV). Grok Bot fuera; X en el roadmap | $0 |
| Medios LATAM | RSS → news sitemap → Firecrawl (free tier) solo como respaldo | $0 |
| Clasificación y fit | Jev (TypeSafe): batería de pieza (formato, gancho, pilar…) y de tema (6 criterios del fit); Python combina con umbrales y pesos (`docs/jev.md`) | < 2 $ al mes |
| Explicación | Lift de los rasgos de Jev + timing, autor y difusión (Python), con n; el LLM generativo solo redacta y Jev verifica cada afirmación | Céntimos por ejecución |
| Consulta | MCP (Claude, ChatGPT o Grok, con la suscripción del usuario) sobre los mismos services que el dashboard | $0 para nosotros |
| Validación | Backtest, estabilidad del ranking, ranking ciego de 30X, Google Trends por país | $0 |

**Orden:**
1. P0: YouTube, rutas `/opportunities`, `30x.yaml` y audience fit con Jev.
2. Explicación determinista y test de Poisson.
3. Servidor MCP + brief.
4. Backtest, estabilidad y ranking ciego.
5. Todo lo demás se documenta como limitación.

---

## 1. Qué haría un profesional de primer nivel (y aún no estamos haciendo)

Un data scientist de inteligencia editorial o un científico social computacional, antes de construir más, intentaría **demostrar que el radar no es ruido**.

- **Definir "tendencia" de forma refutable.** Fijar el criterio antes de ver los resultados. Por ejemplo: "emerging = la tasa de la ventana actual supera a la anterior con p < 0.1 y hay al menos N piezas". Así se separa una tendencia de un pico aislado, de la estacionalidad o de un artefacto de medición. El ajuste por volumen del corpus ya va en esa dirección.
- **Backtest (hindcast).** Congelar los datos en una fecha pasada (`as_of = 10/10`), dejar que el sistema prediga y comprobar con lo observado del 11 al 17/10. Medir precision@10 de los temas `emerging` y cuántos días de ventaja dan. Es la prueba central de la primera pregunta del reto.
- **Incertidumbre con muestras pequeñas.** Pasar de 3 a 6 piezas es "+100 %" y no significa nada. Hacen falta un test de razón de tasas de Poisson, intervalos y un mínimo de piezas. Para los outliers de canales pequeños, shrinkage bayesiano empírico.
- **Estabilidad del ranking.** Perturbar pesos y umbrales ±10–20 % y medir cuánto cambia el top 10. Si cambia casi entero, el ranking lo deciden los parámetros, no los datos.
- **Validar Jev con humanos antes de confiar en él.** Se necesitan 30–50 piezas etiquetadas a mano por otra persona (`data/evaluations/jev_pieces.yaml`). Una pregunta con menos del 70 % de acuerdo no se usa en la demo (`docs/jev.md`). Para el fit de los temas: ranking ciego del equipo y correlación de Spearman frente a Jev.
- **"Por qué funcionó" con controles.** Comparar cada outlier con piezas del mismo canal y del mismo tema, controlando la edad de la pieza. Cada hipótesis tiene que poder resultar falsa.
- **Medir el desfase global → LATAM.** Si el LATAM Gap existe, los temas aparecen antes en las fuentes globales (sobre todo USA) que en las de LATAM. Con el backfill de 14 días se puede medir. Si no lo medimos, la tesis es solo una suposición.
- **Ser explícitos con LinkedIn.** El ejemplo del reto dice "en LinkedIn" y ahí no podemos hacer scraping. Hay que decirlo claramente y comprobar si nuestras fuentes funcionan como proxy, contrastándolas con una muestra de LinkedIn curada a mano.

## 2. Material más bruto del que partir

- **Respuestas crudas de las APIs**, guardadas tal cual: JSON de `videos.list` de YouTube, hits de HN Algolia (`created_at_i`, `points`, `num_comments`), entradas RSS completas y cada snapshot con su timestamp.
- **Los posts públicos de 30X y de Andrés Bilbao, uno por uno**: caption, formato, fecha, likes y comentarios visibles, y el rendimiento de cada post frente a la mediana de su propio perfil. Esto sustituye al resumen del brief ("contenido de IA para líderes").
- **Las decisiones reales del equipo de media de 30X**: qué produjeron en las últimas semanas, a partir de qué referencia y cómo les fue. Basta con una entrevista de 20 minutos.
- **Series diarias externas que no entran en ningún score**: Google Trends por RSS **por país** (US frente a MX, CO, AR, CL, PE), que es la mejor señal para comparar el principal origen de tendencias (USA) con LATAM. Como apoyo, Wikipedia Pageviews API (pública, gratuita, diaria, `en` / `es`); ojo: `es.wikipedia` mezcla el tráfico de España y de LATAM.
- **Un calendario de eventos conocidos** (lanzamientos de modelos y productos, con su fecha) para comprobar si el radar los detectó a tiempo.

## 3. Métodos y herramientas

| Objetivo | Método | Herramienta (ya en el stack o dependencia directa) |
|---|---|---|
| Tendencia temprana real | Backtest con `as_of`, precision@k, días de ventaja | Polars, `as_of` de la ventana móvil |
| Aceleración significativa | Test de razón de tasas de Poisson (binomial condicional) y mínimo de piezas | `scipy.stats.binomtest` |
| Outliers robustos | Shrinkage bayesiano empírico sobre `outlier_ratio` | NumPy |
| Calidad del clustering | Revisión manual de la pureza en una muestra; estabilidad entre seeds y umbrales con ARI | `sklearn.metrics.adjusted_rand_score`, `silhouette_score` |
| Estabilidad del ranking | Perturbación Monte Carlo de pesos, medida con Kendall τ y RBO | `scipy.stats.kendalltau` |
| Jev fiable | Piezas etiquetadas a mano (acuerdo ≥ 70 % por pregunta), preguntas `_rev` contra el sesgo hacia la primera opción, Spearman frente al ranking humano, pregunta `injection` | `typesafe-sdk`, pytest + respx |
| LATAM Gap | Desfase entre la primera aparición en fuentes globales y de LATAM por tema; correlación cruzada de los conteos diarios | Polars |
| Demanda externa | Google Trends US frente a países LATAM; pageviews en/es antes y después de la detección | Google Trends RSS, Wikipedia REST API (`httpx`) |

## 4. Qué demostraría que el resultado es correcto (sin depender de nuestra opinión)

1. **El tiempo.** Congelar el ranking del sábado y compararlo con lo que pase después. Dentro de la hackathon, el backtest sobre el backfill cumple ese papel.
2. **Una señal independiente que no entra en el score.** Google Trends (primero en US y después en LATAM) o las pageviews de Wikipedia suben después de que el radar marque un tema.
3. **El equipo de media de 30X, a ciegas.** Reciben 20 temas en orden aleatorio, sin scores, y eligen su top 10. Medimos cuánto se solapa con el top 10 del sistema.
4. **El historial público de 30X.** Los temas con audience fit alto deberían coincidir con los posts de 30X que rindieron por encima de su mediana.
5. **Reproducibilidad y enlaces.** La misma ejecución sobre el mismo snapshot da los mismos scores, y todas las URLs de evidencia responden 200 (comprobado automáticamente).

### Prioridad por el deadline (dom 18/10 · entrega interna 11:15 COL)

No da tiempo a todo. Por coste e impacto en la demo, propongo este orden:

1. Backtest
2. Test de Poisson para la aceleración
3. Estabilidad del ranking
4. Ranking ciego del equipo de 30X

El resto se documenta como limitación.

**Ownership (§3 de CLAUDE.md):** todos los cálculos son de Melkin. Steven solo tendría que confirmar que se guardan las respuestas crudas y los snapshots. La slide de la demo, junto con el frontend lead.

---

## 5. Fuentes: cómo las elegiría un profesional

### Estado actual (DB local, sáb 17/10 ~13:00 ESP)

- **YouTube tiene 0 piezas.** `data/sources.yaml` declara 38 canales, pero en `sources` solo hay filas `hackernews` (7) y `rss` (34). Probablemente `seed_sources` no cargó YouTube (API key o conversión de handle a channel ID). YouTube es P0 y es la única fuente con engagement y Shorts.
- **Corpus desequilibrado.** De 1085 piezas, HN aporta 725 (67 %), `tech` en total 904, `latam_es` 157 y `business` solo 24 (2 %). Siete fuentes `business` tienen entre 0 y 3 piezas.
- **El grupo B no es LATAM.** 66 de las 157 piezas `latam_es` vienen de España (Expansión ES 36, Xataka 10, Genbeta 10, El País 7, Hipertextual 2, MIT TR en español 1). Sin ellas quedan **91 piezas LATAM**, casi todas de tecnología general (Infobae 39, WIRED en Español 14, Expansión MX 11, La Nación 10…). Hay 7 canales de YouTube de España (DotCSV, XavierMitjana, midudev, NateGentile7, carlosazaustre, BettaTech, mouredev) que también salen.
- **El grupo A (global) ya está bien cubierto:** sobre todo USA (HN, TechCrunch, The Verge, WIRED, MIT TR, YC, a16z…), más UK y Europa (DeepMind, Hugging Face, Benedict Evans, Exponential View). Las fuentes ya están marcadas como `region: global`; no hace falta cambiarlas.

### Criterios

1. **Fuentes por capa de difusión.** Cada fuente ocupa un lugar en la cadena por la que una idea llega a la audiencia (difusión de innovaciones, Rogers). Las capas 0–3 son **globales** (detección, sobre todo USA) y la capa 4 es **LATAM** (target). Una oportunidad temprana es un tema que acelera en las fuentes globales y que todavía es bajo o inexistente en LATAM. Esa es la definición operativa del LATAM Gap.
2. **Cuotas por capa.** Muestra estratificada, con un tope de piezas por fuente y ventana, para que ninguna fuente domine el corpus, la saturación ni el ajuste por volumen.
3. **Independencia.** Un medio es un voto, y las notas sindicadas se deduplican. HN ya cuenta como un único medio (`outlet_key`).
4. **Calidad de medición por fuente:** si tiene `published_at` fiable, métricas públicas, backfill y cuántas piezas guarda el feed (truncación del RSS).
5. **Validación separada de la detección.** Hay fuentes que nunca entran en un score y solo sirven para comprobar el resultado.
6. **La propia audiencia como fuente.** El contenido público de 30X y de Andrés Bilbao es el ground truth del fit.
7. **Legalidad.** Solo fuentes que cumplen ToS: API oficial, RSS o curación manual.

### Mapa de fuentes

Estado: ✅ ya está · ⚠️ está pero es débil · ❌ roto · ➕ añadir.

| Capa | Rol | Fuentes | Acceso | Estado |
|---|---|---|---|---|
| **0 · Origen** (semanas de ventaja) | Dónde nace un tema | arXiv (cs.AI, cs.CL) · Hugging Face Hub (modelos y Spaces en tendencia, likes) · HF Daily Papers (upvotes) · GitHub (repos recientes por estrellas) · blogs oficiales de los labs | API pública / RSS | ✅ blogs de labs · ➕ el resto |
| **1 · Conversación técnica temprana** | Primera adopción | HN · Bluesky (API abierta de AT Protocol) · Lobsters · Reddit (r/LocalLLaMA, r/MachineLearning) | API / RSS | ✅ HN (sobrerrepresentado) · ➕ Bluesky · ⚠️ Reddit: su Data API restringe el uso comercial; solo con revisión de ToS |
| **2 · Medios y creadores tech** | Amplificación | Medios tech en inglés, newsletters, YouTube tech | RSS / YouTube API | ✅ RSS · ❌ YouTube a 0 |
| **3 · Traductores a negocio** | Cuando el tema llega a directivos | HBR, McKinsey Insights, BCG, Gartner newsroom, Fortune (Eye on AI), Axios, a16z, Sequoia · podcasts de negocio e IA (RSS) · YouTube de negocio | RSS / YouTube API | ⚠️ pocas piezas · ➕ podcasts y más RSS |
| **4 · LATAM empresarial** (target) | Llegada a la audiencia de 30X | Bloomberg Línea, América Economía, El Economista (MX), El Financiero (MX), Portafolio y Valora Analitik (CO), iProUP (AR), Diario Financiero (CL), Gestión (PE), LatamList · blogs tech de Mercado Libre y Nubank · YouTube de creadores y escuelas LATAM (Platzi, EDteam…) | RSS / YouTube API | ⚠️ 91 piezas, sobre todo tecnología general · ➕ negocio LATAM · ➖ desactivar las fuentes de España |
| **5 · Formatos sociales** | El "cómo" (gancho, formato) | LinkedIn, Instagram y TikTok (curación manual) · TikTok Creative Center por región (referencia) · YouTube Shorts | Manual / API | ➕ sensor editorial |
| **Audiencia** | Ground truth del fit | Posts públicos de 30X y de Andrés Bilbao, registrados uno por uno | Manual | ➕ |
| **Validación** (no puntúa) | Juez externo | Google Trends RSS por país (US frente a MX, CO, AR, CL, PE) · GDELT DOC 2.0 (volumen de noticias por país) · Wikipedia Pageviews (en/es; `es` mezcla España y LATAM) | API pública / RSS | ➕ |

Estado: ➖ = desactivar (`active: false`, sin borrar, para no perder el historial).

Las URLs de los feeds no están verificadas: cada una se comprueba con `feedparser` antes de entrar en `sources.yaml`.

### Qué cabe antes del deadline

1. **Ya (Steven, crítico):** arreglar el seed de YouTube.
2. **Hoy (Steven, ~30 min, sin código nuevo):** solo editar `sources.yaml` para el collector RSS que ya existe:
   - unos 6 feeds de la capa 3 (negocio en inglés y podcasts);
   - unos 6–8 de la capa 4 (negocio LATAM), que pasa a ser la capa más débil; para cada medio, primero RSS, luego news sitemap y Firecrawl solo como respaldo (ver §6);
   - desactivar las fuentes de España (6 RSS y 7 canales de YouTube).

   El contrato no cambia: el segment `latam_es` se queda con ese nombre, pero pasa a significar "LATAM".
3. **Hoy (Melkin):** un tope de piezas por outlet y ventana en el clustering, para que HN no domine. Función pura con test.
4. **Domingo, si sobra:** Google Trends RSS por país, como validación (también entra por RSS).
5. **Fuera, documentado como limitación:** arXiv, HF, GitHub, Bluesky, GDELT y Reddit. Cada una necesita un collector nuevo; quedan como roadmap con su capa ya definida.

---

## 6. Herramientas de terceros evaluadas (17/10)

### Grok Bot (xAI) · Descartado

Producto de agentes de xAI, en beta desde el 11/08/2026. Cada bot tiene un ordenador en la nube con navegador, mantiene las sesiones con login y ejecuta routines programadas o disparadas por eventos. No confundir con la API de Grok.

**Por qué no lo usamos para LinkedIn, Instagram o TikTok:** entraría con la cuenta de alguien del equipo y leería feeds con login. El reto excluye exactamente eso ("contenido detrás de un login de terceros", "violar términos de servicio") y también lo prohíbe la regla 2 de CLAUDE.md.

| Riesgo | Detalle |
|---|---|
| ToS y cuenta | LinkedIn, Meta y TikTok prohíben el acceso automatizado. Si lo detectan, pueden suspender la cuenta personal que usamos también para la curación manual |
| Evasión de bloqueos | La opción de enrutar el tráfico por una IP doméstica para esquivar los bloqueos de datacenter es eludir una protección. No se usa |
| El feed no es una muestra | Un feed con login está personalizado por el algoritmo: sesgo estructural, no comparable entre ejecuciones |
| Datos personales | Posts de particulares, conexiones y nombres (regla 1) |
| Seguridad | Sesión con login + contenido no confiable = prompt injection capaz de actuar con la cuenta. Los bots comparten archivos, sesiones y credenciales |
| Métricas no observadas | Lo que el bot "lee en pantalla" lo reporta un LLM, no está medido (reglas 3 y 4) |
| Integración | No hay API ni webhook documentados para invocarlo desde nuestra plataforma, y CLAUDE.md §7 dice "sin agentes autónomos" |
| Coste y fiabilidad | Beta, uso semanal opaco y flujos que se rompen cuando cambia la página |

**Uso posible (P1, después del servidor MCP):** Grok Bot como *consumidor* de nuestro MCP. Por ejemplo, un "bot editorial de 30X" con una routine semanal: `get_trending_opportunities` → brief en Google Docs → aviso por Slack. Falta verificar en su documentación que admite servidores MCP propios, y alguien del equipo necesita un plan compatible.

**LinkedIn, Instagram y TikTok** se quedan como estaban: curación manual (`POST /signals/manual`) y TikTok Creative Center como referencia. Roadmap con vías oficiales: LinkedIn Marketing API (requiere aprobación de partner) y Meta Content Library (acceso de investigador).

### Firecrawl · Solo como respaldo para la capa 4 (negocio LATAM)

**Redes:** no. Según dos competidores, Firecrawl ya rechaza URLs de Instagram, YouTube y TikTok ("This website is no longer supported"); no hay declaración oficial de Firecrawl. Además, el contenido útil está detrás de login, con el mismo problema de ToS.

**Dónde aporta:** medios de negocio LATAM sin RSS o con el RSS roto. Lee la página de sección y devuelve `{title, url, published_at}` con un JSON schema, sin selectores por sitio.

**Orden para dar de alta un medio LATAM**, del más barato al más caro:
1. **RSS** verificado con `feedparser`.
2. **News sitemap** (`news-sitemap.xml` / `sitemap_news.xml`, con `publication_date`): gratis y determinista, se lee con `httpx`.
3. **Firecrawl**, solo si no hay ninguno de los dos.

**Coste:** unos 1 crédito por página. 8 secciones × 12 ejecuciones al día ≈ 3000 créditos al mes, dentro del plan Hobby ($16 al mes). Las fuentes no coinciden sobre el free tier (500 créditos una vez o 1000 al mes); confirmarlo en `firecrawl.dev/pricing`. El modo JSON con LLM cuesta más y los créditos no se acumulan.

**Salvaguardas:**
- Validar `published_at`: debe ser parseable y ≤ `now`. Si no, usar `first_observed_at` y marcar la pieza como `preliminary`.
- Guardar solo metadatos (título, URL, fecha), nunca el texto completo (regla 1). Revisar `robots.txt` y los términos de cada medio.
- Contenido delimitado al LLM (regla 6).
- Deduplicar notas de agencia (EFE, AFP) replicadas en varios medios.
- Alerta cuando una fuente pase a 0 piezas.

**Prioridad:** P1, después del P0. Área de Steven. No sustituye a Brave para el descubrimiento web.

---

## 7. Redes sociales: sensor editorial (decidido el 17/10)

LinkedIn, Instagram y TikTok no sirven para *detectar* tendencias tempranas: las tendencias de IA nacen antes en las capas globales. Sirven para *explicarlas*: formato, gancho y si el tema ya llegó a redes. El reto pide "qué temas **y formatos**", así que tienen que estar.

| Plataforma | En la hackathon | Para qué |
|---|---|---|
| YouTube | Arreglar el seed (P0), incluidos los Shorts | Señal automática de redes: velocidad, outliers y formato corto |
| LinkedIn · Instagram · TikTok | Sensor editorial: unas 40 piezas curadas (10–15 por plataforma) de contenido de IA que funciona en LATAM | Formatos, ganchos, llegada a redes |
| Instagram de 30X y de Andrés Bilbao | Unos 20 posts registrados con sus métricas visibles | `30x.yaml` y ground truth del fit |
| X | Roadmap (API pay-per-use, ~$0.005 por post) | Evita el setup, el coste y añadir `x` al contrato |
| Instagram Business Discovery | Spike de 1 hora el domingo, solo si el P0 está cerrado | Métricas oficiales automatizadas |

**Formato:** `data/manual/signals.csv` con `url, platform, account (pública), published_at, observed_at, format, hook, language, country, views, likes, comments, tags, curator`. Un loader lo carga como `ContentItem` + `MetricSnapshot`. `linkedin`, `instagram` y `tiktok` ya existen en `Platform`, así que **el contrato no cambia**. Si se vuelve a medir el domingo, hay dos snapshots y algunas piezas pasan a `observed`. El formulario con oEmbed (`POST /signals/manual`) es P1.

**Límites que se dicen en la UI:** es una muestra curada, no representativa; solo cuentas públicas de organizaciones y creadores; nada de comentarios ni de datos de usuarios.

---

## 8. Explicación a coste casi nulo

**El cálculo es determinista** (`intelligence/explain.py`, función pura con tests). Es un análisis contrastivo dentro de cada tema: outliers frente al resto. Los rasgos de cada pieza los clasifica Jev en la batería de pieza (`docs/jev.md`); el resto sale de los datos.

| Dimensión | Cómo se obtiene | Dato |
|---|---|---|
| Gancho | Jev `hook` / `hook_rev` (pregunta, dato o cifra, contraintuitivo, historia, cómo hacer, noticia, lista); si no coinciden, "incierto" | `title`, `description` |
| Formato | Jev `format` / `format_rev` + Short (< 60 s) frente a vídeo largo + etiqueta manual | `duration_seconds`, `format`, CSV |
| Timing | Horas desde la primera aparición del tema; día y hora | `published_at` |
| Autor | `outlier_ratio` (ya normalizado por canal) | snapshots |
| Difusión | Capas y orden de aparición (global → LATAM) | `segment`, `published_at` |

Para cada rasgo, el **lift** (% entre los outliers frente a % en el resto) **con n**. Un lift ≥ 2 en al menos 2 outliers es un "patrón observado"; si no, "anecdótico". Lo incierto no cuenta. Por ejemplo: "3 de 4 outliers usan un gancho de dato o cifra, frente a 3 de 10". Son hipótesis, no causalidad. `limitations` sale de las banderas de datos (`growth_status`, n, una sola fuente, sin snapshots, muestra curada).

**El audience fit no lo calcula un LLM:** son 6 preguntas `score` de Jev en la batería de tema, combinadas en Python con pesos en código (CLAUDE.md §7).

**El LLM generativo solo redacta** (SDK oficial del proveedor, sin LiteLLM):
- Una llamada por oportunidad (top ~15), solo dentro de `analyze`, para `why_it_matters` y `limitations`.
- Recibe como datos la tabla de lift y los juicios de Jev, delimitados.
- Devuelve afirmaciones con el id de su evidencia. Jev verifica cada una y lo no respaldado se elimina (batería 4 de `docs/jev.md`).
- Salida en Pydantic y caché por hash de las entradas.
- Nunca por petición, y sin texto completo, transcripciones ni análisis de vídeo.
- Cada llamada registra su consumo en `usage_events` (CLAUDE.md §4).

**La explicación profunda bajo demanda** la redacta el asistente del usuario vía MCP (§9).

**Contrato:** sin cambios. Los lifts viajan como texto dentro de `why_it_matters` y `limitations`. Mostrarlos estructurados en la UI requeriría un campo nuevo, y hay que avisar antes.

---

## 9. Consulta en lenguaje natural: la interfaz para decidir qué publicar

```
Usuario escribe → Asistente (Claude / ChatGPT / Grok) → MCP 30X Signal → services (solo lectura)
               ← respuesta con URLs                  ← JSON con evidencia
```

La misma lógica sirve a tres canales: dashboard, MCP y, más adelante, un chat dentro de la app. Ninguno recalcula ni hace scraping. El razonamiento lo paga el asistente del usuario.

| El usuario escribe | Herramienta | Devuelve |
|---|---|---|
| "¿Qué temas de IA están despegando esta semana?" | `get_trending_opportunities(period=7d)` | Top N con lifecycle, aceleración, recomendación y confianza |
| "¿Por qué está creciendo X? ¿Es fiable?" | `analyze_opportunity(id)` | Evidencia (URLs), rasgos con lift y n, `limitations` |
| "¿Qué encaja mejor con ejecutivos LATAM, A o B?" | `compare_audience_fit(ids)` | Fit por criterio con justificación, LATAM Gap |
| "¿Hay algo sobre agentes en LinkedIn o YouTube?" | `search_content_signals(q, platform)` | Piezas con métricas y fechas |
| "Dame un post de LinkedIn sobre X para CEOs" | `generate_editorial_brief(id, platform, goal, format)` | Ángulo, gancho, estructura, evidencias, encaje |

**Decisión:** `generate_editorial_brief` **pasa de P2 a P1**, porque es lo que convierte el análisis en una acción. Comparte service con `POST /editorial/brief`. El **chat dentro de la app queda en P2**: usaría las mismas herramientas, pero cuesta unas 2 llamadas por pregunta y roza el "sin agentes autónomos" de CLAUDE.md §7. Para la demo basta con MCP desde Claude.

**Reglas:**
- Cada respuesta incluye `recommendation`, `why_it_matters`, `confidence`, evidencia con URLs y `limitations`.
- Si faltan datos, la herramienta dice "sin datos suficientes" en lugar de dar números.
- Las descripciones de las herramientas instruyen al asistente a citar URLs y a distinguir observado, estimado y preliminar.
- El texto de las fuentes viaja como dato (regla 6).

**Riesgos:**
1. `backend/app/mcp/` está vacío y depende de que las rutas y services estén en `main`.
2. Un cliente remoto necesita la URL pública (Railway, `MCP_PUBLIC_URL`). Probar en local no cumple el criterio de "sesión limpia".
3. Cada cliente (Claude, ChatGPT, Grok) conecta un MCP propio de forma distinta. Hay que probar al menos uno de punta a punta y documentar los demás.
4. Si el dato es pobre (YouTube a 0, sin fit), la respuesta será pobre aunque esté bien redactada.
5. Sin auth: datos públicos de solo lectura, se declara como limitación.

**Plan (Melkin):**
- Sáb 20:30–00:30 ESP: servidor MCP con las 5 herramientas, montado en FastAPI (Streamable HTTP), con un test por herramienta.
- Dom por la mañana: desplegar, probar desde Claude con 3 preguntas reales y grabarlo como respaldo para la demo.

---

## 10. Indicación para Claude Code (versión final)

```
Contexto: 30X Signal (ver CLAUDE.md y docs/validation-plan.md). Soy Melkin, responsable
de AI & Intelligence. El pipeline `analyze` ya existe (embeddings, clustering, velocity y
acceleration ajustadas por volumen, outliers, lifecycle). Enfoque: detección global (sobre
todo USA), target LATAM, España fuera. Objetivo: que un usuario escriba una pregunta y
reciba qué publicar, por qué y con qué evidencia, sobre un análisis que podamos DEMOSTRAR
que no es ruido, a coste casi nulo. Deadline: dom 18/10, 11:15 COL.

1. Explicación determinista (intelligence/explain.py, función pura con tests): para cada
   tema, compara outliers con el resto por gancho y formato (juicios de Jev de la batería
   de pieza, sin contar los inciertos), timing (horas desde la primera aparición del
   tema), autor (outlier_ratio) y difusión (capas y orden global → LATAM). Devuelve el
   lift con n ("patrón observado" si lift ≥ 2 en ≥ 2 outliers). Genera `limitations` a
   partir de las banderas de datos.

2. Jev y redacción (docs/jev.md): audience fit y accionabilidad con la batería de tema,
   combinados en Python. El LLM generativo (SDK oficial, sin LiteLLM) solo redacta
   why_it_matters en una llamada por oportunidad (top ~15) dentro de `analyze`, con la
   tabla de lift como dato delimitado, afirmaciones con el id de su evidencia que Jev
   verifica, y caché por hash. Nunca por petición. Todo registra consumo en
   usage_events.

3. Rigor: test de Poisson para la aceleración con mínimo de piezas (se refleja en
   lifecycle_reason y growth_status) y tope de piezas por outlet en el clustering. No
   cambies el contrato Opportunity; si fuera imprescindible, avísame antes.

4. Sensor editorial: loader de data/manual/signals.csv (url, platform, account pública,
   published_at, observed_at, format, hook, language, country, métricas visibles, tags,
   curator) como ContentItem + MetricSnapshot para linkedin/instagram/tiktok. Sin
   scraping, sin login, sin datos personales.

5. Servidor MCP (app/mcp/, solo lectura, Streamable HTTP montado en FastAPI, solo usa
   services): get_trending_opportunities, analyze_opportunity, compare_audience_fit,
   search_content_signals y generate_editorial_brief (comparte service con POST
   /editorial/brief). Cada respuesta incluye recommendation, why_it_matters, confidence,
   evidencia con URLs y limitations; si faltan datos, dilo en vez de dar números. Las
   descripciones de las herramientas piden al asistente citar URLs y distinguir
   observado, estimado y preliminar. Un test por herramienta.

6. Validación (si cabe): backtest con --as-of (sin datos posteriores a as_of: filtra
   published_at y los snapshots), precision@10 y días de ventaja; Monte Carlo ±20 % de
   pesos con Kendall τ; formulario de ranking ciego de 20 temas para 30X; Google Trends
   por país como señal independiente.

Entregables: código y tests, docs/validation.md con resultados reales (incluidos los
negativos) y limitaciones (muestra curada en redes, LinkedIn/IG/TikTok solo manual, MCP
sin auth), demo grabada con 3 preguntas reales desde Claude vía MCP y 1 slide de "cómo
sabemos que funciona". Nunca inventes resultados: si algo no se pudo medir, se queda
vacío y se explica. Antes de empezar, dame el plan ordenado por impacto/coste y qué
dejarías fuera por el deadline.
```
