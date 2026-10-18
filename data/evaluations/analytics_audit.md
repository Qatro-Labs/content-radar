# Auditoría de la parte analítica (runs 33, 35 y 37)

> 18/10/2026. Consultas de solo lectura sobre Supabase (`SET TRANSACTION READ ONLY`). Los
> arreglos se recalcularon en memoria con las funciones puras de `app/intelligence/`, sin
> ejecutar `analyze`. Cada número lleva su n. Ramas: `intel/analytics-fixes` (PR #62) e
> `intel/analytics-fixes-2`.

## Resumen

| # | Hallazgo | Evidencia | Decisión |
|---|---|---|---|
| 1 | La aceleración se calculaba sobre conteos minúsculos (2 frente a 1 ya daba +100 % y momentum máximo) | Run 35: 8 de 22 temas `accelerating`/`emerging` con p < 0,1 | **Arreglado** (PR #62): p-valor binomial exacto sobre notas originales; `accelerating` exige p ≤ 0,10; `emerging` lo muestra y avisa; momentum con log-ratio |
| 2 | "Esperar caso" domina | Run 37: 33 de 53 temas con `org_application` ≤ 1; Jev `business_case` da 0 casos en 31 de ellos | **Se mantiene la regla**: leer los artículos completos de 5 temas no encontró casos. Su texto ya dice lo que mide (títulos y descripciones) |
| 3 | `latam_gap` casi siempre `null` | Run 35: 36 de 56; solo 7,6 % del corpus viene de fuentes `business` | **Arreglado** (PR #62): Jev `business_use` decide si hay conversación de negocio. Run 37: `null` de 33 a 28, `true` de 4 a 9. Los 28 `null` restantes son correctos (ver abajo) |
| 4 | "El score mide sobre todo el tamaño del cluster" | Spearman(score, fuentes independientes) = 0,81; (score, notas de 6 días) = 0,24–0,25 en los 3 runs | **En parte refutado**: sigue al número de fuentes, que es la validación cruzada que se busca, no al volumen. **Arreglada** la saturación (percentil a cuota absoluta). El tope de `cross_source` se documenta: cambiarlo mueve 1 tema del top 10 |
| 5 | El top 10 repite temas | Coseno entre centroides: ningún par del top 10 supera el p90 del corpus (0,83) | **Sin cambio**: no hay más redundancia que entre dos temas cualesquiera |
| 6 | Falta una etapa "en descenso" | 16 de los `unknown` en cada run son "en descenso" | **Pendiente de decisión**: se puede derivar sin tocar el contrato (ver abajo) |

## 1. Aceleración

Test exacto de razón de tasas de Poisson: condicionado a `actual + anterior` notas del tema, el
conteo actual es binomial con p0 = cuota del corpus en la ventana actual. Run 37, después del PR
#62: `accelerating` de 14 a 7, `emerging` 3, `publish_now` de 1 a 0. El único `publish_now`
("Control del coste de la IA en empresas") tenía 3 notas frente a 2, con p ≈ 0,44.

Con Benjamini–Hochberg no pasa ningún tema (mejor p ≈ 0,02 frente a un primer umbral de ≈ 0,002):
el umbral es por tema y se documenta como limitación en [`docs/scoring.md`](../../docs/scoring.md).

## 2. "Esperar caso"

**Criterio fijado antes de leer:** la regla es demasiado estricta si 2 o más de los 5 temas "sin
caso" con mejor score tienen al menos un artículo completo que nombra una organización que no es un
proveedor de IA aplicándola en su operación con un resultado. Víctimas de un ataque, reguladores,
investigadores o el propio proveedor no cuentan.

| Tema (run 37) | ¿Caso real? | Base |
|---|---|---|
| Riesgos de seguridad de los agentes de IA en empresas | No en lo legible | 1 artículo completo (riesgos); otros 4 no se pudieron leer (medio bloqueado o página vacía) |
| Agentes de IA de OpenAI que acceden a sistemas ajenos | No | 2 artículos completos: informe del proveedor e incidente con víctimas |
| Conciencia y riesgos de los agentes de IA | No en lo legible | 2 artículos completos y 1 parcial: opinión y debate |
| Avances de la IA en matemáticas y ciencia | Sin determinar | El artículo principal (WSJ) no se pudo leer; los vídeos solo dan el título |
| Oferta de empleo de Anthropic para principiantes en EE. UU. | No | 2 newsletters completas: benchmarks, política, investigación |

**Resultado: 0 de 5.** Las justificaciones del LLM (riesgos, incidentes, investigación,
contratación) coinciden con lo que dicen los artículos. Limitación: 1 tema sin determinar y
varios medios sin leer.

**Hallazgo aparte:** el tema "Oferta de empleo de Anthropic para principiantes" parece llevar el
nombre de una sola pieza (un TikTok sobre esa oferta), mientras que las dos newsletters leídas
tratan de noticias generales de IA. Solo se leyeron 2 de sus 7 piezas, así que no está probado que
el tema esté mal agrupado; conviene revisarlo a mano antes de fijar `DEMO_RUN_ID`.

## 3. LATAM gap: los 28 `null` del run 37

| n | Motivo |
|---|---|
| 21 | Jev no ve ninguna pieza sobre el uso de la IA en organizaciones |
| 2 | Jev ve 1 o 2 piezas de negocio, por debajo del 15 % de las decididas |
| 5 | Hay conversación de negocio, pero la cuota LATAM está entre 0,10 y 0,30: cobertura parcial |

`null` ya no significa "sin datos": significa que no hay conversación de negocio o que la cobertura
regional es parcial. El texto que recibe el LLM para redactar lo dice así
(`backend/app/editorial/explanation.py`).

## 4. Qué ordena el score

Recalculado con las reglas del PR #62 (momentum con log-ratio):

| Run | Spearman(score, fuentes) | Spearman(score, notas 6 d) | `cross_source` = 100 |
|---|---|---|---|
| 33 | 0,81 | 0,25 | 21 de 56 |
| 35 | 0,81 | 0,24 | 21 de 56 |
| 37 | 0,81 | 0,24 | 18 de 53 |

Ablación con las reglas de las dos ramas (quitar un componente y repartir su peso), top 10
compartido con el completo:

| Run | Sin momentum | Sin fit | Sin `cross_source` | Sin frescura | Sin accionabilidad |
|---|---|---|---|---|---|
| 33 | 5/10 | 9/10 | 8/10 | 9/10 | 9/10 |
| 35 | 5/10 | 9/10 | 8/10 | 9/10 | 9/10 |
| 37 | 7/10 | 7/10 | 8/10 | 8/10 | 8/10 |

Momentum es lo que más ordena; `cross_source` cambia 2 temas del top 10, no más que los demás.

| Variante | Top 10 compartido (33 · 35 · 37) | Descartes (33 · 35 · 37) |
|---|---|---|
| `cross_source` en escala log (100 = 12 fuentes) | 9 · 9 · 9 | 5→5 · 5→5 · 7→7 |
| Saturación absoluta, 100 = 2 % | 8 · 8 · 9 | 5→4 · 5→4 · 7→3 |
| Saturación absoluta, 100 = 1,5 % | 9 · 8 · 10 | 5→5 · 5→5 · 7→5 |

- **Saturación:** se adopta la cuota absoluta con 100 = 2 %. Con el percentil, el 25 % de los temas
  quedaba siempre ≥ 75 y se descartaban temas de 7–11 notas por ser los más grandes de la muestra.
  Con el 2 %, solo se descartan los de 15 notas en descenso. Es el umbral más prudente para afirmar
  "saturado" (regla 3).
- **`cross_source`:** su tope (100 con 5 fuentes y 2 plataformas) deja a un tercio de los temas
  empatados arriba, pero la escala log solo cambia 1 tema del top 10 y ningún descarte. No se
  toca a 3 h del feature freeze; queda documentado.

## 5. Repeticiones en el top 10

Centroide de cada tema = media de los embeddings de sus piezas (`paraphrase-multilingual-MiniLM-L12-v2`).
Coseno con el tema más cercano, en los 53 temas del run 37: p50 0,75, p90 0,83, máximo 0,85.

Top 10 con las reglas de las dos ramas (frente al del PR #62 solo, entra "Avances de la IA en
matemáticas y ciencia" y sale "Agentes de IA de OpenAI que acceden a sistemas ajenos"): el par más
parecido tiene 0,78 ("Agentes de IA que ejecutan tareas en empresas" y "Riesgos de seguridad de los
agentes de IA"), por debajo del p90 del corpus. Comparten palabras ("agentes de IA"), pero son
ángulos distintos. No se aplica MMR: escondería oportunidades distintas.

Limitación: el centroide medio comprime los vectores hacia una dirección común (p50 0,75), así
que la métrica discrimina poco.

## 6. Etapa "en descenso"

En los tres runs, 16 temas `unknown` son "en descenso": aceleración < 0 sin cumplir otra regla. Se
deriva exactamente de campos del contrato: `lifecycle == "unknown"`, `growth_status !=
"preliminary"` y `acceleration < 0` (por el orden de `classify`). Añadir un valor a `Lifecycle`
cambia el contrato congelado y toca backend, MCP, agente, fixture y frontend.

## Reproducir

Los scripts de esta auditoría se ejecutaron desde `backend/` con `PYTHONPATH=. uv run python
<script> <run>`, contra la DB compartida en solo lectura. No se guardan aquí porque leen
`DATABASE_URL` directamente; la lógica que miden es la de `app/intelligence/`.
