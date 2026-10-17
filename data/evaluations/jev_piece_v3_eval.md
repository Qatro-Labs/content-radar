# Validación de Jev: batería de pieza `piece.v3` frente a `piece.v2` (17/10/2026)

**Decisión:** se adopta `piece.v3`. Respecto a v2 solo cambia una cosa: se añade la pregunta
`ai_in_title`, y el filtro de ruido quita una pieza solo si `about_ai` **y** `ai_in_title` dicen "no"
con seguridad. Las demás preguntas, `business_use` incluida, quedan como en v2: reformularlas no
mejoró lo suficiente (ver más abajo).

**Limitación principal:** como en la v2, las etiquetas no son humanas. Son de **evaluadores LLM a
ciegas**. Vieron el título y la descripción, lo mismo que ve Jev, y nunca las respuestas de Jev. Lo
que se mide es el **acuerdo entre modelos**, no el acierto frente a un editor. Las 200 piezas son
públicas y se cruzan con la DB por URL. Los ids que aparecen aquí son los de `content_items`.

## Qué fallaba en la v2 y por qué

La evaluación de la v2 encontró dos piezas buenas que el filtro quitaba con seguridad:

| Pieza (id DB) | Título | Descripción | v2 `about_ai` |
|---|---|---|---|
| 4293, La República (CO) | «La IA se compra. La gerencia para usarla, no» | «El país multiplica negocios, pero no los hace crecer…» | 0,27 |
| 628, HN | «Show HN: Run AI-generated logic safely inside your app» | Un runtime WebAssembly para lógica no confiable; la IA no vuelve a salir | 0,22 |

En las dos, la IA está en el título y la descripción habla de otra cosa. `about_ai` pregunta si «el
tema principal» es la IA, con el criterio «la IA aparece solo de pasada». Jev lo lee de forma
literal sobre todo el `state`, y como la mayor parte del texto no trata de IA, contesta "no" con
seguridad. No es un caso aislado: en la muestra grande, 24 de las 55 piezas etiquetadas que v2
quitaba eran buenas, sobre todo con un `about_ai` entre 0,2 y 0,3.

## Muestras

- **40 piezas** de la hoja de la v2 (`jev_piece_v2_llm_labels.csv`).
- **160 piezas nuevas** de la DB (`jev_piece_v3_sample_labels.csv`; la hoja guarda 300 caracteres
  de descripción, pero el evaluador vio hasta 1.000, como Jev), elegidas al azar con semilla
  fija y estratificadas según el `about_ai` de v2: 35 en (0,2; 0,3], 15 en ≤ 0,2, 40 inciertas y
  70 con ≥ 0,7. Están sobrerrepresentadas las piezas que v2 quitaba, que son las que interesan.
  Las etiquetó un subagente LLM con las mismas definiciones de `about_ai` y `business_use` que la
  hoja de la v2.
- Antes de ver ninguna respuesta se fijó el criterio de adopción para el filtro: al menos 3 piezas
  buenas quitadas menos, no perder más del 10 % de las piezas fuera de tema quitadas, una precisión
  igual o mayor que la de v2 y ganar también al umbral 0,2. Para `business_use`: +10 puntos de
  cobertura sin perder más de 3 de acuerdo, o +5 de acuerdo sin perder cobertura, y sin más falsos
  "sí".

## Resultado: filtro de ruido

Las 200 piezas etiquetadas (199 con etiqueta de `about_ai`), con los umbrales de
`app/intelligence/jev.py`:

| Regla para quitar una pieza | Quita | Fuera de tema | Buenas (error) | Precisión |
|---|---|---|---|---|
| v2: `about_ai` ≤ 0,3 (respuestas guardadas) | 55 | 31 | 24 | 56 % |
| v2: misma pregunta, llamada nueva (control) | 56 | 31 | 25 | 55 % |
| v2 con umbral 0,2 (sin coste, sin llamadas) | 18 | 14 | 4 | 78 % |
| `about_ai_c` reformulada («¿trata de IA?», título o descripción) | 14 | 13 | 1 | 93 % |
| **v3: `about_ai` ≤ 0,3 y `ai_in_title` ≤ 0,3** | **36** | **27** | **9** | **75 %** |

La v3 quita 15 piezas buenas menos que v2 (24 → 9) y solo 4 piezas fuera de tema menos (31 → 27, un
13 % menos). Sobre estas 200 piezas, eso incumple por poco el criterio del 10 % fijado antes. Las 4 piezas
fuera de tema que la v3 deja pasar están en la franja (0,2; 0,3] («Katie Zacharia…», «This Tesla
Actually Flies (NOT AI)», «OpenAI engineer arrested…» y «Open Components…»), y esa franja está
sobrerrepresentada: 35 de sus 55 piezas están en la muestra, frente a 15 de las 181 con ≤ 0,2. La
regla `about_ai` y `ai_in_title` ya estaba en el script de puntuación antes de que llegaran las 160
etiquetas; no se eligió después de ver los resultados.
La muestra está sesgada hacia las piezas que v2 quitaba, así que se estimó el efecto sobre las 1.579
piezas juzgadas, ponderando cada estrato de la muestra de 160 por su tamaño real:

| Regla | Quita (estimado) | Fuera de tema | Buenas |
|---|---|---|---|
| v2 | ~236 (real: 236) | ~159 | ~77 |
| v2 con umbral 0,2 | ~181 | ~133 | ~48 |
| `about_ai_c` | ~113 | ~101 | ~12 |
| **v3** | **~178** | **~153** | **~25** |

Con esta estimación, la v3 sigue quitando el ~96 % del ruido que quitaba v2, y las piezas
buenas que quita bajan a un tercio (~77 → ~25). Supera al umbral 0,2, que quita menos ruido y más piezas buenas, y a `about_ai_c`,
que deja pasar la mitad del ruido. La estimación es gruesa: el estrato ≤ 0,2 tiene 15 piezas en la
muestra, así que cada una pesa unas 12 piezas. Del total, ~219 piezas estarían fuera de tema.

Qué cambia al leer los títulos. Ahora se quedan, entre otras: la 4293 y la 628 (sus `ai_in_title`
son 0,98 y 0,99), «Educación online: negocio impulsado por IA ya mueve cerca de US$ 300 millones en
Perú», «Más del 35 % de tutelas en Colombia… plantean mejorarlas con IA», «Una inteligencia
artificial habría borrado la segunda temporada del reality…» y «Port of the TypeScript compiler… by
LLM». También se cuela algo de ruido con la IA en el título: «OpenAI engineer arrested in bugging of
executive conference room», «This Tesla Actually Flies (NOT AI)» y «Katie Zacharia Was Linked to an
AI Rare-Earths Startup». Siguen fuera piezas buenas en las que la IA solo está en la descripción:
«The technology shifts every business leader should be watching», «Amazon has over 1 million
robot workers…», «Redesigning source control at Anthropic» y «Rewiring capital projects to boost
construction productivity».

**Batería v3 real (archivo `piece.v3.yaml`) sobre las 40 piezas de la hoja v2:** quita 4 piezas: 3
fuera de tema y una sin etiqueta («🔮 What is left to do»). No quita ninguna buena. La v2 quitaba 5
etiquetadas, 2 de ellas buenas (4293 y 628). En la llamada nueva, 4293 queda con `about_ai` 0,26 y
`ai_in_title` 0,98, y 628 con 0,23 y 0,99. `ai_in_title` dio la misma decisión en las 40 piezas que
en el experimento. El resto de preguntas cambió como mucho 2 de 40 decisiones frente a las
respuestas guardadas de v2 (`dev_audience` y `tech_jargon` 2, `about_ai`, `business_use` y `launch`
1, el resto 0, y `format` y `hook` 0).

## Resultado: `business_use` (sin cambio)

| Pregunta | Etiquetadas | Jev seguro | Acuerdo cuando está seguro | Falso sí | Falso no |
|---|---|---|---|---|---|
| v2 (guardadas) | 200 | 147 (74 %) | 139/147 (95 %) | 7 | 1 |
| v2 (control) | 200 | 146 (73 %) | 139/146 (95 %) | 6 | 1 |
| `business_use_b` («¿explica qué cambia para las organizaciones que usan o compran IA?») | 200 | 159 (80 %) | 147/159 (92 %) | 1 | 11 |
| `org_adoption` o `org_impact` (dos preguntas atómicas combinadas) | 200 | 136 (68 %) | 122/136 (90 %) | 12 | 2 |

`business_use_b` gana 6 puntos de cobertura y pierde 3 de acuerdo, y cambia los errores de signo: de
falsos "sí" a falsos "no". Dice "no" a piezas que sí tratan del uso en organizaciones, como 4293,
«La IA analiza tu comportamiento en Netflix…» o «Estudiar programación ya no garantiza trabajo», y
"sí" a «Claude Haiku 5.5». No llega al criterio, así que `business_use` sigue como en v2. Con 200
piezas, Jev duda en el 26 %, no en el ~40 % que daban las 40 piezas de la hoja v2. Esa muestra está
estratificada por `about_ai`; en las 1.579 piezas juzgadas, `business_use` es incierto en 360 (23 %).
`relevant` no cambia: sale de `about_ai` y `business_use`, y ninguna de las dos cambia.

`about_ai_c` acierta más como pregunta (91 % frente a 84 %), pero como filtro quita la mitad de
ruido. Como el campo `about_ai` solo se usa para filtrar, no compensa cambiarlo.

## Ruido entre llamadas

Se repitió la misma pregunta v2 en una llamada nueva sobre las 200 piezas y se comparó con lo
guardado: `about_ai` cambió 3 decisiones de 200 y `business_use`, 7. Las diferencias del filtro (24
→ 9 piezas buenas quitadas) están muy por encima de ese ruido. Las de `business_use_b` (+13 piezas
seguras), no tanto.

## Coste de esta validación

Hubo 240 llamadas a `jev-1.13.0`. La batería experimental (8 preguntas) se pasó por las 200 piezas
y sumó 236.151 tokens de entrada. La batería v3 completa (13 preguntas) se pasó por las 40 piezas de
la hoja v2: 90.553 tokens, unos 2.264 por llamada. En total, ~327.000 tokens, que son ~0,014 $ a
0,042 $ por millón.

## Puesta en producción

La clave de caché incluye la versión de la batería, así que con la v3 desplegada no se reutiliza
ningún juicio de la v2. Hasta que `analyze` reclasifique, ninguna pieza tiene juicio: el filtro no
quita nada, el LLM no recibe pistas de Jev y los briefs fallan con `NoSafeEvidence`, porque sin
respuesta de `injection` la pieza se excluye. Por eso, al desplegar hay que lanzar `analyze` en un
entorno con `TYPESAFE_API_KEY` y comprobar que el número de piezas clasificadas se acerca al de
cargadas. Reclasificarlo todo son ~1.600 llamadas, ~3,6 M de tokens, ~0,15 $. Ese mismo `analyze`
deja entrar ~58 piezas más en el clustering, así que el ranking cambia: hay que revisarlo y volver a
fijar `DEMO_RUN_ID`.

## Archivos

| Archivo | Qué es |
|---|---|
| `jev_piece_v3_sample_labels.csv` | Las 160 etiquetas nuevas (`id` = id de la DB) |
| `jev_piece_v3_variants.yaml` | Batería experimental: control v2 y variantes de `about_ai` y `business_use` |
| `jev_piece_v3_variants_answers.json` | Respuestas de Jev a la batería experimental, por URL (200 piezas) |
| `jev_piece_v2_stored_answers.json` | Respuestas v2 guardadas en la DB para esas 200 piezas |
| `jev_piece_v3_answers.json` | Respuestas de la batería `piece.v3.yaml` real (40 piezas de la hoja v2) |
| `eval_jev_battery.py` | Llama a Jev con una batería sobre las piezas de las hojas, sin escribir en la DB, y puntúa |

## Cómo repetirlo

Desde `backend/`. `score` no llama a Jev. `run` lee la DB y llama a Jev, pero no escribe en la DB:

```bash
E=../data/evaluations
S="--sheet $E/jev_piece_v2_llm_labels.csv --sheet $E/jev_piece_v3_sample_labels.csv"

# Tablas de arriba, a partir de las respuestas guardadas
PYTHONPATH=. uv run python $E/eval_jev_battery.py score --answers $E/jev_piece_v2_stored_answers.json \
  $S --map about_ai=about_ai --map business_use=business_use --filter about_ai
PYTHONPATH=. uv run python $E/eval_jev_battery.py score --answers $E/jev_piece_v3_variants_answers.json \
  $S --map about_ai=about_ai --map about_ai=about_ai_c --map business_use=business_use \
  --map business_use=business_use_b --filter about_ai --filter about_ai_c --filter about_ai+ai_title

# Volver a preguntar a Jev (200 llamadas, ~0,01 $)
PYTHONPATH=. uv run python $E/eval_jev_battery.py run \
  --battery app/editorial/prompts/jev/piece.v3.yaml $S --out /tmp/v3_answers.json
PYTHONPATH=. uv run python $E/eval_jev_battery.py score --answers /tmp/v3_answers.json $S \
  --map about_ai=about_ai --map business_use=business_use --filter about_ai+ai_in_title
```

Las estimaciones sobre las 1.579 piezas salen de ponderar cada estrato de la muestra de 160 por su
tamaño en la DB (en v2: ≤ 0,2: 181; (0,2; 0,3]: 55; inciertas: 218; ≥ 0,7: 1.125).
