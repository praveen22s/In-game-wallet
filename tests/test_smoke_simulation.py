"""Simulate the smoke concurrency test scenario inside pytest to verify no balance mismatch."""
import pytest
import asyncio
from httpx import ASGITransport, AsyncClient
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app


@pytest.mark.asyncio
async def test_smoke_simulation_concurrent_requests():
    """Simulate smoke concurrency test: 50 topups + 50 rewards concurrently
    
    Expected balance: 50*5 + 50*3 = 400
    """
    user_id = "smoke-test-user"
    topup_count = 50
    reward_count = 50
    topup_amt = 5.0
    reward_amt = 3.0
    
    expected_balance = topup_count * topup_amt + reward_count * reward_amt
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tasks = []
        
        # Create topup tasks
        for i in range(topup_count):
            key = f"smoke-top-{i}-{uuid.uuid4()}"
            tasks.append(
                client.post(
                    "/wallet/topup",
                    json={
                        "userId": user_id,
                        "amountUSD": topup_amt,
                        "idempotencyKey": key
                    }
                )
            )
        
        # Create reward tasks
        for i in range(reward_count):
            key = f"smoke-rew-{i}-{uuid.uuid4()}"
            tasks.append(
                client.post(
                    "/game/reward",
                    json={
                        "userId": user_id,
                        "amountCoins": reward_amt,
                        "rewardId": f"r{i}",
                        "idempotencyKey": key
                    }
                )
            )
        
        # Execute all concurrently
        responses = await asyncio.gather(*tasks)
        
        # Verify all requests succeeded
        for resp in responses:
            assert resp.status_code == 200, f"Request failed with {resp.status_code}"
        
        # Get final balance
        resp = await client.get(f"/wallet/{user_id}")
        assert resp.status_code == 200
        body = resp.json()
        actual_balance = body.get("balance")
        
        print(f"\nSmoke simulation results:")
        print(f"  Expected: {expected_balance}")
        print(f"  Actual:   {actual_balance}")
        print(f"  Mismatch: {actual_balance - expected_balance}")
        
        # Assert balance matches
        assert abs(actual_balance - expected_balance) < 1e-6, \
            f"Balance mismatch: expected {expected_balance}, got {actual_balance}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
