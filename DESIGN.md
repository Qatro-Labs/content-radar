# Design System: 30X Signal

> Fuente de verdad visual del frontend (formato DESIGN.md de Google Stitch). Se lee antes de tocar UI.
> Las vistas y su contenido están en `.claude/rules/frontend.md`; el stack, en `CLAUDE.md` §9.
> Referencia aprobada el 17/10: artboard **D · Claro (A + C)** del canvas
> [30X Signal — Direcciones visuales](https://claude.ai/artifact/BVjFhXdfVVXrpB2yucQmsT) (privado: pedir acceso).
> Los datos del canvas son de ejemplo.

## 1. Atmósfera

Instrumento de precisión sobre papel claro. Una sala de control de datos editoriales, pero luminosa: tinta casi negra
sobre gris muy pálido, tarjetas blancas y un único color de señal, un lima de rotulador, que marca lo que merece
publicarse. El radar es el protagonista; todo lo demás explica lo que el radar muestra.

- **Densidad 6 · "Daily App Balanced".** Denso donde hay datos (ranking, panel de detalle), aireado alrededor.
- **Variación 4 · "Offset Asymmetric".** Rejilla estable de producto, con bloques de ancho desigual (radar 2:1 panel).
- **Movimiento 5 · "Fluid CSS".** Un solo efecto llamativo por vista (en el Radar: el barrido y el ping); el resto
  son microinteracciones que siguen a la selección.

Jerarquía de lectura en cada pantalla: **score → evolución → explicación → acción**.

Linaje: de la dirección A (Mission Control) se quedan los cuadrantes con nombre, la mira con lectura en los ejes,
el ranking denso, los contadores y "Qué no sabemos". De la C (Liquid Signal) se quedan las tarjetas redondeadas, la
tipografía display con carácter, el anillo de score, la tarjeta flotante sobre el radar y "Para quién importa"
con lectura en una frase. De ninguna: monoespaciada decorativa, glows, cristal ni gradientes.

## 2. Paleta y roles

Una sola familia de grises fríos (sin mezclar con grises cálidos). Nunca negro puro.

**Base**
- **Lienzo** (#F2F3F5) — fondo de la página.
- **Superficie** (#FFFFFF) — tarjetas, panel, tabla, tooltips.
- **Superficie hundida** (#F6F7F8) — baldosas dentro de una tarjeta (stats), hover de filas.
- **Fondo del gráfico** (#F7F8F9) — área del radar.
- **Pista** (#ECEEF1) — fondo de barras y del anillo de score.
- **Control** (#E6E8EB) — pista de los segmented controls sobre el lienzo; dentro de una tarjeta, #F2F3F5.
- **Línea de dato** (#E2E5E9) — solo ejes y líneas medias del radar. **Línea de tabla** (#EEF0F2) — solo filas del ranking.

**Tinta**
- **Tinta** (#121418) — texto principal, botón primario, anillo de score, barras de score y selección.
- **Tinta de lectura** (#22262C) — párrafos largos ("Por qué importa").
- **Tinta suave** (#3D434C) — texto secundario y celdas de tabla.
- **Etiqueta** (#4A505A) — etiquetas de controles y de métricas.
- **Apagado** (#626873) — metadatos, ejes, nota al pie. Mínimo para texto: no usar grises más claros.

**Señal (único acento)**
- **Lima señal** (#C6F432) — solo como **relleno bajo tinta**: "Publicar ya", cuadrante "Prioridad", fila
  seleccionada, segmento "En español" de "Para quién importa", marca del logo. Nunca como texto ni como línea fina
  sobre blanco (no tiene contraste).
- **Lavado de señal** (rgba(198, 244, 50, 0.16)) — cuadrante "Prioridad". Fila seleccionada: 0.18.

**Etapa del ciclo de vida** (son estados, no acentos; se distinguen también por luminosidad)

| Etapa | Relleno (burbuja) | Trazo (ping, latido) | Fondo del chip | Texto del chip |
|---|---|---|---|---|
| Emergente | #3D7BFF | #3D7BFF | #E8F0FF | #1D4FC4 |
| Acelerando | #B5E61D | #6E8F00 | #EEF9CC | #3C5A00 |
| En pico | #FF9A3C | #E07A14 | #FFF0E0 | #9A4A00 |
| Saturado | #F0565C | #F0565C | #FDE8E9 | #B0262C |
| Sin etapa | hueco (blanco) | #8A919C discontinuo | #F0F1F3 | #50565F |

**Otros roles**
- **Aviso** (#FFF4E5, texto #8A4B00) — bloque "Qué no sabemos". Chip "Datos de ejemplo": #FFF0DC / #8A4B00.
- **Negativo** (#B0262C) — aceleración negativa, "Descartar" (fondo #FDE8E9).
- **Neutro de acción** (#F0F1F3, texto #22262C) — "Buscar ángulo" y "Esperar caso".
- **Saturación** (#FF9A3C) — barra de saturación (es una alerta suave, no un logro).
- **Audiencia** — Tech #121418 · Negocio #8A919C · En español = Lima señal.

## 3. Tipografía

Dos familias, las dos sans. Sin serif y sin monoespaciada en la interfaz (la mono solo para código real, por
ejemplo un snippet de conexión MCP).

- **Display: Bricolage Grotesque** (600; 700 solo en la marca). Títulos y números grandes. Tracking −0.02 a −0.04em,
  interlineado 1.0–1.1. Paquete: `@fontsource-variable/bricolage-grotesque`.
- **UI y texto: Geist** (400, 500, 600). Todo lo demás. Paquete: `@fontsource-variable/geist`.
- **Cifras tabulares siempre** (`font-variant-numeric: tabular-nums`) para que las columnas y los contadores no bailen.

| Uso | Familia | Tamaño / interlineado | Peso | Tracking |
|---|---|---|---|---|
| H1 de vista | Bricolage | `clamp(2.25rem, 4vw, 3.5rem)` / 1.0 | 600 | −0.04em |
| Tema seleccionado (panel) | Bricolage | 30px / 1.08 | 600 | −0.03em |
| Título de tarjeta | Bricolage | 20–22px / 1.2 | 600 | −0.02em |
| Número grande (score, contadores) | Bricolage | 36–38px / 1.0 | 600 | −0.03 a −0.04em |
| Número de baldosa | Bricolage | 20–28px / 1.1 | 600 | −0.02em |
| Frase destacada | Geist | 17–18px / 1.55 | 400 | 0 |
| Texto base | Geist | 15px / 1.5 | 400–500 | 0 |
| Secundario, celdas | Geist | 14px / 1.5 | 400–500 | 0 |
| Chips, ejes, metadatos | Geist | 12–13px / 1.4 | 500–600 | 0 |

- Siempre en minúscula de oración ("Para quién importa"), nunca en mayúsculas con tracking.
- Títulos de dos líneas como máximo; ancho de lectura de párrafo ≤ 720px (~65 caracteres).
- **Prohibidas:** Inter, Roboto, Arial, Open Sans, cualquier serif, y la monoespaciada como "voz técnica".

## 4. Componentes

Base: **shadcn-vue** (sobre Reka UI), restyled con los tokens de §11. Iconos: `@lucide/vue` (stack fijado en
`CLAUDE.md` §9), trazo 1.75–2, 16/20px, color Tinta suave; solo cuando un icono dice algo que el texto no dice.

- **Tarjeta:** blanca sobre el lienzo, radio 20px, padding 20–24px, **sin borde y sin sombra**: la separación es el
  cambio de tono. Las baldosas internas: #F6F7F8, radio 14px.
- **Botón primario:** fondo Tinta, texto blanco, radio 12px, alto ≥ 46px, peso 600. Hover #2A2E35; active
  `scale(0.98)`. Nombre del botón = la acción ("Generar brief"). Un primario por panel.
- **Botón secundario:** fondo #F2F3F5, texto Tinta; hover #E8EAED. Sin contornos.
- **Segmented control** (periodo, orden): pista #E6E8EB (o #F2F3F5 dentro de una tarjeta), radio 12px, padding 4px;
  segmento activo blanco, peso 600; inactivo transparente, Etiqueta. Alto del segmento ≥ 36px dentro de una pista de 44px.
- **Navegación:** barra plana, sin cristal ni píldora flotante: marca a la izquierda, tres vistas (Radar · Explorar
  · Crear), periodo y estado de datos a la derecha. Vista activa: fondo blanco, radio 10px.
- **Chip de etapa:** píldora, fondo y texto según §2, punto de 8px con el relleno (o trazo discontinuo en "Sin
  etapa"). Siempre con texto, nunca solo color.
- **Chip de recomendación:** radio 8–10px, peso 600. "Publicar ya" en Lima señal; "Buscar ángulo" y "Esperar caso" en
  neutro; "Descartar" en negativo.
- **Badge de outlier:** "6,1×" en Lima señal con texto Tinta (Explorar, lista de evidencias; outliers primero).
- **Badge de evidencia:** "Observado" · "Estimado" · "Preliminar" en neutro, siempre visible junto al dato.
- **Anillo de score:** 112px, trazo 9px, Tinta sobre Pista, número Bricolage 38px en el centro y "de 100" debajo.
- **Barra de métrica:** alto 6px, radio completo, Pista + relleno (Tinta; Saturación en naranja). Etiqueta a la
  izquierda (120px), valor a la derecha con banda cuando aplica ("Alto · 82").
- **Barra apilada "Para quién importa":** alto 12px, radio completo, 3px entre segmentos; debajo, tres cifras
  grandes con su leyenda y una frase de lectura.
- **"Qué no sabemos":** bloque Aviso con título en negrita y la limitación. Obligatorio en todo detalle.
- **Contador (KPI):** baldosa blanca radio 16px, cifra Bricolage 36px y etiqueta en frase ("acelerando").
- **Tooltip / tarjeta flotante del radar:** blanca, radio 14px, la única con sombra (§5). Chip de etapa, tema,
  "Oportunidad 79 · ↑ +80 %".
- **Tabla de ranking:** filas de 56px con línea #EEF0F2; hover #F6F7F8; seleccionada en lavado de señal y puesto en
  negrita. Columnas: Puesto · Tema · Etapa · Aceleración · Outliers · Fuentes · Oportunidad (barra + cifra) · Acción.
- **Carga:** skeletons con la forma exacta del contenido (#ECEEF1 → #F2F3F5, 1.6s). Nada de spinners circulares.
- **Vacío:** si hay menos oportunidades que las esperadas, se muestran las que hay y una frase que explica por qué
  ("Hay 7 temas con datos suficientes esta semana"). Nunca se rellena.
- **Error:** inline, en la tarjeta afectada, con qué falló y qué sigue funcionando.
- **Foco:** anillo de 2px en Tinta con 2px de separación, siempre visible al navegar con teclado.

## 5. Layout, espaciado y elevación

- Contenedor máximo **1440px**, gutter 32px (16px en móvil). Base de 4px; huecos de 16px entre tarjetas, 8px entre
  baldosas, 20px dentro del panel de detalle.
- **Radar (Discover):** cabecera (H1 + frase a la izquierda, contadores a la derecha) → fila principal con el radar
  (`flex: 999 1 680px`) y el panel de detalle (`flex: 1 1 380px`) a la misma altura → fila bento "Para quién importa"
  (1) + "Por qué importa" (2) → ranking a todo el ancho → nota al pie de metodología.
- **Radios:** 20px tarjetas · 16px contadores · 14px baldosas, gráfico y tooltip · 12px botones y pistas · 9–10px
  segmentos y enlaces de navegación · 8px chips de acción · completo en chips de estado y barras.
- **Elevación:** nada en reposo lleva sombra. Solo lo que flota: tooltip del radar, popovers y diálogos
  (`0 14px 32px -10px rgba(18, 20, 24, 0.22), 0 2px 6px rgba(18, 20, 24, 0.06)`). Los diálogos, sobre un velo
  rgba(18, 20, 24, 0.4).
- **Líneas:** solo donde son dato (ejes y líneas medias del radar) o tabla (filas del ranking). En el resto, tono y
  espacio.

## 6. Responsive

- **< 768px:** todo a una columna (el panel de detalle baja bajo el radar; la fila bento se apila). La navegación y
  los controles hacen wrap; la marca y el periodo quedan arriba.
- La página nunca hace scroll horizontal. El ranking sí puede, **dentro de su tarjeta** (`overflow-x: auto`, ancho
  mínimo 1000px), como cualquier tabla ancha.
- El radar mantiene 16:9 con un alto mínimo de 300px; en móvil las etiquetas de burbuja se ocultan y queda la
  tarjeta flotante de la selección.
- Títulos con `clamp()`; texto nunca por debajo de 14px (12px solo en lecturas de ejes).
- Objetivos táctiles ≥ 44px. Altura completa con `min-h-[100dvh]`, nunca `h-screen`.

## 7. Movimiento

**Regla de efectos (de `frontend.md`):** como mucho un efecto llamativo por vista, y nunca tapa los datos. En el
Radar ese efecto es el **escaneo**; todo lo demás es discreto y sigue a la acción del usuario.

**Curvas y tiempos**
- UI: `cubic-bezier(0.16, 1, 0.3, 1)` (ease-out). Rebote solo en la aparición de burbujas: `cubic-bezier(0.34, 1.4, 0.64, 1)`.
  Barrido: lineal.
- 150ms hover · 200–320ms selección y desplazamientos · 420ms barras · 480ms aparición de burbuja · 1100ms ping ·
  1800ms barrido.

**Radar**
- **Barrido al cargar y al cambiar de periodo:** un haz pivota en la esquina "Prioridad" (de 170° a 290°, 1.8s,
  0.2s de retardo) con una estela del lavado de señal. Cada burbuja aparece (escala 0.2 → 1 con rebote) cuando el
  haz cruza su ángulo, así que se "detecta" como en un radar.
- **Ping al seleccionar:** tres ondas del trazo de la etapa, 1.1s, escaladas ×4.6, separadas 160ms. En la primera
  carga, la seleccionada hace ping cuando el haz la detecta.
- **Latido con significado:** solo laten los temas que crecen, y la frecuencia codifica la aceleración. La nota al
  pie lo dice ("las burbujas que laten están creciendo").

  | Aceleración | Periodo del latido |
  |---|---|
  | ≥ 1.0 (+100 %) | 1.4s |
  | ≥ 0.5 | 2.0s |
  | > 0.2 | 2.8s |
  | > 0 | 3.6s |
  | ≤ 0, sin dato o "Sin etapa" | estática |

- **Selección:** la mira, las lecturas de los ejes y la tarjeta flotante se deslizan a la nueva burbuja (320ms).
- **Hover enlazado:** fila del ranking ↔ burbuja del radar se resaltan mutuamente.
- Burbuja: hover `scale(1.12)`, active `scale(0.94)`.

**Panel y listas**
- El anillo de score se dibuja al cargar (1.1s) y la cifra cuenta hasta el nuevo valor al cambiar de selección (450ms).
- Barras de métrica y de audiencia crecen hasta su valor (420ms); textos del panel con fundido y 4px de subida (300ms).
- Ranking: entrada escalonada de 40ms por fila y barras de score que crecen.

**Implementación**
- El latido es nativo de ECharts: serie `effectScatter` con `rippleEffect.period` calculado desde `acceleration` y
  `brushType: 'stroke'`. El ping, un `effectScatter` temporal o `graphic`. El barrido, una capa CSS sobre el canvas.
- Fuera del gráfico, `<Transition>` / `<TransitionGroup>` y CSS; `motion-v` solo si no alcanza.
- Solo `transform` y `opacity` (barras con `scaleX` y `transform-origin: left`). Nada de animar `top`, `left`,
  `width` o `height` en producción.
- **`prefers-reduced-motion: reduce`:** sin barrido, ping, latido ni entradas; los datos aparecen al instante. Se
  mantiene el feedback de hover y active.
- Nada de bucles infinitos fuera del latido. Nada de puntos "live" que parpadean.

## 8. Gráficos (ECharts + `vue-echarts`)

Única librería de charts. Ningún gráfico decorativo: si no responde una pregunta del usuario, no va.

- **Radar de oportunidades (bubble):** X = `audience_fit_score` (0–100) · Y = `momentum_score` (0–100) · tamaño =
  `evidence_strength` (normalizado; `18 + 0.34·s` px) · color = `lifecycle` (relleno de §2, borde blanco de 2px;
  "Sin etapa" hueco con trazo discontinuo). Seleccionada: +6px y anillo de Tinta de 2px separado por 2px de blanco.
- Líneas medias en 50/50 (#E2E5E9) que forman cuatro cuadrantes con nombre: **Prioridad** (arriba a la derecha, con
  lavado de señal, en Tinta 600) · Momentum sin encaje · Encaje sin momentum · Poca señal (en Apagado).
- Mira de la selección: líneas de Tinta al 28 % hasta los ejes y dos lecturas en píldora de Tinta con texto blanco.
- **Timeline (Explorar):** barras por día; ventana actual en Tinta, ventana anterior en #C9CED6, con su badge de evidencia.
- **Tipografía en ECharts:** `textStyle.fontFamily = 'Geist'`, 12–13px, color Apagado. Sin títulos ni leyendas
  internas de ECharts: la leyenda es HTML (chips de etapa) para que sea accesible.
- Cada gráfico tiene una alternativa textual (el ranking es la del radar).

## 9. Texto y datos en pantalla

- UI en español; código en inglés. Frase corta y concreta, sin clichés ("potencia", "revoluciona", "sin fricción").
- Formato: decimales con coma ("6,1×"), espacio antes de % ("+80 %"), flechas ↑ ↓ → para la aceleración, fechas
  "17/10, 02:50 UTC".
- **Etiquetas fijas:** Emergente · Acelerando · En pico · Saturado · Sin etapa | Publicar ya · Buscar ángulo ·
  Esperar caso · Descartar | Observado · Estimado · Preliminar | confianza alta · media · baja.
- **Banda de encaje:** Alto ≥ 67 · Medio ≥ 34 · Bajo < 34 (umbrales iniciales, ajustables con Melkin). Se muestra la
  banda junto a la cifra, no la cifra sola.
- **Honestidad de datos** (`CLAUDE.md` §2): un dato ausente se escribe "no disponible", nunca 0 ni guion. Si hay 7
  oportunidades, se muestran 7. La confianza va aparte del score. Cada detalle lleva "Qué no sabemos". La
  saturación se rotula "dentro de las fuentes monitoreadas" y el encaje "evaluación editorial, no una medición". El
  segmento `latam_es` se rotula "En español". Visible siempre: desde cuándo se monitorea ("Datos desde el 17/10,
  02:50 UTC").
- Cualquier dato de ejemplo lleva el chip "Datos de ejemplo".
- **El coste de operación no aparece en la interfaz** (como mucho, un enlace discreto). Se consulta bajo demanda
  por `GET /costs` y la tool MCP `get_operating_cost` (PR #12).

## 10. Anti-patrones (prohibidos)

- Tema oscuro (por ahora la app es solo clara).
- Monoespaciada decorativa, etiquetas pequeñas en mayúsculas con tracking, eyebrows sobre los títulos.
- Numeración índice tipo 01 / 02 / 03 (el puesto del ranking es un dato y se escribe "1").
- Líneas finas, cajas con contorno de 1px, retículas, marcas de corte o miras decorativas (la mira del radar es dato).
- Gradientes en fondos, botones o texto. Única excepción: la estela transitoria del barrido.
- Sombras en reposo, glows, cristal / backdrop blur, navegación en píldora flotante.
- Lima señal como texto o línea fina sobre blanco.
- Morado / índigo, crema con terracota, negro puro (#000000), acentos saturados de neón.
- Emojis, Inter / Roboto / Arial, cualquier serif.
- Más de un efecto llamativo por vista; bucles infinitos que no codifican un dato; puntos "live" parpadeantes.
- Filas de tres tarjetas idénticas con icono; dashboards falsos de barras grises.
- Métricas inventadas, cifras redondas de relleno, 0 en lugar de "no disponible", el panel de coste.

## 11. Tokens (Tailwind v4 + shadcn-vue)

Variables CSS en `src/assets/main.css`. El bloque `@theme inline` que genera la CLI de shadcn-vue mapea las
variables base; aquí van los valores y los tokens propios. Ojo: en shadcn, `--accent` es el fondo de hover de menús,
no el acento de marca; el acento de marca es `--signal`.

```css
:root {
  --background: #F2F3F5;
  --foreground: #121418;
  --card: #FFFFFF;
  --card-foreground: #121418;
  --popover: #FFFFFF;
  --popover-foreground: #121418;
  --primary: #121418;
  --primary-foreground: #FFFFFF;
  --secondary: #F2F3F5;
  --secondary-foreground: #121418;
  --muted: #F6F7F8;
  --muted-foreground: #626873;
  --accent: #F2F3F5;
  --accent-foreground: #121418;
  --destructive: #B0262C;
  --border: #E6E8EB;
  --input: #E6E8EB;
  --ring: #121418;
  --radius: 0.75rem;

  --signal: #C6F432;
  --signal-foreground: #121418;
  --signal-wash: rgb(198 244 50 / 0.16);
  --ink-soft: #3D434C;
  --track: #ECEEF1;
  --sunken: #F6F7F8;
  --plot: #F7F8F9;
  --notice: #FFF4E5;
  --notice-foreground: #8A4B00;

  --lc-emerging: #3D7BFF;      --lc-emerging-bg: #E8F0FF;      --lc-emerging-fg: #1D4FC4;
  --lc-accelerating: #B5E61D;  --lc-accelerating-stroke: #6E8F00;
  --lc-accelerating-bg: #EEF9CC; --lc-accelerating-fg: #3C5A00;
  --lc-peaking: #FF9A3C;       --lc-peaking-stroke: #E07A14;
  --lc-peaking-bg: #FFF0E0;    --lc-peaking-fg: #9A4A00;
  --lc-saturated: #F0565C;     --lc-saturated-bg: #FDE8E9;     --lc-saturated-fg: #B0262C;
  --lc-unknown: #8A919C;       --lc-unknown-bg: #F0F1F3;       --lc-unknown-fg: #50565F;

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-pop: cubic-bezier(0.34, 1.4, 0.64, 1);
  --shadow-float: 0 14px 32px -10px rgb(18 20 24 / 0.22), 0 2px 6px rgb(18 20 24 / 0.06);
}

@theme inline {
  --font-sans: 'Geist Variable', system-ui, sans-serif;
  --font-display: 'Bricolage Grotesque Variable', 'Geist Variable', sans-serif;
  --color-signal: var(--signal);
  --color-signal-foreground: var(--signal-foreground);
  --color-ink-soft: var(--ink-soft);
  --color-track: var(--track);
  --color-sunken: var(--sunken);
  --color-notice: var(--notice);
  --color-notice-foreground: var(--notice-foreground);
  --radius-card: 1.25rem;
  --radius-tile: 0.875rem;
  --shadow-float: var(--shadow-float);
}
```

Los colores de etapa los consume ECharts desde `src/lib/lifecycle.ts` (un mapa `lifecycle → { fill, stroke, bg, fg, label }`
que lee estas variables), para que el radar, los chips y la leyenda usen la misma fuente.
