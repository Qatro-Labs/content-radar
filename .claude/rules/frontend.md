---
paths:
  - "frontend/**"
---

# Frontend — vistas y dirección visual

Complementa a `CLAUDE.md` §9 (stack) y a `.claude/rules/engineering-standards.md` §9 (código Vue).
Antes de tocar UI, lee `DESIGN.md`.

## Tres vistas

1. **Discover (Radar):** gráfico de burbujas de ECharts como protagonista y ranking sincronizado.
   - **Arranca sin tema seleccionado** (D2, 17/10). El panel lateral muestra «Esta semana» (los temas de «Publicar
     ya»); al elegir una burbuja o una fila pasa a la vista previa del tema, y "Ver expediente" abre
     `/explore/:id`. Ninguna vista pide «elige algo».
   - X = audience fit · Y = momentum · tamaño = evidence strength (normalizado) · color = lifecycle.
   - Cuadrante superior derecho = prioridad. Filtros: periodo y los contadores-filtro de la cabecera (Publicar ya ·
     Acelerando · Emergentes · Sin etapa), todos en la URL. El ranking lleva mini barras de 6 días (`/timeline`).
   - Ranking (D6, 17/10): Puesto · Tema · Etapa (badge con `lifecycle_reason` en el tooltip) · 6 días ·
     Aceleración (↑ +80 %, con Observado · Estimado · Preliminar) · Oportunidad. Se ordena por oportunidad;
     el orden por aceleración se pide por URL (`sort=acceleration`, lo usa el agente) y no tiene botón. Si
     una métrica falta, la UI lo dice; no la rellena.
   - Avisar de forma visible desde cuándo se monitorea (primer snapshot: 17/10 ~02:50 UTC) para que
     nadie lea los periodos largos como historial medido.
   - **Rad, el agente del Radar** (artboards E y «Rad», 17–18/10): una barra de pregunta fija abajo en
     Radar, Explorar y el expediente. Rad responde moviendo la página: pulsa los mismos filtros,
     resalta, selecciona, abre el expediente y señala sus secciones, y busca piezas en Explorar, con una
     presencia que viaja hasta cada objetivo antes de actuar. Se puede charlar: cada pregunta lleva las
     anteriores, los temas citados y lo que se ve (nunca las respuestas del modelo). Sus acciones cambian
     la URL igual que los controles, así que una vista de Rad se puede compartir y repetir. El frontend
     no llama al LLM ni al MCP: consume el stream de eventos del backend (`useRadarAgent`). Componentes
     y movimiento en `DESIGN.md` §4 y §7.
2. **Explore (Evidencia):** dos estados, los dos con contenido propio.
   - **Sin tema (`/explore`): «Lo que está funcionando».** Todas las piezas de todos los temas: tabla ordenada por
     rendimiento frente a su canal (outliers primero; sin gráfico de dispersión, descartado el 17/10) y panel lateral
     («Dónde está funcionando» o el detalle de la pieza, con enlace a su tema). Necesita un endpoint de piezas de todos los temas;
     mientras no exista, se monta con `/evidence` de cada oportunidad.
   - **Con tema (`/explore/:id`): el expediente** (artboard I). "Cómo se compone" (`score_breakdown`) · timeline de
     la ventana actual frente a la anterior con su confianza · "Por qué importa" completo · criterios de encaje con
     citas que resaltan su evidencia · **barra apilada de `audience_mix`** · evidencia por plataforma (enlaces
     originales, fechas, métricas, velocidad y **badge de outlier `6.1×`** con la barra 1×/3×; outliers primero) ·
     **qué no podemos saber** · "Generar brief".
3. **Create (Content Studio, P1):** oportunidad + plataforma + objetivo + formato → brief (ángulo,
   gancho, estructura, evidencias, por qué encaja). Se puede copiar. No es un editor.

P2: Topic Network con Vue Flow (`@vue-flow/core`) y animaciones avanzadas.

## Dirección visual

Definida en [`DESIGN.md`](../../DESIGN.md) (aprobada el 17/10). "Intelligence platform", no un admin
dashboard. **Tema claro:** lienzo gris pálido, tarjetas blancas sin borde ni sombra, tinta casi negra y
un único acento (lima señal) usado solo como relleno; el color de etapa, solo para estados. Los
gráficos son el centro de la interfaz. Jerarquía: **score → evolución → explicación → acción**.
Ningún gráfico decorativo. El coste de operación no se muestra en la UI.

**Regla de efectos:** como mucho un efecto llamativo por vista. En el Radar es el escaneo (barrido al
cargar y ping al seleccionar). El latido de las burbujas codifica la aceleración: solo late lo que
crece. Lo demás son microinteracciones que siguen a la selección. Mientras el agente actúa, el efecto
es su presencia, y el barrido solo vuelve a pasar cuando el agente lee datos. Ningún efecto puede tapar
los datos ni bajar el rendimiento. Detalle en `DESIGN.md` §7.

## Librerías y recursos de UI

| Uso | Recurso | Cómo se usa |
|---|---|---|
| Componentes base | [shadcn-vue](https://www.shadcn-vue.com) | Sistema principal; se instalan con su CLI y el código queda en `components/ui/` |
| Tema / tokens | `DESIGN.md` §11 · [tweakcn](https://tweakcn.com/) | Los valores están en `DESIGN.md`; tweakcn solo para ajustar el tema claro de shadcn-vue |
| Componentes animados | [Inspira UI](https://inspira-ui.com), [Vue Bits](https://vue-bits.dev) | Pocos y con intención (regla de efectos). Copiar el componente al repo, no instalar librerías enteras |
| Animación | `<Transition>` / `<TransitionGroup>`; `motion-v` si no alcanza | Transiciones de panel, selección y entrada de listas |
| Gráficos | ECharts con `vue-echarts` | Única librería de charts durante la hackathon |
| Utilidades de composición | `@vueuse/core` (v14, la misma copia que Reka UI) | Tamaño de elementos, movimiento reducido, transiciones numéricas, portapapeles |

Referencias de inspiración para el equipo (galerías, bloques de React como referencia visual,
assets): `docs/design-resources.md`.

## Diseñar con agentes

- `DESIGN.md` en la raíz (formato DESIGN.md de Google Stitch: paleta, tipografía, espaciado, radios,
  estados y tono). Referencias: [designmd.supply](https://www.designmd.supply/) y
  [typeui.sh](https://www.typeui.sh/).
- Skills de [taste-skill](https://www.tasteskill.dev/) instaladas en `.claude/skills/` (revisadas el
  17/10): `minimalist-ui`, `stitch-design-taste` (regenera `DESIGN.md`) y `design-taste-frontend`
  (solo landing o pitch: su autor la excluye de dashboards).
- Otras skills útiles: `frontend-design` e [impeccable](https://impeccable.style/) contra el diseño
  genérico, y
  [emilkowalski/skills](https://github.com/emilkowalski/skills) (`/apple-design`,
  `/animation-performance`) para el pulido final.
- Si alguien tiene acceso, el MCP de Mobbin sirve para comparar pantallas con referencias reales.
- Antes de instalar una skill o un MCP de terceros, revisar su contenido.
