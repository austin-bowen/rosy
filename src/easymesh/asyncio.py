import asyncio


async def forever():
    """Never returns."""
    while True:
        await asyncio.sleep(60)


def noop():
    """Does nothing. Use to return control to the event loop."""
    return asyncio.sleep(0)
