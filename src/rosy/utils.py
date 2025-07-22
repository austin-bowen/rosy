def require(result, message: str = None) -> None:
    if not result:
        raise ValueError(message) if message else ValueError()
