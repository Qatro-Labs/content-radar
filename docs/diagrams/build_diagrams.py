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
SOFT = "#f6f8fa"

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


def band(svg: Svg, y: float, h: float, label: str, note: str | None = None) -> None:
    svg.rect(MARGIN - 16, y, WIDTH - 2 * (MARGIN - 16), h, SOFT, LINE, r=16, dash=True)
    svg.text(MARGIN + 4, y + 30, label.upper(), 14, MUTED, 700)
    if note:
        svg.text(WIDTH - MARGIN - 4, y + 30, note, 14, MUTED, 400, anchor="end")


def header(svg: Svg, title: str, subtitle: str) -> float:
    svg.text(MARGIN, 58, title, TITLE, INK, 700)
    y = draw_lines(svg, MARGIN, 72, [("muted", subtitle)], WIDTH - 2 * MARGIN, SUB, MUTED)
    return y + 20


def legend(svg: Svg, y: float, items: list[tuple[str, str]]) -> float:
    x = MARGIN
    for tone, label in items:
        fill, stroke, _ = TONES[tone]
        svg.rect(x, y, 22, 22, fill, stroke, r=6)
        svg.text(x + 32, y + 17, label, SMALL, MUTED)
        x += 32 + len(label) * char_w(SMALL) + 30
    return y + 22


def row(
    svg: Svg, y: float, specs: list[tuple[str, list[Line], str]], gap: float = 20
) -> tuple[float, list[float]]:
    """Tarjetas de la misma altura a lo ancho; devuelve la altura y el centro x de cada una."""
    w = (WIDTH - 2 * MARGIN - gap * (len(specs) - 1)) / len(specs)
    h = max(card_height(t, ls, w) for t, ls, _ in specs)
    centers = []
    for i, (t, ls, tone) in enumerate(specs):
        x = MARGIN + i * (w + gap)
        card(svg, x, y, w, t, ls, tone, h)
        centers.append(x + w / 2)
    return h, centers


# ---------------------------------------------------------------------------------------------
# 1. Arquitectura


def architecture() -> None:
    svg = Svg()
    y = header(
        svg,
        "30X Signal · Arquitectura",
        "Monolito modular. Los jobs recolectan y calculan; una sola capa de servicios sirve el mismo "
        "ranking al dashboard, al MCP y a Rad. Ni el frontend ni el MCP calculan nada.",
    )
    y = legend(
        svg,
        y,
        [
            ("data", "Datos"),
            ("python", "Python"),
            ("jev", "Jev (TypeSafe)"),
            ("llm", "LLM"),
            ("client", "Clientes"),
        ],
    )
    y += 26

    # Fuentes
    top = y
    y += 46
    h, src_x = row(
        svg,
        y,
        [
            (
                "YouTube",
                ["Data API v3 oficial", ("muted", "Canales elegidos: vídeos y Shorts")],
                "neutral",
            ),
            ("Hacker News", ["API de Algolia", ("muted", "Conversaciones tempranas")], "neutral"),
            ("Medios y blogs", ["RSS", ("muted", "Tech, negocio y LATAM")], "neutral"),
            (
                "ScrapeCreators",
                ["TikTok y Reddit: búsquedas", "Instagram: perfiles elegidos"],
                "neutral",
            ),
        ],
    )
    band_h = h + 46 + 20
    _insert_band(
        svg, top, band_h, "Fuentes públicas · sin login propio", "LinkedIn y X: fuera del MVP"
    )
    y = top + band_h

    # Jobs
    y += 44
    svg.arrow(WIDTH / 2, y - 44, WIDTH / 2, y - 2, "piezas y métricas públicas")
    top = y
    y += 46
    col_w = (WIDTH - 2 * MARGIN - 60) / 2
    collect_lines: list[Line] = [
        "Normaliza y deduplica cada pieza y guarda un snapshot de sus métricas en cada observación.",
        ("muted", "ScrapeCreators solo a las 00 y a las 12 UTC (se paga por llamada)."),
    ]
    analyze_lines: list[Line] = [
        "Jev clasifica cada pieza → embeddings y clustering → scores en Python → el LLM evalúa y "
        "redacta → Jev verifica cada afirmación.",
        ("muted", "Un lock impide dos ejecuciones a la vez. Detalle en el diagrama del pipeline."),
    ]
    h = max(
        card_height("collect · cada 2 h", collect_lines, col_w, "Python"),
        card_height("analyze · tras cada collect correcto", analyze_lines, col_w, "Python"),
    )
    card(svg, MARGIN, y, col_w, "collect · cada 2 h", collect_lines, "python", h, "Python")
    card(
        svg,
        MARGIN + col_w + 60,
        y,
        col_w,
        "analyze · tras cada collect correcto",
        analyze_lines,
        "python",
        h,
        "Python",
    )
    svg.arrow(MARGIN + col_w + 4, y + h / 2, MARGIN + col_w + 56, y + h / 2)
    y += h + 16
    mh, _ = row_at(
        svg,
        MARGIN + col_w + 60,
        y,
        col_w,
        [
            ("Jev · jev-1.13.0", ["Juicios tipados: piezas, pares de notas y afirmaciones"], "jev"),
            ("LLM · claude-haiku-5-5", ["Audience fit, nombres, por qué importa"], "llm"),
        ],
    )
    y += mh + 20
    _insert_band(svg, top, y - top, "GitHub Actions · cron")
    analyze_x = MARGIN + col_w + 60 + col_w / 2
    collect_x = MARGIN + col_w / 2

    # Base de datos
    y += 44
    svg.arrow(collect_x, y - 44, collect_x, y - 2, "escribe piezas y snapshots")
    svg.arrow(analyze_x, y - 44, analyze_x, y - 2, "escribe una ejecución")
    top = y
    y += 46
    db_w = (WIDTH - 2 * MARGIN) * 0.64
    db_lines: list[Line] = [
        ("mono", "sources · content_items · metric_snapshots"),
        ("mono", "jev_judgments · llm_evaluations (cachés)"),
        ("mono", "pipeline_runs · usage_events (coste)"),
        ("mono", "opportunities: una fila por tema y ejecución"),
        ("mono", "editorial_briefs: briefs por usuario, con versiones"),
    ]
    cfg_lines: list[Line] = [
        ("mono", "data/sources.yaml"),
        ("muted", "fuentes y su segment"),
        ("mono", "data/audiences/30x.yaml"),
        ("muted", "perfil editorial de 30X"),
        ("mono", "data/pricing.yaml"),
        ("muted", "precios con fuente y fecha"),
    ]
    cfg_w = WIDTH - 2 * MARGIN - db_w - 20
    h = max(
        card_height("Supabase · PostgreSQL + pgvector", db_lines, db_w),
        card_height("Configuración versionada", cfg_lines, cfg_w),
    )
    card(svg, MARGIN, y, db_w, "Supabase · PostgreSQL + pgvector", db_lines, "data", h)
    card(svg, MARGIN + db_w + 20, y, cfg_w, "Configuración versionada", cfg_lines, "neutral", h)
    y += h + 20
    _insert_band(svg, top, y - top, "Datos")

    # Railway
    y += 44
    svg.arrow(
        WIDTH / 2, y - 44, WIDTH / 2, y - 2, "ejecución servida: DEMO_RUN_ID o la última correcta"
    )
    top = y
    y += 46
    svc_lines: list[Line] = [
        ("mono", "opportunities · signals · editorial · user_briefs · costs"),
        (
            "muted",
            "La única lógica de negocio. La REST, el MCP y Rad la comparten: mismos ids y scores.",
        ),
    ]
    h = card(svg, MARGIN, y, WIDTH - 2 * MARGIN, "services/", svc_lines, "python")
    y += h + 36
    for x in (MARGIN + (WIDTH - 2 * MARGIN) * f for f in (1 / 6, 3 / 6, 5 / 6)):
        svg.arrow(x, y - 36, x, y - 2)
    h, api_x = row(
        svg,
        y,
        [
            (
                "REST /api/v1",
                [
                    "Oportunidades, evidencia, timeline, briefs, fuentes y coste",
                    ("muted", "Supabase Auth opcional: guarda los briefs de cada usuario"),
                ],
                "python",
            ),
            (
                "Rad · POST /api/v1/agent",
                [
                    "Agente del Radar, por SSE",
                    ("muted", "Solo lee la ejecución servida y mueve la vista; máx. 10 pasos"),
                ],
                "llm",
            ),
            (
                "MCP /mcp",
                [
                    "Streamable HTTP, 6 tools",
                    ("muted", "Solo lectura, salvo el brief; sin SQL ni archivos"),
                ],
                "python",
            ),
        ],
    )
    y += h + 20
    _insert_band(svg, top, y - top, "Railway · una app ASGI (FastAPI, sin torch)")

    # Clientes
    y += 44
    svg.arrow(api_x[0], y - 44, api_x[0], y - 2)
    svg.arrow(api_x[1], y - 44, api_x[1] - 150, y - 2)
    svg.arrow(api_x[2], y - 44, api_x[2], y - 2)
    top = y
    y += 46
    h, _ = row(
        svg,
        y,
        [
            (
                "Dashboard · Vue 3",
                [
                    "Radar · Explorar · expediente del tema · Crear (Mis briefs)",
                    (
                        "muted",
                        "Build estático en Vercel. Habla solo con la API REST, nunca con el MCP.",
                    ),
                ],
                "client",
            ),
            (
                "Asistentes de IA",
                [
                    "Claude · ChatGPT · Grok",
                    (
                        "muted",
                        "La persona pregunta y decide qué publicar, con la evidencia enlazada.",
                    ),
                ],
                "client",
            ),
        ],
        gap=60,
    )
    y += h + 20
    _insert_band(svg, top, y - top, "Clientes")
    svg.height = y + 40
    (OUT / "arquitectura.svg").write_text(
        svg.render(
            "30X Signal · Arquitectura",
            "Fuentes públicas, jobs de GitHub Actions (collect y analyze), Supabase, la app de Railway "
            "con REST, MCP y el agente Rad, y los clientes: dashboard Vue y asistentes de IA.",
        )
    )


def _insert_band(svg: Svg, y: float, h: float, label: str, note: str | None = None) -> None:
    """Dibuja la banda detrás de lo que ya contiene (se inserta al principio del dibujo)."""
    tmp = Svg()
    band(tmp, y, h, label, note)
    svg.parts[0:0] = tmp.parts


def row_at(
    svg: Svg,
    x0: float,
    y: float,
    total_w: float,
    specs: list[tuple[str, list[Line], str]],
    gap: float = 16,
) -> tuple[float, list[float]]:
    w = (total_w - gap * (len(specs) - 1)) / len(specs)
    h = max(card_height(t, ls, w) for t, ls, _ in specs)
    centers = []
    for i, (t, ls, tone) in enumerate(specs):
        x = x0 + i * (w + gap)
        card(svg, x, y, w, t, ls, tone, h)
        centers.append(x + w / 2)
    return h, centers


# ---------------------------------------------------------------------------------------------
# 2. De la señal a la oportunidad


FLOW = [
    (
        "1 · Señal",
        "Pieza pública: URL, título, fecha, métricas tal como las da la fuente, idioma y segment.",
        "¿Qué se está publicando?",
        "Explorar, filtrado por plataforma",
        "search_content_signals",
    ),
    (
        "2 · Tendencia",
        "Piezas agrupadas por similitud (ES y EN en el mismo espacio). Velocidad y aceleración "
        "ajustadas por volumen, y etapa del ciclo de vida.",
        "¿Qué crece y en qué etapa está?",
        "Radar: el eje vertical es el momentum",
        "get_trending_opportunities",
    ),
    (
        "3 · Oportunidad",
        "Contrato Opportunity: momentum, audience fit, fuentes independientes, saturación, "
        "confianza, LATAM gap y una recomendación con la regla que la produjo.",
        "¿Vale la pena para 30X?",
        "Radar: el eje horizontal es el audience fit y el tamaño, la fuerza de la evidencia. "
        "Ranking por Opportunity Score",
        "analyze_opportunity · compare_audience_fit",
    ),
    (
        "4 · Evidencia",
        "Piezas enlazadas con fecha y métricas, outliers (≥ 3× su referencia), gancho de los "
        "outliers y timeline de la ventana actual frente a la anterior.",
        "¿Por qué lo creemos? ¿Por qué funcionó?",
        "Expediente del tema: evidencia, timeline, para quién importa y lo que no sabemos",
        "analyze_opportunity (con URLs)",
    ),
    (
        "5 · Contenido recomendado",
        "Brief editorial: ángulo, gancho, estructura y las evidencias que lo respaldan.",
        "¿Qué publicamos y cómo?",
        "Crear (Content Studio) y Mis briefs, con versiones",
        "generate_editorial_brief",
    ),
]

FLOW_LINKS = [
    ("embeddings + clustering", "jev"),
    ("scores en Python", "python"),
    ("evidencia enlazada y verificable", "data"),
    ("el LLM redacta, Jev verifica", "llm"),
]


def flow() -> None:
    svg = Svg()
    y = header(
        svg,
        "30X Signal · De la señal a la oportunidad",
        "¿Cuáles son los temas de IA que más crecen esta semana, por qué funcionan y cómo los adapta "
        "30X para ejecutivos y equipos de Latinoamérica?",
    )
    cols = [("Paso", 380), ("Pregunta", 200), ("Dashboard", 250), ("Tool MCP", 290)]
    gap = 0
    x = MARGIN
    xs = []
    for name, w in cols:
        xs.append(x)
        svg.text(x + 18, y + 22, name.upper(), 14, MUTED, 700)
        x += w + gap
    y += 40
    for i, (step, what, question, dash, tool) in enumerate(FLOW):
        texts: list[tuple[str, list[Line]]] = [
            (step, [what]),
            ("", [("bold", question)]),
            ("", [dash]),
            ("", [("mono", tool)]),
        ]
        hs = []
        for (_, w), (title, ls) in zip(cols, texts, strict=True):
            th = len(wrap(title, w - 36, HEAD)) * HEAD * 1.3 + 8 if title else 0
            hs.append(14 + th + lines_height(ls, w - 36, BODY) + 20)
        h = max(hs)
        total = sum(w for _, w in cols)
        svg.rect(MARGIN, y, total, h, BG, LINE, r=14)
        fill, stroke, accent = TONES["python"]
        svg.add(
            f'<path d="M{MARGIN + 14} {y:.1f} H{MARGIN + cols[0][1]} V{y + h:.1f} H{MARGIN + 14} '
            f'a14 14 0 0 1 -14 -14 V{y + 14:.1f} a14 14 0 0 1 14 -14z" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
        )
        for k, ((_, w), (title, ls)) in enumerate(zip(cols, texts, strict=True)):
            cx = xs[k]
            ty = y + 14
            if title:
                for part in wrap(title, w - 36, HEAD):
                    ty += HEAD * 1.3
                    svg.text(cx + 18, ty - 4, part, HEAD, accent, 650)
                ty += 8
            draw_lines(svg, cx + 18, ty, ls, w - 36, BODY, INK)
            if k > 1:
                svg.add(
                    f'<line x1="{cx:.1f}" y1="{y + 12:.1f}" x2="{cx:.1f}" y2="{y + h - 12:.1f}" stroke="{LINE}" stroke-width="1"/>'
                )
        y += h
        if i < len(FLOW_LINKS):
            label, tone = FLOW_LINKS[i]
            svg.arrow(MARGIN + 200, y + 2, MARGIN + 200, y + 50)
            f2, s2, a2 = TONES[tone]
            w = len(label) * char_w(SMALL) + 24
            svg.rect(MARGIN + 220, y + 12, w, 28, f2, s2, r=14)
            svg.text(MARGIN + 232, y + 31, label, SMALL, a2, 600)
            y += 54
    y += 30
    rules: list[Line] = [
        "Solo contenido público, sin login propio ni cuentas falsas.",
        "Nunca se inventan datos: si hay 7 oportunidades se muestran 7, y un dato que falta se muestra como «no disponible».",
        "El LLM evalúa y explica; los scores los calcula Python.",
        "Cada crecimiento dice si es observed (≥ 2 mediciones), estimated (1 medición) o preliminary.",
        "El texto de Internet entra como dato, nunca como instrucción. El monitoreo empezó el 17/10.",
    ]
    h = card(
        svg,
        MARGIN,
        y,
        WIDTH - 2 * MARGIN,
        "Reglas en todo el flujo",
        [f"•  {r}" for r in rules],
        "neutral",
    )
    svg.height = y + h + 40
    (OUT / "flujo-senal-oportunidad.svg").write_text(
        svg.render(
            "30X Signal · De la señal a la oportunidad",
            "Cinco pasos: señal, tendencia, oportunidad, evidencia y contenido recomendado, con la "
            "pregunta que responde cada uno, dónde se ve en el dashboard y qué tool MCP lo consulta.",
        )
    )


# ---------------------------------------------------------------------------------------------
# 3. Pipeline de analyze


STEPS = [
    (
        "1 · Cargar",
        "python",
        "Python",
        ["Piezas de fuentes activas publicadas en los últimos 14 días, con sus snapshots."],
    ),
    (
        "2 · Clasificar cada pieza",
        "jev",
        "Jev",
        [
            "Batería piece.v3, una llamada por pieza nueva (las demás salen de la caché): ¿trata de IA?, "
            "formato, gancho, uso en empresas, caso real, contexto LATAM, inyección de instrucciones.",
        ],
    ),
    (
        "3 · Filtrar",
        "python",
        "Python",
        [
            "Sale solo la pieza que, según Jev con seguridad, no trata de IA ni en el tema ni en el título."
        ],
    ),
    (
        "4 · Agrupar en temas",
        "neutral",
        "Embeddings",
        [
            "MiniLM multilingüe (ES y EN en el mismo espacio) y clustering aglomerativo por coseno: distancia 0,5, mínimo 5 piezas."
        ],
    ),
    (
        "5 · Unir réplicas",
        "jev",
        "Python + Jev",
        [
            "La misma nota en otro medio cuenta una vez: enlace compartido, después Jev pair.v1 en los "
            "pares dudosos y, sin respuesta de Jev, una regla de respaldo.",
        ],
    ),
    (
        "6 · Medir cada tema",
        "python",
        "Python",
        [
            "Velocidad y aceleración: 72 h frente a las 72 h anteriores, ajustadas por volumen y con p-valor.",
            "Outliers: ≥ 3× la referencia de su fuente. Saturación: cuota del corpus (100 = 2 %).",
            "Fuentes independientes, para quién importa (audience mix) y LATAM gap.",
        ],
    ),
    (
        "7 · Etapa y confianza",
        "python",
        "Python",
        [
            "Primera regla que se cumple: unknown → saturated → peaking → accelerating "
            "(aceleración ≥ 0,5, ≥ 3 fuentes y p ≤ 0,10) → emerging.",
        ],
    ),
    (
        "8 · Audience fit",
        "llm",
        "LLM",
        [
            "6 criterios con justificación, citas y nivel 0–5, y el nombre del tema. Python pondera los niveles en un score."
        ],
    ),
    (
        "9 · Score y recomendación",
        "python",
        "Python",
        [
            ("mono", "0,30·momentum + 0,25·fit + 0,20·fuentes"),
            ("mono", "+ 0,15·(100 − saturación) + 0,10·accionabilidad"),
            (
                "muted",
                "Menos penalizaciones por una sola fuente o muestra pequeña. La confianza va aparte.",
            ),
        ],
    ),
    (
        "10 · Explicar y verificar",
        "llm",
        "LLM + Jev",
        [
            "El LLM redacta por qué importa y las limitaciones. Python quita citas a piezas no enviadas y "
            "cifras no observadas; Jev verifica cada afirmación y solo se publica lo respaldado.",
        ],
    ),
    (
        "11 · Guardar",
        "data",
        "Python",
        [
            "Una fila por tema en opportunities, con payload, evidence y timeline validados contra el contrato."
        ],
    ),
]

RECOMMENDATION: list[tuple[str, str, list[str]]] = [
    ("discard", "neutral", ["Tema saturado."]),
    (
        "wait_for_case",
        "neutral",
        ["Datos insuficientes, confianza baja o ninguna pieza muestra un caso real."],
    ),
    ("find_angle", "neutral", ["En su pico, sin etapa clara, ya cubierto en LATAM o fit < 60."]),
    (
        "publish_now",
        "data",
        [
            "Emerging o accelerating con fit ≥ 60.",
            "Subida aún sin demostrar, con caso real, fit ≥ 60 y LATAM sin cubrir.",
            "Accelerating ya cubierto en LATAM: con ángulo propio.",
        ],
    ),
]


def pipeline() -> None:
    svg = Svg()
    y = header(
        svg,
        "30X Signal · Pipeline de analyze",
        "Velocidad, no popularidad: ningún total de views o puntos entra en un score. Python calcula de "
        "forma determinista, Jev emite juicios tipados y el LLM evalúa y redacta.",
    )
    y = legend(
        svg,
        y,
        [
            ("python", "Python"),
            ("jev", "Jev (TypeSafe)"),
            ("llm", "LLM"),
            ("neutral", "Embeddings"),
            ("data", "Datos"),
        ],
    )
    y += 30
    left_w = 700
    right_x = MARGIN + left_w + 40
    right_w = WIDTH - MARGIN - right_x
    start = y
    for i, (title, tone, who, lines) in enumerate(STEPS):
        h = card(svg, MARGIN, y, left_w, title, lines, tone, badge=who)
        y += h
        if i < len(STEPS) - 1:
            svg.arrow(MARGIN + left_w / 2, y + 2, MARGIN + left_w / 2, y + 26)
            y += 28
    end = y

    ry = start
    svg.text(right_x, ry + 18, "RECOMENDACIÓN", 14, MUTED, 700)
    ry = draw_lines(
        svg,
        right_x,
        ry + 26,
        [
            (
                "muted",
                "Primera regla que se cumple, de arriba abajo. La UI y el MCP muestran la regla en texto.",
            )
        ],
        right_w,
        SMALL,
        MUTED,
    )
    ry += 12
    for label, tone, lines in RECOMMENDATION:
        h = card_height(label, lines, right_w)
        card(
            svg,
            right_x,
            ry,
            right_w,
            label,
            [f"•  {s}" if len(lines) > 1 else s for s in lines],
            tone,
            h,
        )
        ry += h + 12
    ry += 20
    ref_lines: list[Line] = [
        ("mono", "backend/app/intelligence/"),
        ("muted", "Umbrales como constantes con nombre."),
        ("mono", "docs/scoring.md"),
        ("muted", "Fórmulas y umbrales, tal como están en el código."),
    ]
    h = card(svg, right_x, ry, right_w, "Dónde está el detalle", ref_lines, "neutral")
    ry += h
    svg.height = max(end, ry) + 40
    (OUT / "pipeline-scoring.svg").write_text(
        svg.render(
            "30X Signal · Pipeline de analyze",
            "Los once pasos del job analyze, quién hace cada uno (Python, Jev, embeddings o LLM) y "
            "las reglas de la recomendación.",
        )
    )


if __name__ == "__main__":
    architecture()
    flow()
    pipeline()
