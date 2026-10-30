"""Transport-owned results. Errors contain safe categories, never raw API bodies."""
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid


class ErrorCode(str, Enum):
    MISSING_KEY = 'missing_api_key'
    INVALID_KEY = 'invalid_api_key'
    PERMISSION = 'permission_denied'
    UNAVAILABLE = 'provider_unavailable'
    MODEL = 'model_unavailable'
    RATE = 'rate_limit'
    QUOTA = 'quota_exceeded'
    TIMEOUT = 'request_timeout'
    NETWORK = 'network_failure'
    OFFLINE = 'offline_restriction'
    ENDPOINT = 'invalid_endpoint'
    CAPABILITY = 'unsupported_capability'
    CANCELLED = 'request_canceled'
    MALFORMED = 'malformed_response'
    BUDGET = 'request_budget'


_MESSAGES = {
    ErrorCode.MISSING_KEY: 'No API key configured. Add your key in Settings → AI Providers, then retry.',
    ErrorCode.INVALID_KEY: 'The provider rejected the API key. Replace it in Settings → AI Providers.',
    ErrorCode.PERMISSION: 'Permission denied. Check provider permissions and research-data authorization.',
    ErrorCode.UNAVAILABLE: 'The provider is unavailable. Check that the service is running.',
    ErrorCode.MODEL: 'The requested model is unavailable. Check the exact model ID and account access.',
    ErrorCode.RATE: 'Rate limit exceeded. Wait before retrying.',
    ErrorCode.QUOTA: 'Provider quota exceeded. Check your provider account.',
    ErrorCode.TIMEOUT: 'Request timed out. Review any partial output before retrying.',
    ErrorCode.NETWORK: 'Network request failed. Check connectivity and the endpoint.',
    ErrorCode.OFFLINE: 'Cursiv is operating in offline mode. Cloud requests are disabled.',
    ErrorCode.ENDPOINT: 'Invalid or unsafe endpoint. Use HTTPS remotely or an explicit loopback address locally.',
    ErrorCode.CAPABILITY: 'This request needs a capability not supported in this path. No tool was executed.',
    ErrorCode.CANCELLED: 'Request canceled.',
    ErrorCode.MALFORMED: 'The provider returned an incomplete or malformed response.',
    ErrorCode.BUDGET: 'Cursiv stopped this request at its request or context budget. Use a smaller task or context, then retry deliberately.',
}


class ProviderError(Exception):
    def __init__(self, provider: str, code: ErrorCode, *, retry_after: int | None = None):
        self.provider, self.code, self.retry_after = provider, code, retry_after
        super().__init__(self.message)

    @property
    def message(self):
        from .provider_registry import get
        try:
            name = get(self.provider).name
        except KeyError:
            name = 'Cloud Automatic' if self.provider == 'cloud_auto' else 'Selected provider'
        return f'{name} request {"blocked" if self.code == ErrorCode.OFFLINE else "failed"}: {_MESSAGES[self.code]}'


@dataclass
class Request:
    provider: str
    model: str
    messages: list[dict]
    max_tokens: int = 2000
    cancel: object = None
    # Already assembled notebook/memory/document context needs a separate grant.
    research_authorized: bool = False
    local_only: bool = False
    capability: str = 'text'
    request_id: str = field(default_factory=lambda:uuid.uuid4().hex)
    endpoint_url: str = ''
    authorized_destination: tuple | None = None


@dataclass
class Result:
    provider: str
    requested_model: str
    attempted_provider: str = ''
    actual_model: str | None = None
    responding_provider: str | None = None
    text: str = ''
    tool_calls: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)
    finish_reason: str | None = None
    usage: dict = field(default_factory=dict)
    latency: float = 0
    error: str | None = None
    error_message: str = ''
    streaming: bool = False
    streamed: bool = False
    canceled: bool = False
    local: bool = False
    request_id: str = ''
    artifacts: list = field(default_factory=list)

    def metadata(self):
        data = asdict(self)
        # Transcript already owns response text; metadata never holds prompt/keys.
        data.pop('text')
        data['artifacts']=[{k:v for k,v in item.items() if k != 'base64'} for item in self.artifacts]
        return data

    def label(self):
        from .provider_registry import get
        model = self.actual_model or (self.requested_model + ' (requested; not independently reported)')
        return f'{"Local" if self.local else "Cloud"} · {get(self.provider).name} · {model}'
