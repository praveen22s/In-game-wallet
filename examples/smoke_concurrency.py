"""Smoke script to simulate concurrent topup and reward requests against the in-memory server.

Usage examples (PowerShell):
  python examples/smoke_concurrency.py --user smoke1 --topups 50 --rewards 50

Options:
  --base-url     Base URL of service (default http://127.0.0.1:8000)
  --user         userId to target
  --topups       number of concurrent topup operations
  --rewards      number of concurrent reward operations
  --topup-amt    amount per topup (USD -> coins)
  --reward-amt   amount per reward (coins)
  --concurrency  fire all operations concurrently if set (default true)
"""
import argparse
import asyncio
import uuid
import time
import httpx


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--user", default="smoke-user")
    p.add_argument("--topups", type=int, default=100)
    p.add_argument("--rewards", type=int, default=100)
    p.add_argument("--topup-amt", type=float, default=5.0)
    p.add_argument("--reward-amt", type=float, default=3.0)
    return p.parse_args()


async def run_smoke(args):
    user = args.user
    topups = args.topups
    rewards = args.rewards
    topup_amt = args.topup_amt
    reward_amt = args.reward_amt

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30.0) as client:

        async def do_topup(i):
            key = f"smoke-top-{i}-{uuid.uuid4()}"
            await client.post("/wallet/topup", json={"userId": user, "amountUSD": topup_amt, "idempotencyKey": key})

        async def do_reward(i):
            key = f"smoke-rew-{i}-{uuid.uuid4()}"
            await client.post("/game/reward", json={"userId": user, "amountCoins": reward_amt, "rewardId": f"r{i}", "idempotencyKey": key})

        print(f"Starting smoke test: user={user} topups={topups} rewards={rewards}\n")
        start = time.time()

        tasks = []
        for i in range(topups):
            tasks.append(do_topup(i))
        for i in range(rewards):
            tasks.append(do_reward(i))

        # Fire concurrently
        await asyncio.gather(*tasks)

        elapsed = time.time() - start
        expected = topups * topup_amt + rewards * reward_amt

        # Fetch resulting balance
        r = await client.get(f"/wallet/{user}")
        r.raise_for_status()
        body = r.json()

        print(f"Elapsed: {elapsed:.2f}s")
        print(f"Expected balance: {expected}")
        print(f"Server balance:   {body.get('balance')}")
        if abs(body.get('balance', 0) - expected) < 1e-6:
            print("SUCCESS: balances match — no lost updates detected.")
        else:
            print("FAIL: balance mismatch — potential concurrency issue.")


def main():
    args = parse_args()
    try:
        asyncio.run(run_smoke(args))
    except Exception as e:
        print("Error during smoke test:", e)


if __name__ == "__main__":
    main()
