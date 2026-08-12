import asyncio

import pytest


@pytest.mark.asyncio
async def test_retry_once_retries_a_transient_error_exactly_once() -> None:
    from backend.app.ai.retry import retry_once

    attempts = 0
    delays: list[float] = []

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("temporary")
        return "ok"

    async def no_sleep(delay: float) -> None:
        delays.append(delay)

    result = await retry_once(
        operation,
        is_transient=lambda exc: isinstance(exc, TimeoutError),
        sleep=no_sleep,
    )

    assert result == "ok"
    assert attempts == 2
    assert delays == [0.25]


@pytest.mark.asyncio
async def test_retry_once_reraises_non_transient_error_without_sleeping() -> None:
    from backend.app.ai.retry import retry_once

    error = ValueError("invalid request")
    attempts = 0
    delays: list[float] = []

    async def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise error

    async def no_sleep(delay: float) -> None:
        delays.append(delay)

    with pytest.raises(ValueError) as raised:
        await retry_once(
            operation,
            is_transient=lambda exc: isinstance(exc, TimeoutError),
            sleep=no_sleep,
        )

    assert raised.value is error
    assert attempts == 1
    assert delays == []


@pytest.mark.asyncio
async def test_retry_once_propagates_the_second_transient_error_unchanged() -> None:
    from backend.app.ai.retry import retry_once

    first_error = TimeoutError("first")
    second_error = TimeoutError("second")
    attempts = 0

    async def operation() -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise first_error
        raise second_error

    async def no_sleep(_: float) -> None:
        return None

    with pytest.raises(TimeoutError) as raised:
        await retry_once(
            operation,
            is_transient=lambda exc: isinstance(exc, TimeoutError),
            sleep=no_sleep,
        )

    assert raised.value is second_error
    assert attempts == 2


@pytest.mark.asyncio
async def test_retry_once_does_not_catch_cancellation() -> None:
    from backend.app.ai.retry import retry_once

    attempts = 0

    async def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise asyncio.CancelledError()

    async def no_sleep(_: float) -> None:
        pytest.fail("retry sleep must not run for cancellation")

    with pytest.raises(asyncio.CancelledError):
        await retry_once(
            operation,
            is_transient=lambda exc: True,
            sleep=no_sleep,
        )

    assert attempts == 1
