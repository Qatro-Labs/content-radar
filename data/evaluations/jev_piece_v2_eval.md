# Validación de Jev: batería de pieza `piece.v2` (17/10/2026)

**Qué se midió:** el acuerdo entre las decisiones de Jev en producción (`jev-1.13.0`, batería
`piece.v2`, respuestas guardadas en `jev_judgments` de Supabase) y las etiquetas de **un evaluador
LLM a ciegas** sobre 40 piezas públicas.

**Limitación principal:** las etiquetas no son humanas. Las puso un agente LLM (Claude) que solo vio
el título y la descripción de cada pieza (lo mismo que ve Jev) y el perfil de 30X
(`data/audiences/30x.yaml`), sin acceso a las respuestas de Jev. Es un **acuerdo entre modelos**, no
un acierto frente a un editor: si los dos fallan igual, el acuerdo sale alto. CLAUDE.md §7 pide
30–50 piezas etiquetadas a mano; queda pendiente. La hoja para hacerlo es la misma
(`jev_piece_v2_llm_labels.csv` con las columnas vacías) y el script acepta `--sheet`.

## Resultado

"Jev seguro" = la probabilidad supera los umbrales de `app/intelligence/jev.py` (sí ≥ 0,7 · no ≤ 0,3).
Lo incierto no se cuenta como acierto ni como error: el pipeline lo trata como "sin dato".

| Pregunta | Uso en el pipeline | Etiquetadas | Jev seguro | Acuerdo cuando Jev está seguro |
|---|---|---|---|---|
| `about_ai` | Filtro: lo que Jev dice con seguridad que no es IA sale del análisis | 39 | 37 (95 %) | 95 % (2 desacuerdos) |
| `latam_context` | Pista para el criterio de relevancia LATAM del audience fit | 40 | 38 (95 %) | 97 % (1) |
| `business_case` | Pista para "aplicación real en organizaciones" | 40 | 35 (88 %) | 97 % (1) |
| `business_use` | Pista para el audience fit | 40 | 25 (62 %) | 88 % (3, todos Jev más permisivo) |
| `relevant` | No es una pregunta de Jev: se compara con `about_ai` y `business_use` | 40 | 24 (60 %) | 83 % (4) |

Datos completos en `jev_piece_v2_llm_results.json`; etiquetas en `jev_piece_v2_llm_labels.csv`.

## Lo que hay que saber

- **El filtro `about_ai` pierde alguna pieza buena.** La pieza 4293 de la DB (La República,
  Colombia: «La IA se compra. La gerencia para usarla, no») y la 628 (HN: «Show HN: Run AI-generated
  logic safely inside your app») tienen `about_ai` en 0,27 y 0,22: Jev está seguro y se equivoca, así
  que salen del análisis. Hoy el filtro quita 225 de 1.550 piezas juzgadas (umbral 0,3).
  *Corrección del 17/10:* una versión anterior de este documento daba 0,11 y 0,07 y concluía que
  endurecer el umbral no lo arreglaba. Esos valores eran de las piezas 1119 y 872 de la DB, que son
  otras: la columna `id` de la hoja es un número de fila, no el id de la DB (las piezas se cruzan por
  URL). La medida con más piezas y la batería que lo corrige están en `jev_piece_v3_eval.md`.
- **`business_use` y `relevant` son las preguntas más inciertas** (Jev no se decide en ~4 de cada 10
  piezas). Como solo son pistas para el LLM y lo incierto se le pasa como tal, no cambian scores por
  sí solas.
- **`latam_context`:** el único desacuerdo es la misma pieza 4293, que dice "el país" sin nombrar
  Colombia. El evaluador fue estricto (la regla pide una mención explícita) y Jev no.

## Cómo repetirlo

```bash
cd backend
PYTHONPATH=. uv run python ../data/evaluations/score_jev.py            # resumen
PYTHONPATH=. uv run python ../data/evaluations/score_jev.py --json     # con el detalle
PYTHONPATH=. uv run python ../data/evaluations/score_jev.py --sheet <hoja_humana.csv>
```

Solo lee la DB de `DATABASE_URL` (no llama a Jev). Las piezas se buscan por URL y los juicios con la
misma clave de caché que usa `analyze`.

*Desde la v3:* `score_jev.py` lee los juicios con la clave de la batería actual, así que puntúa la v3
(y no devuelve nada hasta que `analyze` reclasifique). Los números exactos de la v2 salen de las
respuestas guardadas: `eval_jev_battery.py score --answers jev_piece_v2_stored_answers.json`
(ver `jev_piece_v3_eval.md`).
