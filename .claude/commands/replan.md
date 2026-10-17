---
description: Cierra el bucle. Toma un plan que volvió BLOQUEADO, re-interroga solo lo abierto, actualiza el plan en sitio y lo deja listo para relanzar /build.
argument-hint: <ruta-al-plan | slug>
disable-model-invocation: true
---

Tercera fase del ciclo `spec → build → replan`. Entrada: `$ARGUMENTS`.

Se usa cuando `plan-implementer` paró con `GATE: blocked`, o cuando `code-standards-auditor`
devolvió `rework` y arreglarlo exige una decisión de producto o de diseño.

## 0. Contexto

Lee completo `docs/engineering-standards.md`.

## 1. Localizar el plan

Igual que `/build`: ruta, `.claude/plans/<slug>.plan.md`, o lista por fecha y pregunta.
Si no existe, para: para planear de cero está `/spec`.

## 2. Leer el estado real

Lee el plan entero. Después mira qué pasó de verdad:

- `git log --oneline <rama-base>..HEAD`
- `git status --porcelain`
- `git diff <rama-base>...HEAD --stat`

Un intento bloqueado deja el repo a medias; si lo ignoras, el segundo intento repite pasos.

## 3. Clasificar cada bloqueo

Para cada pregunta abierta, antes de preguntar nada:

- **Hecho averiguable** → míralo en el código o en la doc oficial, resuélvelo y bórralo de la lista
  anotando dónde lo comprobaste.
- **Decisión del humano** → va al interrogatorio.
- **Plan mal escrito** → reescribe el paso y explica qué le faltaba.

No devuelvas al humano preguntas que el código ya responde.

## 4. Interrogatorio acotado

Solo sobre las decisiones del humano. Con `AskUserQuestion`, hasta 4 por llamada, tu recomendación
primero. No reabras "Decisiones tomadas" ni "Alternativas rechazadas" sin pedir permiso explícito.

## 5. Actualizar el plan en sitio

Mismo archivo:

1. Decisiones nuevas en "Decisiones tomadas", numeradas desde la última, con su porqué.
2. Pasos afectados reescritos.
3. Pasos ya completados marcados `[HECHO en <sha corto>]`.
4. Entrada nueva en "Historial de intentos".
5. "Preguntas abiertas" → `(ninguna)` y gate → `LISTO`.

Si no se cerró todo, el gate se queda en `BLOQUEADO` y dices qué falta. Un plan medio cerrado que
dice `LISTO` es peor que uno bloqueado.

## 6. Relanzar

Resume en 5 líneas qué cambió y pregunta:

> ¿Relanzo `/build`?

Si dice que sí, sigue el flujo de `/build` sobre este plan.
