from enum import StrEnum


class ArticleSource(StrEnum):
    FOREIGN_AFFAIRS = "Foreign Affairs"
    FOREIGN_POLICY = "Foreign Policy"


CANONICAL_SOURCES = frozenset(source.value for source in ArticleSource)

LEGACY_SOURCE_MAP = {
    "FA": ArticleSource.FOREIGN_AFFAIRS.value,
    "FP": ArticleSource.FOREIGN_POLICY.value,
}


def normalize_article_source(source: str) -> str:
    """Return a canonical source name, mapping legacy shorthand values."""
    normalized = source.strip()
    if normalized in LEGACY_SOURCE_MAP:
        return LEGACY_SOURCE_MAP[normalized]
    if normalized in CANONICAL_SOURCES:
        return normalized
    raise ValueError(
        f"Unsupported article source '{source}'. Allowed sources: "
        f"{sorted(CANONICAL_SOURCES)} and legacy aliases {sorted(LEGACY_SOURCE_MAP.keys())}."
    )
