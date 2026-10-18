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


def card_height(title: str, lines: list[Line], w: float, badge: str | None = None) -> float:
    inner = w - 36
    h = (
        18
        + len(wrap(title, inner - (len(badge) * char_w(13) + 30 if badge else 0), HEAD))
        * HEAD
        * 1.3
    )
    return h + lines_height(lines, inner, BODY) + 22


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
) -> float:
    fill, stroke, accent = TONES[tone]
    h = h or card_height(title, lines, w, badge)
    svg.rect(x, y, w, h, fill, stroke)
    inner = w - 36
    ty = y + 14
    badge_w = len(badge) * char_w(13) + 22 if badge else 0
    for part in wrap(title, inner - (badge_w + 8 if badge else 0), HEAD):
        ty += HEAD * 1.3
        svg.text(x + 18, ty - 4, part, HEAD, accent, 650)
    if badge:
        svg.rect(x + w - 18 - badge_w, y + 16, badge_w, 26, BG, stroke, r=13)
        svg.text(x + w - 18 - badge_w / 2, y + 34, badge, 13, accent, 600, anchor="middle")
    draw_lines(svg, x + 18, ty + 4, lines, inner, BODY, INK)
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
    )
    y += h + 44
    third = (full - 2 * gap) / 3
    xs = [MARGIN + i * (third + gap) for i in range(3)]
    svg.arrow(xs[0] + third / 2, y - 44, xs[0] + third / 2, y - 2)
    specs = [
        ("Colectores", ["Leen cada fuente y guardan piezas y métricas públicas."], "python"),
        ("Motor de análisis", ["Agrupa las piezas en temas y calcula los scores."], "python"),
        ("Modelos de IA", ["Jev clasifica y verifica; el LLM evalúa y redacta."], "llm"),
    ]
    h = max(card_height(t, ls, third) for t, ls, _ in specs)
    for x, (t, ls, tone) in zip(xs, specs, strict=True):
        card(svg, x, y, third, t, ls, tone, h)
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
    )
    y += h + 44
    for x in xs:
        svg.arrow(x + third / 2, y - 44, x + third / 2, y - 2)
    specs = [
        ("API REST", ["Sirve oportunidades, evidencia y briefs al dashboard."], "python"),
        ("Agente Rad", ["Responde preguntas sobre el Radar y mueve la vista."], "llm"),
        ("Servidor MCP", ["Las mismas consultas desde un asistente de IA."], "python"),
    ]
    h = max(card_height(t, ls, third) for t, ls, _ in specs)
    for x, (t, ls, tone) in zip(xs, specs, strict=True):
        card(svg, x, y, third, t, ls, tone, h)
    y += h + 44
    half = (full - gap) / 2
    svg.arrow(xs[0] + third / 2, y - 44, xs[0] + third / 2, y - 2)
    svg.arrow(xs[1] + third / 2, y - 44, MARGIN + half - 60, y - 2)
    svg.arrow(xs[2] + third / 2, y - 44, xs[2] + third / 2, y - 2)
    specs = [
        ("Dashboard", ["Radar, exploración de evidencia y creación de briefs."], "client"),
        ("Asistentes de IA", ["Claude, ChatGPT o Grok, conectados por MCP."], "client"),
    ]
    h = max(card_height(t, ls, half) for t, ls, _ in specs)
    for i, (t, ls, tone) in enumerate(specs):
        card(svg, MARGIN + i * (half + gap), y, half, t, ls, tone, h)
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


FLOW: list[tuple[str, str, str]] = [
    ("Señal", "Una pieza pública con sus métricas.", "¿Qué se publica?"),
    ("Tendencia", "Piezas parecidas agrupadas en un tema que crece.", "¿Qué está creciendo?"),
    (
        "Oportunidad",
        "El tema puntuado para la audiencia de 30X, con una recomendación.",
        "¿Vale la pena?",
    ),
    ("Evidencia", "Las piezas que lo respaldan, enlazadas a su fuente.", "¿Por qué lo creemos?"),
    ("Contenido", "Un brief con ángulo, gancho y estructura.", "¿Qué publicamos?"),
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
    specs = [
        (f"{i} · {name}", [what, ("bold", question)])
        for i, (name, what, question) in enumerate(FLOW, 1)
    ]
    h = max(card_height(t, ls, w) for t, ls in specs)
    for i, (title, lines) in enumerate(specs):
        x = MARGIN + i * (w + gap)
        card(svg, x, y, w, title, lines, "data" if i == n - 1 else "python", h)
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


STEPS: list[tuple[str, str, str, str]] = [
    (
        "Clasificar",
        "jev",
        "Jev",
        "Decide si cada pieza trata de IA y etiqueta su formato y su gancho.",
    ),
    (
        "Agrupar",
        "neutral",
        "Embeddings",
        "Une las piezas parecidas en temas, en español y en inglés.",
    ),
    (
        "Medir",
        "python",
        "Python",
        "Velocidad, aceleración, outliers, saturación y fuentes independientes de cada tema.",
    ),
    ("Evaluar", "llm", "LLM", "Encaje del tema con la audiencia de 30X, en seis criterios."),
    ("Decidir", "python", "Python", "Opportunity Score, confianza y recomendación."),
    (
        "Explicar",
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
    )
    y += h
    for i, (name, tone, who, what) in enumerate(STEPS, 1):
        svg.arrow(WIDTH / 2, y + 2, WIDTH / 2, y + 30)
        y += 32
        y += card(svg, MARGIN, y, full, f"{i} · {name}", [what], tone, badge=who)
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
