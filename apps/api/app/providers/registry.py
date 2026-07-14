from app.core.config import settings
from app.providers.base import LLMProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider


ProviderFactory = type[GeminiProvider] | type[GroqProvider]


PROVIDERS: dict[str, ProviderFactory] = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
}

DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-3.5-flash",
    "groq": "llama-3.1-8b-instant",
}


def build_provider(api_key: str | None = None, provider_name: str | None = None, model: str | None = None) -> LLMProvider:
    provider_name = (provider_name or settings.llm_provider).lower()
    provider_class = PROVIDERS.get(provider_name)
    if provider_class is None:
        supported = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"Unsupported LLM_PROVIDER={settings.llm_provider!r}. Supported providers: {supported}.")

    selected_model = model or settings.llm_model
    if provider_name != settings.llm_provider and model is None:
        selected_model = DEFAULT_MODELS[provider_name]

    return provider_class(api_key=api_key if api_key is not None else settings.llm_api_key, model=selected_model)
