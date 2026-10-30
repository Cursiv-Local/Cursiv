"""Provider identities and conservative catalogs; registration never depends on keys.

Catalog entries are documented IDs, NOT claims of account access or current service
availability. Capabilities are unknown until a discovery response supplies them.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    protocol: str
    base_url: str
    credential: str = ''
    catalog: tuple[str, ...] = ()
    local: bool = False
    docs: str = ''


@dataclass
class Model:
    id: str
    provider: str
    source: str = 'catalog'
    verified: bool = False
    name: str = ''
    size: int | None = None
    context: int | None = None
    tools: bool | None = None
    vision: bool | None = None
    structured: bool | None = None
    quantization: str = ''
    details: dict = field(default_factory=dict)


_providers: dict[str, Provider] = {}


def register(provider: Provider):
    if provider.id in _providers:
        raise ValueError('Provider already registered')
    _providers[provider.id] = provider


def providers():
    return tuple(_providers.values())


def get(provider: str) -> Provider:
    return _providers[provider]


for _item in (
    Provider('ollama', 'Ollama', 'ollama', 'http://127.0.0.1:11434',
             catalog=('qwen3:4b-instruct',), local=True, docs='https://docs.ollama.com/api'),
    Provider('openai', 'OpenAI', 'openai', 'https://api.openai.com/v1', 'openai_key',
             ('gpt-4o',), docs='https://developers.openai.com/api/reference/resources/models'),
    Provider('groq', 'Groq', 'openai', 'https://api.groq.com/openai/v1', 'groq_key',
             ('llama-3.3-70b-versatile', 'openai/gpt-oss-20b'), docs='https://console.groq.com/docs/models'),
    Provider('gemini', 'Google Gemini', 'gemini', 'https://generativelanguage.googleapis.com/v1beta', 'gemini_key',
             ('gemini-3.8-flash',), docs='https://ai.google.dev/api/models'),
    Provider('claude', 'Anthropic Claude', 'claude', 'https://api.anthropic.com/v1', 'anthropic_key',
             ('claude-sonnet-4-5',), docs='https://platform.claude.com/docs/en/api/models/list'),
    Provider('openrouter', 'OpenRouter', 'openai', 'https://openrouter.ai/api/v1', 'openrouter_key',
             ('openai/gpt-4o',), docs='https://openrouter.ai/docs/api_reference/overview'),
    Provider('lmstudio', 'LM Studio', 'openai', 'http://127.0.0.1:1234/v1', 'lmstudio_key', local=True,
             docs='https://lmstudio.ai/docs/developer/openai-compat'),
    Provider('custom', 'Custom Endpoint', 'openai', '', 'custom_key'),
    Provider('grok', 'xAI', 'openai', 'https://api.x.ai/v1', 'api_key', ('grok-3',),
             docs='https://docs.x.ai/docs/api-reference'),
):
    register(_item)
