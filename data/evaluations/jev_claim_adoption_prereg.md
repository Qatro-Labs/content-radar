# Pre-registro: adopción de la verificación de afirmaciones con Jev

18/10/2026, 12:35 (hora de España) · decisiones D1, D2 y D3 de Melkin. Se commitea antes de
cualquier llamada al LLM o a Jev; nada de lo que sigue se cambia después de mirar resultados.

Evaluación anterior: [`jev_claim_v1_eval.md`](jev_claim_v1_eval.md). `claim.v2` conservó el 67 %
(24/36) con el umbral de 0,8. Con 0,6 habría conservado el 78 % (28/36), pero ese umbral se eligió
mirando aquella muestra, así que aquí se mide con una muestra nueva.

## Candidato (único)

| Pieza | Valor |
| --- | --- |
| Prompt del LLM | `backend/app/editorial/prompts/explain_opportunity.v2.md` (sha256 `496fe511e59c73f0144cc715192833830a2cee50a2985026780fbe5f971c4e01` desde la enmienda 1; antes `b8694345…`) |
| Batería de Jev | `backend/app/editorial/prompts/jev/claim.v2.yaml`, `version: 2` (sha256 `4d8b4505cc6f4778f4ca069bb615089af1113c7680f1c0e1b58796700f5b107a`; si se adopta, solo cambia su comentario de cabecera, que menciona el umbral) |
| Regla de publicación | `support` = `supports` con `confidence` ≥ **0,6** y `support_rev` = `supports` (el resto de `claim_supported`, igual) |
| Modelos | LLM `claude-haiku-5-5` · Jev `jev-1.13.0` |
| `state` de Jev | El de `claim_state`: afirmación, `measured_facts` y piezas citadas (fuente, título, descripción) |

Cambio del prompt v2 respecto a v1: cada afirmación se apoya solo en `<facts>` y en las piezas que
cita; `<fit>` solo sirve para elegir de qué hablar. Siempre 3 afirmaciones en orden fijo (qué
pasa · por qué le importa a un directivo de LATAM · qué conviene hacer), para que la posición 2 se
pueda identificar.

## Fuente de datos

- La **primera ejecución correcta de `analyze` con id > 37**, fijada por id (no «la última»: el
  cron puede moverla durante la evaluación). Solo lectura (`SET TRANSACTION READ ONLY` como primera
  sentencia de cada sesión).
- Entradas del prompt v2 construidas como los briefs (`services/editorial.py`, `_prepare`):
  `load_evidence_pieces` → `load_judgments` → sin `excluded_from_llm` → primeras `MAX_PIECES`,
  `named_label` (enmienda 1), `opportunity_facts(o, served.timeline)` y `fit_notes(o)`. El orden de las piezas
  puede diferir del de `build_topic_input` en `analyze`.
- Se llama al LLM una vez por tema con fit y al menos una pieza segura, sin pasar por
  `explain_topics` (no se escribe en la DB). Las afirmaciones pasan `python_checked` igual que en
  producción.
- La línea base v1 es el texto servido en esa misma ejecución (prompt v1, flag apagado), emparejado
  con su salida en `llm_evaluations` como hace `eval_claim_verification.py`.

## Muestra etiquetada

- **Semilla 18.** Unos 14 temas estratificados por recomendación (round-robin, como `pick_real`),
  hasta 3 afirmaciones por tema: **40 afirmaciones reales** que pasaron Python.
- **10 negativas sintéticas** (MOCK de evaluación, `synthetic=true`, etiquetadas `unsupported` por
  construcción), de salidas v2 de temas que no están en la muestra: 5 de cita cambiada y 5 de hecho
  insertado, como en la evaluación anterior.
- **Parada:** con menos de 30 afirmaciones v2 válidas en la muestra, no se evalúa y no se adopta.
- **Etiquetas:** las pone Claude (evaluador LLM, no una persona), a ciegas respecto a Jev, con la
  definición de D10, mirando solo lo que verá Jev (afirmación, `measured_facts` y piezas citadas).
  Se commitean antes de la primera llamada a Jev.
  - `supported`: todo lo que da por hecho está en los datos medidos o en el título o la descripción
    de una pieza citada, aunque sea con otras palabras. Una hipótesis («puede», «sugiere») o una
    recomendación coherente con la de los datos no necesita más respaldo; en una lectura dirigida
    al lector («para un directivo de Latinoamérica…») se comprueban los hechos en que se apoya.
  - `unsupported`: añade algo que no está.
  - `contradicted`: choca con los datos o con las piezas.

## Criterios de adopción (sobre la estimación puntual)

**D10**, sobre la muestra etiquetada:

1. **Conserva:** ≥ 70 % de las `supported` salen publicadas.
2. **Filtra:** ≥ 60 % de las `unsupported` o `contradicted` (sintéticas y naturales) salen
   rechazadas. Se informa por tipo: cita cambiada, hecho insertado, natural.
3. **Temas con texto:** ≥ 80 % de los temas de la muestra (filas reales) conservan al menos una
   afirmación.

**Guard de cobertura de la posición 2** («entender por qué importa» en la demo), sobre **todos**
los temas con explicación v1 y v2 de la ejecución (N):

- *Llena en v1:* la afirmación de índice 2 de la salida v1 está en el texto servido (pasó Python;
  flag apagado).
- *Llena en v2:* la salida v2 tiene 3 afirmaciones y la de índice 2 pasa la etapa que toque. Una
  salida de 2 afirmaciones cuenta como no llena.
- **Guard A (prompt):** v2 llena tras Python. Pasa si `llenas_v2 ≥ llenas_v1 − ceil(0,10 · N)`, es
  decir, como mucho 10 puntos porcentuales por debajo de v1.
- **Guard B (flag encendido):** v2 llena tras Python **y** Jev con la regla del candidato. Pasa con
  la misma tolerancia.

**Decisiones:**

| Se cumple | Qué se adopta |
| --- | --- |
| Guard A | Prompt v2 por defecto (`PROMPT_VERSION = 2`), también con el flag apagado (D2) |
| D10 (los tres) y guard B | Además, `jev_verify_claims=True`, `claim.v2.yaml` y umbral 0,6 (D3) |
| Ninguno, o no está listo a las 14:15 | Nada: solo D1 y esta evaluación escrita |

La decisión se toma con la estimación puntual, como fijó D10. Para cada proporción se informa
también el **intervalo de Wilson al 95 %**, que no cambia la decisión. Cada número lleva su n.

## Presupuesto

- LLM: una llamada por tema con fit (unos 52): menos de 0,5 $ con los precios de
  `data/pricing.yaml`. Tope: 1 $.
- Jev: todas las afirmaciones v2 que pasan Python (unas 156) más las 10 sintéticas: unas 170
  llamadas. Tope: 300.
- El gasto real se calcula con los tokens devueltos y `data/pricing.yaml`.

## Si se adopta

El PR dice el impacto en la demo: cambian los textos servidos de «por qué importa»; la caché de
explicaciones no sirve (otra versión del prompt), así que el siguiente `analyze` vuelve a pagar el
LLM de todos los temas y, con el flag, la verificación de todas sus afirmaciones; hace falta ese
`analyze` y una revisión antes de fijar `DEMO_RUN_ID`.

## Enmienda 1 (12:45, antes de mirar ninguna salida)

Melkin reportó un bug: `<topic_label>` llevaba el título de una pieza (`safe_label`) y no el nombre
final del tema que pone el audience fit. En la ejecución 38, el tema «Adopción y control de la IA
en empresas» explica la «automejora recursiva de la IA», el título de su pieza representativa.

- El arreglo (`named_label`) va en el código de producción y se aplica igual a v1 y a v2. La línea
  del prompt que describe `<topic_label>` pasa a «el nombre del tema, generado a partir de sus
  piezas» en los dos prompts; es el único cambio del prompt v2 (nuevo sha256 arriba).
- Las 53 salidas v2 ya generadas con el rótulo antiguo se descartan sin mirarlas (solo se leyeron
  sus contadores de tokens) y se generan de nuevo. Sus 53 llamadas cuentan en el gasto.
- La línea base v1 sigue siendo el texto servido en la ejecución 38, que se generó con el rótulo
  antiguo. El guard compara la cobertura de la posición 2, no el contenido, así que se mantiene.
- Nada más cambia: candidato, criterios, guard, tolerancia, muestra y semilla.

## Enmienda 2 (antes de mirar ninguna salida)

En los briefs y en esta evaluación, el nombre del tema cuenta como título de pieza también si
coincide con algún `content_items.title` de la DB, no solo con la evidencia servida (recortada a
25): así falla en cerrado (regla 6). Comprobado en solo lectura: en la ejecución 38 no cambia
ninguno de los 53 rótulos, así que las salidas v2 generadas tras la enmienda 1 siguen valiendo.
