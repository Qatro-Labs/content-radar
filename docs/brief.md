# 30X Signal — Brief de producto

> **Qué es:** el *porqué* de 30X Signal. Recoge el problema de 30X, para quién lo construimos, qué
> capacidades cuentan, qué podemos afirmar con los datos y cuándo está lista la entrega.
> El *cómo* (reglas, contratos, scoring, stack y calendario) vive en [`CLAUDE.md`](../CLAUDE.md).
> Si este archivo y `CLAUDE.md` se contradicen, manda `CLAUDE.md` y se corrige este.

---

## 1. El problema

30X necesita convertir la conversación sobre IA en contenido útil para líderes y equipos de empresa
de Latinoamérica. Las señales están repartidas entre plataformas, idiomas y formatos, y lo más
popular no siempre es lo que más le sirve a esa audiencia.

Reunir enlaces no resuelve nada. Hay que convertir señales sueltas en **una decisión editorial
respaldada por fuentes**. El producto gira en torno a esa diferencia entre *popularidad* y
*oportunidad editorial*.

## 2. Para quién

| Rol | Quién | Qué necesita |
|---|---|---|
| **Usuario del producto** | Quien investiga y decide los contenidos de 30X | Saber qué publicar, con qué ángulo y por qué, con fuentes que pueda abrir y comprobar |
| **Audiencia editorial** | Ejecutivos, líderes, fundadores y equipos de LATAM que quieren aplicar IA en su negocio | Contenido con utilidad empresarial y comprensible sin perfil técnico |

**Criterio de valor:** pesa más la utilidad empresarial y el encaje con la línea editorial de 30X
que la atención acumulada. Una pieza con menos views puede valer más para 30X.

El perfil detallado (pilares, tono, formatos y qué no encaja) se define en
`data/audiences/30x.yaml` (CLAUDE.md §7). No tenemos datos propios sobre el comportamiento real de
esa audiencia. Por eso el audience fit es una evaluación editorial y no una medición.

## 3. Las preguntas que responde el producto

Son las preguntas del usuario. Cada una se enlaza con la pregunta del reto a la que contribuye
(CLAUDE.md §1) y con los campos del contrato `Opportunity` que la responden (CLAUDE.md §6).

| # | Pregunta del usuario | Pregunta del reto | La responde | Prioridad |
|---|---|---|---|---|
| 1 | ¿Qué temas y piezas empiezan a destacar? | Tendencia temprana · Por qué funcionó | `acceleration`, `lifecycle`, `outlier_count`, `top_outlier_ratio` | P0 |
| 2 | ¿Qué está creciendo y con qué evidencia? | Tendencia temprana | `velocity`, `growth_status`, `confidence`, evidencias | P0 |
| 3 | ¿Qué encaja con la audiencia de 30X? | Relevancia | `audience_fit_score`, `audience_mix` | P0 |
| 4 | ¿Qué tema ya tiene demasiada cobertura parecida? | Tendencia temprana | `saturation_score`, etapas `peaking` y `saturated` | P0 |
| 5 | ¿Qué tema internacional se puede adaptar al contexto empresarial latinoamericano? | Relevancia | `latam_gap` | P1 |
| 6 | ¿Qué publicar, con qué ángulo y formato, y cuándo? | Por qué funcionó · Relevancia | `recommendation` y `why_it_matters` (P0) · brief de Content Studio (P1) | P0 / P1 |

## 4. Propuesta de valor

30X Signal junta descubrimiento, evaluación y recomendación editorial en un solo recorrido. Cada
oportunidad deja claro qué está pasando, por qué le importa a 30X, qué datos la respaldan y cómo
convertirla en contenido.

Lo que la demo tiene que demostrar:

- **Relevancia para 30X por encima de la popularidad:** el ranking premia el encaje con la audiencia,
  no el volumen.
- **Evidencia visible:** fuentes originales, fechas, métricas tal como las da la fuente y límites de
  interpretación.
- **LATAM Opportunity Gap:** temas con tracción internacional y poca cobertura observada entre
  referentes empresariales en español.
- **Inteligencia accionable:** ángulo, gancho, estructura y formato por plataforma.
- **Acceso dual:** el mismo análisis en el dashboard y en asistentes de IA vía MCP.

## 5. Mapa de capacidades

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
| Audience Fit Score | Rúbrica 0–5 × 6 criterios contra el perfil de 30X, con justificación por criterio | SparkToro | `editorial/audience`, `intelligence/relevance` | P0 |
| Opportunity Score | Ordena oportunidades por señal, relevancia, evidencia y saturación | Propia | `intelligence/ranking` | P0 |
| Explainable Insights | Une cada interpretación con su evidencia, su hipótesis y sus limitaciones | Feedly AI | `editorial/analyzer` (`why_it_matters`, `limitations`) | P0 |
| Content Pattern Analysis | Compara los outliers con el resto del tema: gancho, formato, estructura y timing | vidIQ / 1of10 | `editorial/analyzer` | P0 |
| Interactive Radar | Permite explorar, filtrar, seleccionar y abrir evidencias | Propia | `frontend/`: vistas Discover y Explore | P0 |
| Historical Tracking | Guarda observaciones y muestra la evolución cuando hay historial | Exploding Topics | `metric_snapshots` (P0) · timeline (P1) | P0 / P1 |
| Content Recommendations | Propone tema, ángulo y formato por plataforma | SparkToro / vidIQ | `recommendation` (P0) · `editorial/briefs` y vista Create (P1) | P0 / P1 |
| LATAM Opportunity Gap | Compara la atención internacional con la cobertura observada en español | Propia | `intelligence/audience_mix` → `latam_gap` | P1 |
| MCP Integration | Permite consultar oportunidades, temas y evidencias desde asistentes de IA | Propia | `mcp/` | P1 |

## 6. Qué podemos afirmar con los datos

Este es el vocabulario para todo texto que lea una persona: la UI, las salidas del LLM, las
respuestas MCP y el pitch. Concreta las reglas de CLAUDE.md §2.

| Afirmación | Se sostiene cuando | Cómo se dice |
|---|---|---|
| "Está creciendo" | Hay ≥2 observaciones comparables (`observed`) | Con la tasa y su unidad: "+80 % de piezas nuevas frente a los 3 días anteriores" |
| Estimación o señal preliminar | Hay una sola observación, o la pieza aparece sin aceleración demostrada (`estimated`, `preliminary`) | Con la etiqueta "estimado" o "preliminar"; es una señal, no crecimiento |
| Outlier | Existe la referencia comparable (mediana del canal o de la búsqueda) | "6,1× la mediana de su canal". Si falta la referencia: "sin línea base" |
| Saturación | Siempre, porque es relativa a la muestra | "en las fuentes que monitoreamos" |
| LATAM Gap | Ambos grupos de fuentes tienen cobertura suficiente (CLAUDE.md §5) | "poca cobertura observada entre referentes en español". Es una hipótesis sobre la muestra |
| Audience fit | Se aplicó la rúbrica al perfil de 30X | "evaluación editorial asistida por IA" |
| Por qué funcionó | Se comparó el outlier con el resto del tema | Como hipótesis, con su limitación al lado |
| Gancho o estructura | Depende de lo que se haya podido leer | Distinguir "inferido del título" de "revisado en el contenido" |
| Fuentes independientes | Tras quitar las republicaciones | Medios distintos, no copias de la misma nota |
| Clientes MCP | Se probó la conexión | Solo los clientes que se probaron de verdad |
| Dato ausente | No hay dato | "No disponible" (CLAUDE.md §2) |

## 7. Lista de verificación de la entrega

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

**Entrega**
- La app está desplegada y funciona desde una sesión limpia, no solo en local.
- El recorrido de demo (CLAUDE.md §1) funciona de punta a punta.
- El README explica la puesta en marcha y no contiene secretos.
- Están documentados las fuentes activas, los límites de los datos, el algoritmo de priorización y
  lo que quedó pendiente (entregables de CLAUDE.md §13).
- Se entrega antes de la entrega interna (dom 18:15 ESP / 11:15 COL).

## 8. Ideas sin prioridad asignada

Salieron en las conversaciones de producto, pero no tienen prioridad en CLAUDE.md §12. Para que
entren tienen que pasar el filtro de valor (§12) y el equipo tiene que acordarlo en el canal. Si se
aprueban, se anotan en `CLAUDE.md`.

- Feedback editorial con tres respuestas: «Me interesa», «No es relevante» y «Ya publicamos sobre
  esto». El endpoint `POST /editorial/feedback` ya figura en CLAUDE.md §6.
- Seguimiento configurable de referentes.
- Tendencias relacionadas.
- Etapa `declining` en `lifecycle`. Cambia el contrato `Opportunity`.
