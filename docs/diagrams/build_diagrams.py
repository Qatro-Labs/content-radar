# ruff: noqa: E501 (textos de los diagramas, en una línea para poder editarlos)
"""Genera los diagramas SVG de docs/diagrams/ (solo stdlib).

    python3 docs/diagrams/build_diagrams.py

Los SVG se ven en GitHub como <img>: sin webfonts, con fondo propio para el modo oscuro y con una
pila de fuentes del sistema. El ancho de texto se estima (no hay métricas), así que el ajuste de
línea es conservador.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from pathlib import Path

from icons import ICONS

OUT = Path(__file__).parent
WIDTH = 1200
MARGIN = 40

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

INK = "#1f2328"
MUTED = "#57606a"
LINE = "#d0d7de"
BG = "#ffffff"

# Un color por actor: así se lee de un vistazo quién calcula, quién juzga y quién redacta.
TONES = {
    "neutral": ("#f6f8fa", "#d0d7de", "#1f2328"),
    "python": ("#ddf4ff", "#54aeff", "#0550ae"),
    "jev": ("#fbefff", "#c297ff", "#6639ba"),
    "llm": ("#fff1e5", "#fb8f44", "#953800"),
    "data": ("#dafbe1", "#4ac26b", "#116329"),
    "client": ("#fff8c5", "#d4a72c", "#7d4e00"),
}

TITLE = 30
SUB = 17
HEAD = 19
BODY = 16
SMALL = 15
LEAD = 1.45


def char_w(size: int, mono: bool = False) -> float:
    return size * (0.62 if mono else 0.52)


def wrap(text: str, width: float, size: int, mono: bool = False) -> list[str]:
    limit = max(8, int(width / char_w(size, mono)))
    words, lines, cur = text.split(), [], ""
    for word in words:
        nxt = f"{cur} {word}".strip()
        if len(nxt) <= limit or not cur:
            cur = nxt
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


@dataclass
class Svg:
    height: float = 0
    parts: list[str] = field(default_factory=list)

    def add(self, s: str) -> None:
        self.parts.append(s)

    def text(
        self,
        x: float,
        y: float,
        s: str,
        size: int = BODY,
        color: str = INK,
        weight: int = 400,
        mono: bool = False,
        anchor: str = "start",
    ) -> None:
        family = MONO if mono else SANS
        self.add(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(s)}</text>'
        )

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str,
        stroke: str,
        r: int = 12,
        dash: bool = False,
    ) -> None:
        d = ' stroke-dasharray="6 5"' if dash else ""
        self.add(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"{d}/>'
        )

    def arrow(self, x1: float, y1: float, x2: float, y2: float, label: str | None = None) -> None:
        self.add(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{MUTED}" '
            f'stroke-width="2" marker-end="url(#arrow)"/>'
        )
        if label:
            lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
            w = len(label) * char_w(SMALL) + 18
            if x1 == x2:
                self.rect(lx + 10, ly - 15, w, 28, BG, LINE, r=14)
                self.text(lx + 19, ly + 5, label, SMALL, MUTED)
            else:
                self.rect(lx - w / 2, ly - 34, w, 28, BG, LINE, r=14)
                self.text(lx, ly - 15, label, SMALL, MUTED, anchor="middle")

    def render(self, title: str, desc: str) -> str:
        h = self.height
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{h:.0f}" '
            f'viewBox="0 0 {WIDTH} {h:.0f}" role="img" aria-labelledby="t d">'
            f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>'
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
            f'markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{MUTED}"/>'
            "</marker></defs>"
            f'<rect width="{WIDTH}" height="{h:.0f}" fill="{BG}"/>'
        )
        return head + "".join(self.parts) + "</svg>\n"


Line = str | tuple[str, str]  # texto, o (estilo, texto) con estilo "mono" | "muted" | "bold"


def lines_height(lines: list[Line], width: float, size: int) -> float:
    total = 0.0
    for line in lines:
        style, s = line if isinstance(line, tuple) else ("", line)
        total += len(wrap(s, width, size, style == "mono")) * size * LEAD
    return total


def draw_lines(
    svg: Svg, x: float, y: float, lines: list[Line], width: float, size: int, color: str
) -> float:
    for line in lines:
        style, s = line if isinstance(line, tuple) else ("", line)
        mono = style == "mono"
        for part in wrap(s, width, size, mono):
            y += size * LEAD
            svg.text(
                x,
                y - size * 0.35,
                part,
                size - (1 if mono else 0),
                MUTED if style == "muted" else color,
                600 if style == "bold" else 400,
                mono,
            )
    return y


ICON_TILE = 38
ICON_GAP = 12


def title_width(w: float, badge: str | None, icon: str | None) -> float:
    inner = w - 36
    if badge:
        inner -= len(badge) * char_w(13) + 30
    if icon:
        inner -= ICON_TILE + ICON_GAP
    return inner


def title_bottom(y: float, title: str, w: float, badge: str | None, icon: str | None) -> float:
    lines = len(wrap(title, title_width(w, badge, icon), HEAD))
    bottom = y + 18 + lines * HEAD * 1.3
    if icon:
        bottom = max(bottom, y + 16 + ICON_TILE + 4)
    return bottom


def card_height(
    title: str, lines: list[Line], w: float, badge: str | None = None, icon: str | None = None
) -> float:
    top = title_bottom(0, title, w, badge, icon)
    return top + 4 + lines_height(lines, w - 36, BODY) + 20


def draw_icon(svg: Svg, x: float, y: float, name: str, stroke: str, accent: str) -> None:
    svg.rect(x, y, ICON_TILE, ICON_TILE, BG, stroke, r=10)
    scale = 22 / 24
    off = (ICON_TILE - 22) / 2
    svg.add(
        f'<g transform="translate({x + off:.1f} {y + off:.1f}) scale({scale:.4f})" fill="none" '
        f'stroke="{accent}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f"{ICONS[name]}</g>"
    )


def card(
    svg: Svg,
    x: float,
    y: float,
    w: float,
    title: str,
    lines: list[Line],
    tone: str = "neutral",
    h: float | None = None,
    badge: str | None = None,
    icon: str | None = None,
) -> float:
    fill, stroke, accent = TONES[tone]
    h = h or card_height(title, lines, w, badge, icon)
    svg.rect(x, y, w, h, fill, stroke)
    tx = x + 18
    title_lines = wrap(title, title_width(w, badge, icon), HEAD)
    ty = y + 14
    if icon:
        draw_icon(svg, x + 18, y + 16, icon, stroke, accent)
        tx += ICON_TILE + ICON_GAP
        if len(title_lines) == 1:
            ty = y + 16 + ICON_TILE / 2 - HEAD * 1.3 / 2 - 1
    for part in title_lines:
        ty += HEAD * 1.3
        svg.text(tx, ty - 4, part, HEAD, accent, 650)
    if badge:
        badge_w = len(badge) * char_w(13) + 22
        svg.rect(x + w - 18 - badge_w, y + 22, badge_w, 26, BG, stroke, r=13)
        svg.text(x + w - 18 - badge_w / 2, y + 40, badge, 13, accent, 600, anchor="middle")
    draw_lines(svg, x + 18, title_bottom(y, title, w, badge, icon) + 4, lines, w - 36, BODY, INK)
    return h


def header(svg: Svg, title: str, subtitle: str) -> float:
    svg.text(MARGIN, 58, title, TITLE, INK, 700)
    y = draw_lines(svg, MARGIN, 72, [("muted", subtitle)], WIDTH - 2 * MARGIN, SUB, MUTED)
    return y + 20


# ---------------------------------------------------------------------------------------------
# 1. Arquitectura


def architecture() -> None:
    svg = Svg()
    y = header(
        svg,
        "30X Signal · Componentes",
        "Los jobs recolectan y analizan; una sola capa de servicios sirve el mismo ranking al dashboard, al agente y a los asistentes de IA.",
    )
    y += 10
    full = WIDTH - 2 * MARGIN
    gap = 40

    h = card(
        svg,
        MARGIN,
        y,
        full,
        "Fuentes públicas",
        ["YouTube · Hacker News · medios y blogs (RSS) · TikTok · Reddit · Instagram"],
        "neutral",
        icon="globe",
    )
    y += h + 44
    third = (full - 2 * gap) / 3
    xs = [MARGIN + i * (third + gap) for i in range(3)]
    svg.arrow(xs[0] + third / 2, y - 44, xs[0] + third / 2, y - 2)
    specs = [
        (
            "Colectores",
            ["Leen cada fuente y guardan piezas y métricas públicas."],
            "python",
            "download",
        ),
        (
            "Motor de análisis",
            ["Agrupa las piezas en temas y calcula los scores."],
            "python",
            "cpu",
        ),
        (
            "Modelos de IA",
            ["Jev clasifica y verifica; el LLM evalúa y redacta."],
            "llm",
            "sparkles",
        ),
    ]
    h = max(card_height(t, ls, third, icon=ic) for t, ls, _, ic in specs)
    for x, (t, ls, tone, ic) in zip(xs, specs, strict=True):
        card(svg, x, y, third, t, ls, tone, h, icon=ic)
    svg.arrow(xs[2] - 2, y + h / 2, xs[1] + third + 2, y + h / 2)
    y += h + 44
    svg.arrow(xs[0] + third / 2, y - 44, xs[0] + third / 2, y - 2)
    svg.arrow(xs[1] + third / 2, y - 44, xs[1] + third / 2, y - 2)

    h = card(
        svg,
        MARGIN,
        y,
        full,
        "Base de datos",
        ["Piezas, métricas y cada ejecución del análisis con su ranking."],
        "data",
        icon="database",
    )
    y += h + 44
    svg.arrow(WIDTH / 2, y - 44, WIDTH / 2, y - 2)
    h = card(
        svg,
        MARGIN,
        y,
        full,
        "Servicios",
        ["La única lógica de negocio: todos los canales leen los mismos datos."],
        "python",
        icon="layers",
    )
    y += h + 44
    for x in xs:
        svg.arrow(x + third / 2, y - 44, x + third / 2, y - 2)
    specs = [
        ("API REST", ["Sirve oportunidades, evidencia y briefs al dashboard."], "python", "server"),
        ("Agente Rad", ["Responde preguntas sobre el Radar y mueve la vista."], "llm", "bot"),
        ("Servidor MCP", ["Las mismas consultas desde un asistente de IA."], "python", "plug"),
    ]
    h = max(card_height(t, ls, third, icon=ic) for t, ls, _, ic in specs)
    for x, (t, ls, tone, ic) in zip(xs, specs, strict=True):
        card(svg, x, y, third, t, ls, tone, h, icon=ic)
    y += h + 44
    half = (full - gap) / 2
    svg.arrow(xs[0] + third / 2, y - 44, xs[0] + third / 2, y - 2)
    svg.arrow(xs[1] + third / 2, y - 44, MARGIN + half - 60, y - 2)
    svg.arrow(xs[2] + third / 2, y - 44, xs[2] + third / 2, y - 2)
    specs = [
        (
            "Dashboard",
            ["Radar, exploración de evidencia y creación de briefs."],
            "client",
            "layout-dashboard",
        ),
        (
            "Asistentes de IA",
            ["Claude, ChatGPT o Grok, conectados por MCP."],
            "client",
            "message-square",
        ),
    ]
    h = max(card_height(t, ls, half, icon=ic) for t, ls, _, ic in specs)
    for i, (t, ls, tone, ic) in enumerate(specs):
        card(svg, MARGIN + i * (half + gap), y, half, t, ls, tone, h, icon=ic)
    svg.height = y + h + 40
    (OUT / "arquitectura.svg").write_text(
        svg.render(
            "30X Signal · Componentes",
            "Fuentes públicas, colectores, motor de análisis con modelos de IA, base de datos, "
            "servicios, API REST, agente Rad y servidor MCP, y los clientes: dashboard y asistentes de IA.",
        )
    )


# ---------------------------------------------------------------------------------------------
# 2. De la señal a la oportunidad


FLOW: list[tuple[str, str, str, str]] = [
    ("Señal", "radio", "Una pieza pública con sus métricas.", "¿Qué se publica?"),
    (
        "Tendencia",
        "trending-up",
        "Piezas parecidas agrupadas en un tema que crece.",
        "¿Qué está creciendo?",
    ),
    (
        "Oportunidad",
        "target",
        "El tema puntuado para la audiencia de 30X, con una recomendación.",
        "¿Vale la pena?",
    ),
    (
        "Evidencia",
        "file-search",
        "Las piezas que lo respaldan, enlazadas a su fuente.",
        "¿Por qué lo creemos?",
    ),
    ("Contenido", "pen-line", "Un brief con ángulo, gancho y estructura.", "¿Qué publicamos?"),
]


def flow() -> None:
    svg = Svg()
    y = header(
        svg,
        "30X Signal · De la señal al contenido",
        "Cada paso responde una pregunta. El dashboard y los asistentes de IA (por MCP) recorren los mismos pasos.",
    )
    y += 10
    gap = 28
    n = len(FLOW)
    w = (WIDTH - 2 * MARGIN - gap * (n - 1)) / n
    specs = [(name, icon, [what, ("bold", question)]) for name, icon, what, question in FLOW]
    h = max(card_height(t, ls, w, icon=ic) for t, ic, ls in specs)
    for i, (title, icon, lines) in enumerate(specs):
        x = MARGIN + i * (w + gap)
        card(svg, x, y, w, title, lines, "data" if i == n - 1 else "python", h, icon=icon)
        if i < n - 1:
            svg.arrow(x + w + 2, y + h / 2, x + w + gap - 2, y + h / 2)
    y += h + 28
    spans = [("Explorar", 0, 1), ("Radar", 1, 3), ("Expediente del tema", 3, 4), ("Crear", 4, 5)]
    svg.text(MARGIN, y + 20, "EN EL DASHBOARD", 14, MUTED, 700)
    y += 34
    for label, a, b in spans:
        x0 = MARGIN + a * (w + gap)
        x1 = MARGIN + b * (w + gap) - gap
        fill, stroke, accent = TONES["client"]
        svg.rect(x0, y, x1 - x0, 40, fill, stroke, r=10)
        svg.text((x0 + x1) / 2, y + 26, label, BODY, accent, 600, anchor="middle")
    svg.height = y + 40 + 40
    (OUT / "flujo-senal-oportunidad.svg").write_text(
        svg.render(
            "30X Signal · De la señal al contenido",
            "Cinco pasos: señal, tendencia, oportunidad, evidencia y contenido, con la pregunta que "
            "responde cada uno y la vista del dashboard donde se ve.",
        )
    )


# ---------------------------------------------------------------------------------------------
# 3. Pipeline de análisis


STEPS: list[tuple[str, str, str, str, str]] = [
    (
        "Clasificar",
        "tags",
        "jev",
        "Jev",
        "Decide si cada pieza trata de IA y etiqueta su formato y su gancho.",
    ),
    (
        "Agrupar",
        "group",
        "neutral",
        "Embeddings",
        "Une las piezas parecidas en temas, en español y en inglés.",
    ),
    (
        "Medir",
        "gauge",
        "python",
        "Python",
        "Velocidad, aceleración, outliers, saturación y fuentes independientes de cada tema.",
    ),
    (
        "Evaluar",
        "scale",
        "llm",
        "LLM",
        "Encaje del tema con la audiencia de 30X, en seis criterios.",
    ),
    (
        "Decidir",
        "list-ordered",
        "python",
        "Python",
        "Opportunity Score, confianza y recomendación.",
    ),
    (
        "Explicar",
        "shield-check",
        "llm",
        "LLM + Jev",
        "El LLM redacta por qué importa; Jev verifica cada afirmación.",
    ),
]


def pipeline() -> None:
    svg = Svg()
    y = header(
        svg,
        "30X Signal · Pipeline de análisis",
        "Velocidad, no popularidad. Python calcula todos los scores; los modelos de IA clasifican, evalúan y redactan.",
    )
    y += 10
    full = WIDTH - 2 * MARGIN
    h = card(
        svg,
        MARGIN,
        y,
        full,
        "Entrada",
        ["Piezas públicas de los últimos 14 días, con sus métricas."],
        "neutral",
        icon="inbox",
    )
    y += h
    for i, (name, icon, tone, who, what) in enumerate(STEPS, 1):
        svg.arrow(WIDTH / 2, y + 2, WIDTH / 2, y + 30)
        y += 32
        y += card(svg, MARGIN, y, full, f"{i} · {name}", [what], tone, badge=who, icon=icon)
    svg.arrow(WIDTH / 2, y + 2, WIDTH / 2, y + 30)
    y += 32
    h = card(
        svg,
        MARGIN,
        y,
        full,
        "Salida: ranking de oportunidades",
        [
            "Cada tema con su evidencia y una recomendación: publicar ya · buscar ángulo · esperar caso · descartar."
        ],
        "data",
        icon="trophy",
    )
    svg.height = y + h + 40
    (OUT / "pipeline-scoring.svg").write_text(
        svg.render(
            "30X Signal · Pipeline de análisis",
            "Seis pasos, de las piezas públicas al ranking: clasificar, agrupar, medir, evaluar, "
            "decidir y explicar, con quién hace cada uno.",
        )
    )


if __name__ == "__main__":
    architecture()
    flow()
    pipeline()
