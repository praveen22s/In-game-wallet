"""Small demo client that calls the in-memory server endpoints.
Run while server is running locally at http://127.0.0.1:8000
"""
import asyncio
import uuid
import httpx


BASE = "http://127.0.0.1:8000"


async def do_demo():
    user = "demo-user-1"

    async with httpx.AsyncClient(base_url=BASE, timeout=10.0) as client:
        # Top-up 25 USD with idempotency key
        topup_key = str(uuid.uuid4())
        r = await client.post("/wallet/topup", json={"userId": user, "amountUSD": 25, "idempotencyKey": topup_key})
        print("topup =>", r.status_code, r.json())

        # Duplicate retry of same idempotency key should not double credit
        r2 = await client.post("/wallet/topup", json={"userId": user, "amountUSD": 25, "idempotencyKey": topup_key})
        print("topup(retry) =>", r2.status_code, r2.json())

        # Game reward
        reward_key = str(uuid.uuid4())
        r3 = await client.post("/game/reward", json={"userId": user, "amountCoins": 10, "rewardId": "weekly-1", "idempotencyKey": reward_key})
        print("reward =>", r3.status_code, r3.json())

        # Final balance
        rf = await client.get(f"/wallet/{user}")
        print("wallet =>", rf.status_code, rf.json())


if __name__ == "__main__":
    asyncio.run(do_demo())
