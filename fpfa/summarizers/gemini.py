from typing import Optional
from google import genai
from ..config import load_config


CORE_PROMPT = (
    "Task: Write 1-2 dense sentences capturing the main conclusion or central "
    "argument of the article, focusing only on the primary claim without "+
    "supporting details.\n\nTitle: {title}\nAuthor: {author}\nText: {text}"
)

DETAIL_PROMPT = (
    "Task: Provide 1-2 dense paragraphs summarizing the main arguments and "
    "points of the article. Include essential background and progression of "
    "ideas. Do not include anything except the summary.\n\nTitle: {title}\n"
    "Author: {author}\nText: {text}"
)

QUOTES_PROMPT = (
    "Task: Extract and list the most important factual data points or "
    "statistics and 2-3 key direct quotes verbatim. Return bullet points "
    "only.\n\nTitle: {title}\nAuthor: {author}\nText: {text}"
)


class GeminiSummaryGenerator:
    def __init__(self, api_key: Optional[str] = None):
        self.cfg = load_config()
        api_key = api_key or self._env_key()
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.available = self.client is not None

    def _env_key(self) -> Optional[str]:
        import os

        return os.environ.get("GEMINI_API_KEY")

    def _gen(self, model: str, prompt: str) -> str:
        if not self.client:
            return "Summary generation unavailable (no API key)."
        try:
            res = self.client.models.generate_content(model=model, contents=prompt)
            return (res.text or "").strip() or "Summary generation failed."
        except Exception:
            return "Summary generation failed."

    def core_thesis(self, title: str, author: str, text: str) -> str:
        prompt = CORE_PROMPT.format(title=title, author=author, text=text)
        return self._gen(self.cfg.model_core, prompt)

    def detailed_abstract(self, title: str, author: str, text: str) -> str:
        prompt = DETAIL_PROMPT.format(title=title, author=author, text=text)
        return self._gen(self.cfg.model_detail, prompt)

    def supporting_quotes(self, title: str, author: str, text: str) -> str:
        prompt = QUOTES_PROMPT.format(title=title, author=author, text=text)
        return self._gen(self.cfg.model_quotes, prompt)
