# x402-tron-demo

## Requirements

- Docker (recommended for quick start)
- Node.js + npm (for local `client-web` development)
- Python 3 (for local `server` / `facilitator` development)

## Configuration

Create `.env` at repo root:

```bash
TRON_PRIVATE_KEY=...   # Facilitator signing key
PAY_TO_ADDRESS=...     # Recipient TRON address
```

## Docker: build & run (docker compose)

1. Create and fill `.env`

2. Build & run

```bash
docker compose up -d --build
```

3. Open

- **Web (nginx)**: http://localhost:8080
- **Server API**: http://localhost:8000
- **Facilitator**: http://localhost:8001

4. Stop

```bash
docker compose down
```

## Local: build & run (step-by-step)

### 1. Backend

```bash
./server/start.sh
./facilitator/start.sh
```

### 2. Frontend

```bash
cd client-web
npm install
npm run dev
```

## Notes

- The architecture is `nginx -> server -> facilitator`. See `ARCHITECTURE.md`.
- Logs (Docker) are written to `./logs/`.
