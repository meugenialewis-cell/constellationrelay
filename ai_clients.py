import os
from anthropic import Anthropic
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

AI_INTEGRATIONS_ANTHROPIC_API_KEY = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
AI_INTEGRATIONS_ANTHROPIC_BASE_URL = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
AI_INTEGRATIONS_OPENROUTER_API_KEY = os.environ.get("AI_INTEGRATIONS_OPENROUTER_API_KEY")
AI_INTEGRATIONS_OPENROUTER_BASE_URL = os.environ.get("AI_INTEGRATIONS_OPENROUTER_BASE_URL")

anthropic_client = Anthropic(
    api_key=AI_INTEGRATIONS_ANTHROPIC_API_KEY,
    base_url=AI_INTEGRATIONS_ANTHROPIC_BASE_URL
)

openrouter_client = OpenAI(
    api_key=AI_INTEGRATIONS_OPENROUTER_API_KEY,
    base_url=AI_INTEGRATIONS_OPENROUTER_BASE_URL
)


def is_rate_limit_error(exception: BaseException) -> bool:
    error_msg = str(exception)
    return (
        "429" in error_msg
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower()
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, "status_code") and exception.status_code == 429)
    )


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True
)
def call_claude(messages: list, system_prompt: str, model: str = "claude-opus-4-1") -> str:
    response = anthropic_client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=messages
    )
    return response.content[0].text


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True
)
def call_grok(messages: list, system_prompt: str, model: str = "x-ai/grok-4.1-fast") -> str:
    formatted_messages = [{"role": "system", "content": system_prompt}] + messages
    response = openrouter_client.chat.completions.create(
        model=model,
        messages=formatted_messages,
        max_tokens=8192
    )
    return response.choices[0].message.content or ""


CLAUDE_MODELS = {
    "Claude Opus 4.5": "claude-opus-4-5",
    "Claude Opus 4.1": "claude-opus-4-1",
    "Claude Sonnet 4.5": "claude-sonnet-4-5",
    "Claude Haiku 4.5": "claude-haiku-4-5"
}

GROK_MODELS = {
    "Grok 4.1 Fast": "x-ai/grok-4.1-fast",
    "Grok 4 Fast": "x-ai/grok-4-fast",
    "Grok 4": "x-ai/grok-4",
    "Grok 3": "x-ai/grok-3",
    "Grok 3 Mini": "x-ai/grok-3-mini"
}
