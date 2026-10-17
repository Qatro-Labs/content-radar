# Estándares de ingeniería — 30X Signal

Lectura obligatoria para `/spec`, `/build`, `plan-implementer` y `code-standards-auditor`.
Complementa a `CLAUDE.md` (reglas de producto §2, ownership §3, contratos §6, convenciones §11);
no la repite.

Precedencia, de mayor a menor:

1. Las reglas no negociables de `CLAUDE.md` §2.
2. El código que ya existe alrededor de lo que tocas.
3. Este documento.
4. Tus defaults.

Si este documento y el código vecino chocan, gana el código vecino y lo anotas como deuda.

---

## 1. Diseño

- Arquitectura de `CLAUDE.md` §4 y §10: rutas delgadas → `services/` → `intelligence/` o `db/`.
  La API y el MCP llaman a los mismos services; ninguno duplica lógica.
- **Cálculo pesado fuera del request.** Embeddings, clustering y scoring corren en jobs
  (`app.jobs.*`) y se persisten. La API y el MCP leen resultados ya calculados.
- **El LLM explica, no calcula.** Ningún score sale de un LLM. Si un número aparece en la UI o
  en el MCP, lo calculó Python de forma determinista.
- Vocabulario de diseño: *module*, *interface* (firma + invariantes + modos de error), *seam*,
  *adapter*, *depth*. Un módulo es profundo cuando esconde mucho comportamiento detrás de una
  interfaz pequeña.
- **Regla de dos.** No abstraigas por una sola implementación: un adapter es un seam hipotético,
  dos son uno real. `SignalCollector` (`app/collectors/base.py`) es el ejemplo bueno: varias
  implementaciones reales detrás de un `Protocol`.
- SOLID como diagnóstico de un dolor real, no como checklist.

## 2. Patrones de diseño

Se proponen en `/spec` y los elige el humano. En implementación no se introduce un patrón que el
plan no nombró. Sesgo por defecto: **sin patrón**, salvo que elimine duplicación real o un
condicional que ya creció tres veces.

## 3. Legibilidad, comentarios y docstrings

Cuando legibilidad y cualquier otra cosa (brevedad, cleverness, micro-performance) chocan, gana
legibilidad.

- Nombres que no necesitan comentario: `compute_acceleration()` y no `process()`.
- Un nivel de abstracción por función. Return temprano con guard clauses.
- Nada de flags booleanos que cambian el comportamiento: son dos funciones.
- Sin negaciones dobles (`if not is_disabled`).
- Identificadores en inglés. Comentarios en español, como el código existente.

### Comentarios: los necesarios

Un comentario explica **por qué**, nunca **qué**. Si hace falta explicar qué hace el código, el
nombre falló: arregla el nombre.

Sí llevan comentario:

- Una decisión no obvia, sobre todo si la alternativa evidente es incorrecta.
  Ejemplo del repo: `MIN_SNAPSHOT_GAP` en `app/services/signals.py`.
- Una fórmula o un umbral de scoring: de dónde sale (p. ej. "`CLAUDE.md` §7").
- Un workaround con referencia externa (issue, doc, límite de una API).
- Regex o expresiones densas.
- Restricciones de una API externa (cuotas de YouTube, límites del pooler).

Nunca: comentarios que repiten el código, separadores de sección, código comentado, `# noqa` o
`# type: ignore` sin motivo, TODO sin responsable.

### Docstrings: no por defecto

Una función bien nombrada y tipada no necesita docstring. Solo se escriben cuando alguien fuera
del módulo **lee** ese texto:

- **Tools del MCP:** el docstring es la descripción que lee el asistente. Obligatorio y cuidado.
- **Contratos compartidos** (`app/schemas/`): una o dos líneas de módulo que digan qué contrato es
  y quién lo consume. Para los campos, `Field(description=...)`, que llega a OpenAPI y al tipo TS.
- **Rutas de FastAPI** solo si la descripción aporta algo a `/docs` que el nombre no dice.

Nunca un docstring que reformula la firma o enumera los parámetros.

## 4. Tamaño

Señales de "para y mira", no leyes. Excederlas exige una razón que se pueda decir en una frase.

- Funciones: objetivo ≤ 20 líneas; pasadas las 30, se extrae.
- Archivos: objetivo ≤ 300 líneas; pasadas las 500, se parte por responsabilidad.
- Argumentos: ≤ 3 posicionales; más, keyword-only o un dataclass/modelo.
- Anidamiento: ≤ 2 niveles dentro de una función.
- Componentes Vue: objetivo ≤ 200 líneas; si crece, se extrae un subcomponente o un composable.

## 5. Constantes y enums

- Cero literales mágicos en condiciones, límites, claves o estados.
- **Umbrales de scoring como constantes con nombre** (`CLAUDE.md` §11), en el módulo que los usa:
  `OUTLIER_RATIO_MIN = 3.0`, `CURRENT_WINDOW_DAYS = 3`.
- Conjuntos cerrados → `StrEnum`, como `Platform` o `Segment` en `app/schemas/signal.py`.
- El mismo literal en dos sitios es una constante que falta.
- Excepción: `0`, `1`, `""`, `None` en su significado obvio.

## 6. Python idiomático

- Tipos en todas las firmas nuevas. Pyright sin errores en los archivos tocados; nada de `Any` ni
  `# type: ignore` sin justificar.
- Pydantic para lo que cruza fronteras (API, MCP, salidas del LLM, contratos). `dataclass` para
  agregados internos. Nada de diccionarios anónimos paseándose entre funciones.
- `Protocol` para tipar seams sin herencia.
- Comprehensions cuando caben en una línea legible; si no, `for`.
- `enumerate`, `zip`, `itertools`, `collections` antes que reinventarlos. `pathlib`, f-strings.
- Excepciones específicas. `except Exception` solo en un borde que loguea y re-lanza o degrada
  de forma explícita. Nunca `except: pass`.
- Nada de mutable default args, `type()` en lugar de `isinstance`, ni `== None`.
- Funciones de scoring **puras**: entran datos, sale un resultado. Sin DB, sin red, sin reloj
  implícito (el "ahora" se pasa como argumento).

## 7. Acceso a datos (SQLAlchemy 2 async + Postgres)

- **Sin lazy loading.** En async, acceder a una relación no cargada falla. Las relaciones se
  cargan de forma explícita con `selectinload` (colecciones) o `joinedload` (muchos-a-uno).
- Nunca una query dentro de un bucle cuando se puede hacer en bloque: `where(... .in_(ids))`,
  `insert().values([...])` o `on_conflict_do_update`.
- Agregados en SQL (`func.count`, `func.max`, `group_by`), no en Python.
- Índice en toda columna nueva que se filtre u ordene.
- Todo cambio de modelo lleva su migración de Alembic con nombre descriptivo
  (`uv run alembic revision --autogenerate -m "..."`), revisada a mano antes de commitear.
- `metric_snapshots` nunca se actualiza ni se borra: sin historial no hay velocidad.
- Conexiones: la DB compartida va por el *session pooler* de Supabase. No abrir pools grandes.
- No optimices sin medir.

## 8. Tests

Los tests atrapan regresiones reales; no suben cobertura.

- Prueba comportamiento externo en el seam más alto posible. Si un refactor que no cambia el
  comportamiento rompe el test, el test está mal.
- **Red antes de green.** Test que falla por el motivo correcto → código mínimo que lo pasa.
  Rebanadas verticales: un test, una implementación, repetir.
- Nada de tests tautológicos: el valor esperado sale de un ejemplo trabajado a mano o del spec,
  nunca de recalcularlo como lo hace el código.
- **Casos límite obligatorios en scoring** (`CLAUDE.md` §11): 0 snapshots, una sola fuente,
  ventana anterior vacía, métrica ausente (`None`). No son inventados: van a pasar con datos reales.
- Fuera de eso, un caso entra solo si el plan lo nombra, puede pasar con datos reales o ya se
  rompió una vez.
- `@pytest.mark.parametrize` con `ids=` legibles cuando solo cambia el input.
- Mockea el borde (HTTP con `respx`, reloj), nunca la lógica bajo prueba. Nada de red real.
- Tests de DB contra `radar_test` (ver `backend/tests/conftest.py`).
- Frontend: Vitest + Vue Testing Library para lógica de presentación no trivial (formateo de
  métricas, estados vacíos). La UI visual se verifica a mano en el navegador.

## 9. Frontend (Vue)

- `<script setup lang="ts">` y Composition API. Props con `defineProps<...>()` tipado.
- **Tipos de la API solo desde `src/types/api.ts`** (generado con `openapi-typescript`). Nunca
  escribir a mano tipos que vienen del backend.
- Datos remotos solo vía composables en `src/api/` (TanStack Vue Query + `openapi-fetch`).
  Los componentes no llaman a `fetch`.
- **El frontend no calcula tendencias ni scores.** Solo formatea lo que llega.
- **Métrica ausente → se dice** ("sin dato", "preliminar"). Nunca se rellena ni se estima en el
  front.
- Filtros del Radar en la URL (query params de Vue Router).
- Texto de UI en español. Sin `any`.
- Componentes de `components/ui/` (shadcn-vue): se usan, no se reescriben salvo para el tema.
- Antes de tocar UI: leer `DESIGN.md`.

## 10. Boy Scout

Deja el código mejor de como lo encontraste, **sin desviarte del plan** y solo en archivos que ya
tocas: renombrar algo que miente, sacar un literal a constante, borrar código muerto o imports sin
usar, tipar una firma que tocas.

Prohibido sin permiso: refactors en archivos que el plan no toca, cambiar contratos o firmas que
otros llaman, migraciones o dependencias no previstas. Lo que veas y no arregles va al informe como
deuda (`path:línea` + una línea).

## 11. Herramientas y verificación

Backend (`cd backend`):

```bash
uv run ruff check . && uv run ruff format --check .
uv run pyright <archivos tocados>
uv run pytest
```

Frontend (`cd frontend`), con los scripts que existan en `package.json`:

```bash
pnpm lint && pnpm type-check && pnpm test && pnpm build
```

- Ramas cortas por área: `data/…`, `intel/…`, `fe/…`, `chore/…`. `main` siempre desplegable.
- Commits en inglés, en imperativo y cortos, con el estilo del historial
  (`Add HN, RSS and YouTube collectors and collect job`).
- Dependencias con versión mínima exacta y lockfile commiteado. No añadir paquetes publicados hace
  menos de 7 días. Torch y similares, solo en el grupo `ml` (`CLAUDE.md` §7).
- Nunca secretos en el código, en los planes ni en los commits.

## 12. La prueba final

Antes de dar algo por terminado:

1. ¿Un compañero entiende cada función leyéndola una vez?
2. ¿Cada nombre dice la verdad completa?
3. ¿Los tests fallarían si rompes el comportamiento, y solo entonces?
4. ¿Queda el módulo más fácil de cambiar mañana que ayer?
5. ¿Algún dato mostrado podría leerse como real sin serlo? (`CLAUDE.md` §2.3)

Si alguna respuesta es "no", el trabajo no está terminado: dilo en el informe.
