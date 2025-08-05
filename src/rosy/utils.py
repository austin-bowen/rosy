from asyncio import CancelledError

ALLOWED_EXCEPTIONS = (
    CancelledError,
    KeyboardInterrupt,
    SystemExit,
    GeneratorExit,
)


def require(result, message: str = None) -> None:
    if not result:
        raise ValueError(message) if message else ValueError()
