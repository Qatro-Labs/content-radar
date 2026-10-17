# <slug> — <título corto>

> Plan generado con `/spec`. Lo implementa `plan-implementer` con contexto limpio.
> El implementador NO ve la conversación que produjo este documento: todo lo que necesite tiene que
> estar escrito aquí.

## Metadatos

- **Slug:** `<area>-<slug>` · **Issue:** <#n o "ninguno">
- **Owner (CLAUDE.md §3):** Steven | Melkin | Frontend lead
- **Prioridad (CLAUDE.md §12):** P0 | P1 | P2 · **Checkpoint que desbloquea (§13):** <cuál>
- **Valor (filtro de CLAUDE.md §12):** <paso del recorrido de demo que mejora> · **Pregunta de
  `docs/brief.md` §4:** <#n>
- **Repo:** <path absoluto>
- **Rama base:** <rama> @ `<sha corto>`
- **Rama de trabajo:** `<data|intel|fe|chore>/<slug>`
- **Fecha:** <YYYY-MM-DD HH:MM ESP>
- **Contratos tocados:** ninguno | `Opportunity` / `Evidence` / `ContentSignal` / OpenAPI / tools MCP
  — si toca alguno: **avisado en el canal:** sí (<cuándo>) | no → gate `BLOQUEADO`
- **Auditoría tras `/build`:** sí | no *(sí siempre que toque scoring, contratos o datos)*
- **Estado del gate:** `LISTO` | `BLOQUEADO`

## Problema

Qué falta o qué está roto, desde la perspectiva de quien lo sufre. Sin solución todavía.

## Criterios de aceptación

Del issue (verbatim) o acordados en el interrogatorio. Cada uno verificable.

1. …

## No-objetivos

Lo que queda fuera. El implementador no lo toca aunque parezca una mejora obvia.

- …

## Reglas de CLAUDE.md §2 en juego

Cuáles aplican y cómo las respeta el plan (datos inventados, LLM que calcula, texto externo
no confiable, tipo de evidencia…). Si ninguna aplica, decirlo.

- …

## Contexto verificado del código

Hechos comprobados durante el planning. El implementador los relee antes de editar y reporta si
algo ya no coincide.

| Qué | Dónde | Estado actual |
| --- | --- | --- |
| … | `path/file.py:120` | … |

## Decisiones tomadas

Cerradas en el interrogatorio. El implementador las ejecuta, no las reabre.

### D1 — <decisión>

- **Elegido:** …
- **Por qué:** …
- **Descartado:** … *(razón)*

## Diseño de módulos

- **Seam:** dónde vive la interfaz y por qué ahí.
- **Interfaz:** firma, invariantes, orden, modos de error. Qué devuelve cuando faltan datos.
- **Ubicación (CLAUDE.md §10):** qué va en `services/`, `intelligence/`, `api/routes/`, `mcp/`, `src/…`.

## Patrones de diseño *(opcional: omitir si no hay patrón)*

Sin esta sección, no se usa ningún patrón. Si hay uno, decidido por el humano:

- **<patrón>** — qué problema del plan resuelve y qué cuesta.

## Acceso a datos *(opcional: omitir si no toca la DB)*

Qué queries, cómo se cargan las relaciones (`selectinload` / `joinedload`, sin lazy loading), si
hay migración y qué pasa con los datos existentes.

## Alternativas rechazadas *(opcional)*

- **<alternativa>** — rechazada porque …

## Plan de implementación

Pasos ordenados. Cada paso es verificable por sí solo y termina en un commit. El implementador
añade ` [HECHO]` al título del paso en ese mismo commit.

### Paso 1 — <qué>

- **Archivos:** `path/a.py`, `path/b.py`
- **Cambio:** …
- **Test primero:** `backend/tests/test_x.py::test_caso` — comportamiento externo esperado
  *(frontend sin lógica testeable: "verificación manual: <qué mirar en el navegador>")*
- **Verificación:** `<comando exacto>`
- **Commit:** `<Imperative English message>`

## Estrategia de test

- **Seams:** … (el más alto posible)
- **Prior art:** `backend/tests/test_….py` — imitar este estilo
- **Casos que entran:** lista cerrada, cada uno justificado (plan, datos reales o regresión)
- **Casos descartados por ruido:** …
- **Parametrización:** qué se agrupa y con qué `ids=`

## Verificación final

Comandos exactos, en orden. El implementador los corre todos y pega la salida real.

```bash
<comando 1>
```

## Riesgos *(opcional)*

- **<riesgo>** — señal de que ocurrió → qué hacer.

## Historial de intentos

Lo mantienen `plan-implementer` (cuando se bloquea) y `/spec` en modo continuar.

| Fecha | Qué bloqueó | Qué se decidió | Commits que quedaron |
| --- | --- | --- | --- |

## Preguntas abiertas

**Tiene que estar vacío para pasar el gate.** Si el implementador encuentra una pregunta nueva, la
añade aquí, pone el gate en `BLOQUEADO` y para.

- (ninguna)
