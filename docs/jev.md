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
| Detectar notas replicadas | Enlace compartido en Python; **Jev** en la franja dudosa; regla de respaldo si Jev no decide |
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

Batería `piece.v3.yaml`. Cada pregunta mide una sola condición observable; las preguntas compuestas
de la v1 dejaban inciertas más de la mitad de las piezas. La v3 es la v2 más `ai_in_title`
(validación en `data/evaluations/jev_piece_v3_eval.md`).

| Pregunta | Tipo y criterio | Para qué |
|---|---|---|
| `about_ai` | `noul`: ¿el tema principal es la IA? | Filtrar ruido antes del clustering |
| `ai_in_title` | `noul`: ¿el título habla de IA? | Segunda condición del filtro: una pieza sale solo si `about_ai` y `ai_in_title` son "no" seguros. Jev lee `about_ai` de forma literal sobre todo el texto y quitaba piezas con la IA en el título y una descripción sobre otra cosa (24 de 55 quitadas eran buenas; con v3, 9 de 36) |
| `injection` | `noul`: ¿el texto contiene instrucciones dirigidas a un sistema de IA? | Regla 6: si supera 0,5, la pieza no entra en el contexto del LLM. Es una heurística, no la defensa principal |
| `format`, `format_rev` | `choice` contrastivo (qué es y qué no): noticia · opinión · tutorial · caso de uso · entrevista · demo · pregunta a la comunidad · lista | "Temas y formatos" del reto |
| `hook`, `hook_rev` | `choice`: pregunta · dato o cifra · contraintuitivo · historia · cómo hacer · noticia · lista | "Por qué funcionó" |
| `launch` | `noul`: ¿anuncia un producto, modelo, función o versión nueva? | Distinguir un pico de noticia de una tendencia |
| **Pistas para el LLM** | | El LLM decide el audience fit; estos conteos le llegan como datos y la UI los muestra como apoyo |
| `business_use` | `noul`: ¿trata del uso, la adopción o el impacto de la IA en organizaciones? | Criterios "impacto en decisiones" y "aplicación real". Es un juicio de audiencia: ~30 % incierto con cualquier redacción, por eso no filtra. Incierto en 360 de 1.579 piezas (23 %); 95 % de acuerdo cuando está seguro (200 etiquetadas); reformularla en la v3 no mejoró |
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

Implementada en `backend/app/editorial/prompts/jev/pair.v1.yaml`, con la lógica pura en
`intelligence/replicas.py` y la caché en `services/replicas.py`. Corre en `analyze` entre el
clustering y los scores.

Solo se comparan piezas del mismo tema y de medios distintos (`outlet_key`: todas las queries de HN
son un medio). Para cada par:

1. **Enlace compartido** (la misma `url`, o el `target_url` de HN o Reddit apuntando a la otra, o
   los dos `target_url` iguales): es republicación y no se pregunta a Jev.
2. **Candidato a Jev** si la similitud coseno es ≥ 0,70 o tienen el mismo título normalizado (≥ 5
   palabras). Se juzgan de mayor a menor similitud, con un tope de 250 llamadas nuevas por
   ejecución.
3. Un veredicto seguro de Jev manda en las dos direcciones: el nivel 3 es republicación y los
   niveles 0–2 son independientes, aunque la regla diga otra cosa. También cuando la regla los une
   a través de otras piezas: en la nota que contiene un par independiente se quitan las aristas de
   la regla.
4. **Regla de respaldo** (sin clave, fallo de Jev, veredicto incierto o fuera del tope): mismo
   título normalizado o similitud ≥ 0,90. Lo que decide la regla se marca en `limitations` como
   no verificado con Jev. Una republicación cuenta como verificada solo si llega a su representante
   por enlaces compartidos o síes de Jev, sin pasar por la regla.

`state`: `{a: {title, description, source}, b: {title, description, source}}`, ordenado por
`item_id` para que (A, B) y (B, A) compartan caché. La descripción se recorta a 500 caracteres; sin
URL, segmento, región ni métricas.

| Pregunta | Tipo y criterio | Para qué |
|---|---|---|
| `same_story` | `score`: temas distintos · mismo tema, hechos distintos · mismo acontecimiento contado por separado · la misma nota replicada | Fuentes independientes (`cross_source_score`) y saturación |

Es el patrón *entity alignment* del cookbook. Se redondea `score` al nivel más cercano. El nivel 2
("mismo acontecimiento contado por separado") no es incierto: es cobertura independiente, que es
justo la validación cruzada que mide `cross_source_score`. La incertidumbre la da `confidence`.

Las piezas unidas por republicaciones forman una nota; su representante es la publicada antes. Las
filas van a `jev_judgments` con `battery = "pair"` y `content_item_id` nulo: la clave es el hash del
`state` canónico, la batería, su versión y el modelo.

### 3. Verificación: después del LLM

**Estado: implementada y apagada por defecto (`JEV_VERIFY_CLAIMS=false`) hasta validarla.** Mientras
esté apagada, `why_it_matters` solo pasa las comprobaciones de Python y no se puede decir que Jev
lo verifica. La validación con afirmaciones reales no la superó todavía (ver más abajo).

El LLM devuelve `why_it_matters` como una lista de afirmaciones, cada una con las URLs de la
evidencia que la respalda. En `analyze`, por cada afirmación:

1. Python comprueba que cita una pieza que el LLM recibió y que no trae cifras que no estén en los
   datos ni en la evidencia (`intelligence/explanation.py`, `python_checked`).
2. Jev responde la batería `claim.v1`
   (`backend/app/editorial/prompts/jev/claim.v1.yaml`) en una llamada: un `choice` `support`
   (`supports` · `contradicts` · `says_nothing`, patrón *citation check* del cookbook) y su
   `support_rev`, con las opciones en orden inverso para detectar el sesgo hacia la primera.
3. Se publica solo si `support` es `supports` con `confidence` ≥ 0,8 y `support_rev` también dice
   `supports` (`claim_supported`, en `intelligence/jev.py`).

**Qué va en el `state`:** la afirmación, los datos medidos que recibió el LLM (`measured_facts`,
las mismas frases de `opportunity_facts`) y las piezas citadas que el LLM recibió, solo con fuente,
título y descripción. Sin URL, plataforma, segmento ni región, y sin las justificaciones del fit.
Los datos medidos entran porque las afirmaciones reales mezclan lo que dicen las piezas con lo que
calculó Python («saturado», «4 piezas frente a 12», «conviene descartar»). Contra las piezas solas,
Jev, que lee de forma literal, dejaría sin respaldo la frase de qué conviene hacer. Las
justificaciones del fit no entran: son texto del LLM, y verificar al LLM con su propio texto sería
circular.

**Notas en `limitations`** (sin cambio de contrato; la UI las muestra en «Qué no sabemos»):

- «Jev no encontró respaldo en la evidencia citada para N afirmaciones del LLM: no se publican.»
  Las afirmaciones rechazadas se quitan siempre del texto, también en un tema no verificado.
- Si Jev rechaza todas, el tema conserva la plantilla de datos medidos con la nota de «ninguna
  afirmación superó la comprobación de evidencia», como cuando falla Python.
- Si falta el juicio de alguna afirmación (no hay `TYPESAFE_API_KEY` y no estaba en caché, Jev
  falló o se agotó el presupuesto), se publican las que pasaron Python y Jev no rechazó, y el tema
  entero lleva la nota «"Por qué importa" no está verificado por Jev»: no se mezclan en el mismo
  texto frases verificadas y sin verificar sin decirlo.

**Caché y presupuesto:** `jev_judgments` con `battery = "claim"` y `content_item_id` nulo. La clave
es el hash del `state`, la batería, su versión y el modelo, así que una segunda ejecución con las
mismas explicaciones no llama a Jev. Como mucho 200 llamadas nuevas por ejecución
(`MAX_CLAIM_VERIFICATIONS_PER_RUN`), repartidas en el orden del ranking, para gastar primero en lo
que se ve arriba del Radar. Cada llamada real cuenta en `usage_events` como `claim_battery`.

**Validación (18/10, no adoptada):** 40 afirmaciones reales de la ejecución servida y 10 negativas
sintéticas, etiquetadas antes de ver a Jev ([`jev_claim_v1_eval.md`](../data/evaluations/jev_claim_v1_eval.md)).
El criterio estaba fijado de antemano: conserva ≥ 70 % de las respaldadas, filtra ≥ 60 % de las
negativas y ≥ 80 % de los temas conservan alguna afirmación. `claim.v1` conserva el 58 % y su
revisión `claim.v2` el 67 %; las dos filtran el 93 %. Por eso `JEV_VERIFY_CLAIMS` sigue en `false`.
La causa principal es el umbral de `confidence` ≥ 0,8: casi todas las respaldadas que se pierden
tienen `supports` en las dos preguntas con menos confianza. Bajarlo es una decisión del equipo y
pide una muestra nueva para medirlo.

**Limitaciones:**

- La evidencia es solo título y descripción. El LLM tiene que ceñirse a lo que dicen; si no, casi
  todo saldrá `says_nothing`.
- Una ausencia («ninguna pieza muestra…») se comprueba solo contra las piezas citadas, no contra
  todas las del tema.
- **Pendiente:** los briefs (`POST /editorial/brief`, `generate_editorial_brief`) no se verifican.
  Se generan dentro del request, y verificar ahí añadiría la latencia de Jev y una ruta de fallo
  nueva en el MCP. Además, el brief no tiene la forma «afirmación + URLs».

## Del juicio a la decisión (en Python)

| Tipo | Se acepta si | Si no |
|---|---|---|
| `choice` | La probabilidad máxima es ≥ 0,6 y coincide con su `_rev` | "Incierto" |
| `noul` | ≥ 0,7 cuenta como sí; ≤ 0,3, como no. `noul` no devuelve `confidence`: si hace falta una, se usa \|2p − 1\| | "Incierto" |
| `score` | `confidence` ≥ 0,5; por debajo es incierto. `score` es una **media ponderada** por probabilidad, no un nivel: se redondea al nivel más cercano y nunca se interpreta como magnitud precisa. En el par, el nivel redondeado decide (3 = republicación, 0–2 = independientes) | "Incierto" |

Lo incierto no entra en los conteos y la UI lo muestra como tal. Son umbrales iniciales; se ajustan
con la validación.

## "Por qué funcionó", medido

Con las respuestas de la batería de pieza, Python compara los outliers con el resto del tema:

```
lift = (% de outliers con el rasgo) / (% del resto con el rasgo)
```

Un rasgo con lift ≥ 2 que tienen al menos 2 outliers es un "patrón observado". Si no llega, es
"anecdótico". Con pocos outliers por tema, casi todo saldrá "anecdótico", y se dice así.

**Implementado (18/10), solo para el gancho:** `intelligence/why_it_worked.py` → campo
`outlier_hooks` de `Opportunity`, que el MCP devuelve en `analyze_opportunity`. Cuenta solo piezas
originales (una republicación copia el título), deja fuera las piezas sin `outlier_ratio` y las de
gancho incierto, y no compara si el resto tiene menos de 2 piezas. Si el resto no usa un gancho, el
lift queda en `null`. El gancho se validó antes de usarlo: 94 % de acuerdo en las 31 de 36 piezas
que Jev decide (`data/evaluations/jev_hook_v3_eval.md`). Pendiente: que el LLM redacte la hipótesis
y Jev la verifique. Ejemplo: *"Los outliers usan
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

> **Estado (17/10):** hecho con etiquetas de evaluadores LLM a ciegas, no humanas:
> `jev_piece_v2_eval.md` (40 piezas) y `jev_piece_v3_eval.md` (200 piezas, comparación v2 → v3).
> Faltan las etiquetas a mano; las hojas y los scripts de `data/evaluations/` sirven igual con ellas.

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
| Pieza (v3) | ~1.500 de backfill + ~200 al día | ~2.260 (medido) | ~0,14 $ el backfill; ~0,57 $/mes |
| Par | ~220 pares en la primera ejecución; después, solo los nuevos | ~800 | ~0,01 $ la primera ejecución |
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
