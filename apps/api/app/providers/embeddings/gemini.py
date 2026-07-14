import httpx

from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.errors import EmbeddingError


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str, dimensions: int) -> None:
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise EmbeddingError("A Gemini API key is required to generate embeddings.")
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
            "outputDimensionality": self.dimensions,
        }
        response = self._post_embed_content(url=url, payload=payload)
        values = response.json().get("embedding", {}).get("values", [])
        if len(values) != self.dimensions:
            raise EmbeddingError(
                f"Gemini returned {len(values)} embedding dimensions, expected {self.dimensions}."
            )
        return [float(value) for value in values]

    def _post_embed_content(self, url: str, payload: dict) -> httpx.Response:
        for attempt in range(2):
            try:
                response = httpx.post(url, json=payload, timeout=30)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                reason = exc.response.reason_phrase
                if status_code in RETRYABLE_STATUS_CODES and attempt == 0:
                    continue
                raise EmbeddingError(
                    f"Gemini embedding request failed with HTTP {status_code} {reason} (model={self.model})."
                ) from exc
            except httpx.HTTPError as exc:
                raise EmbeddingError(
                    f"Gemini embedding request failed with {exc.__class__.__name__} (model={self.model})."
                ) from exc

        raise EmbeddingError(f"Gemini embedding request failed after retry (model={self.model}).")
