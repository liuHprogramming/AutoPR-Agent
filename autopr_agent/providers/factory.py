from __future__ import annotations

from autopr_agent.llm import LocalHeuristicModel, ModelProvider
from autopr_agent.providers.openai_compatible import OpenAICompatibleProvider


def create_provider(
    name: str = "local",
    model: str | None = None,
    base_url: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
) -> ModelProvider:
    if name == "local":
        return LocalHeuristicModel()
    if name == "openai-compatible":
        return OpenAICompatibleProvider(
            model=model or "gpt-4.1-mini",
            base_url=base_url or "https://api.openai.com/v1/chat/completions",
            api_key_env=api_key_env,
        )
    raise ValueError(f"Unknown provider: {name}")
