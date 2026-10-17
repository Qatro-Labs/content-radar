---
description: Fase de implementación. Lanza plan-implementer (contexto limpio) sobre un plan cerrado por /spec y, si toca, una auditoría independiente.
argument-hint: <ruta-al-plan | slug>
disable-model-invocation: true
---

Fase de implementación del ciclo `spec → build`. Entrada: `$ARGUMENTS`.

## 1. Localizar el plan

- Ruta → úsala.
- Slug → `.claude/plans/<slug>.plan.md`.
- Vacío → lista `.claude/plans/*.plan.md` por fecha de modificación y pregunta cuál.

Si no existe, para y di que hay que correr `/spec` primero. No improvises un plan.

## 2. Comprobar el gate

Lee **solo** la cabecera: "Metadatos" (gate, contratos tocados, auditoría) y "Preguntas abiertas".

- Gate `BLOQUEADO` o preguntas abiertas → para. Muéstralas y recomienda `/replan <ruta>`.
  No las resuelvas tú.
- Contrato tocado sin aviso en el canal → para y pide que se avise primero.
- Gate `LISTO` → sigue.

No leas el plan entero: lo lee el implementador en su propio contexto.

## 3. Comprobar el árbol de trabajo

`git status --porcelain`. El propio archivo del plan sin trackear es lo esperado. Si hay otros
cambios sin commitear, dilo y pregunta si seguir, hacer stash o abortar. Espera respuesta.

## 4. Lanzar

Lanza el subagente `plan-implementer` con este prompt y nada más:

```
Implementa el plan que está en <RUTA-ABSOLUTA-DEL-PLAN>.

Ese archivo es tu única fuente de intención. Léelo entero antes de tocar código.
Repo: <RUTA-ABSOLUTA-DEL-REPO>.
```

No le pases contexto de esta conversación: el contexto limpio es el objetivo.
Sin `isolation: "worktree"` salvo que el usuario lo pida: el backend depende de Docker y de
`backend/.env`, que un worktree nuevo no hereda.

## 5. Auditoría independiente

Si el plan dice "Auditoría: sí" y el implementador terminó con commits, lanza
`code-standards-auditor` sobre `<rama-base>...HEAD`.

Si el veredicto es `rework` o hay un `blocker`:

- Hallazgo mecánico (tamaño, constante, comentario, query, test) → relanza `plan-implementer` con
  la lista de hallazgos y la ruta del plan.
- Hallazgo que exige una decisión de producto o de diseño → `/replan <ruta>`.

No lo arregles tú desde esta sesión.

## 6. Reportar

En este orden:

- Informe del implementador: gate, rama, commits, pasos, verificación real, auto-auditoría, deuda,
  drift.
- Veredicto del auditor y sus hallazgos (si corrió).
- Qué queda pendiente y qué decisión necesita el usuario.

Si todo pasó, pregunta si hacer push y abrir el PR. El PR resume el plan, enlaza
`.claude/plans/<slug>.plan.md` y avisa de los contratos tocados.

Si volvió `BLOQUEADO`, el plan ya tiene las preguntas anotadas: recomienda `/replan <ruta>`.
