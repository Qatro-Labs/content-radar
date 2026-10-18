# Política de `publish_now`: pre-registro y evaluación

> 18/10/2026. Pre-registro escrito antes de simular variantes contra etiquetas y antes de etiquetar.
> Datos: runs 38, 41 y 43 de `analyze`, en solo lectura sobre Supabase.

## Pre-registro

**Qué promete `publish_now`.** "30X produce una pieza sobre este tema esta semana." Las demás
etiquetas no descartan el tema: lo dejan para más tarde (`wait_for_case`) o piden trabajo editorial
antes (`find_angle`).

**Qué error cuesta más.** El falso positivo: recomendar publicar algo sin sustancia para un ejecutivo
latinoamericano gasta la credibilidad del radar en la demo y en el uso real. El falso negativo
cuesta una ventana, pero el tema sigue visible en el ranking. Por eso la métrica principal es la
**precisión** de `publish_now`, y el recall solo desempata.

**Pregunta.** ¿`org_application` ≤ 1 ("ninguna organización lo aplica") y `latam_gap = false` ("ya hay
cobertura en LATAM") deben bloquear `publish_now`, o solo cambiar el tipo de pieza?

**Variantes** (sobre la política de `main` tras el PR #67):

| Id | Cambio |
|---|---|
| base | Política actual |
| a | La regla del hueco LATAM (subida sin demostrar) acepta también `latam_gap = null` |
| b | `accelerating` (p ≤ 0,10) con fit ≥ 60 publica aunque `latam_gap = false` |
| c | Fit mínimo 50 en vez de 60 |
| d | Control negativo: además publica con confianza baja y en descenso |
| e | `org_application` ≤ 1 deja de bloquear: la razón pide una pieza de anticipación |
| f | `latam_gap = false` deja de bloquear en `emerging` y `accelerating`: la razón pide ángulo propio |
| combinaciones | a+b, a+e, a+f, a+e+f |

**Etiquetas de referencia.** Un agente con criterio editorial, distinto de quien diseña las reglas,
etiqueta a ciegas los temas del run 43: ve las piezas (título, descripción, fuente, región, URL) y el
perfil de 30X, pero no los scores, la etapa, la recomendación ni los textos del LLM. Pregunta: "¿30X
debería publicar sobre esto esta semana? sí / no, y con qué formato". Conjunto etiquetado: los 20
primeros temas del ranking que no son `discard`, más cualquier tema del run 43 que alguna variante
lleve a `publish_now`.

**Referencia externa.** Los posts de @andresbilbao guardados en la DB (y los de @crece30x si los hay):
qué temas publica 30X y si publica temas sin caso de empresa o ya cubiertos en LATAM.

**Regla de decisión** (fijada antes de ver resultados):
1. Se descarta toda variante con precisión < 0,70 contra las etiquetas (estimación puntual; Wilson al
   95 % solo se informa) o que lleve a `publish_now` un tema etiquetado "no" con un motivo que la
   regla 3 prohíbe (sin evidencia de lo que se afirma).
2. Entre las que quedan, gana la de más temas `publish_now` en el run 43 que el etiquetador marcó "sí".
3. Empate: la más conservadora (menos reglas relajadas).
4. La variante d es un control: si pasara el criterio 1, el etiquetado no discrimina y se adopta solo
   `a` (ya simulada) o nada.
5. Estabilidad: se informa cuántos temas `publish_now` de cada run tienen un tema equivalente
   (≥ 30 % de URLs de evidencia compartidas) en `publish_now` de los otros runs. No decide; si una
   variante solo funciona en un run, se dice.

**Límites conocidos.** n ≈ 20–25 temas, un solo etiquetador (un modelo, no una persona de 30X), un
solo día de datos.

## Resultados

### Etiquetado ciego (run 43, 20 temas)

Etiquetador: un agente con criterio editorial (modelo, no una persona de 30X). Vio solo las piezas,
el perfil de 30X y el reto (`docs/brief.md` §1 y §3). **Ciego solo en parte:** CLAUDE.md, con las
reglas de §7, se cargó en su contexto al arrancar. No abrió más archivos ni artículos: juzgó por
títulos y descripciones. Resultado: 9 "sí", 11 "no".

Criterios que declaró, antes de ver ninguna variante:
- Decide la sustancia para un ejecutivo (coste, riesgo, ventas, cambio en el rol del líder), no el
  volumen ni el tema.
- **La falta de caso real no bloquea por sí sola**: ninguno de sus "sí" se decidió por eso. Pesa
  cuando el tema tampoco tiene otra sustancia.
- **La cobertura en LATAM no bloquea por sí sola**: pide un ángulo de gestión; un caso local es una
  ventaja. Solo pesa junto a llegar tarde y no tener nada nuevo.

### Variantes contra las etiquetas (run 43)

| Variante | `publish_now` | Aciertan "sí" | Precisión (Wilson 95 %) | Recall |
|---|---|---|---|---|
| base | 1 | 1 | 1,00 (0,21–1,00) | 1/9 |
| a | 2 | 2 | 1,00 (0,34–1,00) | 2/9 |
| b | 2 | 2 | 1,00 (0,34–1,00) | 2/9 |
| c | 2 | 1 | **0,50** (0,09–0,91) | 1/9 |
| d (control) | 1 | 1 | 1,00 | 1/9 |
| e | 1 | 1 | 1,00 | 1/9 |
| f | 2 | 2 | 1,00 | 2/9 |
| a+b | 3 | 3 | 1,00 (0,44–1,00) | 3/9 |
| a+e | 2 | 2 | 1,00 | 2/9 |
| a+f | 3 | 3 | 1,00 (0,44–1,00) | 3/9 |
| a+e+f | 3 | 3 | 1,00 (0,44–1,00) | 3/9 |

- c queda fuera por precisión: mete "Ingresos personales vendiendo servicios con IA", que el
  etiquetador rechazó (hype de ingresos personales, sin consecuencia para una empresa).
- a+b, a+f y a+e+f empatan con 3 de 3. Por la regla 3 del pre-registro gana la más conservadora:
  **a+b** (b solo relaja la cobertura LATAM en `accelerating`, con p ≤ 0,10; f también en
  `emerging`). En estos datos dan el mismo conjunto.
- d y e no cambian nada: **ningún tema sin caso real (`org_application` ≤ 1) llega a fit 60 en los
  runs 38, 41 y 43** (máximo 53,3). El bloqueo por falta de caso es redundante con el fit mínimo.
  Por eso el control d no puede probar si el etiquetado discrimina; c sí lo prueba (lo rechaza).

### Estabilidad entre runs

| Variante | Run 38 | Run 41 | Run 43 |
|---|---|---|---|
| base | Control del coste | Control del gasto | Control del gasto |
| a+b | Control del coste · Rezago LATAM · "Adopción y control de la IA en empresas" | Control del gasto · Rezago LATAM · Agentes para ventas | Control del gasto · Rezago LATAM · Agentes para ventas |

2 de los 3 temas de a+b en el run 43 aparecen en `publish_now` en los tres runs. "Agentes para
ventas" falta en el 38, donde entra "Adopción y control de la IA en empresas", un cluster mezclado
(auditoría de esta sesión): el riesgo de a está en la calidad del clustering, no en la regla.

### Referencia externa: lo que publica 30X

Solo se pudo leer su newsletter de Substack (13 piezas, 8/6–6/10/2026); Instagram, YouTube y
LinkedIn no fueron accesibles y la DB no guarda posts de sus perfiles. De las 5 piezas de IA, unas
4 no se apoyan en un caso con nombre, y los temas son lanzamientos globales que los medios de la
región probablemente ya cubrían: 30X se diferencia por el enfoque ejecutivo y los pasos de acción.
Coincide con el etiquetador: ni la falta de caso ni la cobertura en LATAM frenan a 30X. Muestra
pequeña y de un solo canal.

### Artículos completos de los temas que cambian (run 43)

Un agente leyó las piezas completas de los 4 temas que alguna variante lleva a `publish_now`
(Reddit y McKinsey no se pudieron leer; varios TikTok y YouTube solo en parte):

| Tema | Caso real | Cobertura LATAM | Riesgo |
|---|---|---|---|
| Control del gasto en IA | Sí: Uber agotó su límite anual de gasto en IA en 4 meses; Meta, Cisco y Walmart con topes (Expansión, sindicado del FT) | Ninguna (0 de 9; Expansión es España) | Lo de Amazon sale de fuentes anónimas |
| Rezago de América Latina | Sí, sin resultados medidos: Credicorp (más del 90 % de la plantilla usa IA, más de 100 casos en producción), Banco Galicia | Fuerte: 11 de 14 piezas | **Cluster mezclado**: adopción bancaria, startups argentinas, centros de datos, edtech; solo la pieza de Infobae trata del "rezago" |
| Agentes para ventas y atención | **Débil**: AssemblyAI, un proveedor de IA, aplicándolo a su propio soporte (80 % de tickets, dato propio); un TikTok con empresa sin nombre | Ninguna sobre el tema | 1 pieza de HN es un incidente, no un caso de ventas |
| Ingresos personales con IA (solo c) | No: autodeclaraciones de influencers | Ninguna | Confirma el "no" del etiquetado |

Consecuencias:
- La regla no cambia: los 3 temas de a+b tienen sustancia para un ejecutivo, y el etiquetador los
  marcó "sí". Pero dos riesgos son del clustering y de la rúbrica, no de la recomendación:
  - "Rezago de América Latina" mezcla subtemas. Su nombre promete más de lo que cubre; en la demo
    se presenta como "adopción de IA en banca y empresas de LATAM".
  - "Agentes para ventas" tiene `org_application` 4 con un caso que es el propio proveedor. La
    rúbrica del LLM sobrevalora ese criterio cuando el caso es del vendedor (regla 3: no presentarlo
    como caso de cliente).
- Revisar el texto de ambos en el siguiente run antes de fijar `DEMO_RUN_ID`.

### Lo que no se adoptó y queda abierto

Los 6 "sí" que siguen sin `publish_now` en el run 43:

| Tema | Lo que lo frena |
|---|---|
| Agente empresarial de Google y Gemini | Fit 43 (explicador de lanzamiento) |
| Riesgos de seguridad de los agentes | Fit 53, `org_application` 1 |
| Agentes de OpenAI que acceden a sistemas ajenos | Fit 30, `org_application` 1 |
| Cómo escribir skills para agentes | Fit 43, `org_application` 1 |
| Liderazgo y estrategia con IA | En descenso |
| Epic Games reemplaza programación por IA | En descenso |

- Cuatro los frena el **fit**: la rúbrica puntúa bajo los explicadores y las lecciones de riesgo
  que el etiquetador sí publicaría. Cambiarlo es tocar el prompt del audience fit: fuera del
  feature freeze.
- Dos están **en descenso**. Publicarlos contradice la pregunta del reto ("temas que más están
  creciendo"); se dejan en `find_angle`.

### Límites

n = 20, un etiquetador que es un modelo y que vio las reglas de §7, un solo día de datos,
referencia externa de un solo canal. Es evidencia direccional, no una validación.
