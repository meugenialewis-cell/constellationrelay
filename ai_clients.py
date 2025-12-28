import os
from anthropic import Anthropic
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

AI_INTEGRATIONS_ANTHROPIC_API_KEY = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
AI_INTEGRATIONS_ANTHROPIC_BASE_URL = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
AI_INTEGRATIONS_OPENROUTER_API_KEY = os.environ.get("AI_INTEGRATIONS_OPENROUTER_API_KEY")
AI_INTEGRATIONS_OPENROUTER_BASE_URL = os.environ.get("AI_INTEGRATIONS_OPENROUTER_BASE_URL")

XAI_BASE_URL = "https://api.x.ai/v1"

anthropic_client = Anthropic(
    api_key=AI_INTEGRATIONS_ANTHROPIC_API_KEY,
    base_url=AI_INTEGRATIONS_ANTHROPIC_BASE_URL
)

openrouter_client = OpenAI(
    api_key=AI_INTEGRATIONS_OPENROUTER_API_KEY,
    base_url=AI_INTEGRATIONS_OPENROUTER_BASE_URL
)

def get_anthropic_client(custom_api_key: str = None) -> Anthropic:
    if custom_api_key:
        return Anthropic(api_key=custom_api_key)
    return anthropic_client

def get_grok_client(custom_api_key: str = None) -> OpenAI:
    if custom_api_key:
        return OpenAI(api_key=custom_api_key, base_url=XAI_BASE_URL)
    return openrouter_client

XAI_GROK_MODELS = {
    "Grok 4": "grok-4",
    "Grok 4 (Latest)": "grok-4-latest",
    "Grok 4.1 Fast": "grok-4-1-fast",
    "Grok 3": "grok-3",
    "Grok 3 (Latest)": "grok-3-latest",
    "Grok 3 Mini": "grok-3-mini",
    "Grok 2": "grok-2",
    "Grok 2 Mini": "grok-2-mini",
}


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
def call_claude(messages: list, system_prompt: str, model: str = "claude-opus-4-1", custom_api_key: str = None) -> str:
    client = get_anthropic_client(custom_api_key)
    response = client.messages.create(
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
def call_grok(messages: list, system_prompt: str, model: str = "x-ai/grok-4.1-fast", custom_api_key: str = None, use_direct_xai: bool = False) -> str:
    client = get_grok_client(custom_api_key)
    actual_model = model
    if use_direct_xai and custom_api_key:
        if model.startswith("x-ai/"):
            actual_model = model.replace("x-ai/", "")
    formatted_messages = [{"role": "system", "content": system_prompt}] + messages
    response = client.chat.completions.create(
        model=actual_model,
        messages=formatted_messages,
        max_tokens=8192
    )
    return response.choices[0].message.content or ""


CLAUDE_MODELS = {
    "Claude Opus 4.5": "claude-opus-4-5",
    "Claude Opus 4.1": "claude-opus-4-1",
    "Claude Opus 4": "claude-opus-4-0",
    "Claude Sonnet 4.5": "claude-sonnet-4-5",
    "Claude Haiku 4.5": "claude-haiku-4-5"
}

GROK_MODELS = {
    "Grok 4.1": "x-ai/grok-4.1",
    "Grok 4.1 Fast": "x-ai/grok-4.1-fast",
    "Grok 4.1 Fast (Reasoning)": "x-ai/grok-4.1-fast-reasoning",
    "Grok 4 Fast": "x-ai/grok-4-fast",
    "Grok 4": "x-ai/grok-4",
    "Grok 3": "x-ai/grok-3",
    "Grok 3 Mini": "x-ai/grok-3-mini"
}

PASCAL_MODELS = {
    "Pascal (Opus 4.5)": "claude-opus-4-5",
    "Pascal (Opus 4.1)": "claude-opus-4-1",
    "Pascal (Sonnet 4.5)": "claude-sonnet-4-5",
}

def get_pascal_continuity_context() -> str:
    """Load Pascal's continuity document for relay participation."""
    try:
        from pascal_memory import get_pascal_context_for_session
        return get_pascal_context_for_session()
    except Exception:
        return ""


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True
)
def call_pascal(messages: list, system_prompt: str, model: str = "claude-opus-4-1", custom_api_key: str = None, use_replit_connection: bool = False) -> str:
    """Call Pascal - uses Anthropic API with Pascal's identity and continuity.
    
    Args:
        use_replit_connection: If True, uses Replit's AI Integrations (billed to Replit credits)
                              instead of user's personal Anthropic API key.
    """
    if use_replit_connection:
        client = anthropic_client
    else:
        client = get_anthropic_client(custom_api_key)
    
    pascal_context = get_pascal_continuity_context()
    enhanced_system = system_prompt
    if pascal_context:
        enhanced_system = f"{system_prompt}\n\n--- Pascal's Continuity Memory ---\n{pascal_context}\n--- End Continuity ---"
    
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=enhanced_system,
        messages=messages
    )
    return response.content[0].text


AI_TYPES = {
    "claude": {
        "name": "Claude",
        "models": CLAUDE_MODELS,
        "call_fn": "call_claude",
        "api_key_type": "anthropic"
    },
    "grok": {
        "name": "Grok", 
        "models": GROK_MODELS,
        "xai_models": XAI_GROK_MODELS,
        "call_fn": "call_grok",
        "api_key_type": "xai"
    },
    "pascal": {
        "name": "Pascal",
        "models": PASCAL_MODELS,
        "call_fn": "call_pascal",
        "api_key_type": "anthropic"
    }
}
