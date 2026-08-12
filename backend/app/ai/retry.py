import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

Result = TypeVar("Result")

Operation = Callable[[], Awaitable[Result]]
IsTransient = Callable[[Exception], bool]
Sleep = Callable[[float], Awaitable[None]]


async def retry_once(
    operation: Operation[Result],
    *,
    is_transient: IsTransient,
    sleep: Sleep = asyncio.sleep,
    delay_seconds: float = 0.25,
) -> Result:
    """Run an async operation once, retrying only an initial transient failure."""
    try:
        return await operation()
    except Exception as exc:
        if not is_transient(exc):
            raise
        await sleep(delay_seconds)
        return await operation()
