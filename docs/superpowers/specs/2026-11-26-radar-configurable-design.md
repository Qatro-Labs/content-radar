# Radar configurable por empresa — diseño

*26/11/2026 · Estado: borrador para aprobar · Origen: conversación con Steven*

## 1. Intención

30X Signal hoy es un radar para un solo cliente (30X) y un solo tema (IA). Todo lo que lo hace "de IA" está escrito a mano: fuentes en `data/sources.yaml`, filtro de ruido en `collectors/text.py`, preguntas de Jev (`about_ai`, `ai_in_title`…), prompts y el perfil `data/audiences/30x.yaml`.

Queremos que sea **una app para muchas empresas**. Cada empresa configura desde la UI **qué contenido crea, para quién y con qué objetivo**, y de eso se deriva qué se monitorea, qué se filtra, cómo se puntúa y qué se recomienda. Nadie toca archivos.

**Usuario:** equipos de marketing de empresas (2–10 personas, no técnicos) que hoy deciden qué publicar a ojo.
**Para qué lo usan:** cada semana, elegir los temas que van al calendario de contenido, con evidencia que justifique la elección.

**Ejemplo guía:** una constructora de Medellín que crea contenido para compradores de primera vivienda. Lo que le sirve no son noticias del sector construcción, sino temas como "cambios a Mi Casa Ya en 2027" o "auge de apartamentos pequeños".

## 2. Objetivos, no objetivos y anti-objetivos

**Objetivos**
- Una empresa crea su cuenta, configura su radar en ~5 minutos sin conocimientos técnicos y recibe sus primeros temas el mismo día.
- Cada lunes el equipo ve "tus temas de esta semana" (tantos como piezas publica) y los pasa a un calendario con su brief.
- La parte cuantitativa del motor (velocidad, aceleración con p-valor, outliers, etapa, saturación, fuentes independientes, réplicas) se reutiliza sin cambios de fondo. El audience fit y las reglas de recomendación **sí cambian**: hoy suponen una audiencia de ejecutivos B2B (§6.8.1) y necesitan validarse de nuevo.
- El costo por cliente crece más despacio que el número de clientes.

**No objetivos (por ahora)**
- Facturación, planes y pagos (sí se diseñan los límites que los harán posibles, §6.6).
- Editor de contenido o publicación automática en redes.
- Conectar las cuentas propias del cliente por OAuth para medir su rendimiento (se deja la puerta abierta, §9).
- LinkedIn.

**Anti-objetivos (sería un fracaso aunque funcione)**
- Que la configuración muestre jerga interna (RSS, queries, embeddings, outliers, segmentos).
- Que un radar nuevo muestre temas inventados o "rellenos" porque hay pocos datos (regla 3 de CLAUDE.md: si hay 3 temas reales, se muestran 3).
- Que una empresa vea datos, perfil o competencia de otra.
- Depender de scraping para que el radar funcione (ver §5).

## 3. Restricciones

- Reglas no negociables de CLAUDE.md §2 siguen vigentes: solo contenido público, nada de datos personales, nunca inventar datos, el LLM evalúa y Python calcula, texto externo delimitado (prompt injection).
- **Cupo de YouTube:** 100 llamadas/día a `search.list` para toda la app. Se prefieren `playlistItems` de canales conocidos (1 unidad).
- **Auth existente:** Supabase (`app/api/auth.py`, `/me`, `AUTH_REQUIRED`). Se construye encima, no se reemplaza.
- **Validación de Jev:** hoy solo está medida con piezas de IA. Un sector nuevo necesita una validación con piezas etiquetadas antes de confiar en sus filtros.
- Stack de CLAUDE.md §8 (FastAPI, Postgres + pgvector, Vue 3, cron). Sin colas nuevas salvo que haga falta (§8).

## 4. Enfoques considerados

| | Enfoque | A favor | En contra |
|---|---|---|---|
| A | Un radar completo (recolección + análisis) por empresa | El más simple: el pipeline actual repetido | Costo lineal; recolecta 10 veces la misma fuente; agota el cupo de YouTube; cada radar arranca de cero |
| **B** | **Recolección compartida + análisis por empresa** | Costo sublineal; un radar nuevo arranca rápido si sus fuentes ya existen; las fuentes de una empresa enriquecen el depósito | Modelo de datos más complejo; el filtro de relevancia tiene que ser bueno |
| C | Catálogo de sectores cerrado armado por nosotros | Calidad controlada, barato | No es configurable; si una empresa no encaja en un sector, no hay producto |

**Elegido: B, con paquetes de fuentes por sector (lo bueno de C) como semilla de las sugerencias.** Steven lo aprobó el 26/11.

## 5. Decisiones ya tomadas

1. **Configuración guiada por UI**, empezando por la web de la empresa. El recorrido de bocetos (aprobado, "se ven bien"):
   1. *Cuéntanos de tu empresa:* URL de la web y redes (opcional).
   2. *¿Así describirías a tu empresa?:* la IA arma un borrador del perfil; cada campo se edita.
   3. *¿Qué vigilamos por ti?:* sugerencias en lenguaje de marketing (lo que le interesa a tu cliente · referentes · tu competencia) con casillas, más el ritmo de publicación (piezas por semana).
   4. *Armando tu radar:* progreso visible; aviso por correo al terminar; invitar al equipo mientras tanto.
2. **Cada lunes:** vista "Tus temas de esta semana" con N temas (N = ritmo de publicación), cada uno con recomendación, el porqué en una línea, evidencia y "+ Calendario". Un calendario semanal donde cada tema abre su brief, exportable.
3. **Fuentes oficiales y abiertas por defecto.** Medición del 26/11 (ventana del 17/10, run #20): sin TikTok ni Reddit el ranking casi no cambia (85 % de la evidencia viene de YouTube, HN y RSS), pero se pierde el 44 % de los outliers (casi todos de TikTok). Por eso:
   - Núcleo: YouTube (incluido Shorts), RSS, HN, Google News RSS y GDELT, Wikipedia Pageviews, Reddit por API oficial, Instagram Graph API (Business Discovery) para competencia.
   - ScrapeCreators y twitterapi.io quedan como complementos opcionales detrás de un flag, apagados por defecto en las empresas nuevas.
4. **Cuenta de empresa con equipo:** el radar pertenece a la empresa; todos sus miembros ven y trabajan sobre el mismo.
5. **Escala de esta fase: 3–5 empresas piloto.** Basta un cron que recorre los workspaces y un reparto fijo del cupo de YouTube. Lo que cambia al crecer (caché de embeddings, planificador de tareas, otra estrategia para YouTube) queda anotado en §9, no se construye ahora.
6. **Onboarding abierto con aviso.** Cualquier empresa puede crear su radar. Si su sector no tiene un `source_pack` validado (o eligió "ninguno"), el radar muestra un aviso visible de "filtro en prueba" y cada tema lo lleva en `limitations`. Los sectores con más uso se validan primero.
7. **Las fuentes oficiales nuevas son un proyecto previo, aparte** (§10). Este proyecto empieza cuando ese termina.

## 6. Diseño

### 6.1 Modelo de datos (nuevo)

- `workspaces` — una empresa: nombre, web, estado del onboarding, límites.
- `workspace_members` — usuario de Supabase ↔ workspace, con rol (`owner`, `member`).
- `radar_profiles` — el perfil editable (versión actual + historial): `creates_about`, `audience`, `goal`, `channels/formats`, `languages`, `target_region`, `out_of_scope`, `posts_per_week`. Reemplaza a `data/audiences/30x.yaml` como entrada de prompts, Jev y rúbrica.
- `sources` pasa a ser **compartida**: una fila por fuente real (canal, feed, búsqueda), sin dueño. Se añade `workspace_sources` (workspace ↔ source, con `role`: `interest` | `referent` | `competitor` y `enabled`). Una fuente se recolecta mientras al menos un workspace la tenga activa.
- `source_packs` — paquetes por sector revisados por nosotros (lista de fuentes + subtemas de ejemplo).
- `pipeline_runs`, `opportunities`, `editorial_briefs`, `editorial_feedback` y `usage_events` reciben `workspace_id`. La recolección (`collect`) sigue siendo global; el análisis (`analyze`) es por workspace.
- `calendar_entries` — workspace, semana, día, formato, `opportunity_id` (de qué ejecución), brief asociado.

`content_items` y `metric_snapshots` no cambian: son del depósito compartido.

### 6.2 Configuración (onboarding)

1. **Borrador del perfil.** Se descarga la web indicada (página de inicio y unas pocas internas enlazadas) y, si las hay, se leen las redes públicas por API oficial. El texto va al LLM delimitado como dato no confiable. Sale un `radar_profiles` en borrador con salida Pydantic. Si la web no se puede leer, el usuario rellena el perfil a mano (mismo formulario).
2. **Plan de monitoreo.** Con el perfil:
   - Se elige el `source_pack` más cercano (el LLM lo elige de la lista cerrada, o ninguno).
   - El LLM propone además subtemas (en los idiomas del perfil), referentes y competidores candidatos, con URL o handle.
   - **Python valida cada candidato** antes de mostrarlo: el feed abre con feedparser, el canal de YouTube existe, la búsqueda devuelve piezas en los últimos 14 días; se muestra el volumen semanal estimado. Lo que no valida no se muestra.
   - El usuario marca o desmarca y puede añadir los suyos (URL o nombre; se validan igual).
3. **Primer radar.** Al confirmar: backfill de 14 días solo de las fuentes nuevas para el depósito, después `analyze` del workspace. La pantalla de progreso lee el estado de un `pipeline_run`. Correo al terminar.
4. **Si hay pocos datos:** el radar dice cuántas piezas encontró y sugiere añadir fuentes; nunca rellena (anti-objetivo).

### 6.3 Análisis por workspace

`analyze` recibe un `workspace_id` y:
- Carga las piezas de las fuentes activas del workspace dentro de la ventana.
- **Relevancia:** reemplaza `is_ai_related` y `keep_about_ai`. Dos capas: similitud de embedding con el perfil (`creates_about` + subtemas aprobados) como filtro barato, y la batería de pieza de Jev con preguntas plantilla ("¿trata de {creates_about}?", "¿le sirve a {audience}?"). Las preguntas fijas de IA (`ai_in_title`, `dev_audience`, `tech_jargon`) se vuelven genéricas o se quitan.
- **Segmentos:** `tech` / `business` / `latam_es` dejan de ser fijos. Cada `workspace_source` hereda un segmento de su `role` y del idioma/región: `interés`, `referente`, `competencia`, y región objetivo vs. resto. El "LATAM Gap" se generaliza a **brecha de región objetivo**: tema presente fuera, poco cubierto en la región objetivo del perfil.
- **Audience fit:** misma rúbrica de 6 criterios, con el texto de cada criterio parametrizado por el perfil (p. ej. "relevancia LATAM" → "relevancia para {target_region}", "encaje con pilares 30X" → "encaje con {creates_about}").
- Prompts (`evaluate_topic`, `explain_opportunity`, brief, Rad) reciben el perfil como variables.
- Caché de Jev y LLM por hash de entrada + versión, como hoy: dos workspaces con piezas y perfil parecidos no pagan dos veces la clasificación de la misma pieza **solo** si la pregunta es idéntica; las preguntas plantilla cambian por perfil, así que la caché de pieza es por workspace en la práctica.

### 6.4 Experiencia semanal

- Vista principal del workspace: **Tus temas de esta semana** (N = `posts_per_week`; si hay menos temas recomendables, se muestran menos y se dice por qué). Debajo, el radar completo actual (burbujas + ranking) como "ver todos los temas".
- "+ Calendario" crea un `calendar_entry` y genera el brief con los formatos del perfil.
- Calendario semanal en la app; exportación a CSV e iCal. (Notion/Google Calendar por integración: después.)
- Correo del lunes con los temas de la semana y enlace a la app.
- Rad y el MCP quedan acotados al workspace del usuario (el MCP necesita un token por workspace).

### 6.5 Recolección compartida

- `collect` recorre todas las fuentes con al menos un `workspace_source` activo, una vez por fuente.
- Prioridad de cupo de YouTube: `playlistItems` por canal; `search.list` solo para búsquedas de subtemas, con presupuesto diario repartido entre workspaces.
- Una fuente sin workspaces activos deja de recolectarse (se conservan sus datos).

### 6.6 Límites (para poder cobrar después)

Por workspace, como constantes configurables: número máximo de fuentes propias, de búsquedas por palabra clave, de miembros y de `analyze` por día. La UI muestra el límite cuando se alcanza. Los números concretos los decide negocio.

### 6.7 Migración del radar actual

El radar de 30X pasa a ser el primer workspace: su perfil se carga desde `30x.yaml`, sus fuentes desde `sources.yaml` (como `source_pack` "IA para negocio" + `workspace_sources`). La demo congelada (`DEMO_RUN_ID`) sigue apuntando a una ejecución de ese workspace.

### 6.8 Decisiones tomadas por Claude tras la revisión del builder (revisar)

1. **Rúbrica y recomendación genéricas.** Los 6 criterios del audience fit dejan de suponer ejecutivos B2B: *impacto en el objetivo* (`goal`) · *caso real o aplicación concreta* · *comprensible para {audience}* · *relevancia para {target_region}* · *encaje con {creates_about}* · *convertible en contenido para {channels}*. La regla `org_application ≤ 1 → wait_for_case` de `ranking.py` pasa a ser "ningún caso concreto" con el criterio 2 genérico. El `business_use` de Jev, que decide `latam_gap`, se sustituye por "le sirve a {audience}". Supone cambiar la tabla de `recommendation` de CLAUDE.md §7 y validar de nuevo el LLM y Jev (§7).
2. **El filtro de tema sale de la recolección.** Hoy `is_ai_related` descarta piezas dentro de los colectores (`ai_filter: true`). Con fuentes compartidas, eso tiraría lo que otra empresa necesita. Toda la relevancia pasa a `analyze`: los colectores guardan todo lo que trae la fuente. Para que Jev no cueste más por el volumen extra, la similitud de embeddings filtra antes de Jev (§6.3). La regex de IA queda como prefiltro opcional del workspace de 30X.
3. **Aislamiento y depósito.** Las fuentes se comparten solo para recolectar. Un workspace nunca ve qué otros workspaces usan una fuente, ni sus competidores, ni sus búsquedas. Las sugerencias del onboarding salen solo de los `source_packs` y de la propuesta del LLM para ese perfil, nunca de lo que añadieron otros. Como una misma pieza puede venir de varias fuentes (dos búsquedas distintas), se añade la tabla `content_item_sources` (pieza ↔ fuente) y la unicidad `(platform, external_id)` se mantiene en `content_items`. El análisis de un workspace carga las piezas por esa tabla, filtradas por sus `workspace_sources`.
4. **Nuevo `audience_mix` en el contrato.** Segmentos fijos y genéricos: `target_region` (fuentes de la región objetivo del perfil), `global` (el resto) y `competitor` (fuentes con rol competencia). `latam_gap` se renombra a `region_gap`. Es un cambio de contrato que rompe compatibilidad. Se migra todo a la vez (frontend, MCP, Rad y fixture están en el mismo repo) y se avisa en el canal antes de mergear (CLAUDE.md §11). El workspace de 30X se migra con `target_region = latam`.
5. **Auth obligatoria y 30X como demo pública.** Todas las rutas de datos y las tools MCP reciben el workspace del usuario autenticado (`AUTH_REQUIRED` desaparece para ellas). El workspace de 30X se marca como `public_demo`: se puede leer sin login, solo lectura, y lo sigue sirviendo `DEMO_RUN_ID`.
6. **La semana se congela el lunes.** Al primer `analyze` del lunes de cada workspace (en su zona horaria; por defecto, la de `target_region`) se guarda un `weekly_picks` con copia del payload de los N temas. El calendario y los briefs apuntan a esa copia, no a un `opportunity_id` de una ejecución, así que no se rompen cuando cambian los clusters. "Ver todos los temas" sigue mostrando la última ejecución.

## 7. Calidad y validación

- Antes de abrir un `source_pack` a clientes: 30–50 piezas etiquetadas a mano de ese sector para medir el filtro de relevancia y la batería de Jev (como `data/evaluations/` hoy).
- Primer sector de prueba: construcción/vivienda (el ejemplo guía) o robótica. Elige el builder con Steven según qué empresa piloto haya.
- Cada workspace ve en su radar cuántas piezas analizó y de cuántas fuentes, para que la escasez de datos sea visible.

## 8. Lo que queda al builder

- Orden de construcción y partición en entregas (sugerencia: modelo de datos + análisis parametrizado con un segundo workspace creado por script → onboarding UI → experiencia semanal → límites).
- Cómo ejecutar `analyze` por workspace (cron que recorre workspaces, o disparado al terminar `collect`) y el arranque del primer radar desde la API sin bloquear la petición.
- Diseño visual exacto de las pantallas, siguiendo `DESIGN.md` y los bocetos aprobados.
- Proveedor de correo.
- Cuántas páginas de la web leer en el borrador del perfil.

## 9. Después

- Conectar las cuentas propias por OAuth (Instagram Graph, LinkedIn Pages, TikTok Display) para "qué funciona con mi audiencia".
- Integraciones de calendario (Google Calendar, Notion).
- Planes y facturación sobre los límites de §6.6.
- Al pasar de ~5 workspaces: caché de embeddings por pieza, planificador de tareas en vez del cron, y una estrategia de YouTube que no dependa de `search.list`.
- Reddit por API oficial (revisar sus términos comerciales) e Instagram Graph Business Discovery para la competencia (requiere cuenta business y la revisión de la app por Meta).

## 10. Proyecto previo: fuentes oficiales y abiertas

Corto y separado. Se diseña y planea por su cuenta antes de empezar este. Alcance decidido por Steven (26/11):

**Fuentes de piezas** (implementan `SignalCollector` y entran como evidencia):
- **YouTube Shorts** con la API oficial que ya usamos. Cubre el hueco de los outliers de vídeo corto que deja TikTok.
- **Google News RSS** (`news.google.com/rss/search?q=…&hl=…&gl=…`): noticias de cualquier tema por idioma y país. Antes de construir, revisar sus términos de uso.
- **GDELT**: noticias globales abiertas, con país e idioma.

**Señales de demanda** (por tema, no por pieza: **no** son `ContentSignal` ni evidencia). Hace falta un modelo nuevo de serie temporal por término y región:
- **Google Trends**, solo por vías oficiales: el RSS público de tendencias diarias por país y la API oficial de Google Trends (alpha, con acceso por solicitud). **Nada de `pytrends` ni librerías parecidas**, porque hacen scraping, justo lo que queremos evitar.
- **Wikipedia Pageviews API**: interés diario por artículo, oficial y gratis.

Cómo entran en el producto (lo decide su propio diseño): como respaldo de la demanda de un tema ("las búsquedas de X en Colombia subieron 40 % esta semana"), que se muestra junto a la evidencia. No entran en el Opportunity Score hasta validar que suman algo.
