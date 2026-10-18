# Evaluación de adopción: prompt `explain_opportunity.v2` + `claim.v2` con umbral 0,6

18/10/2026 · ejecución 38 de `analyze` · LLM `claude-haiku-5-5` · Jev `jev-1.13.0` · pre-registro
[`jev_claim_adoption_prereg.md`](jev_claim_adoption_prereg.md) (commit «Pre-register the explain v2
+ claim.v2 adoption eval», con dos enmiendas anteriores a mirar cualquier salida).

**Resultado: se adopta.** Se cumplen los tres criterios de D10 y los dos guards de cobertura, con
la regla fijada de antemano (estimación puntual). `JEV_VERIFY_CLAIMS` pasa a `true` por defecto,
con `claim.v2`, umbral de `confidence` 0,6 y el prompt v2. El margen en «filtra» es nulo (9/15,
justo el 60 %) y la verificación apenas atrapa las sobregeneralizaciones reales: ver
[Limitaciones](#limitaciones).

## Muestra

- **Fuente:** la ejecución 38 (primera correcta después de la 37, código de `main` con #61 y #64,
  flag apagado), leída en solo lectura. Tiene 53 temas con audience fit y piezas seguras.
- **Salidas v2:** una llamada al LLM por tema con el prompt v2, con las entradas construidas como
  los briefs y el rótulo corregido (`topic_label`, enmiendas 1 y 2), sin escribir en la DB. Las 53
  salidas tienen 3 afirmaciones; 158 de 159 pasan las comprobaciones de Python.
- **Muestra etiquetada** (`jev_claim_adoption_sample.csv`, semilla 18): 40 afirmaciones v2 reales de
  14 temas (posición 1: 14, posición 2: 13, posición 3: 13; buscar ángulo 18, esperar caso 16,
  descartar 6) y 10 negativas sintéticas de otros temas (MOCK de evaluación, `synthetic=true`): 5
  de cita cambiada y 5 de hecho insertado.
- **Etiquetas:** de Claude en un contexto nuevo (evaluador LLM a ciegas), **no de una persona**,
  mirando solo lo que ve Jev. Se commitearon antes de la primera llamada a Jev (commit «Add the
  labelled sample…»). Reales: 35 `supported`, 5 `unsupported`, 0 `contradicted`. El texto del
  evaluador decía 34/6, pero su JSON, que es lo que se aplicó, da 35/5.

| id | Por qué no está respaldada (según el evaluador) |
| --- | --- |
| 8 | Ninguna de las piezas citadas habla de conciencia ni de manipulación |
| 11 | Llama «producto empresarial» a Box; la pieza solo dice que el modelo está disponible en Box |
| 13 | «La mayoría» de las piezas: solo 2 de las 4 citadas tratan de benchmarks o competidores |
| 19 | La pieza dice que Automattic tiene más de 1.400 personas, no que forme a 1.400 personas |
| 38 | Une dos datos: 5 piezas en 3 días y 5 fuentes en todo el tema no son 5 fuentes en 3 días |

## Resultados

Intervalos de Wilson al 95 %. La decisión se toma con la estimación puntual (pre-registro).

| Criterio | Resultado | Wilson 95 % | Mínimo | ¿Cumple? |
| --- | --- | --- | --- | --- |
| 1. Conserva las `supported` | 33/35 (94 %) | 81–98 % | 70 % | Sí |
| 2. Filtra las negativas | 9/15 (60 %) | 36–80 % | 60 % | Sí, en el límite |
| 3. Temas de la muestra con texto | 14/14 (100 %) | 78–100 % | 80 % | Sí |

**Guard de cobertura de la posición 2** («por qué le importa a un directivo de LATAM»), sobre los
53 temas. Tolerancia: `ceil(0,10 · 53)` = 6 temas por debajo de v1.

| Etapa | Temas con la posición 2 | Wilson 95 % | Mínimo | ¿Pasa? |
| --- | --- | --- | --- | --- |
| v1 servido (Python, flag apagado) | 53/53 (100 %) | 93–100 % | — | — |
| Guard A: v2 tras Python | 53/53 (100 %) | 93–100 % | 47 | Sí |
| Guard B: v2 tras Python y Jev | 49/53 (92 %) | 82–97 % | 47 | Sí |

**Por tipo de negativa (filtra):** hecho insertado 5/5 (100 %; 57–100 %) · cita cambiada 3/5
(60 %; 23–88 %) · natural 1/5 (20 %; 4–62 %).

**Por posición (conserva):** posición 1 12/12 (100 %; 76–100 %) · posición 2 9/10 (90 %;
60–98 %) · posición 3 12/13 (92 %; 67–99 %). En la evaluación anterior, la posición 2 conservaba
4/11 con `claim.v2` y umbral 0,8.

**Sobre los 53 temas:** se publicarían 141 de las 158 afirmaciones v2 que pasan Python (89 %;
83–93 %), y los 53 temas conservan al menos una (100 %; 93–100 %).

**Comprobación:** con los defaults ya cambiados, `claim_supported` de producción reproduce sobre
las 168 respuestas guardadas los mismos 33/35, 9/15 y 49/53 que la copia de la regla en
`eval_explain_v2.py`.

## Limitaciones

- **Filtra justo en el mínimo, con un intervalo ancho (36–80 %, n = 15).** Con otra muestra podría
  quedar por debajo.
- **Jev atrapa los hechos inventados, no las sobregeneralizaciones.** Filtra 5/5 de hecho insertado,
  pero deja pasar 4 de las 5 negativas naturales (filas 8, 13, 19 y 38, con `supports` y
  `confidence` de 0,76 a 0,94): «la mayoría», atribuir a las piezas lo que no dicen, o unir dos
  cifras. El pitch no debe decir que Jev detecta esos fallos; Python sigue bloqueando las cifras
  que no están en los datos.
- **Dos negativas de «cita cambiada» no lo son del todo.** Las filas 43 (posición 2) y 44
  (posición 3) se apoyan solo en los datos medidos, que el `state` conserva, así que cambiarles la
  evidencia no las deja sin respaldo; Jev las acepta (0,83 y 0,97). No se reetiquetaron tras ver a
  Jev. Corolario: en las posiciones 2 y 3, apoyadas en los datos medidos por diseño del prompt v2,
  una cita equivocada no se detecta.
- **Etiquetas de un LLM, no de una persona.** Mismo método que `jev_claim_v1_eval.md`.
- **Las entradas se construyeron como los briefs**, no con `build_topic_input`; el orden de las
  piezas puede diferir del de `analyze`. La línea base v1 se generó con el rótulo antiguo (antes del
  arreglo de `topic_label`); el guard compara cobertura, no contenido.
- **Una sola ejecución.** El LLM no es determinista: el siguiente `analyze` generará otros textos.

## Coste

| Proveedor | Llamadas | Tokens | Coste (`data/pricing.yaml`) |
| --- | --- | --- | --- |
| LLM, salidas v2 descartadas (enmienda 1) | 53 | 238.818 de entrada · 47.714 de salida | 0,048 $ |
| LLM, salidas v2 evaluadas | 53 | 238.401 de entrada · 52.223 de salida | 0,050 $ |
| Jev, `claim.v2` | 168 | 299.567 de entrada | 0,013 $ |
| **Total** | | | **0,11 $** |

## Archivos

- `jev_claim_adoption_prereg.md`: el pre-registro y sus dos enmiendas.
- `eval_explain_v2.py`: `generate`, `sample`, `judge` y `score`.
- `jev_claim_adoption_outputs.json`: las 53 salidas v2 y la posición 2 de v1 servida.
- `jev_claim_adoption_sample.csv`: la muestra etiquetada.
- `jev_claim_adoption_answers.json`: las 168 respuestas de Jev.
