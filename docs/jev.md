# Jev: decisiones atómicas sobre piezas

> Cómo usamos Jev (TypeSafe): qué le preguntamos, umbrales, paralelismo, caché, validación y coste.
> Los principios están en [`CLAUDE.md`](../CLAUDE.md) §7. Verificado contra
> [docs.typesafe.ai](https://docs.typesafe.ai) el 2026-10-17, con una revisión independiente.

## Por qué Jev

- **Lo sugiere el reto:** "modelos que clasifican y priorizan (JEV puede ser un buen aliado aquí)".
- **Devuelve decisiones, no texto:** respuestas tipadas con probabilidades y, en `choice` y `score`,
  `confidence`. Así sabemos cuándo duda, en vez de inventar.
- **Paralelo por diseño:** las preguntas de una llamada se evalúan en paralelo y aisladas contra el
  mismo `state`. Añadir preguntas apenas cambia la latencia y unas no contaminan a otras.
- **Barato si se agrupa:** 0,042 $ por millón de tokens de entrada, salida gratis, y el `state` se
  paga una vez por llamada. En el cookbook oficial, 13 preguntas en una llamada costaron 12 veces
  menos que 13 llamadas de una pregunta.

## Reparto del trabajo

| Paso | Quién lo hace |
|---|---|
| Agrupar piezas en temas | Embeddings + scikit-learn |
| Clasificar cada pieza: relevancia, formato, gancho… | **Jev** |
| Detectar notas replicadas | **Jev** (mientras no esté: regla de similitud coseno + fuente distinta) |
| Calcular: velocidad, outliers, lifecycle, *lift*, scores y `recommendation` | Python |
| Evaluar cada tema (los 6 criterios del audience fit) | LLM |
| Redactar: nombres de tema, `why_it_matters`, `limitations`, ángulos, briefs | LLM |
| Verificar cada afirmación del LLM contra su evidencia | **Jev** |
| Validar todas las entradas y salidas | Pydantic |

Para el pitch: *los embeddings agrupan, Jev clasifica cada pieza, Python calcula, el LLM evalúa cada
tema y redacta, y Jev verifica lo que escribe el LLM.*

**Por qué el tema no lo evalúa Jev:** el audience fit es un juicio de conjunto sobre un tema de hasta
decenas de piezas. Según su propia documentación, Jev lee de forma literal, sus niveles de `score`
no están calibrados como números y pierde precisión cuando el `state` crece. Eso lo hace mejor el
LLM.

## Una llamada por entidad, con todas sus preguntas

Cada entidad (una pieza, un par de piezas o una afirmación del LLM) se evalúa en **una sola
llamada** que lleva todas las preguntas que podamos necesitar: una *batería*. Es el patrón
*speculative fan-out* de TypeSafe. El código decide después qué respuestas usa.

## Las tres baterías

### 1. Pieza: una llamada por pieza nueva, en el job `analyze`

`state`: `{title, description (≤ 1.000 caracteres; se omite si no hay), channel, platform, language}`.
Nunca lleva el segmento ni la región de la fuente: con ellos, Jev contesta a partir de la fuente y no
del contenido (medido: `latam_context` salía sí en el 100 % de las piezas de fuentes LATAM).

Batería `piece.v2.yaml`. Cada pregunta mide una sola condición observable; las preguntas compuestas
de la v1 dejaban inciertas más de la mitad de las piezas.

| Pregunta | Tipo y criterio | Para qué |
|---|---|---|
| `about_ai` | `noul`: ¿el tema principal es la IA? | Filtrar ruido antes del clustering |
| `injection` | `noul`: ¿el texto contiene instrucciones dirigidas a un sistema de IA? | Regla 6: si supera 0,5, la pieza no entra en el contexto del LLM. Es una heurística, no la defensa principal |
| `format`, `format_rev` | `choice` contrastivo (qué es y qué no): noticia · opinión · tutorial · caso de uso · entrevista · demo · pregunta a la comunidad · lista | "Temas y formatos" del reto |
| `hook`, `hook_rev` | `choice`: pregunta · dato o cifra · contraintuitivo · historia · cómo hacer · noticia · lista | "Por qué funcionó" |
| `launch` | `noul`: ¿anuncia un producto, modelo, función o versión nueva? | Distinguir un pico de noticia de una tendencia |
| **Pistas para el LLM** | | El LLM decide el audience fit; estos conteos le llegan como datos y la UI los muestra como apoyo |
| `business_use` | `noul`: ¿trata del uso, la adopción o el impacto de la IA en organizaciones? | Criterios "impacto en decisiones" y "aplicación real". Es un juicio de audiencia: ~30 % incierto con cualquier redacción, por eso no filtra |
| `dev_audience` | `noul`: ¿va dirigida sobre todo a desarrolladores o investigadores? | "Todavía no llegó a ejecutivos" |
| `business_case` | `noul`: ¿describe cómo una organización concreta usa la IA? (no cuenta el lanzamiento de un proveedor) | Criterio "aplicación real" |
| `tech_jargon` | `noul`: ¿usa jerga técnica de software o de IA? | Criterio "comprensible para directivos" |
| `latam_context` | `noul`: ¿menciona Latinoamérica o un país, empresa, institución o persona de la región? (España no cuenta) | Criterio "relevancia LATAM" |
| `pillar` | `choice`: los pilares de `data/audiences/30x.yaml` + "ninguno" | Criterio "encaje con pilares 30X". Pendiente: entra cuando exista el perfil |

**Medido sobre una muestra fija de 120 piezas** (piezas inciertas, v1 → v2): relevancia 55 % →
`about_ai` 17 %; anuncio 69 % → `launch` 8–10 %; legibilidad (`score` de 4 niveles) 42 % →
`tech_jargon` 14 %; caso real 23 % → 14–16 %; `latam_context` sí fuera de LATAM 38–42 % → 0 %.
Repetir la misma llamada cambia como mucho 4 de 120 decisiones por pregunta. Menos incierto no
es más acierto: el acierto se mide con la validación de abajo.

Los `_rev` repiten la pregunta con las opciones en orden inverso. Jev tiende a elegir la primera
opción; si las dos respuestas no coinciden, la clasificación es "incierta". Van en la misma llamada,
así que no añaden latencia y apenas coste.

### 2. Par: una llamada por par candidato

Los candidatos son pares de piezas del mismo tema, de fuentes distintas y con embeddings muy
parecidos.

`state`: `{a: {title, description, source}, b: {title, description, source}}`.

| Pregunta | Tipo y criterio | Para qué |
|---|---|---|
| `same_story` | `score`: temas distintos · mismo tema, hechos distintos · mismo acontecimiento contado por separado · la misma nota replicada | Fuentes independientes (`cross_source_score`) y saturación |

Es el patrón *entity alignment* del cookbook. Se redondea `score` al nivel más cercano, y los
niveles intermedios se marcan como inciertos. Mientras esta batería no esté, un par con similitud
coseno ≥ umbral y fuente distinta cuenta como nota replicada.

### 3. Verificación: después del LLM

El LLM devuelve `why_it_matters` y los briefs como una lista de afirmaciones, cada una con el id de
la evidencia que la respalda. Por cada afirmación:

1. Python comprueba que la evidencia citada pertenece al tema.
2. Jev responde un `choice` contra el texto de esa evidencia: `supports` · `contradicts` ·
   `says_nothing` (cookbook *citation check*).
3. Se publica solo si es `supports` con `confidence` ≥ 0,8. Un `supports` por debajo de 0,8, un
   `says_nothing` o un `contradicts` no se publican y quedan registrados.

**Limitación:** la evidencia es solo título y descripción. El LLM tiene que ceñirse a lo que dicen;
si no, casi todo saldrá `says_nothing`. Si no sobrevive ninguna afirmación, la UI dice "sin
afirmaciones verificables" en vez de mostrar un texto vacío.

## Del juicio a la decisión (en Python)

| Tipo | Se acepta si | Si no |
|---|---|---|
| `choice` | La probabilidad máxima es ≥ 0,6 y coincide con su `_rev` | "Incierto" |
| `noul` | ≥ 0,7 cuenta como sí; ≤ 0,3, como no. `noul` no devuelve `confidence`: si hace falta una, se usa \|2p − 1\| | "Incierto" |
| `score` | `confidence` ≥ 0,5. `score` es una **media ponderada** por probabilidad, no un nivel: para leer la `legend` se redondea al nivel más cercano, y nunca se interpreta como magnitud precisa | "Incierto" |

Lo incierto no entra en los conteos y la UI lo muestra como tal. Son umbrales iniciales; se ajustan
con la validación.

## "Por qué funcionó", medido

Con las respuestas de la batería de pieza, Python compara los outliers con el resto del tema:

```
lift = (% de outliers con el rasgo) / (% del resto con el rasgo)
```

Un rasgo con lift ≥ 2 que tienen al menos 2 outliers es un "patrón observado". Si no llega, es
"anecdótico". Con pocos outliers por tema, casi todo saldrá "anecdótico", y se dice así. El LLM
redacta la hipótesis a partir de esa tabla y la batería 3 la verifica. Ejemplo: *"Los outliers usan
ganchos de 'dato o cifra' 2,5 veces más que el resto (3 de 4, frente a 3 de 10). Hipótesis con
muestra pequeña."*

## Paralelismo y caché

- **Concurrencia:** `AsyncTypeSafeClient` con `asyncio.Semaphore(6)`. El cookbook usa 6 workers
  porque el endpoint limita por encima de ese ritmo. El SDK reintenta 408, 429 y los 5xx con
  backoff (2 reintentos por defecto). Las entidades van en paralelo; 200 piezas nuevas se procesan
  en segundos.
- **Caché:** la clave es el hash del `state` + la versión de la batería + la versión del modelo. Lo
  que no cambia no se vuelve a preguntar, así que el coste es mínimo y el resultado reproducible.
- **Tabla `jev_judgments`:** entidad, pregunta, versión de la batería, modelo (`response.model`),
  respuesta, probabilidades, `confidence` y fecha. Permite auditar y explicar en la UI ("caso de
  uso, 0,92").
- **Baterías versionadas** en `backend/app/editorial/prompts/jev/<batería>.v<n>.yaml` (convención de
  prompts versionados, CLAUDE.md §11).
- **Coste:** cada llamada registra `usage.input_tokens` en `usage_events` (CLAUDE.md §4).
- **Un único cliente** en `intelligence/jev.py`: si cambia el acceso (directo o por una pasarela), el
  cambio se queda ahí.

## Modelos y versión

| Modelo | Alias | Notas |
|---|---|---|
| `jev-1.13.0` | `jev-latest` | **El que fijamos** (`JEV_MODEL`) |
| `jev-1.14.0` | `jev-preview` | Disponible desde el 14 de octubre de 2026 |

Los alias cambian las respuestas sin aviso cuando sale una versión nueva; por eso se fija la
versión y se guarda `response.model` en cada resultado. Límites: 64k tokens por petición y 32k por
pregunta. Solo texto (las imágenes son experimentales).

## Validación antes de confiar

En cuanto haya clave:

- `data/evaluations/jev_pieces.yaml`: entre 30 y 50 piezas reales (ES y EN) etiquetadas a mano para
  las preguntas de la batería de pieza (`about_ai`, `format`, `hook`, `business_use`, `tech_jargon`,
  `business_case`, `latam_context`).
- Se mide el acuerdo por pregunta, se decide en qué idioma van las instrucciones (ES o EN) y se
  ajustan los umbrales. Una pregunta con menos del 70 % de acuerdo no se usa en la demo.
- Límites documentados de jev-1.13 y cómo los cubrimos:

  | Límite | Cómo lo cubrimos |
  |---|---|
  | Sesgo hacia la primera opción | Las preguntas `_rev` |
  | Lectura literal | Criterios explícitos, con casos límite; el juicio de conjunto lo hace el LLM |
  | Sensibilidad a textos que defienden su propia etiqueta | El texto externo va solo en `state`; la pregunta `injection` ayuda, pero la defensa real es no dar tools al LLM, salida estructurada y texto delimitado |
  | Niveles de `score` poco calibrados | Redondear al nivel; nunca interpolar magnitudes |
  | Pierde precisión con `state` grande | Una pieza o un par por llamada |
  | Español sin documentar | La validación de arriba |

## Coste estimado

Es una estimación con los precios oficiales; el coste real lo mide `usage_events`.

| Batería | Volumen | Tokens por llamada (aprox.) | Coste |
|---|---|---|---|
| Pieza (v2) | ~1.500 de backfill + ~200 al día | ~2.100 (medido) | ~0,13 $ el backfill; ~0,55 $/mes |
| Par | ~500 al día | ~800 | ~0,50 $/mes |
| Verificación | ~100 afirmaciones al día | ~800 | ~0,10 $/mes |

Total: alrededor de 1 $ al mes.

## Acceso: confirmarlo hoy

1. Intentar crear la clave en [console.typesafe.ai](https://console.typesafe.ai/keys). Según fuentes
   de terceros, el registro directo está pausado desde el 22 de septiembre (no verificado).
2. Si está pausado, preguntar a la organización: el reto sugiere JEV y puede que tenga acceso.
3. [Vercel AI Gateway](https://vercel.com/changelog/ai-gateway-now-supports-typesafe-clients-and-an-http-api-for-jev)
   admite preguntas tipadas con el modelo `typesafe-ai/jev`, pero no documenta cómo fijar la
   versión. OpenRouter es compatible con OpenAI y no documenta las preguntas tipadas.
4. **Si no hay clave antes de las 19:00 ESP de hoy,** el LLM hace la batería de pieza en lote, con
   el mismo modelo Pydantic (`PieceJudgment`). Cuando llegue la clave, Jev la sustituye sin tocar
   nada más.

## P2

- **Miniaturas de YouTube como imagen en `state`** (PNG o JPEG de 280 a 1.568 px, cabecera
  `TypeSafe-Danger-Zone-Images: true`). La documentación las marca como experimentales, no listas
  para producción.
- **Cola "Revisar" en la UI** con los juicios inciertos de las oportunidades más altas.
