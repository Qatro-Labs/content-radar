# Evaluación de la verificación de afirmaciones con Jev (`claim.v1` y `claim.v2`)

18/10/2026 · modelo `jev-1.13.0` · plan `.claude/plans/intel-claim-verification.plan.md` (D10).

**Resultado: no se adopta.** `JEV_VERIFY_CLAIMS` se queda en `false`. Ni `claim.v1` ni su única
revisión, `claim.v2`, cumplen el criterio «conserva» fijado antes de mirar resultados. Las dos
filtran bien las negativas.

## Muestra

`jev_claim_v1_sample.csv`, generada con `eval_claim_verification.py sample` en solo lectura sobre la
ejecución servida:

- **40 afirmaciones reales** de «por qué importa» que ya pasaron las comprobaciones de Python, de 14
  temas (posiciones 1, 2 y 3; recomendaciones descartar, buscar ángulo, esperar caso y publicar).
- **10 negativas sintéticas** (MOCK de evaluación, `synthetic=true`): 5 de cita cambiada y 5 de
  hecho insertado.

**Etiquetas:** evaluador LLM a ciegas (Claude), con la definición de D10. Las etiquetas se
commitearon antes de cualquier llamada a Jev (commit «Add the labelled claim sample for the Jev
verification eval»). De las 40 reales, 36 son `supported` y 4 `unsupported`:

| id | Por qué no está respaldada |
| --- | --- |
| 14 | Da por hecho que OpenAI es «una empresa de Estados Unidos»; ninguna pieza citada lo dice |
| 17 | Atribuye la ventaja a «quien ya usa IA con criterio»; la pieza habla de la experiencia de los directivos sénior |
| 19 | «Todas se centran en herramientas para programadores»; solo una de las tres piezas citadas lo dice |
| 25 | «5 piezas en los últimos 3 días, publicadas por 6 fuentes»: las 6 fuentes son de las dos ventanas |

## Resultados

Criterio de D10: **conserva** ≥ 70 % de las `supported` · **filtra** ≥ 60 % de las negativas ·
**temas con texto** ≥ 80 %.

| Tanda | Conserva | Filtra | Temas con texto | ¿Cumple? |
| --- | --- | --- | --- | --- |
| `claim.v1`, con datos medidos (D2) | 21/36 (58 %) | 13/14 (93 %) | 13/14 (93 %) | No |
| `claim.v1`, solo evidencia | 8/36 (22 %) | 14/14 (100 %) | 8/14 (57 %) | No |
| `claim.v2`, con datos medidos | 24/36 (67 %) | 13/14 (93 %) | 14/14 (100 %) | No |

**Por tipo de negativa (con datos medidos, v1 y v2):** cita cambiada 5/5 · hecho insertado 5/5 ·
natural 3/4.

**Por posición (conserva):**

| Tanda | Posición 1 | Posición 2 | Posición 3 |
| --- | --- | --- | --- |
| `claim.v1`, con datos | 9/12 | 1/11 | 11/13 |
| `claim.v1`, solo evidencia | 6/12 | 1/11 | 1/13 |
| `claim.v2`, con datos | 10/12 | 4/11 | 10/13 |

**Lectura:**

- **Los datos medidos en el `state` (D2) son necesarios.** Sin ellos, Jev rechaza casi todas las
  recomendaciones (posición 3), que se apoyan en la etapa y la recomendación medidas.
- **La posición 2 es la que falla.** Son frases como «para un directivo de Latinoamérica, esto
  importa porque…». La v2 dice que esa lectura es interpretación editorial y que solo se comprueban
  los hechos en que se apoya; sube de 1/11 a 4/11, no basta.
- **El umbral de confianza es la causa principal.** En la v2, 11 de las 12 `supported` rechazadas
  tienen `supports` en las dos preguntas, pero con `confidence` < 0,8.

## Diagnóstico del umbral (no adoptado)

El umbral de 0,8 viene de CLAUDE.md §7 y se fijó antes de la evaluación. Barrerlo sobre la misma
muestra es solo un diagnóstico: elegir el umbral con estas 50 filas y medirlo con ellas mismas
sobreestima el resultado.

| Umbral de `confidence` | v1: conserva / filtra | v2: conserva / filtra |
| --- | --- | --- |
| 0,8 (actual) | 21/36 · 13/14 | 24/36 · 13/14 |
| 0,6 | 27/36 · 13/14 | 28/36 · 13/14 |
| 0,5 | 29/36 · 12/14 | 31/36 · 11/14 |

Con `claim.v2` y un umbral de 0,6, conservaría el 78 % y filtraría el 93 %. Adoptarlo exige una
decisión del equipo (cambia la regla de CLAUDE.md §7) y, para medirlo bien, una muestra nueva.

## Coste

150 llamadas (50 por tanda) y 225.567 tokens de entrada: unos 0,01 $ a 0,042 $ por millón de
tokens de entrada (`data/pricing.yaml`).

## Archivos

- `jev_claim_v1_sample.csv`: la muestra etiquetada.
- `jev_claim_v1_answers.json`: las respuestas de Jev de las tres tandas.
- `backend/app/editorial/prompts/jev/claim.v2.yaml`: la revisión evaluada. `CLAIM_BATTERY_FILE`
  sigue apuntando a `claim.v1.yaml`, porque ninguna se adopta.
