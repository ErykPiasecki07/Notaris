import asyncio

import httpx2

from notaris.web.app import create_app


def test_health_check_returns_ok() -> None:
    response = asyncio.run(_get_health_response())

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def _get_health_response() -> httpx2.Response:
    transport = httpx2.ASGITransport(app=create_app())
    async with httpx2.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.get("/health")
