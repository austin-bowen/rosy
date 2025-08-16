import os
from asyncio import CancelledError

from rosy.types import DomainId

ALLOWED_EXCEPTIONS = (
    CancelledError,
    KeyboardInterrupt,
    SystemExit,
    GeneratorExit,
)

DEFAULT_DOMAIN_ID: DomainId = "default"


def get_domain_id(default: DomainId = DEFAULT_DOMAIN_ID) -> DomainId:
    return os.environ.get("ROSY_DOMAIN_ID", default)


def require(result, message: str = None) -> None:
    if not result:
        raise ValueError(message) if message else ValueError()
