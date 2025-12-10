import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from server import app, wallets, idempotency, recent_ops


@pytest.fixture(autouse=True)
def clear_state():
    wallets.clear()
    idempotency.clear()
    recent_ops.clear()
    yield


@pytest.mark.asyncio
async def test_stress_concurrent_operations():
    """Stress test: X concurrent topups and Y concurrent rewards on the same user.
    Verifies final balance equals the sum of all ops (no lost updates).
    """
    user = "stress-user"

    TOPUPS = 100
    REWARDS = 100
    TOPUP_AMOUNT = 5.0  # each topup is 5 USD => 5 coins
    REWARD_AMOUNT = 3.0  # each reward is 3 coins

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        async def topup(i):
            key = f"top-{i}"
            r = await client.post("/wallet/topup", json={"userId": user, "amountUSD": TOPUP_AMOUNT, "idempotencyKey": key})
            assert r.status_code == 200

        async def reward(i):
            key = f"rew-{i}"
            r = await client.post("/game/reward", json={"userId": user, "amountCoins": REWARD_AMOUNT, "rewardId": f"r{i}", "idempotencyKey": key})
            assert r.status_code == 200

        # Fire all operations concurrently
        tasks = []
        for i in range(TOPUPS):
            tasks.append(topup(i))
        for i in range(REWARDS):
            tasks.append(reward(i))

        await asyncio.gather(*tasks)

        # Check final balance
        r = await client.get(f"/wallet/{user}")
        assert r.status_code == 200
        body = r.json()

        expected = TOPUPS * TOPUP_AMOUNT + REWARDS * REWARD_AMOUNT
        assert body["balance"] == pytest.approx(expected)
