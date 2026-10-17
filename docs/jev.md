# Jev: la capa de decisión de 30X Signal

> Cómo usamos Jev (TypeSafe): baterías de preguntas, umbrales, paralelismo, caché, validación y
> coste. Los principios están en [`CLAUDE.md`](../CLAUDE.md) §7. Verificado contra
> [docs.typesafe.ai](https://docs.typesafe.ai) el 2026-10-17.

## Por qué Jev

- **Lo sugiere el reto:** "modelos que clasifican y priorizan (JEV puede ser un buen aliado aquí)".
- **Devuelve decisiones, no texto:** respuestas tipadas con probabilidades y `confidence`. Encaja
  con la regla 4 (Python calcula) y con "nunca inventar datos".
- **Paralelo por diseño:** las preguntas de una llamada se evalúan en paralelo y aisladas contra el
  mismo `state`. Añadir preguntas apenas cambia la latencia y unas no contaminan a otras.
- **Barato si se agrupa:** 0,042 $ por millón de tokens de entrada, salida gratis, y el `state` se
  paga una vez por llamada. En el cookbook oficial, 13 preguntas en una llamada costaron 12 veces
  menos y fueron 10 veces más rápidas (0,27 s) que 13 llamadas de una pregunta.

## Reparto del trabajo

| Paso | Quién lo hace |
|---|---|
| Agrupar piezas en temas | Embeddings + scikit-learn |
| Decidir: clasificar, puntuar, verificar | Jev |
| Calcular: umbrales, pesos, scores y `recommendation` | Python |
| Redactar: nombres de tema, `why_it_matters`, briefs | LLM generativo |

Para el pitch: *los embeddings agrupan, Jev decide, Python calcula, el LLM redacta y Jev verifica lo
que el LLM escribe.*

## Una llamada por entidad, con todas sus preguntas

Cada entidad (una pieza, un par de piezas, un tema o un texto generado) se evalúa en **una sola
llamada** que lleva todas las preguntas que podamos necesitar: una *batería*. Es el patrón
*speculative fan-out* de TypeSafe. El código decide después qué respuestas usa.

## Las cuatro baterías

### 1. Pieza: una llamada por pieza nueva, en el job `analyze`

`state`: `{title, description (≤ 1.000 caracteres), channel, platform, language}`.

| Pregunta | Tipo y criterio | Para qué |
|---|---|---|
| `relevant` | `noul`: ¿trata de IA aplicada a empresas u organizaciones? | Filtrar ruido antes del clustering |
| `injection` | `noul`: ¿el texto contiene instrucciones dirigidas a un sistema de IA? | Regla 6: si supera 0,5, la pieza no entra en el contexto del LLM |
| `format`, `format_rev` | `choice`: tutorial · opinión · noticia o lanzamiento · caso de uso · entrevista o podcast · demo · lista | "Temas y formatos" del reto |
| `hook`, `hook_rev` | `choice`: pregunta · dato o cifra · contraintuitivo · historia · cómo hacer · noticia · lista | "Por qué funcionó" |
| `pillar` | `choice`: los pilares de `data/audiences/30x.yaml` + "ninguno" | Criterio "encaje con pilares 30X" |
| `exec_readability` | `score` en 4 niveles: de "requiere perfil técnico" a "lo entiende un directivo sin perfil técnico" | Criterio "comprensible para directivos" y la lectura "aún no llegó a ejecutivos" |
| `business_case` | `noul`: ¿describe un caso real en una organización concreta? | Regla `wait_for_case` |
| `latam_context` | `noul`: ¿menciona empresas, países o el contexto de Latinoamérica? | LATAM Gap |
| `announcement` | `noul`: ¿es el anuncio de un lanzamiento o una noticia puntual? | Distinguir un pico de noticia de una tendencia |

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

Es el patrón *entity alignment* del cookbook. El nivel decide sin umbral ajustado, y los niveles
intermedios se marcan como inciertos.

### 3. Tema: una llamada por tema en cada `analyze`

`state`: `{label, description, piezas representativas (hasta 10, título + descripción corta), audience_mix}`.

| Pregunta | Tipo y criterio | Para qué |
|---|---|---|
| `fit_*` (6) | `score` con 6 niveles descriptivos (0–5), uno por criterio de la rúbrica | `audience_fit_score` (patrón *composite scoring*) |
| `actionability` | `score`: de "solo noticia" a "guía aplicable mañana" | `actionability_score` |
| `has_case` | `noul`: ¿la evidencia incluye un caso real en una organización? | `recommendation` |
| `exec_coverage` | `noul`: ¿la evidencia ya lo explica en clave de negocio para directivos? | La lectura "traducirlo a negocio" |

La justificación de cada criterio es la descripción del nivel elegido (`legend`).

### 4. Verificación: después del LLM generativo

El LLM devuelve `why_it_matters` y los briefs como una lista de afirmaciones, cada una con el id de
la evidencia que la respalda. Por cada afirmación:

1. Python comprueba que la evidencia citada pertenece al tema.
2. Jev responde un `choice` contra el texto de esa evidencia: `supports` · `contradicts` ·
   `says_nothing` (cookbook *citation check*).
3. Si es `supports` con `confidence` ≥ 0,8, se publica. Si es `says_nothing` o `contradicts`, se
   elimina y se registra.

Las afirmaciones de un mismo texto se verifican en paralelo. Así la regla 3 ("nunca inventar") se
cumple de forma automática: lo que muestra la UI está verificado contra su fuente.

## Del juicio a la decisión (en Python)

| Tipo | Se acepta si | Si no |
|---|---|---|
| `choice` | La probabilidad máxima es ≥ 0,6 y coincide con su `_rev` | "Incierto" |
| `noul` | ≥ 0,7 cuenta como sí; ≤ 0,3, como no | "Incierto" |
| `score` | `confidence` ≥ 0,5 | Se usa el valor marcado como incierto, y baja la `confidence` de la oportunidad |

Lo incierto no entra en los conteos del "por qué funcionó" y la UI lo muestra como tal. Son
umbrales iniciales; se ajustan con la validación.

## "Por qué funcionó", medido

Con las respuestas de la batería de pieza, Python compara los outliers con el resto del tema:

```
lift = (% de outliers con el rasgo) / (% del resto con el rasgo)
```

Un rasgo con lift ≥ 2 que tienen al menos 2 outliers es un "patrón observado". Si no llega, es
"anecdótico". El LLM redacta la hipótesis a partir de esa tabla y la batería 4 la verifica.
Ejemplo: *"Los outliers usan ganchos de 'dato o cifra' 2,5 veces más que el resto (3 de 4, frente a
3 de 10). Hipótesis con muestra pequeña."*

## Paralelismo y caché

- **Concurrencia:** `AsyncTypeSafeClient` con `asyncio.Semaphore(6)`. El cookbook usa 6 workers para
  no pasar el rate limit, y el SDK reintenta los 429 y 529 con backoff. Las entidades van en
  paralelo; 200 piezas nuevas se procesan en segundos.
- **Caché:** la clave es el hash del `state` + la versión de la batería + la versión del modelo. Lo
  que no cambia no se vuelve a preguntar, así que el coste es mínimo y el resultado reproducible.
- **Tabla `jev_judgments`:** entidad, pregunta, versión de la batería, modelo (`response.model`),
  respuesta, probabilidades, `confidence` y fecha. Permite auditar y explicar en la UI ("caso de
  uso, 0,92").
- **Baterías versionadas** en `backend/app/editorial/prompts/jev/<batería>.v<n>.yaml` (convención de
  prompts versionados, CLAUDE.md §11).
- **Coste:** cada llamada registra `usage.input_tokens` en `usage_events` (CLAUDE.md §4).
- **Un único cliente** en `intelligence/jev.py`: si cambia el acceso (directo, Vercel AI Gateway u
  OpenRouter), el cambio se queda ahí.

## Validación antes de confiar

- `data/evaluations/jev_pieces.yaml`: entre 30 y 50 piezas reales (ES y EN) etiquetadas a mano para
  `relevant`, `format`, `hook` y `pillar`.
- Se mide el acuerdo por pregunta, se decide en qué idioma van las instrucciones (ES o EN) y se
  ajustan los umbrales. Una pregunta con menos del 70 % de acuerdo no se usa en la demo.
- Límites documentados de jev-1.13 y cómo los cubrimos:

  | Límite | Cómo lo cubrimos |
  |---|---|
  | Sesgo hacia la primera opción | Las preguntas `_rev` |
  | Lectura literal | Criterios explícitos, con casos límite |
  | Sensibilidad a textos que defienden su propia etiqueta | El texto externo va solo en `state`, y la pregunta `injection` |
  | Poca precisión numérica | Los números se calculan en Python |
  | Español sin documentar | La validación de arriba |

## Coste estimado

Es una estimación con los precios oficiales; el coste real lo mide `usage_events`.

| Batería | Volumen | Tokens por llamada (aprox.) | Coste |
|---|---|---|---|
| Pieza | ~1.500 de backfill + ~200 al día | ~1.500 | ~0,10 $ el backfill; ~0,40 $/mes |
| Par | ~500 al día | ~800 | ~0,50 $/mes |
| Tema | ~50 al día | ~4.000 | ~0,25 $/mes |
| Verificación | ~100 afirmaciones al día | ~800 | ~0,10 $/mes |

Total: menos de 2 $ al mes.

## Acceso: confirmarlo hoy

Según fuentes de terceros, TypeSafe ha abierto y pausado el registro directo varias veces desde
septiembre. Los pasos:

1. Intentar crear la clave en [console.typesafe.ai](https://console.typesafe.ai/keys).
2. Si está pausado, preguntar a la organización: el reto sugiere JEV y puede que tenga acceso.
3. Si no, usar Vercel AI Gateway u OpenRouter, que lo sirven con tarjeta. Antes, comprobar que
   admiten las preguntas tipadas.

## P2

- **Miniaturas de YouTube como imagen en `state`:** PNG o JPEG de 280 a 1.568 px, con la cabecera
  `TypeSafe-Danger-Zone-Images: true`. Preguntas: ¿hay una cara?, ¿texto grande?, ¿qué estilo? La
  miniatura pesa mucho en los outliers de YouTube.
- **Cola "Revisar" en la UI** con los juicios inciertos de las oportunidades más altas.
