# 30X Signal — Brief de producto

> **Qué es:** el *porqué* de 30X Signal. Recoge el reto oficial de 30X, cómo lo interpretamos, para
> quién lo construimos, qué capacidades cuentan, qué podemos afirmar con los datos y cuándo está
> lista la entrega.
> El *cómo* (reglas, contratos, scoring, stack y calendario) vive en [`CLAUDE.md`](../CLAUDE.md).
> Si este archivo y `CLAUDE.md` se contradicen, manda `CLAUDE.md` y se corrige este. La excepción
> es §1: el reto es la fuente primaria y no se edita.

---

## 1. El reto oficial

Es el enunciado que entregó 30X, copiado tal cual. Es lo único que 30X compartió además de los
perfiles de referencia.

> **Reto 30X: Radar de contenido** · Área: Media · Tipo: Explorar una oportunidad.
>
> **El reto en una frase:** ¿Cómo puede un equipo de contenido descubrir, de forma confiable y sin
> gastar una fortuna, qué temas y formatos están despegando en redes, por qué funcionan y si encajan
> con su audiencia?
>
> **El problema:** 30X produce contenido sobre IA para líderes y equipos en Latinoamérica, y para
> decidir qué producir el equipo de media busca referentes y piezas que estén funcionando en
> LinkedIn, Instagram, TikTok y YouTube. Hoy eso depende de servicios de scraping pagos que cuestan
> miles de dólares al año y que solo resuelven la mitad de la pregunta: traen datos, pero no dicen
> por qué algo funcionó, si es una tendencia que recién empieza o una que ya todos copiaron, ni si
> le sirve a nuestra audiencia. Es el mismo problema que tiene cualquier marca, medio o creador que
> hace contenido continuamente.
>
> **Preguntas que queremos explorar:**
> 1. ¿Cómo se detecta una tendencia cuando apenas está empezando a crecer?
> 2. ¿Cómo se explica por qué una pieza funcionó: el gancho, el formato, el tema, el momento, quién
>    la publicó?
> 3. ¿Cómo se filtra lo que es relevante para una audiencia concreta, como ejecutivos y equipos de
>    Latinoamérica aprendiendo IA?
>
> **Caminos posibles (no obligatorios):** agentes que navegan y resumen, combinaciones de fuentes
> abiertas, modelos que clasifican y priorizan (JEV puede ser un buen aliado aquí), enfoques que
> usan a la propia comunidad como sensor, o algo que todavía no se nos ha ocurrido.
>
> **Qué entra y qué no.** Entra: cualquier enfoque para descubrir y entender contenido público en
> redes. No entra: datos privados, contenido detrás de un login de terceros, ni técnicas que
> dependan de violar términos de servicio.
>
> **Entregable esperado:** un prototipo funcional que responda una pregunta concreta, por ejemplo:
> "¿cuáles son los 10 temas de IA que más están creciendo esta semana en LinkedIn, por qué y cómo
> lo adaptamos?"
>
> **Qué compartimos:** perfiles de referencia del contenido que hacemos: el Instagram de 30X
> ([@crece30x](https://www.instagram.com/crece30x/)) y el de Andrés Bilbao
> ([@andresbilbao](https://www.instagram.com/andresbilbao/)).
>
> **Restricciones:** solo contenido público y nada de datos personales.

## 2. Cómo leemos el reto

Cada frase del reto marca algo que 30X va a mirar en la demo. Esta tabla dice qué implica cada una
y dónde la respondemos.

| El reto dice | Qué implica para nosotros | Dónde lo respondemos |
|---|---|---|
| "de forma confiable" | Cada afirmación lleva su evidencia y dice si es dato observado, estimado o preliminar | CLAUDE.md §2 (reglas 3 y 5) · §7 de este brief |
| "sin gastar una fortuna" (hoy pagan miles de USD al año) | Solo fuentes gratuitas o con API oficial, y modelos baratos. El coste real de operar el radar se mide en cada llamada y se enseña en el dashboard y por MCP | CLAUDE.md §4 (coste de operación) · `data/pricing.yaml` · [`sources.md`](sources.md) |
| "temas **y formatos**" | El formato es una dimensión más: se analiza qué formato funciona y se recomienda formato por plataforma | `ContentSignal.format` · "por qué funcionó" · `recommendation` |
| "si es una tendencia que recién empieza o una que ya todos copiaron" | Etapa del ciclo de vida y saturación, no solo volumen | `lifecycle` (`emerging` … `saturated`), `saturation_score` |
| "por qué funcionó: gancho, formato, tema, momento, quién" | Outliers frente a su referencia y contraste con el resto del tema, presentado como hipótesis | CLAUDE.md §7 (outliers y "por qué funcionó") |
| "ejecutivos y equipos de Latinoamérica aprendiendo IA" | Encaje con la audiencia evaluado contra el perfil de 30X | `audience_fit_score`, `audience_mix`, `latam_gap` |
| "en redes" y el ejemplo "en LinkedIn" | LinkedIn no tiene API pública para buscar posts de otros, y el reto prohíbe el login. Sus términos tampoco permiten usar su contenido obtenido a través de buscadores sin consentimiento del dueño. LinkedIn entra por vías oficiales o con consentimiento: la API de portabilidad (DMA, "un clic = señal" del curador), los exports de analítica de 30X y de Andrés Bilbao, la curación de la comunidad, el embed oficial y los canales abiertos de sus referentes. Instagram y TikTok entran por curación. El pitch lo cuenta como respuesta a la restricción, no como carencia | CLAUDE.md §5 · [`sources.md`](sources.md) (LinkedIn) |
| "la propia comunidad como sensor" | Sensor editorial: el equipo o la comunidad pega enlaces y los etiqueta | `POST /signals/manual` (P1) |
| "modelos que clasifican y priorizan (JEV)" | **Decidido: usamos [Jev](https://docs.typesafe.ai) (TypeSafe)** para las decisiones atómicas sobre piezas: clasifica cada pieza (relevancia, formato, gancho…), detecta notas replicadas y verifica lo que escribe el LLM. Python prioriza, y el LLM evalúa cada tema y redacta | CLAUDE.md §7 · [`jev.md`](jev.md) |
| "el mismo problema que tiene cualquier marca, medio o creador" | El perfil de audiencia es un archivo: cambiarlo adapta el radar a otra marca. En la demo basta con contarlo | `data/audiences/30x.yaml` · "varias audiencias" es P2 |
| "un prototipo funcional que responda una pregunta concreta" | Una pregunta, respondida con datos reales y evidencia enlazada | La pregunta de CLAUDE.md §1 |

## 3. Para quién

| Rol | Quién | Qué necesita |
|---|---|---|
| **Usuario del producto** | El equipo de media de 30X, que investiga y decide qué producir | Saber qué publicar, con qué ángulo y por qué, con fuentes que pueda abrir y comprobar |
| **Audiencia editorial** | Ejecutivos, líderes, fundadores y equipos de LATAM que están aprendiendo a aplicar IA en su negocio | Contenido con utilidad empresarial y comprensible sin perfil técnico |

**Criterio de valor:** pesa más la utilidad empresarial y el encaje con la línea editorial de 30X
que la atención acumulada. Una pieza con menos views puede valer más para 30X.

El perfil detallado (pilares, tono, formatos y qué no encaja) se define en
`data/audiences/30x.yaml` (CLAUDE.md §7), revisando a mano los perfiles de @crece30x y
@andresbilbao. No tenemos datos propios sobre el comportamiento real de esa audiencia. Por eso el
audience fit es una evaluación editorial y no una medición.

## 4. Las preguntas que responde el producto

Son las preguntas del usuario. Cada una se enlaza con la pregunta del reto a la que contribuye (§1)
y con los campos del contrato `Opportunity` que la responden (CLAUDE.md §6).

| # | Pregunta del usuario | Pregunta del reto | La responde | Prioridad |
|---|---|---|---|---|
| 1 | ¿Qué temas y piezas empiezan a destacar? | 1 (tendencia temprana) · 2 (por qué funcionó) | `acceleration`, `lifecycle`, `outlier_count`, `top_outlier_ratio` | P0 |
| 2 | ¿Qué está creciendo y con qué evidencia? | 1 | `velocity`, `growth_status`, `confidence`, evidencias | P0 |
| 3 | ¿Qué encaja con la audiencia de 30X? | 3 (relevancia) | `audience_fit_score`, `audience_mix` | P0 |
| 4 | ¿Qué tema ya tiene demasiada cobertura parecida? | 1 | `saturation_score`, etapas `peaking` y `saturated` | P0 |
| 5 | ¿Qué tema internacional se puede adaptar al contexto empresarial latinoamericano? | 3 | `latam_gap` | P1 |
| 6 | ¿Qué publicar, con qué ángulo y formato, y cuándo? | 2 · 3 | `recommendation` y `why_it_matters` (P0) · brief de Content Studio (P1) | P0 / P1 |

## 5. Propuesta de valor

Los servicios de scraping que usa 30X hoy traen datos, pero se quedan en la mitad de la pregunta.
30X Signal responde la otra mitad: por qué funciona algo, en qué etapa está y si le sirve a la
audiencia. Además, junta descubrimiento, evaluación y recomendación editorial en un solo recorrido.

Lo que la demo tiene que demostrar:

- **Relevancia para 30X por encima de la popularidad:** el ranking premia el encaje con la
  audiencia, no el volumen.
- **Evidencia visible:** fuentes originales, fechas, métricas tal como las da la fuente y límites
  de interpretación.
- **Coste bajo y medido:** fuentes abiertas y APIs oficiales, con el coste real de operación
  documentado.
- **LATAM Opportunity Gap:** temas con tracción internacional y poca cobertura observada entre
  referentes empresariales en español.
- **Inteligencia accionable:** ángulo, gancho, estructura y formato por plataforma.
- **Acceso dual:** el mismo análisis en el dashboard y en asistentes de IA vía MCP.

## 6. Mapa de capacidades

Las herramientas de la columna "Inspiración" son una referencia conceptual. No copiamos sus datos,
sus algoritmos propietarios ni su alcance comercial. Las rutas son relativas a `backend/app/` y
siguen la estructura objetivo de CLAUDE.md §10. La prioridad es la de §12.

| Capacidad | Qué hace | Inspiración | Dónde vive | Prioridad |
|---|---|---|---|---|
| Semantic Clustering | Agrupa piezas por tema aunque usen otras palabras u otro idioma, y reduce duplicados | Feedly AI | `intelligence/embeddings`, `intelligence/clustering` | P0 |
| Trend Detection | Clasifica la etapa del tema según la evidencia y admite `unknown` | Exploding Topics | `intelligence/lifecycle` | P0 |
| Momentum Score | Mide velocidad y aceleración del tema, separando medición de estimación | BuzzSumo | `intelligence/velocity`, `intelligence/momentum` | P0 |
| Outlier Detection | Detecta piezas que rinden ≥3× la mediana de su canal o fuente, indicando la referencia | 1of10 / vidIQ | `intelligence/outliers` | P0 |
| Cross-Source Validation | Cuenta fuentes independientes; una republicación no cuenta como confirmación | BuzzSumo | `intelligence/ranking` (`cross_source_score`) | P0 |
| Saturation Detection | Mide la cobertura parecida dentro de la muestra y avisa cuando conviene otro ángulo | Exploding Topics / BuzzSumo | `intelligence/saturation` | P0 |
| Audience Fit Score | Rúbrica 0–5 × 6 criterios contra el perfil de 30X: la evalúa el LLM con justificación y evidencia, con las etiquetas de Jev como pistas; Python combina | SparkToro | `editorial/audience`, `intelligence/relevance` | P0 |
| Opportunity Score | Ordena oportunidades por señal, relevancia, evidencia y saturación | Propia | `intelligence/ranking` | P0 |
| Explainable Insights | Une cada interpretación con su evidencia, su hipótesis y sus limitaciones | Feedly AI | `editorial/analyzer` (`why_it_matters`, `limitations`) | P0 |
| Content Pattern Analysis | Jev clasifica gancho y formato; Python calcula el *lift* de los outliers frente al resto del tema (también momento y autor); el LLM redacta la hipótesis | vidIQ / 1of10 | `editorial/analyzer` | P0 · *lift* tras el núcleo |
| Operating Cost | Registra el consumo de cada API y muestra el coste medido y la proyección mensual | Reto (§1) | `services/costs`, `GET /costs`, panel de coste | P0 |
| Interactive Radar | Permite explorar, filtrar, seleccionar y abrir evidencias | Propia | `frontend/`: vistas Discover y Explore | P0 |
| Historical Tracking | Guarda observaciones y muestra la evolución cuando hay historial | Exploding Topics | `metric_snapshots` (P0) · timeline (P1) | P0 / P1 |
| Content Recommendations | Propone tema, ángulo y formato por plataforma | SparkToro / vidIQ | `recommendation` (P0) · `editorial/briefs` y vista Create (P1) | P0 / P1 |
| Community Sensor | El equipo o la comunidad pega enlaces de redes cerradas y los etiqueta | Reto (§1) | `collectors/manual`, `POST /signals/manual` | P1 |
| LinkedIn Sensor | Posts curados por reacción (API de portabilidad DMA) o por URL, con métricas reales de los exports de 30X y Bilbao, mostrados con el embed oficial | Propia | `collectors/linkedin_dma`, `jobs/import_linkedin_export` | P1 |
| Claim Verification | Verifica cada afirmación del LLM contra la evidencia que cita; lo no respaldado no se publica | Cookbook de TypeSafe | Batería de verificación de Jev | P1 · tras el núcleo (CLAUDE.md §12) |
| LATAM Opportunity Gap | Compara la atención internacional con la cobertura observada en fuentes de Latinoamérica (España fuera: decisión del 17/10) | Propia | `intelligence/audience_mix` → `latam_gap` | P1 |
| MCP Integration | Permite consultar oportunidades, temas y evidencias desde asistentes de IA | Propia | `mcp/` | P1 |

## 7. Qué podemos afirmar con los datos

Este es el vocabulario para todo texto que lea una persona: la UI, las salidas del LLM, las
respuestas MCP y el pitch. Concreta las reglas de CLAUDE.md §2.

| Afirmación | Se sostiene cuando | Cómo se dice |
|---|---|---|
| "Está creciendo" | Hay ≥2 observaciones comparables (`observed`) | Con la tasa y su unidad: "+80 % de piezas nuevas frente a los 3 días anteriores" |
| Estimación o señal preliminar | Hay una sola observación, o la pieza aparece sin aceleración demostrada (`estimated`, `preliminary`) | Con la etiqueta "estimado" o "preliminar"; es una señal, no crecimiento |
| Outlier | Existe la referencia comparable (mediana del canal o de la búsqueda) | "6,1× la mediana de su canal". Si falta la referencia: "sin línea base" |
| Saturación | Siempre, porque es relativa a la muestra | "en las fuentes que monitoreamos" |
| LATAM Gap | Ambos grupos de fuentes tienen cobertura suficiente (CLAUDE.md §5) | "poca cobertura observada en fuentes latinoamericanas". Es una hipótesis sobre la muestra |
| Audience fit | Se aplicó la rúbrica al perfil de 30X | "evaluación editorial asistida por IA", en banda (bajo · medio · alto) con sus 6 niveles y sus justificaciones |
| Por qué funcionó | Se comparó el outlier con el resto del tema | Como hipótesis, con su limitación al lado |
| Gancho o estructura | Depende de lo que se haya podido leer | Distinguir "inferido del título" de "revisado en el contenido" |
| Fuentes independientes | Tras quitar las republicaciones | Medios distintos, no copias de la misma nota |
| Señal de LinkedIn | La marcó un curador (reacción o URL) o viene del export de su dueño | "Curado por el equipo". Métricas solo si vienen del export del dueño |
| Afirmación del análisis | Jev la verificó contra la evidencia que cita | Se publica solo si está respaldada; si no, se elimina |
| Juicio de Jev | Hay respuesta con `confidence` | Con su nivel de confianza; con `confidence < 0.5`, "incierto" |
| Coste | Se midió nuestro gasto real (APIs, Jev, LLM, hosting) | Con la cifra medida y la proyección mensual etiquetada como estimación. El coste de los servicios pagos se cita como dato de 30X ("miles de dólares al año"); no calculamos ahorros |
| Clientes MCP | Se probó la conexión | Solo los clientes que se probaron de verdad |
| Dato ausente | No hay dato | "No disponible" (CLAUDE.md §2) |

## 8. Lista de verificación de la entrega

La entrega está lista cuando se cumple todo lo siguiente con datos reales. Se repasa en la revisión
del domingo a las 12:30 ESP y antes del code freeze (CLAUDE.md §13).

**Datos y trazabilidad**
- 100–300 piezas públicas procesadas, de ≥2 fuentes automáticas, YouTube entre ellas.
- La recolección se puede repetir y conserva el historial de snapshots.
- Cada evidencia lleva enlace original, fuente, fecha de publicación y fecha de observación.
- Lo que entra por curación manual está marcado como tal.
- Las republicaciones no inflan la diversidad de fuentes.
- Ningún dato de ejemplo aparece como resultado real.

**Inteligencia editorial**
- Hay temas agrupados y oportunidades ordenadas con criterios explicables (`lifecycle_reason` y
  desglose del score).
- El equipo ha revisado el ranking a mano.
- Opportunity Score y confianza se muestran por separado.
- Se distinguen `observed`, `estimated`, `preliminary` y los datos ausentes.
- Cada outlier muestra su referencia o explica por qué no se pudo calcular.
- Saturación y LATAM Gap se presentan como relativos a la muestra.
- Cada recomendación enlaza sus fuentes e incluye ángulo y formato, sin prometer resultados.

**Dashboard y MCP**
- El dashboard muestra datos reales y permite filtrar, seleccionar y abrir el detalle y las
  evidencias.
- La UI muestra los estados de carga, vacío, error y métrica no disponible.
- Un cliente MCP consulta oportunidades, detalle y evidencias reales. Se documenta qué clientes se
  probaron.
- Dashboard y MCP usan los mismos servicios, así que muestran el mismo ranking.

**Respuesta al reto**
- El prototipo responde la pregunta de CLAUDE.md §1 con datos reales.
- El panel de coste (y `get_operating_cost` por MCP) muestra el coste medido y la proyección
  mensual por separado, con el desglose por proveedor y la fuente de cada precio.
- Cada juicio de Jev guarda la versión del modelo y su `confidence`. Si hubo clave de Jev, se
  validó con piezas etiquetadas a mano en `data/evaluations/`.
- El audience fit del LLM coincide, a grandes rasgos, con el ranking que el equipo revisó a mano.
- El pitch explica cómo entra LinkedIn (API de portabilidad, exports de 30X, curación y embed
  oficial), cómo entran
  Instagram y TikTok (curación), y por qué así (§2).

**Entrega**
- La app está desplegada y funciona desde una sesión limpia, no solo en local.
- El recorrido de demo (CLAUDE.md §1) funciona de punta a punta.
- El README explica la puesta en marcha y no contiene secretos.
- Están documentados las fuentes activas, los límites de los datos, el algoritmo de priorización y
  lo que quedó pendiente (entregables de CLAUDE.md §13).
- Se entrega antes de la entrega interna (dom 18:15 ESP / 11:15 COL).

## 9. Ideas sin prioridad asignada

Salieron en las conversaciones de producto, pero no tienen prioridad en CLAUDE.md §12. Para que
entren tienen que pasar el filtro de valor (CLAUDE.md §12) y el equipo tiene que acordarlo en el
canal. Si se aprueban, se anotan en `CLAUDE.md`.

- Feedback editorial con tres respuestas: «Me interesa», «No es relevante» y «Ya publicamos sobre
  esto». El endpoint `POST /editorial/feedback` ya figura en CLAUDE.md §6.
- Seguimiento configurable de referentes.
- Tendencias relacionadas.
- Etapa `declining` en `lifecycle`. Cambia el contrato `Opportunity`.
