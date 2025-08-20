from typing import Protocol


class SummaryGenerator(Protocol):
    def core_thesis(self, title: str, author: str, text: str) -> str: ...

    def detailed_abstract(self, title: str, author: str, text: str) -> str: ...

    def supporting_quotes(self, title: str, author: str, text: str) -> str: ...

