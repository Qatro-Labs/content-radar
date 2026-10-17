---
description: Fase de planning. Investiga el código, te interroga hasta cerrar las decisiones y escribe un plan autocontenido para que plan-implementer lo ejecute con contexto limpio. Con un plan existente, lo retoma y cierra sus bloqueos.
argument-hint: <descripción libre | #issue | slug-o-ruta-de-un-plan>
disable-model-invocation: true
---

Fase de planning del ciclo `spec → build`, en versión hackathon. Entrada: `$ARGUMENTS`.

**Presupuesto:** unos 15 minutos de sesión. Si la tarea cabe en menos de 30 minutos de trabajo o es
iteración visual de UI, dilo en una línea y propón hacerla directamente sin plan. El plan cuesta
más de lo que ahorra en tareas pequeñas.

## 0. Contexto obligatorio

Lee completo `docs/engineering-standards.md`. Ten presentes de `CLAUDE.md`: §2 (reglas no
negociables), §3 (ownership), §6 (contratos), §11 (convenciones), §12 (prioridades) y §13
(checkpoints). Un plan que choque con ellos no se propone.

## 1. Resolver la entrada

- `#<n>` → `gh issue view <n> --comments`. Copia sus criterios de aceptación verbatim.
- Texto libre → genera un slug `<area>-<slug-corto>` con `area` ∈ `data | intel | fe | mcp | chore`.
- Ruta o slug de un plan que ya existe en `.claude/plans/` → **modo continuar**: salta a la
  sección 9.
- Vacío → pregunta qué se va a planear y para. No inventes.

## 2. Encaje con el plan del equipo

Antes de investigar, deja claro:

- **Owner** según §3. Si la tarea es de otra persona, dilo y pregunta si seguir.
- **Prioridad** P0/P1/P2 según §12 y qué checkpoint de §13 desbloquea. Si es P2 y hay P0 abiertos
  de la misma persona, avisa: ningún P2 puede poner en riesgo un P0.
- **Contratos tocados** (`Opportunity`, `Evidence`, `ContentSignal`, OpenAPI, tools MCP). Si toca
  alguno, el plan no pasa el gate hasta que el humano confirme que avisó en el canal.

## 3. Reconocimiento

Regla: **si un hecho se puede mirar, se mira; solo las decisiones se preguntan.**

- Lee el código que toca la tarea: dónde vive la lógica, qué la llama, qué tests hay y qué estilo
  siguen. Si la zona es amplia, lanza subagentes `Explore` en paralelo.
- **APIs y librerías externas** (MCP SDK, YouTube Data API, SDK del LLM, shadcn-vue, ECharts…):
  comprueba el comportamiento en la documentación oficial con WebFetch antes de decidir nada.
  La memoria del modelo no es una fuente actual.
- **Bugs:** reprodúcelo y encuentra la causa raíz antes de planear el arreglo.

## 4. Diseño (ligero)

Decide y deja escrito:

- **Seam:** dónde vive la interfaz y por qué ahí, respetando §4 y §10 de `CLAUDE.md` (rutas
  delgadas → services → intelligence/db; el frontend no calcula).
- **Interfaz mínima:** firma, invariantes, modos de error y qué devuelve cuando faltan datos
  (`None` / `null` y `growth_status`; nunca un valor inventado).
- **Profundidad:** que quede mucho comportamiento detrás de poca interfaz.

**Patrones:** por defecto, ninguno. Solo si hay duplicación real o un condicional que ya creció
tres veces, presenta opciones con `AskUserQuestion` (incluye siempre "sin patrón" y marca tu
recomendación). Nunca lo decides tú.

## 5. Interrogatorio por rondas

Trata las decisiones como un árbol. La **frontera** son las preguntas cuyas dependencias ya están
resueltas: pregúntalas todas en la misma ronda.

- Usa `AskUserQuestion`: hasta 4 preguntas por llamada, 2–4 opciones cada una, tu recomendación
  primero y marcada "(Recomendado)", con su porqué en la descripción.
- Formula cada pregunta para que aceptar la recomendación sea lo rápido.
- Recalcula la frontera con cada respuesta. Objetivo: **2 rondas, 3 como máximo.** Lo que no sea
  decisivo para implementar, decídelo con el default sensato y anótalo como decisión.
- Nunca preguntes un hecho que puedes mirar.

Temas que hay que cerrar sí o sí, porque el implementador no puede preguntar:

- Alcance exacto y qué queda fuera.
- Casos límite y de error. En scoring, siempre: 0 snapshots, una sola fuente, ventana anterior
  vacía y métrica ausente.
- Seams de test y qué cuenta como "probado".
- Migraciones y datos existentes (los snapshots nunca se borran).
- Cómo se cargan las relaciones de la DB (sin lazy loading en async).
- Alternativas descartadas y por qué.

No escribas el plan hasta que el usuario confirme que hay entendimiento común.

## 6. Gate

¿Queda alguna pregunta abierta, o un contrato tocado sin aviso en el canal? Si sí, no cierres:
sigue preguntando o deja el gate en `BLOQUEADO` explicando qué falta.

## 7. Escribir el plan

Plantilla: `.claude/templates/plan.md`. Rellena **todas** las secciones.
Destino: `.claude/plans/<slug>.plan.md`. Se commitea en la rama de trabajo junto con la
implementación: es el handoff para el resto del equipo.

- El plan es la **única** entrada del implementador. Lo que no esté en el archivo se perdió.
- Referencias `path:línea` comprobadas.
- Metadatos con la rama base y su sha real (`git rev-parse --short HEAD`).
- Comandos de verificación exactos y copiables.
- "Preguntas abiertas" en `(ninguna)` y gate en `LISTO`.
- Ni secretos ni datos personales en el plan.

## 8. Entregar

Muestra un resumen de 5 líneas y la ruta del plan. Pregunta:

> ¿Lanzo la implementación con `plan-implementer` (contexto limpio) ahora?

Si dice que sí, sigue el flujo de `/build` con la ruta absoluta del plan. Si no, imprime
`/build <ruta-absoluta>` para lanzarlo después.

## 9. Modo continuar (plan existente)

Se usa cuando `/build` volvió `BLOQUEADO`, cuando el auditor pidió `rework` por una decisión de
producto o de diseño, o para retomar una tarea a medias. El plan es el estado vivo de la tarea:
decisiones, pasos `[HECHO]`, historial de intentos y preguntas abiertas.

1. **Lee el plan entero** y mira qué pasó de verdad, no lo que el plan dice que iba a pasar:
   - `git log --oneline <rama-base>..<rama-de-trabajo>`: qué commits quedaron.
   - `git status --porcelain`: trabajo sin commitear.
   - Comprueba que cada paso marcado `[HECHO]` tiene su commit (el mensaje del paso) en la rama.
2. **Clasifica cada pregunta abierta** antes de preguntar nada:
   - **Hecho averiguable** → míralo en el código o en la doc oficial, resuélvelo y anota dónde.
   - **Decisión del humano** → al interrogatorio.
   - **Paso mal escrito** → reescríbelo y explica qué le faltaba.
3. **Interroga solo las decisiones**, como en la sección 5. No reabras "Decisiones tomadas" ni
   "Alternativas rechazadas" sin pedir permiso explícito.
4. **Actualiza el plan en sitio** (mismo archivo):
   - Decisiones nuevas numeradas desde la última, con su porqué.
   - Pasos afectados reescritos; los `[HECHO]` se quedan como están.
   - Entrada nueva en "Historial de intentos".
   - "Preguntas abiertas" → `(ninguna)` y gate → `LISTO`. Si algo no se cerró, el gate se queda en
     `BLOQUEADO` y dices qué falta: un plan medio cerrado que dice `LISTO` es peor que uno bloqueado.
5. Resume en 5 líneas qué cambió y pregunta si relanzar `/build`.
