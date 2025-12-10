# In game Wallet — In-memory Backend (no DB)
 
Quick demo & evaluation-ready implementation of the Wallet & Rewards backend using in-memory stores only 

Features

Run locally (recommended)





This repository implements a small in-memory Wallet & Rewards backend (no database) that demonstrates atomic per-user updates, idempotent requests, and safe concurrency for top-ups and rewards.

Quick run & test (copy-paste into PowerShell from the project root ):

1) Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

2) Start the server (leave this terminal open):

```powershell
python server.py
# or (alternative)
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

3) In a second terminal run the demo client (shows topup, retry idempotency, reward, and final balance):

```powershell
python examples\client_demo.py
```

4) Run the smoke concurrency script (example):

```powershell
python examples\smoke_concurrency.py --user smoke1 --topups 50 --rewards 50 --topup-amt 5 --reward-amt 3
```

5) Run the automated tests (concurrency & stress tests included, including new smoke simulation):

```powershell
python -m pytest -v
```

**Test output**: 4 passed with 0 warnings (Pydantic v2 compatible, no deprecation issues)

Optional Docker:

```powershell
docker build -t kraft-wallet .
docker compose up --build
# then visit http://localhost:8000/docs
```

API Endpoints
- POST `/wallet/topup` — Body: `{ userId, amountUSD, idempotencyKey }`
- POST `/game/reward` — Body: `{ userId, amountCoins, rewardId, idempotencyKey }`
- GET `/wallet/{userId}` — Returns `{"balance": number, "recentOps": [...]}`

Notes
- No external database is used; state is kept in memory (resets on restart) . The included smoke test and pytest suite validate that concurrent topups and rewards do not lose updates.
