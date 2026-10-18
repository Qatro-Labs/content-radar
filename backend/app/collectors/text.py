"""Utilidades de texto compartidas por los collectors."""

import html
import re

# "AI" / "IA" solo en mayúsculas y como palabra, para no capturar "ai" dentro de otras palabras
# ni el "ia" de "día" o "tecnología".
_CASE_SENSITIVE = re.compile(r"\b(AI|IA|LLMs?|GPT[-\w.]*|MCP|AGI)\b")
_CASE_INSENSITIVE = re.compile(
    r"\b("
    r"inteligencia artificial|artificial intelligence|machine learning|aprendizaje automático"
    r"|deep learning|aprendizaje profundo|redes? neuronal(es)?|neural networks?"
    r"|generative|generativa|modelos? de lenguaje|language models?|chatbots?"
    r"|chatgpt|openai|anthropic|claude|gemini|copilot|deepseek|mistral|llama|grok|perplexity"
    r"|hugging ?face|nvidia|agentes? de ia|ai agents?|agentic|agéntic[oa]s?|prompts?"
    r"|automatizaci[oó]n con ia|vibe coding"
    r")\b",
    re.IGNORECASE,
)

HEADLINE_CHARS = 140
_TAG = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")


def is_ai_related(*texts: str | None) -> bool:
    text = " ".join(t for t in texts if t)
    return bool(_CASE_SENSITIVE.search(text) or _CASE_INSENSITIVE.search(text))


def clean_html(value: str | None, max_length: int = 2000) -> str | None:
    """HTML de feeds → texto plano corto. El contenido externo es no confiable: solo se guarda."""
    if not value:
        return None
    text = _SPACES.sub(" ", html.unescape(_TAG.sub(" ", value))).strip()
    return text[:max_length] or None


def headline(text: str) -> str:
    """Título de una pieza sin título propio (vídeo corto, reel, tweet): su primera línea."""
    first_line = text.strip().split("\n", 1)[0]
    return first_line[:HEADLINE_CHARS] or text[:HEADLINE_CHARS]
