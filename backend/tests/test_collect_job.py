from app.jobs.collect import parse_exclusions, without_excluded
from app.models import Source


def source(platform: str, kind: str, name: str) -> Source:
    return Source(platform=platform, kind=kind, external_id=name, name=name, segment="tech")


def test_excluding_youtube_searches_keeps_youtube_channels():
    sources = [
        source("youtube", "channel", "OpenAI"),
        source("youtube", "query", "YouTube Shorts · AI agents (global)"),
        source("hackernews", "query", "HN · LLM"),
    ]
    kept = without_excluded(sources, parse_exclusions(["youtube:query"]))
    assert [s.name for s in kept] == ["OpenAI", "HN · LLM"]


def test_no_exclusions_keeps_everything():
    sources = [source("youtube", "query", "Shorts"), source("gdelt", "query", "GDELT")]
    assert without_excluded(sources, parse_exclusions(None)) == sources
