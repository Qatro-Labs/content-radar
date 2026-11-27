# Herramienta de contenido · Entrega 1: workspace mínimo, perfil de marca y lenguaje — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el radar de 30X pertenezca a un workspace con equipo, que ese equipo pueda editar su perfil de marca en la página «Tu marca» y que toda la UI hable sin jerga.

**Architecture:** Tres tablas nuevas (`workspaces`, `workspace_members`, `radar_profiles`) con 30X sembrado como único workspace `public_demo`. Una dependencia de FastAPI resuelve el workspace y si el usuario puede editar. Los briefs pasan de pertenecer a un usuario a pertenecer al workspace. En el frontend: la vista «Tu marca» (boceto C aprobado) y el cambio de etiquetas en los mapas de `lib/`.

**Tech Stack:** FastAPI, SQLAlchemy 2 + Alembic, Pydantic v2, pytest; Vue 3 + TanStack Vue Query + openapi-fetch, Vitest.

**Spec:** `docs/superpowers/specs/2026-11-27-herramienta-de-contenido-design.md` (§5, §6.1, §6.3 "Tu marca", §7.1, §7.5, §8 paso 1, §9). Se apoya en `docs/superpowers/specs/2026-11-26-radar-configurable-design.md` §6.1.

**Fuera de esta entrega (planes siguientes):** el brief con el perfil y la pantalla B (entrega 2); `weekly_picks`, calendario, portada D y navegación nueva (entrega 3); onboarding en frases (entrega 4). En esta entrega **nada consume todavía el perfil**: se guarda y se edita. La entrega 2 lo conecta a los prompts.

## Global Constraints

- UI y comentarios en español; código en inglés. Comentarios: el porqué, nunca el qué (`.claude/rules/engineering-standards.md`).
- TDD: cada tarea escribe el test primero y lo ve fallar.
- Nunca inventar datos (CLAUDE.md §2 regla 3). El perfil sembrado de 30X sale de `data/audiences/30x.yaml` y del prompt `editorial_brief.v1.md`; lo que no está ahí va como valor por defecto marcado.
- Todo texto del perfil es dato no confiable: se guarda tal cual y en el frontend nunca se pinta con `v-html`.
- Tablas nuevas con RLS activada, como en `alembic/versions/c3a9f2e81d47_enable_rls_on_public_tables.py`.
- Solo los miembros del workspace escriben; sin sesión se lee todo en un workspace `public_demo` (spec §7.5).
- Regla de Steven: cualquier pantalla o estado de UI sin boceto aprobado pasa antes por una ronda de **al menos 3 propuestas** y él elige (Task 7).
- Contrato compartido: avisar en el canal antes de mergear (CLAUDE.md §11). Tipos TS siempre regenerados con `pnpm gen:api`, nunca a mano.
- Claude nunca mergea: abre el PR y la persona decide.

## Review Focus

1. **Una persona sin sesión o que no es del equipo intenta escribir** (PUT /profile, DELETE de un brief): 401 sin sesión, 403 con sesión y sin pertenecer, y nada cambia. → Task 4 y Task 5.
2. **Dos miembros guardan el perfil a la vez** sobre la misma versión: el segundo recibe 409 con un mensaje para recargar y no pisa al primero. → Task 4.
3. **Texto con marcado o instrucciones en el perfil** (`<script>`, "ignora lo anterior"): se guarda y se devuelve tal cual, y la vista lo pinta como texto. → Task 4 y Task 8.
4. **El workspace no existe** (nadie corrió la siembra): `/workspace` y `/profile` devuelven 404 con un mensaje claro y el radar sigue funcionando. → Task 4.
5. **Los briefs guardados antes de la migración** siguen apareciendo en «Briefs», ahora como briefs del equipo de 30X, con sus versiones intactas. → Task 5.

## Decisiones del ejecutor de este plan (rulings ya tomados al planear)

- **R1 · Generar un brief sigue abierto; guardarlo es solo para el equipo.** La spec §7.5 pone "generar briefs" entre las escrituras de miembros, pero el recorrido de demo (CLAUDE.md §1) termina en "obtener un brief" para cualquiera. Quien no es miembro recibe el brief sin guardarlo, como hoy sin sesión. Coste si es incorrecto: cerrar `POST /editorial/brief` a miembros es una línea en Task 5.
- **R2 · Todos los briefs existentes pasan al workspace de 30X** en la migración. Hoy los usuarios son el equipo del hackathon y la fase es de desarrollo. Coste si es incorrecto: un brief privado de alguien de fuera pasa a verse en la demo pública. Se puede borrar a mano.
- **R3 · Rama desde `main`, con las dos specs incluidas.** La spec configurable vive hoy solo en `data/official-sources` (PR #95). Se copia idéntica al primer commit para no apilar esta rama sobre el PR. Si el PR se mergea antes, el archivo idéntico no da conflicto.
- **R4 · La vista previa de «Tu marca» usa el último brief guardado del equipo**, y sin briefs, una tarjeta "ejemplo" fija. No llama al LLM (spec §9.4).

---

### Task 1: Esquema del perfil de marca

**Files:**
- Create: `backend/app/schemas/profile.py`
- Test: `backend/tests/test_profile_schema.py`

**Interfaces:**
- Consumes: `BriefPlatform`, `BriefFormat`, `BriefGoal` de `app/schemas/editorial.py`.
- Produces:
  - `Weekday(StrEnum)`: `mon tue wed thu fri sat sun`.
  - `PublishingDay(BaseModel)`: `day: Weekday`, `channel: BriefPlatform`, `format: BriefFormat`.
  - `RadarProfile(BaseModel)`: `creates_about: str`, `audience: str`, `goal: BriefGoal`, `target_region: str`, `languages: list[str]`, `out_of_scope: str = ""`, `tone: list[str]`, `call_to_action: str = ""`, `never_say: str = ""`, `publishing_days: list[PublishingDay]`, y la propiedad `posts_per_week -> int` (= `len(publishing_days)`).
  - `WorkspaceRead`: `slug: str`, `name: str`, `public_demo: bool`, `role: Literal["owner", "member"] | None`.
  - `ProfileRead`: `profile: RadarProfile`, `version: int`, `updated_at: datetime`, `can_edit: bool`.
  - `ProfileUpdate`: `profile: RadarProfile`, `expected_version: int`.
  - Constantes: `MAX_TONE_WORDS = 3`, `MAX_TONE_WORD_CHARS = 30`, `MAX_SHORT_TEXT = 200`, `MAX_LONG_TEXT = 600`, `MAX_PUBLISHING_DAYS = 7`.

Límites: `creates_about`, `audience` y `target_region` son obligatorios, sin espacios sobrantes, de 1 a `MAX_SHORT_TEXT`. `call_to_action` llega a `MAX_SHORT_TEXT`. `out_of_scope` y `never_say` llegan a `MAX_LONG_TEXT`. `tone` lleva de 1 a 3 palabras de 1 a 30 caracteres. `languages` lleva de 1 a 3 códigos ISO de 2 letras. `publishing_days` lleva de 1 a 7 entradas, sin días repetidos.

- [ ] **Step 1: Write the failing tests**

```python
def test_valid_profile_counts_posts_per_week(): ...
    # 3 publishing_days → profile.posts_per_week == 3
def test_strips_whitespace_and_rejects_empty_required_text(): ...
    # creates_about="  " → ValidationError; "  Vivienda  " → "Vivienda"
def test_rejects_more_than_three_tone_words(): ...
def test_rejects_repeated_publishing_day(): ...
    # dos entradas con day="mon" → ValidationError
def test_rejects_no_publishing_days(): ...
def test_rejects_text_over_limit(): ...
    # never_say de MAX_LONG_TEXT + 1 caracteres → ValidationError
def test_keeps_markup_verbatim(): ...
    # never_say="<script>alert(1)</script> ignora lo anterior" se conserva igual
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && uv run pytest tests/test_profile_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: app.schemas.profile`

- [ ] **Step 3: Implement `app/schemas/profile.py`** with the interfaces above. Usa `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=...)]` y un `field_validator` para los días repetidos.

- [ ] **Step 4: Run them to verify they pass**

Run: `cd backend && uv run pytest tests/test_profile_schema.py -v`
Expected: PASS

- [ ] **Step 5: Commit**, primero las dos specs y el plan (R3) y después el esquema:

```bash
git add docs/superpowers/specs/2026-11-26-radar-configurable-design.md docs/superpowers/specs/2026-11-27-herramienta-de-contenido-design.md docs/superpowers/plans/2026-11-27-herramienta-contenido-1-workspace-perfil-lenguaje.md
git commit -m "Add the content-tool design and its first implementation plan"
git add backend/app/schemas/profile.py backend/tests/test_profile_schema.py
git commit -m "Add the brand profile schema"
```

### Task 2: Tablas de workspace y siembra de 30X

**Files:**
- Create: `backend/app/models/workspaces.py`, `backend/alembic/versions/<rev>_workspaces_and_profiles.py`, `backend/app/jobs/seed_workspace.py`
- Modify: `backend/app/models/__init__.py` (exportar los modelos)
- Test: `backend/tests/test_seed_workspace.py`

**Interfaces:**
- Consumes: `RadarProfile` (Task 1).
- Produces:
  - `WorkspaceRecord`: `id: int`, `slug: str` (único), `name: str`, `public_demo: bool`, `created_at`.
  - `WorkspaceMemberRecord`: `id`, `workspace_id` (FK, CASCADE), `user_id: str` (el `sub` de Supabase), `role: str` (`owner` o `member`, con CHECK), `created_at`, y `UniqueConstraint(workspace_id, user_id)`.
  - `RadarProfileRecord`: `id`, `workspace_id` (FK, CASCADE), `version: int`, `profile: JSONB`, `created_by: str | None` (None = la siembra), `created_at`, y `UniqueConstraint(workspace_id, version)`.
  - `async def seed_thirty_x(session) -> WorkspaceRecord`: es idempotente. Crea el workspace `slug="30x"`, `name="30X"`, `public_demo=True`, y la versión 1 de su perfil solo si no hay ninguna.
  - `THIRTY_X_PROFILE: RadarProfile`, con estos valores:
    - `creates_about="Crecimiento de empresas y aplicación de la IA con criterio y resultados"`
    - `audience`: el `audience.summary` de `30x.yaml`
    - `goal=educate`
    - `target_region="Latinoamérica"`
    - `languages=["es"]`
    - `out_of_scope`: el `audience.not_for` de `30x.yaml`
    - `tone=["directo", "práctico"]` (prompt v1, regla 5)
    - `call_to_action=""`
    - `never_say="Promesas de resultados que la evidencia no muestra"`
    - `publishing_days`: lun `instagram/short_video`, mié `instagram/carousel` y vie `instagram/short_video`. Son los días por defecto de la spec §9.5. Un comentario en el código dice que son valores por defecto y no la frecuencia real de 30X.
  - Comando: `uv run python -m app.jobs.seed_workspace`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_seed_creates_public_thirty_x_with_profile_v1(session): ...
    # workspace slug "30x", public_demo True; un RadarProfileRecord version 1, created_by None,
    # y RadarProfile.model_validate(record.profile) == THIRTY_X_PROFILE
async def test_seed_twice_keeps_one_workspace_and_one_profile(session): ...
async def test_seed_does_not_overwrite_an_edited_profile(session): ...
    # con una version 2 ya guardada, sembrar otra vez no añade ni cambia versiones
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && uv run pytest tests/test_seed_workspace.py -v`
Expected: FAIL with `ModuleNotFoundError: app.models.workspaces`

- [ ] **Step 3: Implement the models and the migration** (`uv run alembic revision --autogenerate -m "workspaces and profiles"`). Revisa el archivo generado: tiene que hacer `ALTER TABLE … ENABLE ROW LEVEL SECURITY` para las tres tablas.

- [ ] **Step 4: Implement `seed_thirty_x` and `THIRTY_X_PROFILE` in `app/jobs/seed_workspace.py`**, con un `main()` que abre la sesión y siembra.

- [ ] **Step 5: Run the tests and the migration**

Run: `cd backend && uv run pytest tests/test_seed_workspace.py -v && uv run alembic upgrade head && uv run python -m app.jobs.seed_workspace`
Expected: PASS. La siembra termina sin error, y si se corre una segunda vez no cambia nada.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models backend/alembic/versions backend/app/jobs/seed_workspace.py backend/tests/test_seed_workspace.py
git commit -m "Add workspaces, members and brand profiles, seeded with 30X"
```

### Task 3: Acceso al workspace y gestión de miembros

**Files:**
- Create: `backend/app/services/workspaces.py`, `backend/app/api/workspace_access.py`, `backend/app/jobs/workspace_members.py`
- Modify: `backend/app/core/config.py` (añadir `default_workspace_slug: str = "30x"`)
- Test: `backend/tests/test_workspace_access.py`

**Interfaces:**
- Consumes: los modelos de Task 2; `CurrentUser` y `user_if_signed_in` de `app/api/auth.py`.
- Produces:
  - `services.workspaces`:
    - `get_workspace(session, slug) -> WorkspaceRecord | None`
    - `member_role(session, workspace_id, user_id) -> Literal["owner", "member"] | None`
    - `add_member(session, workspace_id, user_id, role) -> None`: si ya existe, actualiza el rol.
    - `remove_member(session, workspace_id, user_id) -> bool`
    - `current_profile(session, workspace_id) -> RadarProfileRecord | None`: devuelve la versión más alta.
    - `save_profile(session, workspace_id, profile, *, created_by, expected_version) -> RadarProfileRecord`: lanza `ProfileConflict` si `expected_version` no es la última. También la lanza si la carrera de inserción choca con el `UniqueConstraint`.
  - `api.workspace_access`:
    - `@dataclass(frozen=True) WorkspaceAccess(workspace, user: CurrentUser | None, role)` con la propiedad `can_edit` (= `role is not None`).
    - Dependencias async:
      - `workspace_access`: 404 `"Este espacio de trabajo no existe todavía."` si falta. Si es privado y no hay rol, 404 (ningún workspace es privado todavía, pero se cubre).
      - `require_editor`: 401 sin usuario (reutiliza `_unauthorized`); 403 `"Solo el equipo de {name} puede cambiar esto."` si no hay rol.
  - CLI:
    - `uv run python -m app.jobs.workspace_members add --user-id <sub> --role owner|member [--workspace 30x]`
    - `… remove --user-id <sub>`

- [ ] **Step 1: Write the failing tests**

```python
async def test_member_role_none_for_strangers_and_role_for_members(session): ...
async def test_add_member_twice_updates_the_role(session): ...
async def test_save_profile_appends_next_version(session): ...
async def test_save_profile_with_stale_version_raises_conflict(session): ...
async def test_require_editor_401_without_user_403_for_non_member(session): ...
    # se llama a la dependencia directamente con WorkspaceAccess construidos a mano
def test_cli_add_then_remove(session_factory): ...
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && uv run pytest tests/test_workspace_access.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement the service, the dependencies and the CLI** with the interfaces above. `workspace_access` lee el slug de `Settings.default_workspace_slug`. Hay un solo workspace en esta entrega; la selección por usuario llega con el radar configurable.

- [ ] **Step 4: Run them to verify they pass**

Run: `cd backend && uv run pytest tests/test_workspace_access.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/workspaces.py backend/app/api/workspace_access.py backend/app/jobs/workspace_members.py backend/app/core/config.py backend/tests/test_workspace_access.py
git commit -m "Resolve the workspace and who may edit it"
```

### Task 4: Endpoints `/workspace` y `/profile`

**Files:**
- Create: `backend/app/api/routes/workspace.py`
- Modify: `backend/app/api/routes/__init__.py` (registrar el router), `CLAUDE.md` §6 (tablas nuevas y endpoints)
- Test: `backend/tests/test_workspace_routes.py`

**Interfaces:**
- Consumes: Task 3.
- Produces:
  - `GET /api/v1/workspace` → `WorkspaceRead`.
  - `GET /api/v1/profile` → `ProfileRead`. Un workspace sin perfil da 404 `"Este espacio todavía no tiene perfil de marca."`.
  - `PUT /api/v1/profile`, con cuerpo `ProfileUpdate`, → `ProfileRead` de la versión nueva. Exige `require_editor`. Con conflicto devuelve 409 `"Alguien del equipo guardó cambios mientras editabas. Recarga para ver la última versión."`.

- [ ] **Step 1: Write the failing tests** (reutiliza las fixtures `configure` y `client` de `tests/test_user_briefs.py`; si hace falta, muévelas a `conftest.py`)

```python
async def test_anonymous_reads_public_profile_without_edit_rights(...): ...
    # 200, can_edit False, version 1
async def test_workspace_shows_role_for_member_and_none_for_stranger(...): ...
async def test_put_without_token_is_401_and_changes_nothing(...): ...
async def test_put_by_non_member_is_403_and_changes_nothing(...): ...
async def test_member_put_creates_version_2(...): ...
async def test_put_with_stale_version_is_409(...): ...
async def test_markup_in_profile_round_trips_verbatim(...): ...
async def test_missing_workspace_is_404_and_opportunities_still_work(...): ...
    # sin sembrar: /workspace y /profile 404; GET /opportunities sigue 200 con `seeded`
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd backend && uv run pytest tests/test_workspace_routes.py -v`
Expected: FAIL with 404 en todas las rutas nuevas

- [ ] **Step 3: Implement the routes**, delgadas: solo llaman a `services.workspaces` (CLAUDE.md §11).

- [ ] **Step 4: Run them, then the whole suite**

Run: `cd backend && uv run pytest tests/test_workspace_routes.py -v && uv run pytest -q && uv run ruff check . && uv run pyright app/api/routes/workspace.py app/api/workspace_access.py app/services/workspaces.py app/schemas/profile.py`
Expected: PASS; suite verde; ruff y pyright sin errores en estos archivos

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes backend/tests/test_workspace_routes.py CLAUDE.md
git commit -m "Expose the workspace and its brand profile"
```

### Task 5: Los briefs pasan al workspace

**Files:**
- Create: `backend/alembic/versions/<rev>_briefs_belong_to_workspace.py`
- Modify: `backend/app/models/editorial.py`, `backend/app/services/user_briefs.py`, `backend/app/api/routes/editorial.py`
- Test: `backend/tests/test_user_briefs.py` (se adapta), `backend/tests/test_brief_migration.py`

**Interfaces:**
- Consumes: `WorkspaceAccess`, `workspace_access` y `require_editor` (Task 3).
- Produces:
  - `EditorialBriefRecord`: `workspace_id: int` (FK, CASCADE, NOT NULL) e índice `(workspace_id, root_id)` en lugar del de `user_id`. `user_id` se renombra a `created_by: str`.
  - `user_briefs.create_brief(session, request, *, workspace_id: int | None, created_by: str | None, parent_brief_id, briefer, now)`: guarda solo con los dos valores (R1). El padre se busca dentro del workspace.
  - `list_briefs(session, workspace_id)`, `get_brief(session, workspace_id, brief_id)` y `delete_brief(session, workspace_id, brief_id)`.
  - Rutas:
    - `POST /editorial/brief`: guarda si `access.can_edit`; si no, devuelve el brief con `id=null`.
    - `GET /editorial/briefs` y `GET /editorial/briefs/{id}`: usan `workspace_access`, se leen sin sesión en `public_demo` y dan 404 si el brief es de otro workspace.
    - `DELETE`: usa `require_editor`.

- [ ] **Step 1: Write the failing migration test**

```python
async def test_existing_briefs_move_to_thirty_x_keeping_versions(engine_at_previous_revision): ...
    # inserta 2 cadenas (v1, v2) con user_id; upgrade; todas con workspace_id del 30X,
    # created_by == antiguo user_id, root_id/version intactos (R2)
```

- [ ] **Step 2: Adapt `tests/test_user_briefs.py` to the new rules** (renombrar y reescribir):

```python
async def test_member_post_saves_the_brief_in_the_workspace(...): ...
async def test_non_member_post_returns_brief_without_saving(...): ...   # R1, id is None
async def test_anonymous_lists_team_briefs_of_public_workspace(...): ...
async def test_any_member_sees_briefs_created_by_another_member(...): ...
async def test_non_member_delete_is_403_and_keeps_the_brief(...): ...
async def test_anonymous_delete_is_401(...): ...
async def test_parent_from_another_workspace_is_404(...): ...
```

Conserva los tests de versiones (cadena, misma petición, borrar la cadena) cambiando el usuario por un miembro.

- [ ] **Step 3: Run them to verify they fail**

Run: `cd backend && uv run pytest tests/test_user_briefs.py tests/test_brief_migration.py -v`
Expected: FAIL

- [ ] **Step 4: Implement the migration.** Pasos:
  1. Añadir `workspace_id` como columna nula.
  2. Asegurar que existe la fila del workspace 30X con el mismo SQL que la siembra, solo para el workspace.
  3. Rellenar todas las filas con ese workspace (R2).
  4. Poner `NOT NULL`.
  5. Renombrar `user_id` a `created_by`.
  6. Cambiar el índice.

  El `downgrade` deshace los pasos en orden inverso.

- [ ] **Step 5: Implement the model, service and route changes** with the interfaces above. El docstring de `models/editorial.py` pasa a decir "briefs del equipo".

- [ ] **Step 6: Run them, then the whole suite**

Run: `cd backend && uv run pytest tests/test_user_briefs.py tests/test_brief_migration.py -v && uv run pytest -q && uv run ruff check .`
Expected: PASS; suite verde

- [ ] **Step 7: Commit**

```bash
git add backend/alembic/versions backend/app/models/editorial.py backend/app/services/user_briefs.py backend/app/api/routes/editorial.py backend/tests
git commit -m "Make saved briefs belong to the workspace team"
```

### Task 6: Contrato y capa de API del frontend

**Files:**
- Modify: `frontend/src/types/api.ts` (regenerado), `frontend/src/components/editorial/MyBriefs.vue` (título y borrar solo para miembros), `frontend/src/components/editorial/SavedBriefRow.vue` (si muestra el botón de borrar)
- Create: `frontend/src/api/workspace.ts`
- Test: `frontend/src/api/__tests__/workspace.test.ts`, `frontend/src/components/editorial/__tests__/MyBriefs.test.ts` (adaptar)

**Interfaces:**
- Consumes: los endpoints de Task 4 y Task 5.
- Produces:
  - `useWorkspace()`: query `['workspace']` → `WorkspaceRead`.
  - `useProfile()`: query `['profile']` → `ProfileRead`.
  - `useSaveProfile()`: mutación `PUT /profile`. Al terminar bien, invalida `['profile']`. Ante un 409 expone `conflict: true` y no reintenta.
  - `canEdit(workspace: WorkspaceRead | undefined): boolean`.

- [ ] **Step 1: Regenerate the types** with the API running: `cd backend && uv run uvicorn app.main:app` and, in another terminal, `cd frontend && pnpm gen:api`.
Expected: `api.ts` incluye `WorkspaceRead`, `ProfileRead`, `ProfileUpdate`, `RadarProfile` y `PublishingDay`.

- [ ] **Step 2: Write the failing tests**

```ts
it('saving the profile invalidates the profile query', ...)
it('a 409 on save is reported as a conflict and not retried', ...)
it('MyBriefs is titled "Briefs del equipo" and hides delete for non-members', ...)
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd frontend && pnpm test -- workspace MyBriefs`
Expected: FAIL

- [ ] **Step 4: Implement `api/workspace.ts` and the `MyBriefs` change.** Hasta ahora `MyBriefs` solo se veía con sesión (`isConfigured`). Ahora la lista se ve siempre que haya workspace público, y borrar requiere `canEdit`.

- [ ] **Step 5: Run them and the frontend checks**

Run: `cd frontend && pnpm test && pnpm lint && pnpm type-check`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/api frontend/src/components/editorial
git commit -m "Read the workspace and profile from the frontend; briefs are the team's"
```

### Task 7: Ronda de propuestas para los estados de «Tu marca» sin boceto

No escribe código de producto. El boceto C aprobado muestra la página con un miembro editando. Faltan estos estados:
- visitante sin sesión o usuario que no es del equipo (solo lectura);
- cargando;
- error al guardar y conflicto 409;
- cambios sin guardar al salir de la página;
- "Guardado".

- [ ] **Step 1:** Añade al lienzo `https://claude.ai/artifact/SPhz4VdbFSCZZ7mrNxvPDA` una página «Tu marca · estados» con **al menos 3 propuestas** que cubran todos esos estados, interactivas, con datos de ejemplo marcados como tales y el estilo de `DESIGN.md`.
- [ ] **Step 2:** Pide a Steven que elija y **espera su respuesta**. Esto es un bloqueo legítimo: es su regla, no una consulta de progreso.
- [ ] **Step 3:** Anota la elección en el ledger como `Task 7: Steven eligió <propuesta>` con el enlace al tablero.

### Task 8: Vista «Tu marca»

**Files:**
- Create: `frontend/src/views/BrandView.vue`, `frontend/src/components/brand/BrandForm.vue`, `frontend/src/components/brand/BrandPreview.vue`, `frontend/src/lib/brandProfile.ts`
- Modify: `frontend/src/router/index.ts` y `frontend/src/router/routeNames.ts` (ruta `/marca`, `RouteName.Brand`), `frontend/src/components/layout/AppHeader.vue` (enlace «Tu marca»)
- Test: `frontend/src/lib/__tests__/brandProfile.test.ts`, `frontend/src/views/__tests__/BrandView.test.ts`

**Interfaces:**
- Consumes: `useWorkspace`, `useProfile`, `useSaveProfile` y `canEdit` (Task 6); `useSavedBriefs` y `useSavedBrief` de `api/editorial.ts` (para R4); los estados que eligió Steven (Task 7).
- Produces:
  - `lib/brandProfile.ts`:
    - `type BrandDraft`: el `RadarProfile` editable.
    - `toDraft(profile): BrandDraft`
    - `draftErrors(draft): Partial<Record<keyof BrandDraft, string>>`: aplica los mismos límites que Task 1, con mensajes en español.
    - `isDirty(draft, profile): boolean`
    - `previewOf(draft, brief: EditorialBrief | null): BrandPreviewModel`. Con brief, toma de él el tema y el gancho. Sin brief, usa el ejemplo fijo `"Tema de ejemplo"`, marcado `isExample: true`. Siempre toma del borrador el cliente, la región, el cierre, el tono, lo que evita y "Cada lunes verás N temas".

Estructura del boceto C ([tablero](https://claude.ai/artifact/SPhz4VdbFSCZZ7mrNxvPDA#artboard-PerfilVistaPrevia)):
- **Columna izquierda, campos en tres tarjetas:**
  1. cliente, dónde está y sobre qué creas contenido;
  2. tono (botones; máximo 3), qué quieres que haga quien te lee, qué nunca decimos;
  3. días y formatos de publicación, más objetivo.
- **Columna derecha:** la vista previa oscura, que se queda fija al hacer scroll.
- **"Guardar cambios"**, activo solo con cambios válidos.

Texto fijo: el subtítulo es «Cambia algo a la izquierda y mira a la derecha cómo cambiaría tu próximo brief.», y después de guardar aparece «Guardado. Tus próximos briefs usarán este perfil.».

- [ ] **Step 1: Write the failing tests**

```ts
// brandProfile
it('draftErrors flags a fourth tone word and a repeated day', ...)
it('previewOf uses the latest brief topic and hook, or a marked example without briefs', ...)
it('previewOf reflects the draft call to action and never_say immediately', ...)
// BrandView
it('a member edits, saves, and sees the saved message', ...)
it('a visitor sees the profile read-only as chosen in Task 7', ...)
it('a 409 shows the conflict message and keeps the draft', ...)
it('markup in never_say renders as text, not HTML', ...)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd frontend && pnpm test -- brandProfile BrandView`
Expected: FAIL

- [ ] **Step 3: Implement `lib/brandProfile.ts`**, then `BrandForm`, `BrandPreview` and `BrandView`, with shadcn-vue and the `DESIGN.md` tokens. Para los estados de solo lectura, error y cargando, sigue la propuesta elegida en Task 7.

- [ ] **Step 4: Run them and the frontend checks**

Run: `cd frontend && pnpm test && pnpm lint && pnpm type-check && pnpm build`
Expected: PASS

- [ ] **Step 5: Look at it in the real app.** Con la API y `pnpm dev` en marcha, abre `/marca` con sesión de miembro y sin sesión, y compara con el boceto C y con lo elegido en Task 7.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/BrandView.vue frontend/src/components/brand frontend/src/lib/brandProfile.ts frontend/src/lib/__tests__ frontend/src/views/__tests__ frontend/src/router frontend/src/components/layout/AppHeader.vue
git commit -m "Add the Tu marca page with its brief preview"
```

### Task 9: Lenguaje sin jerga

Es un cambio de texto, no de diseño visual: no necesita ronda de propuestas. Si alguna etiqueta más larga rompe una maqueta (chip cortado, columna desbordada), eso sí es un cambio visual y pasa por la regla de 3 propuestas antes de tocar estilos.

**Files:**
- Modify:
  - `frontend/src/lib/opportunityFormat.ts`
  - `frontend/src/lib/lifecycle.ts`
  - `frontend/src/lib/evidenceFormat.ts`
  - `frontend/src/lib/helpText.ts`
  - `frontend/src/lib/exploreView.ts` (etiqueta del filtro)
  - `DESIGN.md` §9 (etiquetas fijas)
  - el texto visible que contenga los términos de la tabla
- Test: los tests existentes en `frontend/src/lib/__tests__/` y `components/**/__tests__/` que fijan las etiquetas antiguas (se actualizan) y uno nuevo, `frontend/src/lib/__tests__/plainLanguage.test.ts`

Mapa exacto (spec §5):

| Dónde | Antes | Después |
|---|---|---|
| `RECOMMENDATION_LABEL.wait_for_case` | Esperar caso | Esperar un caso real |
| lifecycle `emerging` | Emergente | Empieza a crecer |
| lifecycle `accelerating` | Acelerando | Crece rápido |
| lifecycle `peaking` | En pico | En su punto alto |
| lifecycle `saturated` | Saturado | Ya muy cubierto |
| `ratioLabel` con `is_outlier` | Outlier | Rinde 3× o más |
| filtro de Explorar | Outliers | Rinden 3× o más |
| `latamGapLabel(true)` | hueco en LATAM | casi nadie lo cuenta en Latinoamérica |
| `latamGapLabel(false)` | ya cubierto en LATAM | ya se cuenta mucho en Latinoamérica |
| `latamGapLabel(null)` | hueco en LATAM no disponible | cobertura en Latinoamérica no disponible |
| texto visible con "fuentes independientes" | fuentes independientes | fuentes distintas |
| `helpText.ts`, "outlier/outliers" en frases | "es un outlier" | "rinde 3× o más que lo normal" (reescribe cada frase para que se lea natural) |

"Sin tendencia clara", "En descenso", "Publicar ya", "Buscar ángulo" y "Descartar" no cambian. Los nombres internos (`is_outlier`, `outliers` como clave de filtro, `RatioLabel` como tipo) tampoco: solo cambia lo que ve la persona.

- [ ] **Step 1: Write the failing test**

```ts
// plainLanguage.test.ts
it('no user-facing label map contains internal jargon', () => {
  const visible = [
    ...Object.values(RECOMMENDATION_LABEL),
    ...LIFECYCLES.map((l) => lifecycleStyle(l).label),
    latamGapLabel(true), latamGapLabel(false), latamGapLabel(null),
    ...Object.values(HELP_TEXT).flatMap(Object.values),
  ].join(' ')
  expect(visible).not.toMatch(/outlier|momentum|LATAM|Emergente|Saturado|En pico/i)
})
it('uses the exact labels from the spec table', ...)  // una aserción por fila
```

(Ajusta los nombres importados a los que exporta cada archivo. Si `helpText.ts` no exporta un objeto, exporta uno para el test.)

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && pnpm test -- plainLanguage`
Expected: FAIL listando las etiquetas antiguas

- [ ] **Step 3: Change the labels and phrases**, then find leftovers:

Run: `cd frontend && grep -rnE "Emergente|Acelerando|En pico|Saturado|Esperar caso|Outlier|hueco en LATAM|fuentes independientes" src --include=*.vue --include=*.ts | grep -v __tests__`
Expected: solo identificadores y comentarios, ningún texto visible

- [ ] **Step 4: Update the old tests' expectations** to the new labels. Busca también textos del agente que vea la persona: `grep -rnE "Emergente|Saturado|En pico" backend/app/agent`. Actualiza solo lo que llega a la UI.

- [ ] **Step 5: Run everything**

Run: `cd frontend && pnpm test && pnpm lint && pnpm type-check && pnpm build` and `cd backend && uv run pytest -q`
Expected: PASS

- [ ] **Step 6: Look at it.** Recorre Radar, expediente, Explorar y Crear en `pnpm dev`. Comprueba que ninguna etiqueta nueva se corta. Si alguna se corta, para y aplica la regla de 3 propuestas.

- [ ] **Step 7: Commit**

```bash
git add frontend/src DESIGN.md backend/app/agent
git commit -m "Speak marketing, not engine: plain labels across the UI"
```

---

## Cierre de la entrega

- [ ] Suites completas en verde: backend `uv run pytest -q`, `ruff`, `pyright` en los archivos tocados; frontend `pnpm test`, `lint`, `type-check` y `build`.
- [ ] Aviso de cambio de contrato redactado para el canal (briefs del equipo, endpoints nuevos).
- [ ] Abrir el PR contra `main` con una descripción entendible para alguien que no conoce la app. Claude no mergea.
