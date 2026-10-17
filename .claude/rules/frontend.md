---
paths:
  - "frontend/**"
---

# Frontend — vistas y dirección visual

Complementa a `CLAUDE.md` §9 (stack) y a `.claude/rules/engineering-standards.md` §9 (código Vue).
Antes de tocar UI, lee `DESIGN.md`.

## Tres vistas

1. **Discover (Radar):** gráfico de burbujas de ECharts como protagonista y ranking sincronizado.
   - X = audience fit · Y = momentum · tamaño = evidence strength (normalizado) · color = lifecycle.
   - Cuadrante superior derecho = prioridad. Filtros: periodo, lifecycle, confianza, tema, segmento.
   - En el ranking, cada fila muestra la etapa (badge con `lifecycle_reason` en el tooltip), la
     aceleración (↑ +80 %) y el nº de outliers. Ordenar por aceleración, no por volumen. Si una
     métrica falta, la UI lo dice; no la rellena.
   - Avisar de forma visible desde cuándo se monitorea (primer snapshot: 17/10 ~02:50 UTC) para que
     nadie lea los periodos largos como historial medido.
2. **Explore (Evidencia):** timeline de velocidad del tema (barras por día, ventana actual vs.
   anterior) con su confianza · **barra apilada de `audience_mix`** (para quién importa) · Evidence
   Explorer por plataforma (enlaces originales, fechas, métricas, velocidad y **badge de outlier
   `6.1×`**; outliers primero) · AI Insights (por qué funciona, patrones, **qué no podemos saber**,
   encaje con 30X).
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
crece. Lo demás son microinteracciones que siguen a la selección. Ningún efecto puede tapar los datos
ni bajar el rendimiento. Detalle en `DESIGN.md` §7.

## Librerías y recursos de UI

| Uso | Recurso | Cómo se usa |
|---|---|---|
| Componentes base | [shadcn-vue](https://www.shadcn-vue.com) | Sistema principal; se instalan con su CLI y el código queda en `components/ui/` |
| Tema / tokens | `DESIGN.md` §11 · [tweakcn](https://tweakcn.com/) | Los valores están en `DESIGN.md`; tweakcn solo para ajustar el tema claro de shadcn-vue |
| Componentes animados | [Inspira UI](https://inspira-ui.com), [Vue Bits](https://vue-bits.dev) | Pocos y con intención (regla de efectos). Copiar el componente al repo, no instalar librerías enteras |
| Animación | `<Transition>` / `<TransitionGroup>`; `motion-v` si no alcanza | Transiciones de panel, selección y entrada de listas |
| Gráficos | ECharts con `vue-echarts` | Única librería de charts durante la hackathon |

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
