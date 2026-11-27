# De radar a herramienta de contenido — diseño de funcionalidad y UI/UX

*27/11/2026 · Estado: borrador para aprobar · Origen: conversación con Steven*
*Bocetos aprobados: lienzo [Portada «Esta semana» y demás pantallas](https://claude.ai/artifact/SPhz4VdbFSCZZ7mrNxvPDA) (privado; datos de ejemplo).*

## 1. Intención

Hoy la app es un radar para analistas: burbujas, scores y expedientes. Queremos que un **equipo de marketing de una empresa** (2–10 personas, no técnicas, que hoy deciden "a ojo") pase **de "no sé qué publicar" a "tengo los briefs de la semana"**, con evidencia que justifique cada elección.

El producto termina en el **brief**. Lo escribe después un redactor, pero el redactor queda fuera del alcance: no hay asignación, bandeja, enlaces externos ni comentarios. El brief se **copia** o se **descarga en PDF**.

Este diseño se apoya en [`2026-11-26-radar-configurable-design.md`](2026-11-26-radar-configurable-design.md), que ya decide workspaces, perfil de empresa, análisis por workspace, `weekly_picks` y `calendar_entries`. Este documento decide **qué ve y hace la persona** y lo que eso añade al modelo de datos y al brief.

## 2. Objetivos, no objetivos y anti-objetivos

**Objetivos**
- Cada lunes, la portada responde "¿qué publico esta semana?" con N temas (N = piezas por semana del perfil), cada uno con su porqué y su evidencia a un clic.
- En menos de 5 minutos el equipo reparte esos temas en los días de la semana y cada día queda con su brief.
- El brief tiene todo lo que un redactor necesita para escribir sin volver a preguntar: ángulo, gancho, estructura, datos con fuente, cierre (llamada a la acción), tono, qué evitar, extensión y notas del equipo.
- Toda la UI habla en lenguaje de marketing, sin jerga interna.

**No objetivos (por ahora)**
- Escribir el contenido (borradores, guiones completos, copies).
- Flujo con el redactor: asignar, aprobar, comentar, compartir con externos.
- Integraciones con Google Calendar o Notion. Basta con exportar a iCal y CSV.
- Medir el rendimiento de lo publicado.

**Anti-objetivos (sería un fracaso aunque funcione)**
- Rellenar la semana con temas débiles cuando no hay suficientes. Si hay 2 temas buenos y la empresa publica 3, se muestran 2 y se dice por qué (regla 3 de CLAUDE.md).
- Un brief con datos que no salen de una pieza enlazada.
- Que la persona tenga que entender el radar (burbujas, momentum, saturación) para llegar a su brief.
- Que el texto libre del usuario llegue al LLM sin protección.

## 3. Restricciones

- Siguen vigentes las reglas de CLAUDE.md §2: nunca inventar datos, el LLM evalúa y Python calcula, el texto externo va delimitado.
- Hoy `BriefRequest` solo acepta opciones cerradas para que no llegue texto libre al LLM (`backend/app/schemas/editorial.py`). El perfil de marca sí lleva texto libre: hay que tratarlo como dato no confiable, delimitado, igual que la web de la empresa en el onboarding (diseño configurable §6.2).
- **Regla de Steven para la UI:** antes de cualquier cambio de UI/UX se muestran al menos 3 propuestas de diseño y él elige. Las cuatro pantallas de §6 ya pasaron esa ronda. Cualquier pantalla o estado nuevo que aparezca al construir necesita su propia ronda.
- Stack y dirección visual: Vue 3 + shadcn-vue + Tailwind, siguiendo `DESIGN.md` (lienzo #F2F3F5, tarjetas blancas, tinta #121418, lima #C6F432 solo como relleno, Bricolage Grotesque para titulares y Geist para el texto).

## 4. Enfoques considerados

| | Enfoque | A favor | En contra |
|---|---|---|---|
| **A** | **La semana primero:** la portada es "Tus temas de esta semana"; el radar pasa a "Todos los temas" | Encaja con el diseño configurable (vista semanal, calendario, correo del lunes) y con cómo planea un equipo | Hay que rehacer la portada y la navegación |
| B | El estudio de briefs primero: se mejora Crear y el radar queda como portada | Lo más rápido | Sigue pareciendo una herramienta de analistas; hay que interpretar burbujas antes del brief |
| C | Preguntarle a Rad primero: portada conversacional | Vistosa | Difícil de hacer fiable; esconde la evidencia, que es lo que nos diferencia |

**Elegido: A** (Steven, 27/11).

## 5. Lenguaje de la UI

Toda la app usa estas palabras. Los nombres internos siguen igual en código, contrato y MCP.

| Interno | En la UI |
|---|---|
| `publish_now` / `find_angle` / `wait_for_case` / `discard` | Publicar ya / Buscar ángulo / Esperar un caso real / Descartar |
| `emerging` / `accelerating` / `peaking` / `saturated` | Empieza a crecer / Crece rápido / En su punto alto / Ya muy cubierto |
| outlier (≥3×) | "rinde 3× más que lo normal" |
| `source_count` / cross-source | "N fuentes distintas" |
| `region_gap` (antes `latam_gap`) | "casi nadie lo cuenta en {región}" / "ya se cuenta mucho en {región}" |
| saturation, momentum, scores 0–100 | No aparecen en la portada ni en el brief. Siguen en "Todos los temas" y en el expediente |

## 6. Pantallas decididas

Cada pantalla enlaza a su boceto aprobado. Los bocetos son la referencia de estructura y comportamiento. El diseño visual fino lo ajusta el frontend siguiendo `DESIGN.md`.

### 6.1 Navegación

Barra superior: **Esta semana · Todos los temas · Calendario · Briefs · Tu marca**.
- *Todos los temas* es el radar actual (burbujas + ranking) y lleva al expediente de cada tema, sin cambios de fondo.
- *Briefs* es la lista actual de "Mis briefs".
- Rad, el agente, sigue disponible donde está hoy.
- La ruta `/` pasa a ser *Esta semana*. El radar se mueve a `/temas` y `/explore/:id` se mantiene.

### 6.2 Esta semana (portada) — boceto D

[Boceto](https://claude.ai/artifact/SPhz4VdbFSCZZ7mrNxvPDA#artboard-Combinada)

- Título "Tus N temas de esta semana", con la semana y una línea que explica de dónde sale N.
- **Franja "Tu semana":** un hueco por cada día de publicación del perfil, con su formato (p. ej. Lun · Reel). Contador "X de N días con tema". Un hueco lleno muestra el tema y "Brief listo". Al hacer clic se quita el tema (con confirmación ligera o deshacer: lo decide el frontend). Un hueco vacío dice "Libre · elige un tema abajo".
- **Tarjetas numeradas**, una por tema de `weekly_picks`, en orden de ranking. Cada una lleva:
  - recomendación y etapa en chips;
  - el nombre del tema y el porqué en una línea (`why_it_matters` resumido);
  - una línea de cifras en lenguaje simple ("12 fuentes distintas · 2 piezas rinden 3× más que lo normal");
  - el botón **"+ Calendario"**, que abre dentro de la tarjeta el selector de día. Los días ocupados aparecen apagados y no se pueden elegir;
  - al elegir el día, la tarjeta pasa a "En calendario · Lun 30" y aparece "Abrir brief";
  - **"Ver evidencia"**, que despliega las piezas enlazadas con fuente, antigüedad y, si aplica, "rinde N×".
- **Al elegir el día se genera el brief** con el formato y el canal de ese día, en segundo plano. El hueco muestra "Preparando brief…" hasta que está listo.
- "Ver todos los temas (M) →" al final.
- **Con menos temas que días:** se muestran los que hay y una nota con el motivo ("Esta semana solo 2 temas pasan el filtro; el tercer día puedes elegir de Todos los temas").
- Un tema de "Todos los temas" también se puede añadir al calendario desde su expediente.

### 6.3 Perfil de marca

Dos pantallas sobre los mismos datos, el `radar_profiles` del diseño configurable, ampliado (§7.1):

**Onboarding — boceto B, "Tu marca en frases"** ([boceto](https://claude.ai/artifact/SPhz4VdbFSCZZ7mrNxvPDA#artboard-PerfilFrases)). Es el paso 2 del onboarding del diseño configurable ("¿Así describirías a tu empresa?"). El borrador sale de la web de la empresa y se muestra como un párrafo con partes resaltadas. Al tocar una parte se abre debajo su editor, con la explicación de para qué sirve. Un botón "Guardar mi marca" cierra el paso.

**Página "Tu marca" — boceto C, perfil con vista previa** ([boceto](https://claude.ai/artifact/SPhz4VdbFSCZZ7mrNxvPDA#artboard-PerfilVistaPrevia)). Los campos van a la izquierda y la vista previa del brief a la derecha. La vista previa **no llama al LLM en cada tecla**: usa un brief reciente del workspace (o un tema de ejemplo marcado como tal) y sustituye los campos directos del perfil (cliente, región, cierre, evita, piezas y canales). El gancho de ejemplo por tono se regenera solo al pulsar "Ver cómo quedaría" (una llamada) o se omite. Lo decide el plan; ver §9. Los cambios se guardan con "Guardar cambios" y se aplican a los próximos briefs (ver §9.7).

### 6.4 Calendario — boceto C, agenda en lista

[Boceto](https://claude.ai/artifact/SPhz4VdbFSCZZ7mrNxvPDA#artboard-CalAgenda)

- Tabla agrupada por semana. Columnas: fecha, tema, formato, canal y estado.
- Pestañas **Próximas · Publicadas · Todas**.
- **Estados de una entrada:** *Sin tema* (hueco del perfil sin elegir), *Preparando brief*, *Brief listo* y *Publicada*. El estado lo marca a mano el equipo con "Marcar como publicada" o "Marcar como pendiente".
- Al hacer clic en una fila se despliega el ángulo y el gancho, con "Abrir brief" y "Marcar como publicada".
- Un hueco sin tema enlaza a *Esta semana*.
- Exportar a **CSV** e **iCal** (el diseño configurable §6.4).
- Las semanas pasadas se ven en *Publicadas* o en *Todas*. No hay vista de mes.

### 6.5 Brief — boceto B, brief con respaldo al lado

[Boceto](https://claude.ai/artifact/SPhz4VdbFSCZZ7mrNxvPDA#artboard-BriefRespaldo)

- **Encabezado:** fecha, tema, "Copiar brief" y "Descargar PDF".
- **Columna izquierda (el brief):**
  - selector de formato (los formatos de los canales del perfil, p. ej. Reel / Carrusel / Post de blog); cambiarlo **regenera el brief como nueva versión** (las versiones ya existen: `parent_brief_id`);
  - ángulo, gancho, estructura con su extensión ("30–45 segundos", "7 diapositivas"…);
  - datos clave numerados: al tocar uno se resalta su pieza en la columna derecha;
  - cierre (llamada a la acción), tono y evita, en tres baldosas;
  - **notas del equipo:** texto libre que se guarda con el brief y se imprime tal cual en la copia y en el PDF. **La IA no lo lee** (Claude decidió esto para mantener la protección actual; ver §9).
- **Columna derecha (respaldo):** "Por qué este tema" (fuentes distintas, piezas en tu región, enlace al tema completo) y "Piezas que lo respaldan" (la evidencia citada, resaltable).
- **Copiar** produce texto plano con todas las secciones, las URLs de los datos clave y las notas. El **PDF** tiene el mismo contenido maquetado en una página (o dos si hace falta) y las URLs completas.
- "Qué no sabemos" (`limitations`) aparece al final del brief, plegado. Copiar y PDF lo incluyen.

## 7. Cambios de datos y contrato

### 7.1 Perfil (`radar_profiles`, del diseño configurable)

Se añaden a los campos ya previstos (`creates_about`, `audience`, `goal`, `channels/formats`, `languages`, `target_region`, `out_of_scope`, `posts_per_week`):
- `tone`: lista corta de adjetivos (máx. 3);
- `call_to_action`: texto ("Agendar una visita al apartamento modelo");
- `never_say`: texto (promesas, comparaciones o palabras prohibidas);
- `publishing_days`: un día de la semana y un formato por cada pieza (p. ej. `[{day: "mon", format: "reel", channel: "instagram"}, …]`). Su longitud define `posts_per_week`.

Todo el texto del perfil va a los prompts como **dato delimitado** (regla 6), nunca como instrucción.

### 7.2 Calendario (`calendar_entries`, del diseño configurable)

- Una fila por hueco de la semana con tema (los huecos sin tema se calculan desde `publishing_days`, no se guardan).
- Se añade `status`: `brief_pending` | `brief_ready` | `published`, más `published_at` cuando se marca.
- Apunta a `weekly_picks` (la copia congelada del lunes, diseño configurable §6.8.6) y al brief, nunca a un `opportunity_id` de una ejecución.

### 7.3 Brief (`EditorialBrief`) — cambio de contrato

- Se añaden `call_to_action`, `tone`, `avoid` y `length` (texto, p. ej. "30–45 segundos"), que salen del perfil y del formato.
- Se añade `team_notes: str | None`, que escribe el usuario, no pasa por el LLM y se guarda en la versión.
- `BriefPlatform` y `BriefFormat` dejan de ser los fijos de 30X: salen de los canales y formatos del perfil. Los valores se mantienen como enum cerrado en código (lista conocida de canales y formatos), y el perfil elige un subconjunto.
- `angle` y `why_it_fits` dejan de mencionar "30X": el prompt recibe el perfil.
- Se avisa en el canal antes de mergear (CLAUDE.md §11). Se regeneran `frontend/src/types/api.ts` y el fixture.

### 7.4 Endpoints nuevos (orientativo; el plan los fija)

- `GET /week` → los `weekly_picks` de la semana con sus huecos y estados.
- `POST /calendar` / `PATCH /calendar/{id}` / `DELETE /calendar/{id}` → elegir día, marcar como publicada, quitar.
- `GET /calendar?status=&from=&to=` + `GET /calendar.csv` + `GET /calendar.ics`.
- `GET/PUT /profile` → perfil del workspace.
- `GET /editorial/brief/{id}.pdf` (o el PDF se genera en el cliente: lo decide el plan).

### 7.5 Acceso (decidido por Steven, 27/11)

- Se adelanta una versión mínima de `workspaces` y `workspace_members` del diseño configurable (§6.1), con 30X como único workspace.
- Perfil, calendario, semana y briefs pertenecen al workspace, no a un usuario. `editorial_briefs` pasa de `user_id` a `workspace_id` y guarda quién lo creó.
- Solo los miembros del workspace pueden escribir: elegir día, marcar como publicada, editar el perfil, generar briefs y escribir notas. Todos los endpoints de escritura comprueban la pertenencia.
- El workspace de 30X sigue como `public_demo`: sin sesión se puede leer todo y no se puede escribir. La UI esconde o desactiva las acciones y explica "Inicia sesión como miembro del equipo para planear".
- "Briefs" pasa a ser la lista del equipo.

### 7.6 Qué temas entran en la semana (decidido por Steven, 27/11)

- Entran los temas con recomendación **Publicar ya** o **Buscar ángulo**, en orden de ranking, hasta llenar `posts_per_week`.
- Quedan fuera **Esperar un caso real**, **Descartar** y los temas sin audience fit (`audience_fit_score = null`).
- Si no llegan a N, se muestran los que hay y la portada explica cuántos faltan y por qué. Nunca se rellena.

## 8. Orden de construcción

Este trabajo depende del radar configurable (workspaces y perfil). Para no esperar a todo ese proyecto, **Claude propone** construir en este orden:

1. **Workspace mínimo, perfil y lenguaje.** El acceso de §7.5, la tabla `radar_profiles` con los campos de §7.1 y el workspace de 30X cargado desde `30x.yaml`. La página "Tu marca" (C). El cambio de lenguaje de §5 en toda la UI actual.
2. **Brief.** Los cambios de contrato de §7.3 y los prompts con el perfil. La pantalla B, con copiar y PDF.
3. **Semana y calendario.** `weekly_picks`, `calendar_entries` con estado, la portada D, el calendario C, la exportación y la nueva navegación.
4. **Onboarding (perfil en frases, B)** dentro del proyecto del radar configurable, cuando haya creación de workspaces.

Los pasos 1–3 funcionan con un solo workspace (30X) y sirven también a la demo actual. El paso 4 llega con el multi-empresa.

**Filtro de valor (CLAUDE.md §12):** hace más convincente el recorrido de demo de punta a punta ("abrir → elegir oportunidad → obtener un brief"), porque el resultado ya es un plan de la semana con briefs y no solo un ranking.

**Ownership (CLAUDE.md §3):** perfil, calendario y endpoints con Steven; prompts y brief con Melkin; pantallas con el líder de frontend.

## 9. Decisiones tomadas por Claude (revisar)

1. **Las notas del equipo no pasan por el LLM.** Se pegan tal cual al brief. Así se mantiene la regla actual de "nada de texto libre del usuario al LLM". Si se quiere que las notas cambien el brief, hace falta una ronda de diseño de seguridad aparte.
2. **El perfil sí pasa por el LLM**, como dato delimitado. Es inevitable si los briefs tienen que sonar a la marca. El diseño configurable ya lo hacía con la web de la empresa.
3. **Elegir día genera el brief automáticamente** con el formato de ese día. Así la franja se llena de "Brief listo" sin un paso más. Cuesta una llamada al LLM por tema elegido, igual que hoy al pulsar "Generar".
4. **La vista previa de "Tu marca" no llama al LLM por cada cambio.** Sustituye campos sobre un brief existente. Un gancho nuevo por tono, si se quiere, es un botón explícito.
5. **Días y formatos de publicación (`publishing_days`) forman parte del perfil**, porque la franja y el calendario los necesitan. En el onboarding en frases entran como "Publicamos N piezas por semana en…", con días por defecto (L-X-V para 3) editables en "Tu marca".
6. **Estado "publicada" manual.** No se conecta con las redes, para no ampliar el alcance.
7. **En los pasos 1–3 el perfil solo alimenta los briefs, no `analyze`.** El audience fit, Jev y las reglas de recomendación siguen usando `30x.yaml` hasta el proyecto del radar configurable (§6.8.1 de ese diseño), que es donde se validan de nuevo. "Tu marca" dice "Los cambios se aplican a los próximos briefs". `region_gap` es solo un rótulo de la UI en estos pasos. El cambio de contrato `latam_gap` → `region_gap` y el nuevo `audience_mix` siguen en el proyecto configurable.
8. **De qué ejecución sale la semana.** `weekly_picks` se congela a partir de la ejecución que sirve la API (la de `DEMO_RUN_ID` si está fijada, si no la última correcta), con la primera petición de la semana a `GET /week` o con el primer `analyze` del lunes, lo que ocurra antes. Así la portada nunca queda vacía por un cron apagado y coincide con "Todos los temas".
9. **Objetivo del brief.** `goal` pasa a ser un campo cerrado del perfil, con los valores actuales de `BriefGoal` más los que hagan falta. El brief automático usa ese objetivo. El selector de formato del brief no cambia el objetivo.

## 10. Lo que queda al builder

- Diseño visual fino de cada pantalla, dentro de `DESIGN.md` y los bocetos. **Cualquier pantalla o estado sin boceto (vacíos, errores, cargas, móvil) pasa por la regla de 3 propuestas.**
- PDF en el servidor o en el cliente.
- Confirmación o "deshacer" al quitar un tema de un día.
- Nombres exactos de endpoints y tablas.
- Cómo se migran los briefs guardados de 30X al contrato nuevo (valores por defecto para los campos nuevos).
