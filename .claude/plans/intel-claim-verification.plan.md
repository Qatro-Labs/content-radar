# intel-claim-verification — Jev verifica cada afirmación de «por qué importa»

> Plan generado con `/spec`. Lo implementa `plan-implementer` con contexto limpio.
> El implementador NO ve la conversación que produjo este documento: todo lo que necesite tiene que
> estar escrito aquí.
>
> Se planeó sin poder preguntar al humano: cada decisión lleva su porqué y lo descartado. Las que
> se apartan del encargo literal van marcadas **(desvío)**.

## Metadatos

- **Slug:** `intel-claim-verification` · **Issue:** ninguno
- **Owner (CLAUDE.md §3):** Melkin
- **Prioridad (CLAUDE.md §12):** P0 por orden de construcción. Es el primer punto de «Después del
  núcleo»: «verificación de afirmaciones con Jev». · **Checkpoint que desbloquea (§13):** feature
  freeze, dom 15:00 ESP. Tiene que estar mergeado, o apagado detrás del flag (D9), antes de esa hora.
- **Valor (filtro de CLAUDE.md §12):** hace más fiable y más convincente el paso «entender por qué
  importa» del recorrido de demo. Cada frase de `why_it_matters` que se muestra está respaldada
  por la pieza que cita, según Jev. En el pitch, es la frase «Jev verifica lo que escribe el LLM».
  · **Pregunta de `docs/brief.md` §4:** #3 (relevancia), y la regla 3 de §2.
- **Repo:** `/Users/melandres8/Documents/Projects/content-radar`
- **Rama base:** `main` @ `551cf78` en el planning. **Dependencia:** se implementa **después** de
  mergear el plan `intel-dedup-replicas`, que también toca `backend/app/intelligence/jev.py` y
  `backend/app/services/classification.py`. Antes de empezar, el implementador hace
  `git pull --ff-only` en `main`, toma el sha nuevo como base y relee las referencias de la tabla
  de contexto. Lo que haya movido el dedup se anota en el informe, y se sigue si solo cambiaron
  líneas. Si el dedup cambió `Judge`, `JudgeResult`, `load_battery` o la tabla `jev_judgments` de
  forma incompatible con D4–D6, el implementador para y pone el gate en `BLOQUEADO`.
- **Rama de trabajo:** `intel/claim-verification`
- **Fecha:** 2026-10-18 01:15 ESP
- **Contratos tocados:** ninguno. `Opportunity`, `Evidence`, OpenAPI y las tools MCP no cambian. Las
  notas nuevas van en `limitations`, que ya es una lista de textos (D8). Se añade un setting
  interno, `JEV_VERIFY_CLAIMS` (D9). No es contrato.
- **Auditoría tras `/build`:** sí (toca datos que se muestran y regla 3)
- **Estado del gate:** `LISTO`

## Problema

`why_it_matters` sale del LLM (`explain_opportunity`). Hoy solo pasa dos comprobaciones en Python:

- cada afirmación cita una pieza que el LLM recibió;
- no trae cifras que no estén en los datos.

Nada comprueba que la pieza citada diga lo que la afirmación le atribuye. CLAUDE.md §7 y
`docs/jev.md` §3 prometen que Jev verifica cada afirmación y que solo se publica lo respaldado con
`confidence` ≥ 0,8. En `docs/scoring.md` (rama `docs/architecture-scoring`), «Diferencias con
CLAUDE.md» #11 lo registra como no implementado. Un directivo que lee el dossier puede tomar por
dato una frase que el LLM infirió de más.

## Criterios de aceptación

1. Cuando la verificación está activa (D9), en `analyze` cada afirmación de `why_it_matters` que
   pasa las comprobaciones de Python se envía a Jev con la batería `claim.v1` (una llamada por
   afirmación). Se publica solo si cumple dos cosas:
   - `support` responde `supports` con `confidence` ≥ `CLAIM_SUPPORT_MIN_CONFIDENCE = 0.8`;
   - `support_rev` también responde `supports`.

   Las demás se quitan del texto y se cuentan en una nota de `limitations` (D8).
2. Si un tema se queda sin afirmaciones publicables, se comporta como hoy:
   - `why_it_matters` conserva la plantilla de datos medidos;
   - `limitations` lleva `NO_VALID_CLAIM_NOTE`.
3. El `state` de Jev lleva la afirmación, los datos medidos que recibió el LLM y las piezas
   citadas, de cada una solo fuente, título y descripción (D2). Las instrucciones van solo en la
   batería (regla 6).
4. Caché en `jev_judgments`, sin migración:
   - `battery="claim"` y `content_item_id = NULL`;
   - clave = sha256 de `{state, battery, battery_version, model}`.

   Una segunda ejecución con las mismas explicaciones hace **0** llamadas a Jev.
5. Cada llamada real se suma al `UsageMeter` con `Provider.TYPESAFE_JEV`, operación
   `claim_battery` y unidades = `input_tokens`. Las respuestas de caché no se cuentan.
6. Cada ejecución hace como mucho `MAX_CLAIM_VERIFICATIONS_PER_RUN = 200` llamadas nuevas. El
   presupuesto se reparte en el orden de `rank()`.
7. Con la verificación activa, un tema cuya verificación no se pudo completar mantiene el
   comportamiento de hoy (afirmaciones que pasan Python) y añade `UNVERIFIED_NOTE` a `limitations`
   (D7). Pasa en tres casos:
   - no hay `TYPESAFE_API_KEY`;
   - Jev falla en alguna de sus afirmaciones;
   - se agotó el presupuesto.
8. Con la verificación apagada (`JEV_VERIFY_CLAIMS=false`), la salida es idéntica a la de hoy:
   no hay llamadas a Jev ni notas nuevas. Los tests actuales de `test_explanation.py` pasan sin
   cambios.
9. Validación antes de activar (paso 5):
   - se usan afirmaciones reales de la ejecución servida en Supabase, en **solo lectura**;
   - Jev hace ≤ 150 llamadas;
   - el criterio de adopción de D10 está fijado de antemano.

   Si se cumple, el default de `jev_verify_claims` pasa a `True`. Si no, se queda en `False` y se
   documenta.
10. El job `analyze` **no** se ejecuta contra Supabase durante el build.

## No-objetivos

- **Briefs** (`POST /editorial/brief`, `generate_editorial_brief`): quedan fuera. Se generan bajo
  demanda dentro del request, y verificar ahí añadiría latencia de Jev al request y una ruta de
  fallo nueva en el MCP. Lo trivial sería reusar `claim_supported`, pero el brief no tiene la
  forma «afirmación + URLs» de `OpportunityExplanation`. Queda como deuda en `docs/jev.md`.
- Verificar `limitations` del LLM: ya pasan el filtro de cifras y son frases sobre lo que *no* se
  sabe.
- Cambiar el prompt `explain_opportunity.v1.md` o su caché (D3).
- Campos nuevos en `Opportunity` (p. ej. `explanation_verified`) o UI nueva (D8).
- Hipótesis de «por qué funcionó», batería de pares y *lift*.
- Tocar `usage_events`, `record_meter` o `data/pricing.yaml`: solo se usan.

## Reglas de CLAUDE.md §2 en juego

- **Regla 3 (nunca inventar datos):** lo que Jev no respalda no se publica. Lo que no se pudo
  verificar se dice en `limitations` y no se presenta como verificado.
- **Regla 4 (el LLM evalúa, no calcula):** Jev emite un juicio tipado. El umbral y la decisión
  están en Python (`claim_supported`).
- **Regla 6 (texto externo no confiable):** van en `state`, nunca en `questions`:
  - la afirmación, que es texto del LLM derivado de texto externo;
  - el título y la descripción de las piezas.

  Las instrucciones están en `claim.v1.yaml`. Los datos medidos también van en `state`, aunque son
  nuestros: son el material contra el que se verifica, no instrucciones. En los logs no van ni el
  `state` ni el texto de las afirmaciones.
- **Secretos:** `backend/.env` apunta a Supabase. El script de evaluación abre la transacción en
  `READ ONLY` y nunca imprime `DATABASE_URL` ni claves.

## Contexto verificado del código

| Qué | Dónde | Estado actual |
| --- | --- | --- |
| Comprobaciones de Python | `backend/app/intelligence/explanation.py:52-76` | `apply_explanation(result, claims, limitations, *, sent_urls, numbers)`, pura y síncrona. `valid` = cita una URL enviada y cumple `numbers_supported`. Sin `valid` → `_with_notes(result, None, [NO_VALID_CLAIM_NOTE])`. Si hay válidas: limitaciones del LLM filtradas (`MAX_LIMITATIONS=2`, `MAX_LIMITATION_CHARS=240`, sin cifras nuevas), nota «Se descartaron N afirmaciones del LLM sin evidencia o con cifras no observadas.» y `why` = textos unidos con espacio |
| Notas | `backend/app/intelligence/explanation.py:19-22` | `EXPLANATION_FAILED_NOTE`, `NO_VALID_CLAIM_NOTE` |
| `ClaimDraft` | `backend/app/intelligence/explanation.py:25-28` | `text: str`, `cited_urls: list[str]` |
| `_with_notes` | `backend/app/intelligence/explanation.py:43-49` | Quita `EDITORIAL_PENDING_NOTE` y añade notas. Si `why` es `None`, no toca `why_it_matters` |
| Salida del LLM | `backend/app/editorial/explanation.py:61-69` | `Claim{text, evidence_urls: list[str]}`, `OpportunityExplanation{claims, limitations}` |
| Datos medidos que recibe el LLM | `backend/app/editorial/explanation.py:102-119` (`opportunity_facts`), `:80-84` (`ExplainInput.facts`) | Lista de frases en español generadas por Python: etapa, piezas por ventana, aceleración, fuentes, outliers, mezcla de audiencias, cobertura LATAM, recomendación y su motivo, banda de fit |
| Piezas que recibe el LLM | `backend/app/editorial/audience.py:81-87`, `:107-115` | `EvidencePiece{url, source, platform, language, title, description}`. La descripción ya llega recortada a `MAX_DESCRIPTION_CHARS`. Solo piezas seguras (`excluded_from_llm`), como mucho `MAX_PIECES` |
| Service de explicación | `backend/app/services/explanation.py:69-77` (`_apply`), `:106-145` (`explain_topics`) | Construye `ClaimDraft`, `sent_urls` y `numbers` y llama a `apply_explanation`. Tiene `explain` (`ExplainInput`) a mano por tema |
| Job | `backend/app/jobs/analyze.py:74-89` (`_fit_and_explain`), `:92-103` (`_stats`), `:115-142` (`_print_summary`) | `explain_topics(..., explainer=build_explainer(settings), meter=meter)`. El orden con `rank()` se aplica después (`:71`) |
| `rank` | `backend/app/intelligence/opportunities.py:485-492` | Pura, ordena una copia |
| Cliente Jev | `backend/app/intelligence/jev.py:82-116` | `JudgeResult{model, answers, input_tokens, output_tokens}`, `Judge` Protocol, `TypeSafeJudge` (semáforo de 6), `build_judge(settings) -> Judge \| None` (None sin clave) |
| Excepción | `backend/app/intelligence/jev.py:23` | `JudgeError = TypeSafeError` |
| Loader de baterías | `backend/app/intelligence/jev.py:119-130` | `load_battery(name, path)` admite `noul`, `choice` y `score`. En `choice`, `criteria` puede llevar `{what, not_for}` (lo usa `piece.v3.yaml`) |
| Clave de caché | `backend/app/intelligence/jev.py:148-157` | `cache_key(state, model)` **fija** `piece_battery()`. Hay que parametrizar la batería (D5) |
| Umbrales | `backend/app/intelligence/jev.py:31-37` | `CHOICE_MIN_PROB=0.6`, `REV_SUFFIX="_rev"` |
| Respuesta `choice` | `typesafe_sdk/_schemas/models.py:11-30` (venv) | `choice: str`, `confidence: float` (0–1), `probabilities: dict[str, float]`. `answers[q]` llega como `model_dump(mode="json")` |
| Tabla | `backend/app/models/jev.py:14-29` | `cache_key` único, `battery String(32)`, `battery_version`, `requested_model`, `response_model`, `content_item_id` **nullable**, `answers` JSONB, tokens. No hace falta migración |
| Patrón de caché y guardado | `backend/app/services/classification.py:51-92` | `_judge_one` captura `JudgeError` y loguea sin state. `_save` hace `insert … on_conflict_do_nothing(cache_key)` |
| Consumo | `backend/app/collectors/usage.py` (`UsageMeter.add(provider, operation, units, *, output_units)`), `backend/app/schemas/cost.py:19` (`Provider.TYPESAFE_JEV`), `data/pricing.yaml:33-36` | Precio por token de entrada |
| Settings | `backend/app/core/config.py:17-18` | `typesafe_api_key`, `jev_model`. No hay flag de verificación |
| `.env.example` | raíz, líneas 13-14 | `TYPESAFE_API_KEY=`, `JEV_MODEL=jev-1.13.0` |
| UI | `frontend/src/components/dossier/NextStep.vue:62-70` | Muestra `limitations` bajo «Qué no sabemos». No hace falta tocarla |
| Tests de explicación | `backend/tests/test_explanation.py:44-50` (`explained`), `:54-105` (puras), `:144-185` (service, `FakeExplainer`, `fitted_topics`) | Estilo a imitar. `URL = "https://example.com/0"` |
| Tests de Jev | `backend/tests/test_jev.py:61-139` (`labels`, `noul`, `choice`, parametrize con `ids`), `backend/tests/test_classification.py:19-32` (`FakeJudge`) | Estilo a imitar |
| Script de evaluación previo | `data/evaluations/eval_jev_battery.py` | Patrón `run`/`score` con argparse, `PYTHONPATH=.` desde `backend/`, respuestas a JSON reanudables |
| Ejecución servida (planning) | Supabase, solo lectura | Última `analyze` correcta: run **35**, 56 oportunidades, 0 con `NO_VALID_CLAIM_NOTE`. `llm_evaluations` con `operation='explain_opportunity'`: 164 filas, 492 afirmaciones. Sin acceso a Railway: no se sabe si `DEMO_RUN_ID` fija otra ejecución. Se usa «la última correcta» |
| Forma real de las afirmaciones | lectura de 8 filas recientes | Casi todas son mixtas: (1) qué pasa, mezclando datos medidos («saturado», «4 piezas frente a 12») con contenido de las piezas; (2) por qué importa, con frases de ausencia («ninguna pieza muestra resultados medidos») e hipótesis («puede sugerir»); (3) qué hacer, siguiendo la recomendación de los datos medidos. Citan de 1 a 6 URLs |

## Decisiones tomadas

### D1 — Tipo de pregunta: `choice` de 3 opciones con `_rev`

- **Elegido:** `support`, de tipo `choice`, con opciones en este orden:
  `supports` · `contradicts` · `says_nothing`. Además, `support_rev` con las mismas opciones en
  orden inverso, en la misma llamada.
- **Por qué:**
  - Es lo que fija `docs/jev.md` §3 (patrón *citation check* del cookbook).
  - `_rev` controla el sesgo hacia la primera opción, como en la batería de pieza.
  - `choice` devuelve `confidence`, que es lo que pide la regla «≥ 0,8».
- **Descartado:**
  - `score` de 4 niveles (contradice · no lo menciona · parcial · total): `docs/jev.md` dice que
    los niveles de `score` no están calibrados, y una afirmación «parcial» no se publicaría de
    todas formas.
  - `noul` «la evidencia lo afirma»: no devuelve `confidence`, y pierde la distinción entre
    contradice y no dice nada, que sirve para auditar.

### D2 — El `state` incluye los datos medidos **(desvío)**

**Confirmada por Melkin en el chat el 18/10 (~01:00 ESP).**

- **Elegido:** el `state` tiene esta forma:

  ```json
  {
    "claim": "<texto de la afirmación>",
    "measured_facts": ["<frase>", "..."],
    "evidence": [{"source": "...", "title": "...", "description": "..."}]
  }
  ```

  - `measured_facts` es exactamente `ExplainInput.facts`, lo que recibió el LLM.
  - En `evidence` van las piezas citadas que el LLM recibió, sin repetir y en el orden de cita.
    Solo llevan `source`, `title` y `description`; sin descripción, la clave se omite, como en
    `piece_state`.
  - No llevan URL, plataforma, idioma, segmento ni región.
  - Las justificaciones del fit (`<fit>`) **no** entran.
- **Por qué:**
  - El encargo decía «contra las piezas que cita (solo título y descripción)». Pero las
    afirmaciones reales se apoyan a la vez en los datos medidos y en las piezas (ver la tabla de
    contexto: «saturado», «4 piezas frente a 12», «conviene descartar»).
  - Contra las piezas solas, Jev, que lee de forma literal, marcaría `says_nothing` casi todas las
    afirmaciones 1 y 3. Quitaría así de cada tema la frase de «qué conviene hacer».
  - Los datos medidos son nuestros y deterministas: verificar contra ellos cumple la regla 3.
  - El `<fit>` es texto del LLM. Verificar al LLM con su propio texto sería circular.
  - Las piezas siguen yendo solo con título y descripción.
- **Contraste medido:** el paso 5 mide también la variante sin `measured_facts`. Si resulta igual
  de buena o mejor, el implementador **no** cambia el diseño: lo anota en la evaluación para que
  Melkin decida.
- **Descartado:**
  - Solo las piezas: tiraría las afirmaciones de recomendación de forma sistemática.
  - Verificar solo la afirmación 1 y dejar pasar las demás: las afirmaciones no van tipadas, y la
  posición no es una garantía.
  - Un prompt `explain_opportunity.v2` que etiquete la base de cada afirmación: ver D3.

### D3 — No se toca el prompt de `explain_opportunity`

- **Elegido:** el prompt `explain_opportunity.v1.md` y su caché en `llm_evaluations` se quedan
  como están. La verificación corre sobre la salida ya cacheada.
- **Por qué:**
  - Cambiar el prompt invalida la caché de las 56 explicaciones.
  - También cambia los textos de la demo horas antes del freeze.
- **Descartado:** prompt v2 con un campo `basis` por afirmación. Queda como mejora si la validación
  falla por las frases de ausencia.

### D4 — Batería `claim.v1.yaml`

Archivo: `backend/app/editorial/prompts/jev/claim.v1.yaml`, `version: 1`. Las instrucciones van en
español, como en `piece.v3.yaml`, con una cabecera de comentario que explica qué es y remite a
`docs/jev.md` §3. El contenido exacto es este (el implementador puede pulir la redacción, pero no
el sentido ni el orden de opciones):

```yaml
version: 1
questions:
  - id: support
    type: choice
    instructions: >-
      ¿Los datos medidos (`measured_facts`) y las piezas citadas (`evidence`) respaldan la
      afirmación (`claim`)?
    criteria:
      supports:
        what: >-
          todo lo que la afirmación da por hecho aparece en `measured_facts` o en el título o la
          descripción de alguna pieza de `evidence`, aunque sea con otras palabras. Lo que presenta
          como hipótesis ("puede", "sugiere") o como recomendación coherente con `measured_facts`
          no necesita más respaldo. Una ausencia ("ninguna pieza muestra…") está respaldada si
          ninguna pieza de `evidence` lo muestra
        not_for: >-
          afirmaciones que añaden hechos, cifras, nombres, empresas o resultados que no están en
          `measured_facts` ni en `evidence`
      contradicts:
        what: algún dato de la afirmación choca con `measured_facts` o con lo que dicen las piezas
        not_for: afirmaciones que solo añaden algo que los datos y las piezas no mencionan
      says_nothing:
        what: >-
          la afirmación da por hecho algo que ni `measured_facts` ni las piezas de `evidence`
          mencionan
        not_for: afirmaciones cuyo contenido sí aparece, aunque sea con otras palabras
  - id: support_rev
    type: choice
    instructions: <igual que support>
    criteria: <las tres opciones en orden inverso: says_nothing, contradicts, supports, con el mismo texto>
```

- **Por qué:**
  - Las tres opciones son contrastivas (`what` / `not_for`), como en `format` de la batería de
    pieza.
  - Las ausencias y las hipótesis se nombran a propósito: son casi la mitad de las afirmaciones
    reales (afirmación 2).
- **Limitación conocida:** una ausencia se comprueba solo contra las piezas citadas, no contra
  todas las del tema. Se acepta: lo que se comprueba es que la cita no contradiga la afirmación.

### D5 — Clave de caché por batería, sin migración

- **Elegido:** en `intelligence/jev.py`:
  - nueva función `battery_cache_key(battery: Battery, state, model) -> str`, con el mismo JSON
    canónico que hoy;
  - `cache_key(state, model)` delega en ella con `piece_battery()`, así que sus llamadas y su
    resultado no cambian;
  - las filas de afirmación se guardan con `battery="claim"`, `battery_version=1` y
    `content_item_id=None`.

  Si el dedup ya generalizó la clave (p. ej. para la batería de pares), se usa su versión y no se
  crea otra. Se anota en el informe.
- **Por qué:**
  - El payload que se hashea ya incluye el nombre y la versión de la batería, así que no hay
    colisión entre baterías.
  - `content_item_id` ya es nullable, así que no hace falta migración ni tabla nueva.
- **Descartado:**
  - Una tabla `claim_verifications`: duplica `jev_judgments` y exige una migración en Supabase.
  - Un FK a `opportunities`: el id del tema cambia entre ejecuciones.

### D6 — Del juicio a la decisión (Python, puro)

- **Elegido:** `claim_supported(answers) -> bool | None`, en `intelligence/jev.py`:
  - `None` si falta `support` o `support_rev` (sin juicio). El service lo trata como «no
    verificada», no como «rechazada».
  - `True` si se cumplen las tres condiciones:
    - `answers["support"]["choice"] == "supports"`;
    - `answers["support"]["confidence"] >= CLAIM_SUPPORT_MIN_CONFIDENCE` (0.8);
    - `answers["support_rev"]["choice"] == "supports"`.
  - `False` en cualquier otro caso.
- Constantes con nombre:
  - `CLAIM_BATTERY = "claim"`;
  - `CLAIM_BATTERY_FILE`;
  - `CLAIM_SUPPORT_MIN_CONFIDENCE = 0.8`, con el comentario «CLAUDE.md §7, Verificación»;
  - `SUPPORTS = "supports"`;
  - `SUPPORT_QUESTION = "support"`.

  La clave del `_rev` se forma con `REV_SUFFIX`.
- **Por qué:**
  - 0,8 es la regla de CLAUDE.md §7.
  - Es un umbral sobre `confidence`, distinto de `CHOICE_MIN_PROB` (0,6 sobre la probabilidad
    máxima). Por eso tiene constante propia y no se reutiliza la otra.
  - El `_rev` solo tiene que coincidir, como en `_choice`.

### D7 — Un tema entero se verifica o se queda «no verificado»

- **Elegido:** un tema queda verificado solo si **todas** sus afirmaciones que pasaron Python tienen
  juicio (`claim_supported` ≠ `None`). Entonces:
  - se publican las `True`;
  - las `False` se cuentan en la nota de Jev.

  Si falta algún juicio (no hay clave, `JudgeError` o presupuesto agotado):
  - se publican las afirmaciones que pasaron Python, como hoy;
  - se añade `UNVERIFIED_NOTE`.
- **Por qué:**
  - Mezclar en un mismo texto frases verificadas y no verificadas obligaría a marcar cada frase, y
    el contrato no tiene dónde.
  - Tirar un tema entero porque Jev falló sería peor que hoy.
- **Descartado:**
  - Tirar las afirmaciones sin juicio: un fallo de Jev vaciaría el dossier.
  - Publicar la mezcla sin nota: presentaría como verificado lo que no lo está (regla 3).

### D8 — Las notas van en `limitations`, sin cambio de contrato

- **Elegido:** dos constantes nuevas en `intelligence/explanation.py`, con texto final:
  - `UNVERIFIED_NOTE = "«Por qué importa» no está verificado por Jev: solo pasó las comprobaciones de Python (pieza citada y cifras observadas)."`
  - Nota de rechazo de Jev, construida como la de Python: «Jev no encontró respaldo en la evidencia
    citada para 1 afirmación del LLM: no se publica.» / «… para N afirmaciones del LLM: no se
    publican.»

  La nota de Python se mantiene tal cual y cuenta solo las caídas de Python. Si Jev rechaza todas,
  queda solo `NO_VALID_CLAIM_NOTE`, como hoy.
- **Por qué:**
  - `limitations` ya se muestra bajo «Qué no sabemos» (`NextStep.vue:62`) y lo lee el MCP.
  - Un campo `explanation_verified: bool` cambiaría el contrato `Opportunity`, OpenAPI y
    `api.ts`, y habría que avisar en el canal a 13 horas del freeze.
- **Descartado:** el campo booleano en el contrato (anotado como mejora posible, no se hace).

### D9 — Activación con `JEV_VERIFY_CLAIMS`, apagado por defecto hasta validar

- **Elegido:**
  - En `Settings`: `jev_verify_claims: bool = False`, con un comentario que remite a la evaluación.
  - En `services/verification.py`:

    ```python
    @dataclass(frozen=True)
    class ClaimVerifier:
        judge: Judge | None  # None: sin TYPESAFE_API_KEY → temas «no verificados»
        budget: int = MAX_CLAIM_VERIFICATIONS_PER_RUN

    def build_claim_verifier(settings: Settings) -> ClaimVerifier | None:
        if not settings.jev_verify_claims:
            return None
        return ClaimVerifier(judge=build_judge(settings))
    ```

  - `explain_topics(..., verifier: ClaimVerifier | None = None)`. Con `None`, el camino es
    idéntico al de hoy y no hay nota. El paso 5 cambia el default a `True` si se cumple D10.
  - `JEV_VERIFY_CLAIMS` se añade a `.env.example` y a la lista de variables de CLAUDE.md §8.
- **Tres casos, a propósito:**

  | Caso | Comportamiento |
  | --- | --- |
  | Flag apagado | Como hoy, sin nota |
  | Flag encendido y sin clave | `UNVERIFIED_NOTE` en los temas con alguna afirmación sin juicio en caché (un tema con todas sus afirmaciones en caché queda verificado) |
  | Flag encendido y Jev falla en parte | `UNVERIFIED_NOTE` en los temas afectados |

  Por qué no hay nota con el flag apagado: apagar es una decisión del equipo (validación fallida).
  En ese caso, `docs/jev.md` y el pitch dejan de decir que Jev verifica, en vez de poner una nota
  en los 56 dossiers.
- **Por qué no es una constante en código:** la constante no se puede cambiar en Railway ni en
  GitHub Actions sin un commit, y los tests construyen `Settings(...)`.
- **Descartado:** un flag booleano como argumento de función (`engineering-standards.md` §3).

### D10 — Criterio de adopción, fijado antes de mirar resultados

La muestra tiene 50 filas.

**40 afirmaciones reales** de la ejecución servida que pasaron las comprobaciones de Python,
estratificadas así:

- unos 14 temas con 3 afirmaciones cada uno;
- repartidos entre las recomendaciones presentes;
- con las posiciones 1, 2 y 3 representadas.

**10 negativas sintéticas**, construidas a partir de afirmaciones reales distintas de las 40, con
`synthetic=true` y etiquetadas `unsupported` por construcción:

- 5 de **cita cambiada**: la afirmación real con su evidencia sustituida por las piezas que cita
  otra afirmación de un tema distinto. Es el fallo real que hay que atrapar: una cita equivocada.
- 5 de **hecho insertado**: la afirmación real, con su evidencia real, más una frase con un hecho
  que no está ni en `measured_facts` ni en las piezas. Por ejemplo, «, según un estudio de
  McKinsey» o el nombre de una empresa que no aparece.

Las negativas son solo para la evaluación y van marcadas: no tocan datos servidos, así que no
chocan con la regla 3. Hacen falta porque todas las afirmaciones reales ya pasaron Python y es
probable que haya pocas negativas naturales. Sin ellas, un Jev que dijera `supports` a todo
pasaría la evaluación.

Las etiquetas las pone el implementador, a ciegas, **antes** de ver ninguna respuesta de Jev, con
tres valores:

- `supported`: todo lo que da por hecho está en los datos medidos o en el título o la descripción
  de una pieza citada;
- `unsupported`: añade algo que no está;
- `contradicted`.

La evaluación lo declara como «evaluador LLM a ciegas», igual que `jev_piece_v3_eval.md`.

La variante adoptada es la de D2 (con `measured_facts`). Se adopta solo si se cumplen **las tres**
condiciones:

1. **Conserva:** ≥ 70 % de las afirmaciones etiquetadas `supported` salen `True`.
2. **Filtra:** ≥ 60 % de las etiquetadas `unsupported` o `contradicted` salen `False`. Cuentan
   las 10 sintéticas y las negativas naturales que haya. Siempre se aplica. Se informa por separado
   por tipo: cita cambiada, hecho insertado y natural.
3. **No vacía la demo:** ≥ 80 % de los temas de la muestra (solo las filas reales) conservan al
   menos una afirmación.

Se informa también por posición (1, 2, 3) y la variante sin `measured_facts`.

- **Si no se cumple:**
  - Una sola revisión, `claim.v2.yaml`, centrada en la posición o el tipo de negativa que más
    falla, sobre las mismas 50 filas (50 llamadas), solo con la variante D2.
  - Si tampoco se cumple: `jev_verify_claims` se queda en `False`, el código se mergea apagado y
    se documenta en `data/evaluations/jev_claim_v1_eval.md` y en `docs/jev.md`.
- **Presupuesto de llamadas a Jev:**

  | Tanda | Llamadas |
  | --- | --- |
  | Variante D2 | 50 |
  | Variante sin datos | 50 |
  | Revisión, si hace falta | 50 |
  | **Total máximo** | **150** |

- **Por qué:**
  - El 70 % es el umbral que ya usa el equipo para las preguntas de Jev («< 70 % de acuerdo no se
    usa en la demo», `docs/jev.md`).
  - El 80 % de temas con texto protege la demo: sin él, la verificación podría dejar todos los
    dossiers en «sin afirmaciones».

### D11 — Presupuesto por ejecución y orden

- **Elegido:** `MAX_CLAIM_VERIFICATIONS_PER_RUN = 200` llamadas nuevas (fallos de caché) por
  ejecución.
  - Las peticiones se generan recorriendo los temas en el orden de `rank(results)`, solo para
    repartir el presupuesto. La salida de `explain_topics` conserva el orden de entrada.
  - Las afirmaciones con el mismo `state` comparten una sola llamada, como las piezas.
  - Cuando se agota, los temas que quedan entran en D7 («no verificado»).
- **Por qué:**
  - Con 56 temas y unas 3 afirmaciones, son unas 170 por ejecución, así que 200 cubre una
    ejecución completa en frío.
  - El coste es de unos 800 tokens × 200 × 0,042 $/M, menos de 0,01 $.
  - El tope protege de un bucle o de un corpus inesperado.
  - El orden de `rank` gasta primero en lo que se ve arriba del Radar.

### D12 — Seams y ubicación

- **Elegido:**
  - `intelligence/jev.py`: batería, `claim_state`, `claim_supported`, `battery_cache_key`. Es
    puro y no sabe de DB.
  - `intelligence/explanation.py`: partir `apply_explanation` en dos etapas puras (Python y
    composición) y añadir las notas.
  - `services/verification.py` (nuevo): caché, llamadas, presupuesto y consumo. No se toca
    `classification.py`, para no chocar con el dedup.
  - `services/explanation.py`: orquesta las etapas.
- **Por qué:**
  - Sigue las capas de CLAUDE.md §10: rutas, después services, después intelligence.
  - La llamada asíncrona a Jev queda entre dos funciones puras testeables.
- **Deuda asumida:** `_save` y `_cached_keys` de la verificación se parecen a los de
  `classification.py`. Solo se unifican si el dedup ya dejó un helper común. Si no, se anota en el
  informe (regla de dos: hoy hay dos usos, pero unificarlos toca un archivo del dedup).

## Diseño de módulos

- **Seam:** `explain_topics` sigue siendo la única entrada desde el job. La verificación es un
  argumento opcional (`verifier`).
- **Interfaz (nombres finales):**

  ```python
  # intelligence/jev.py
  @dataclass(frozen=True)
  class CitedEvidence:
      source: str
      title: str
      description: str | None

  def claim_battery() -> Battery: ...                     # @lru_cache, como piece_battery
  def claim_state(claim: str, *, facts: Sequence[str], evidence: Sequence[CitedEvidence]) -> dict[str, Any]: ...
  def battery_cache_key(battery: Battery, state: dict[str, Any], model: str) -> str: ...
  def claim_supported(answers: Mapping[str, Any]) -> bool | None: ...

  # intelligence/explanation.py
  def python_checked(claims: Sequence[ClaimDraft], *, sent_urls: Set[str], numbers: Set[str]) -> list[ClaimDraft]: ...
  def compose_explanation(
      result: TopicResult,
      published: Sequence[ClaimDraft],
      limitations: Sequence[str],
      *,
      numbers: Set[str],
      notes: Sequence[str],
  ) -> TopicResult: ...
  def python_drop_note(dropped: int) -> str | None: ...   # texto actual, sin cambios
  def jev_drop_note(dropped: int) -> str | None: ...
  # apply_explanation conserva su firma y su comportamiento: python_checked → compose_explanation
  # con [python_drop_note], igual que hoy.

  # services/verification.py
  CLAIM_BATTERY_OPERATION = "claim_battery"
  MAX_CLAIM_VERIFICATIONS_PER_RUN = 200

  @dataclass(frozen=True)
  class ClaimCheck:            # una afirmación ya validada por Python, lista para Jev
      topic_index: int
      claim: ClaimDraft
      state: dict[str, Any]

  @dataclass
  class VerifyStats:
      verified: int            # llamadas nuevas con respuesta
      cached: int
      failed: int              # JudgeError
      over_budget: int
      rejected: int            # claim_supported False
      unverified_topics: int
      skipped_reason: str | None = None   # "sin TYPESAFE_API_KEY" si judge es None

  async def verify_claims(
      session: AsyncSession,
      checks: Sequence[ClaimCheck],
      *,
      verifier: ClaimVerifier,
      meter: UsageMeter,
  ) -> tuple[dict[str, bool | None], VerifyStats]: ...   # cache_key → veredicto (None = sin juicio)
  ```

- **Invariantes:**
  - `compose_explanation` con `published` vacío equivale a `_with_notes(result, None,
    [NO_VALID_CLAIM_NOTE])`: no añade más notas ni las limitaciones del LLM, como hoy.
  - Con `published` no vacío añade, en este orden:
    - las limitaciones del LLM filtradas;
    - las notas (`python_drop_note`, `jev_drop_note`, `UNVERIFIED_NOTE`, solo las que no son
      `None`).
  - `claim_state` solo incluye las piezas citadas que están en `explain.pieces`, sin repetir y en el
    orden de cita. Si una afirmación pasó Python, tiene al menos una.
  - `verify_claims` nunca lanza por un fallo de Jev. `JudgeError` se loguea como
    `jev_claim_failed` con la `cache_key` y el tipo de error, sin el texto, y el veredicto queda
    `None`.
  - Con `verifier.judge is None` no hay llamadas: todos los veredictos que no estén en caché
    quedan `None` y `skipped_reason` se rellena.
  - Las respuestas de caché **sí** se usan aunque no haya clave: se leen `answers` por
    `cache_key`, como `load_judgments`.
- **Ubicación (CLAUDE.md §10):** `intelligence/` (puro), `services/` (DB + Jev), `jobs/analyze.py`
  (cableado y estadísticas). Nada en `api/`, `mcp/` ni `frontend/`.

## Acceso a datos

- Lectura de la caché: `select(JevJudgment.cache_key, JevJudgment.answers).where(cache_key.in_(keys))`,
  en una sola query.
- Escritura: `insert(JevJudgment).values(rows).on_conflict_do_nothing(index_elements=["cache_key"])`,
  en bloque, con `battery=claim_battery().name`, `battery_version=claim_battery().version`,
  `requested_model=settings.jev_model`, `response_model=result.model`, `content_item_id=None`,
  `answers`, `input_tokens` y `output_tokens`. Commit tras guardar, para que las llamadas pagadas no
  se pierdan si el job falla después.
- Sin relaciones ni lazy loading. **Sin migración.** No se borra ni se actualiza ninguna fila.
- El script de evaluación (paso 5) solo lee de Supabase, con `SET TRANSACTION READ ONLY` como
  primera sentencia de la sesión, y escribe solo archivos en `data/evaluations/`.

## Alternativas rechazadas

- **Verificar dentro de `apply_explanation`:** es síncrona y pura. Meter Jev ahí mezcla la red con
  la lógica que se testea.
- **Reusar `classify_pieces` con otra batería:** está atado a `Piece` y a `content_item_id`, y lo
  toca el dedup.
- **Verificar también los briefs:** ver No-objetivos.
- **Un campo de contrato `explanation_verified`:** ver D8.

## Plan de implementación

### Paso 0 — Base y rama [HECHO]

- **Cambio:**
  - `git pull --ff-only` en `main`;
  - comprobar que el PR de `intel-dedup-replicas` está mergeado (`gh pr list --state merged
    --search dedup` o `git log --oneline -15 main`);
  - `git checkout -b intel/claim-verification`;
  - releer las referencias de la tabla de contexto.

  Si el dedup no está mergeado, para y pon el gate en `BLOQUEADO` con «falta el merge de
  intel-dedup-replicas».
- **Verificación:** `git log --oneline -1` y la tabla releída anotada en el informe.
- **Commit:** ninguno.

### Paso 1 — Batería `claim.v1`, estado, clave y veredicto [HECHO]

- **Archivos:** `backend/app/editorial/prompts/jev/claim.v1.yaml` (nuevo),
  `backend/app/intelligence/jev.py`, `backend/tests/test_jev.py`
- **Cambio:** D4, D5 y D6, con las firmas de «Diseño de módulos». Actualiza la docstring de módulo
  de `jev.py` para que diga «batería de pieza y de afirmación».
- **Test primero** (`backend/tests/test_jev.py`):
  - `test_claim_battery_has_support_and_its_reverse`: preguntas `["support", "support_rev"]` y
    `labels(support_rev) == labels(support)[::-1]`.
  - `test_claim_supported` parametrizado, con `ids=`:
    - `supports` 0,85 + rev `supports` → `True` (`supported`);
    - `supports` 0,79 → `False` (`low_confidence`);
    - `supports` 0,9 + rev `says_nothing` → `False` (`rev_disagrees`);
    - `contradicts` 0,95 + rev `contradicts` → `False` (`contradicts`);
    - `says_nothing` → `False` (`says_nothing`);
    - `{}` → `None` (`no_answers`);
    - solo `support` → `None` (`missing_rev`).

    Usa el helper `choice(label, prob)` de `backend/tests/test_jev.py:52`, que ya pone
    `confidence = prob`.
  - `test_claim_state_carries_only_claim_facts_and_cited_text`: claves exactas
    `{"claim", "measured_facts", "evidence"}` y cada pieza con `{"source", "title",
    "description"}`. Sin `url`, `platform`, `segment` ni `region`.
  - `test_claim_state_omits_missing_description`, parametrizado con `None` y `""`.
  - `test_cache_key_depends_on_battery`: el mismo `state` da claves distintas con
    `piece_battery()` y con `claim_battery()`, y `cache_key(state, m) ==
    battery_cache_key(piece_battery(), state, m)` (la clave de pieza no cambia: la caché de
    `piece` sigue valiendo).
- **Verificación:** `cd backend && uv run pytest tests/test_jev.py -q`
- **Commit:** `Add the Jev claim battery and its support verdict`

### Paso 2 — Partir `apply_explanation` en dos etapas puras [HECHO]

- **Archivos:** `backend/app/intelligence/explanation.py`, `backend/tests/test_explanation.py`
- **Cambio:**
  - `python_checked`, `compose_explanation`, `python_drop_note`, `jev_drop_note` y
    `UNVERIFIED_NOTE` (D8).
  - `apply_explanation` se reescribe sobre ellas, con la misma firma y la misma salida.
  - Actualiza la docstring de módulo: ahora también compone tras el veredicto de Jev.
- **Test primero** (`backend/tests/test_explanation.py`, tests puros con `fitted_topics`):
  - `test_jev_rejected_claims_are_not_published_and_counted`: dos afirmaciones válidas, una
    publicada. `why_it_matters` es la publicada y aparece la nota «Jev no encontró respaldo … para
    1 afirmación del LLM: no se publica.».
  - `test_all_claims_rejected_by_jev_keep_the_measured_template`: `published=[]` →
    `why_it_matters` sin cambios y `limitations` contiene `NO_VALID_CLAIM_NOTE`, sin
    `EDITORIAL_PENDING_NOTE`.
  - `test_unverified_explanation_publishes_python_checked_claims_with_a_note`.
  - Los tests existentes (`:54-105`) pasan **sin cambios** (criterio de aceptación 8).
- **Verificación:** `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://radar:radar@localhost:5433/radar_test_verify uv run pytest tests/test_explanation.py -q`
- **Commit:** `Split the explanation checks so Jev verdicts can be applied`

### Paso 3 — Service de verificación con caché, presupuesto y consumo [HECHO]

- **Archivos:** `backend/app/services/verification.py` (nuevo), `backend/app/core/config.py`,
  `backend/tests/test_verification.py` (nuevo)
- **Cambio:**
  - D7, D9 y D11, y las firmas de «Diseño de módulos».
  - `jev_verify_claims: bool = False` en `Settings`.
  - El service toma `checks` ya ordenados (lo ordena el paso 4) y agrupa por `cache_key`.
  - Lee la caché, llama con `asyncio.gather` a como mucho `verifier.budget` claves que faltan, en
    orden, y guarda.
  - Usa `meter.add(Provider.TYPESAFE_JEV, CLAIM_BATTERY_OPERATION, units=input_tokens or 0)` en
    cada llamada real.
  - Devuelve `claim_supported(answers)` por clave.
- **Test primero** (`backend/tests/test_verification.py`, contra la DB de test):
  - Un `FakeClaimJudge` con respuestas por texto de `state["claim"]` que puede lanzar
    `JudgeError` para un texto concreto.
  - `test_verdicts_are_cached_and_a_second_run_makes_no_calls`: segunda llamada → `calls == 0` y
    los mismos veredictos. La fila guardada tiene `battery == "claim"` y
    `content_item_id is None`.
  - `test_usage_counted_only_for_real_calls`: un `UsageCount` con `calls` igual al número de
    llamadas nuevas y operación `claim_battery`.
  - `test_jev_error_leaves_that_claim_without_verdict`.
  - `test_budget_limits_new_calls`: `budget=1` con 2 claves → 1 llamada, un veredicto `None` y
    `over_budget == 1`.
  - `test_without_judge_cached_verdicts_are_used_and_the_rest_have_none`.
  - `test_identical_states_share_one_call`.
  - `test_build_claim_verifier`: flag apagado → `None`; encendido sin clave →
    `ClaimVerifier(judge=None)`. Con `Settings(_env_file=None, ...)`.
- **Verificación:** `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://radar:radar@localhost:5433/radar_test_verify uv run pytest tests/test_verification.py -q`
- **Commit:** `Verify explanation claims with Jev, cached and bounded per run`

### Paso 4 — Cablear en `explain_topics` y en `analyze` [HECHO]

- **Archivos:** `backend/app/services/explanation.py`, `backend/app/jobs/analyze.py`,
  `backend/tests/test_explanation.py`
- **Cambio:**
  - `explain_topics(..., verifier: ClaimVerifier | None = None)`, que devuelve
    `(list[TopicResult], ExplainStats)`.
  - `ExplainStats` gana `verification: VerifyStats | None = None`.
  - Con `verifier`:
    1. por tema con salida, `python_checked`;
    2. construir `ClaimCheck` en el orden de `rank(results)` (D11), con
       `CitedEvidence(source, title, description)` sacado de `explain.pieces` por URL;
    3. `verify_claims`;
    4. por tema, D7, y después `compose_explanation` con las notas.
  - Sin `verifier`, se sigue llamando a `_apply` como hoy.
  - Partir en funciones privadas de ≤ 20–30 líneas.
  - En `analyze._fit_and_explain`: `verifier=build_claim_verifier(settings)`, con el mismo
    `meter`.
  - En `_stats`: `"claim_verification": asdict(...)` o `None`.
  - En `_print_summary`, una línea:
    `  verificación jev: {verified} verificadas · {cached} de caché · {rejected} rechazadas · {unverified_topics} temas sin verificar`,
    o `  verificación jev: apagada (JEV_VERIFY_CLAIMS)`.
  - Actualiza la docstring de `analyze.py` (la cadena del pipeline).
- **Test primero** (`backend/tests/test_explanation.py`, service):
  - `test_verified_explanation_publishes_only_supported_claims`: `FakeExplainer` con dos
    afirmaciones, una rechazada por `FakeClaimJudge`.
  - `test_with_verification_on_and_no_key_topics_are_marked_unverified`: parte de una caché vacía
  de la batería `claim` (DB de test recién creada), así que no contradice el uso de la caché sin
  clave.
  - `test_without_verifier_nothing_changes`: el test existente
    `test_topics_with_fit_are_explained_and_cached` sigue pasando sin cambios, y no hay
    `UNVERIFIED_NOTE`.
- **Verificación:**
  - `cd backend && TEST_DATABASE_URL=postgresql+asyncpg://radar:radar@localhost:5433/radar_test_verify uv run pytest -q`
  - **No** ejecutes `python -m app.jobs.analyze`: `backend/.env` apunta a Supabase.
- **Commit:** `Wire claim verification into the explanation step of analyze`

### Paso 5 — Validación con afirmaciones reales (solo lectura) y decisión de adopción

- **Archivos:**
  - `data/evaluations/eval_claim_verification.py` (nuevo);
  - `data/evaluations/jev_claim_v1_sample.csv` (nuevo);
  - `data/evaluations/jev_claim_v1_answers.json` (nuevo);
  - `data/evaluations/jev_claim_v1_eval.md` (nuevo);
  - `backend/app/core/config.py` (solo si se adopta).
- **Cambio:** un script con tres comandos, al estilo de `eval_jev_battery.py`.
  - **`sample`:**
    - abre la sesión con `SET TRANSACTION READ ONLY`;
    - toma la última `pipeline_runs` con `job='analyze'` y `status='success'`; si `DEMO_RUN_ID`
      está en `Settings`, usa esa;
    - por cada oportunidad (`opportunities.run_id`), busca en `llm_evaluations`
      (`operation='explain_opportunity'`, mismo `opportunity_id`) la fila cuyas afirmaciones,
      con el espacio normalizado, aparecen como subcadena en el `why_it_matters` servido, y se
      queda con la que más afirmaciones encaja;
    - una afirmación entra si aparece en el `why_it_matters` servido, es decir, si pasó Python;
    - `measured_facts` = `opportunity_facts(Opportunity.model_validate(payload),
      OpportunityTimeline.model_validate(timeline))`;
    - las piezas citadas salen de `content_items` + `sources` por URL: `sources.name`, `title` y
      `description[:MAX_DESCRIPTION_CHARS]`;
    - muestreo estratificado con semilla fija (`random.Random(18)`): 40 afirmaciones reales de
      unos 14 temas, repartidas por `recommendation` y por posición;
    - construye las 10 negativas sintéticas de D10 (5 de cita cambiada y 5 de hecho insertado) a
      partir de otras afirmaciones reales, con la misma semilla. La frase insertada sale de una
      lista fija en el script;
    - escribe el CSV con estas columnas:
      `id, opportunity_id, recommendation, position, synthetic, negative_kind, claim, measured_facts, evidence_json, label`.
      En las reales, `synthetic=false`, `negative_kind` vacío y `label` vacío. En las sintéticas,
      `synthetic=true`, `negative_kind` = `swapped_citation` | `inserted_fact` y
      `label=unsupported`.
  - **Etiquetado:** el implementador rellena `label` (`supported` / `unsupported` / `contradicted`)
    de las 40 reales con la definición de D10, leyendo solo el CSV, **antes** de ejecutar `run`.
    Commitea la muestra etiquetada en un commit **propio**, antes de cualquier `run`. Así el
    historial de git demuestra que las etiquetas se fijaron antes de ver a Jev.
  - **`run --variant facts|evidence_only --battery <yaml> --out <json>`:**
    - llama a `build_judge(get_settings())` directamente, sin el service ni la DB;
    - `facts` usa `claim_state(...)`; `evidence_only`, el mismo estado sin `measured_facts`;
    - se puede reanudar por `id`;
    - aborta si el total de llamadas acumuladas en el JSON llegaría a pasar de 150.
  - **`score`:** por variante, calcula los tres criterios de D10, el desglose por posición y la
    matriz `label × veredicto`.
  - **`jev_claim_v1_eval.md`:**
    - la muestra, quién etiquetó y cómo (evaluador LLM a ciegas);
    - las tablas;
    - si se cumple D10;
    - la comparación con `evidence_only`;
    - las llamadas y el coste aproximado, a partir de `input_tokens`.
  - **Decisión:**
    - si D10 se cumple con `claim.v1`, `jev_verify_claims` pasa a `True`;
    - si no, haz la única revisión (`claim.v2.yaml`, más `CLAIM_BATTERY_FILE` apuntando a ella si
      se adopta) y repite;
    - si sigue sin cumplirse, el flag se queda en `False`.
- **Test primero:** no aplica. Es un script de evaluación, sin lógica de producción nueva; usa
  `claim_state` y `claim_supported`, ya testeadas.
- **Verificación:** con `PYTHONPATH=.` desde `backend/`, en este orden:
  `python ../data/evaluations/eval_claim_verification.py sample --out ../data/evaluations/jev_claim_v1_sample.csv`,
  después `run` dos veces (las dos variantes) y después `score`. Pega la salida de `score` en el
  informe.
- **Commits** (dos, en este orden):
  1. `Add the labelled claim sample for the Jev verification eval`: el script, el CSV etiquetado y
     nada más; va antes de cualquier `run`.
  2. `Validate Jev claim verification on real explanations`: las respuestas, `score` y el `.md`.
     Si se adopta, lleva también el cambio del default, con «Enable claim verification by default»
     como segunda línea del mensaje.

### Paso 6 — Documentación [HECHO]

- **Archivos:** `docs/jev.md`, `.env.example`, `CLAUDE.md`
- **Cambio:**
  - **`docs/jev.md`, sección «3. Verificación»:**
    - el `state` incluye `measured_facts` (D2) y por qué;
    - la pregunta, con su `_rev`;
    - el flag `JEV_VERIFY_CLAIMS` y su estado tras la validación;
    - el enlace a `jev_claim_v1_eval.md`;
    - las notas de `limitations`;
    - el presupuesto por ejecución;
    - los briefs como pendiente.
  - **`.env.example`:** `JEV_VERIFY_CLAIMS=` con el valor adoptado y un comentario de una línea.
  - **`CLAUDE.md` §8:** añade `JEV_VERIFY_CLAIMS` a la lista de variables.
  - **`CLAUDE.md` §7, «Verificación»:** cambia «contra la evidencia que cita» por «contra la
    evidencia que cita y los datos medidos que recibió el LLM».
  - **`docs/scoring.md`:** si ya existe en `main`, actualiza la fila #11 de «Diferencias con
    CLAUDE.md». Si no existe, no lo crees.
- **Verificación:** `git diff --stat`, que solo muestre esos archivos.
- **Commit:** `Document Jev claim verification`

## Estrategia de test

- **Seams:** el más alto posible sin red.
  - `explain_topics` con `FakeExplainer` + `FakeClaimJudge`, contra la DB de test.
  - Las funciones puras de `jev.py` y `explanation.py`.
  - El borde que se mockea es el `Judge` Protocol. Nunca se mockea `claim_supported` ni
    `compose_explanation`.
- **Prior art:**
  - `backend/tests/test_explanation.py`: `fitted_topics`, `explained`, `FakeExplainer`.
  - `backend/tests/test_classification.py`: `FakeJudge`.
  - `backend/tests/test_jev.py`: helpers `choice`/`noul` y parametrize con `ids=`.
- **Casos que entran:**
  - Los de los pasos 1–4.
  - Cada uno sale de un criterio de aceptación o de una decisión (D6 umbral y `_rev`, D7 tema
    parcial, D8 notas, D9 tres casos, D11 presupuesto y deduplicación, D5 caché).
- **Casos límite del dominio:**
  - tema sin afirmaciones válidas en Python: no se envía nada a Jev;
  - afirmación que cita una URL enviada y otra no: el `state` lleva solo la enviada;
  - pieza citada sin descripción: se omite la clave;
  - sin clave de Jev pero con caché: se usa la caché.
- **Casos descartados por ruido:** la redacción concreta de las instrucciones del YAML (la mide el
  paso 5, no un test) y la concurrencia del semáforo (ya cubierta por `TypeSafeJudge`).
- **Parametrización:** `test_claim_supported` (7 casos, `ids=`) y
  `test_claim_state_omits_missing_description` (`None`, `""`).

## Verificación final

```bash
cd /Users/melandres8/Documents/Projects/content-radar/backend
uv run ruff check . && uv run ruff format --check .
uv run pyright app/intelligence/jev.py app/intelligence/explanation.py app/services/verification.py app/services/explanation.py app/jobs/analyze.py app/core/config.py ../data/evaluations/eval_claim_verification.py
TEST_DATABASE_URL=postgresql+asyncpg://radar:radar@localhost:5433/radar_test_verify uv run pytest -q
git -C /Users/melandres8/Documents/Projects/content-radar log --oneline main..intel/claim-verification
```

Lo que **no** se ejecuta: `uv run python -m app.jobs.analyze`, porque `backend/.env` apunta a
Supabase. La comprobación de punta a punta con datos reales la hace Melkin al lanzar el siguiente
`analyze`.

## Riesgos

- **Jev marca `says_nothing` las frases de ausencia o de hipótesis.** Señal: la posición 2 cae por
  debajo del 70 % en el paso 5. Qué hacer: la revisión `claim.v2` centrada en esas frases. Si no
  basta, el flag se queda apagado (D10).
- **Demasiados temas se quedan sin texto.** Señal: falla el criterio 3 de D10. Qué hacer: no se
  adopta. Nunca se baja el 0,8, que es una regla de CLAUDE.md.
- **El dedup cambió el cliente o la tabla.** Señal: el paso 0 no casa con la tabla de contexto.
  Qué hacer: si solo se movieron líneas, se sigue; si cambió una firma de D5 o D6, se para con el
  gate en `BLOQUEADO`.
- **El emparejamiento del paso 5 (afirmaciones guardadas con el texto servido) no encuentra
  fila.** Señal: menos de 50 afirmaciones elegibles. Qué hacer: se usan las que haya (mínimo 30)
  y se dice en la evaluación. Con menos de 30, se informa y se para.
- **Coste:** acotado por D11 y por el tope de 150 llamadas de la evaluación (unos 0,005 $).

## Historial de intentos

| Fecha | Qué bloqueó | Qué se decidió | Commits que quedaron |
| --- | --- | --- | --- |
| 2026-10-18 | Paso 5: el permiso de la sesión denegó la lectura de Supabase (`sample`), y el encargo prohibía llamar a Jev. Sin muestra no hay etiquetado ni `run` ni `score` | Pasos 0–4 y 6 hechos sobre `main` @ `026e504`. El script `eval_claim_verification.py` queda commiteado y probado con `sample` contra la DB local (ejecución 28: 40 reales de 14 temas + 10 sintéticas; esa muestra no se commitea porque no es la ejecución servida). `jev_verify_claims` sigue en `False`, y la documentación lo dice. **Pendiente para Melkin:** (1) `sample` contra Supabase en solo lectura; (2) etiquetar las 40 reales a ciegas y commitear con «Add the labelled claim sample for the Jev verification eval»; (3) `run --variant facts` y `run --variant evidence_only` con `claim.v1.yaml`; (4) `score`, `jev_claim_v1_eval.md` y la decisión de D10; (5) antes de activar `JEV_VERIFY_CLAIMS`, decidir si en un tema «no verificado» (alguna afirmación sin juicio) se quitan las que Jev ya rechazó: D7 literal las publica bajo `UNVERIFIED_NOTE`, y la regla 3 del plan dice que lo que Jev no respalda no se publica. Desvíos menores: test DB `radar_test_claims` (no `radar_test_verify`); `battery_cache_key` ya existía (dedup, D5); `claim_cache_key(state)` añadido en `services/verification.py` para que el service de explicación lea el veredicto por clave; `test_build_claim_verifier` usa `Settings(...)` con los dos campos explícitos y sin `_env_file`, como el resto de tests (pyright rechaza `_env_file`) | `939183c` plan · `339ee65` paso 1 · `cfcd62d` paso 2 · `050d71a` paso 3 · `a90617b` paso 4 · `e41ab15` script del paso 5 · `31d1311` paso 6 |

## Preguntas abiertas

- (ninguna)
