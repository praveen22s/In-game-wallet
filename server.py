from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import asyncio
import time
import logging
from collections import deque

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kraft Wallet - In-Memory Backend")

# --- In-memory stores (no database) ---
wallets: Dict[str, float] = {}
locks: Dict[str, asyncio.Lock] = {}
idempotency: Dict[str, Dict[str, Any]] = {}
recent_ops: Dict[str, deque] = {}

RECENT_OPS_MAX = 10


def get_lock(user_id: str) -> asyncio.Lock:
    if user_id not in locks:
        locks[user_id] = asyncio.Lock()
    return locks[user_id]


def get_recent(user_id: str) -> deque:
    if user_id not in recent_ops:
        recent_ops[user_id] = deque(maxlen=RECENT_OPS_MAX)
    return recent_ops[user_id]


class TopUpReq(BaseModel):
    userId: str = Field(..., alias="userId")
    amountUSD: float = Field(..., gt=0)
    idempotencyKey: str


class RewardReq(BaseModel):
    userId: str
    amountCoins: float = Field(..., gt=0)
    rewardId: str
    idempotencyKey: str


@app.post("/wallet/topup")
async def topup(req: TopUpReq):
    # Idempotency check
    key = req.idempotencyKey
    if key in idempotency:
        # If payload matches previously stored payload, return saved response
        entry = idempotency[key]
        if entry.get("payload") == req.model_dump(by_alias=True, exclude={"idempotencyKey"}):
            logger.info(f"Idempotency hit for topup key={key}, returning cached result")
            return entry["result"]
        raise HTTPException(status_code=409, detail="Idempotency key used with different payload")

    user_id = req.userId
    amount = float(req.amountUSD)  # 1 USD == 1 Kraft Coin

    # Acquire per-user lock
    lock = get_lock(user_id)
    async with lock:
        bal = wallets.get(user_id, 0.0)
        bal += amount
        wallets[user_id] = bal
        logger.info(f"Topup: user={user_id}, amount={amount}, new_balance={bal}")

        op = {"type": "topup", "amount": amount, "timestamp": time.time()}
        get_recent(user_id).appendleft(op)

        result = {"balance": wallets[user_id], "op": op}

    # store idempotency result
    idempotency[key] = {"payload": req.model_dump(by_alias=True, exclude={"idempotencyKey"}), "result": result, "timestamp": time.time()}
    return result


@app.post("/game/reward")
async def reward(req: RewardReq):
    key = req.idempotencyKey
    if key in idempotency:
        entry = idempotency[key]
        if entry.get("payload") == req.model_dump(exclude={"idempotencyKey"}):
            logger.info(f"Idempotency hit for reward key={key}, returning cached result")
            return entry["result"]
        raise HTTPException(status_code=409, detail="Idempotency key used with different payload")

    user_id = req.userId
    amount = float(req.amountCoins)

    lock = get_lock(user_id)
    async with lock:
        bal = wallets.get(user_id, 0.0)
        bal += amount
        wallets[user_id] = bal
        logger.info(f"Reward: user={user_id}, amount={amount}, new_balance={bal}")

        op = {"type": "reward", "amount": amount, "rewardId": req.rewardId, "timestamp": time.time()}
        get_recent(user_id).appendleft(op)

        result = {"balance": wallets[user_id], "op": op}

    idempotency[key] = {"payload": req.model_dump(exclude={"idempotencyKey"}), "result": result, "timestamp": time.time()}
    return result


@app.get("/wallet/{user_id}")
async def get_wallet(user_id: str):
    bal = wallets.get(user_id, 0.0)
    recent = list(get_recent(user_id))
    return {"balance": bal, "recentOps": recent}


@app.get("/debug/state")
async def debug_state():
    """Debug endpoint to inspect server state (operations count)"""
    total_ops = sum(len(get_recent(uid)) for uid in wallets.keys())
    total_idempotency_keys = len(idempotency)
    return {
        "wallets": wallets,
        "total_operations": total_ops,
        "total_unique_idempotency_keys": total_idempotency_keys,
        "users": list(wallets.keys())
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="127.0.0.1", port=8000, log_level="info")
