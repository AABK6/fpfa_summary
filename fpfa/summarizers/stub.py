from .base import SummaryGenerator


class StubSummaryGenerator:
    def core_thesis(self, title: str, author: str, text: str) -> str:
        return f"CORE: {title} — {author}"

    def detailed_abstract(self, title: str, author: str, text: str) -> str:
        return f"ABSTRACT: {title} ({len(text.split())} words)"

    def supporting_quotes(self, title: str, author: str, text: str) -> str:
        return "- Quote A\n- Quote B\n- Fact X"

