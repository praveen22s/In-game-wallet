import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from server import app, wallets, idempotency, recent_ops


@pytest.fixture(autouse=True)
def clear_state():
    # Clear in-memory stores before each test
    wallets.clear()
    idempotency.clear()
    recent_ops.clear()
    yield


@pytest.mark.asyncio
async def test_concurrent_topup_and_reward():
    user = "user123"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        async def do_topup():
            r = await client.post("/wallet/topup", json={"userId": user, "amountUSD": 50, "idempotencyKey": "k-topup-1"})
            assert r.status_code == 200

        async def do_reward():
            r = await client.post("/game/reward", json={"userId": user, "amountCoins": 30, "rewardId": "r-1", "idempotencyKey": "k-reward-1"})
            assert r.status_code == 200

        # Run both at the same time
        await asyncio.gather(do_topup(), do_reward())

        # Check final balance
        r = await client.get(f"/wallet/{user}")
        assert r.status_code == 200
        body = r.json()
        assert body["balance"] == pytest.approx(80.0)


@pytest.mark.asyncio
async def test_idempotency_prevents_double_topup():
    user = "userA"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"userId": user, "amountUSD": 10, "idempotencyKey": "k-dup-1"}
        r1 = await client.post("/wallet/topup", json=payload)
        assert r1.status_code == 200

        # Retry same request with same key — should not double-credit
        r2 = await client.post("/wallet/topup", json=payload)
        assert r2.status_code == 200

        r = await client.get(f"/wallet/{user}")
        assert r.json()["balance"] == pytest.approx(10.0)

