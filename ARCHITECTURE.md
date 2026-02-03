# x402-tron-demo Architecture

## Overall Architecture

```
┌─────────────────────────────────────────────────────┐
│        Docker Container (x402-tron-demo)            │
│                                                     │
│  ┌──────────┐  ┌─────────────────────────────────┐ │
│  │  nginx   │  │  supervisord (process manager)  │ │
│  │  :80     │  └─────────────────────────────────┘ │
│  └────┬─────┘                                       │
│       │                                             │
│       ├─→ / (static files)                          │
│       │   └─→ /usr/share/nginx/html                │
│       │       (client-web React app)               │
│       │                                             │
│       └─→ /api/* (API requests)                     │
│           │                                         │
│           ▼                                         │
│      ┌─────────────┐                                │
│      │   server    │  internal calls                │
│      │   :8000     │ ──────────┐                   │
│      └─────────────┘           │                   │
│                                 ▼                   │
│                          ┌──────────────┐          │
│                          │ facilitator  │          │
│                          │   :8001      │          │
│                          └──────────────┘          │
│                                                     │
│  Logs: /app/logs/                                   │
│    - access.log (nginx)                            │
│    - server-stdout.log                             │
│    - facilitator-stdout.log                        │
└─────────────────────────────────────────────────────┘
```

## Request Flow

### 1. Frontend Access
```
Browser → nginx:80 → /usr/share/nginx/html (React static files)
```

### 2. API Request Flow
```
Frontend JavaScript → nginx:80/api/* → server:8000
```

### 3. Payment Verification Flow
```
server:8000 → facilitator:8001 (internal, localhost)
            → TRON blockchain (verify signature and execute transaction)
```

## Ports

- **80**: nginx (exposed)
  - Static file hosting
  - API reverse proxy

- **8000**: server (inside container)
  - FastAPI backend
  - Handles payment requests
  - Calls facilitator

- **8001**: facilitator (inside container)
  - FastAPI service
  - Verifies payment signatures
  - Executes on-chain transactions

## Service Communication

### External Access
- Users only need to access `http://localhost:80`
- All API requests go through `/api/*`

### Internal Communication
- The server accesses the facilitator via `http://localhost:8001`
- Communication uses localhost inside the same container
- No need to expose the facilitator port externally

## Data Flow

```
1. User clicks the pay button
  ↓
2. Frontend checks USDT allowance
  ↓
3. If allowance is insufficient, trigger TronLink approval
  ↓
4. Frontend asks TronLink to sign the PaymentPermit
  ↓
5. Frontend sends the signature to the server (/api/protected)
  ↓
6. Server verifies the signature and calls the facilitator (/verify)
  ↓
7. Facilitator verifies the signature and submits the on-chain transaction
  ↓
8. After confirmation, return the result
  ↓
9. Server returns the protected resource to the frontend
```

## Environment Variables

All services share the following environment variables (loaded from the `.env` file):

- `TRON_PRIVATE_KEY`: Facilitator private key used to sign transactions
- `PAY_TO_ADDRESS`: Recipient address

## Logs

All service logs are stored under `/app/logs/`:

- `access.log`: nginx access log
- `error.log`: nginx error log
- `server-stdout.log`: server application log
- `server-stderr.log`: server error log
- `facilitator-stdout.log`: facilitator application log
- `facilitator-stderr.log`: facilitator error log
- `supervisord.log`: process manager log

## Deployment

### Development
```bash
# Run locally (without Docker)
./server/start.sh
./facilitator/start.sh
cd client-web && npm run dev
```

### Production
```bash
# Deploy with Docker
docker-compose up -d
```

## Security Considerations

1. **Private key management**:
   - Use environment variables or Docker secrets
   - Do not commit `.env` into version control

2. **CORS configuration**:
   - Restrict `allow_origins` in production
   - Current `*` setting is for development only

3. **Network isolation**:
   - The facilitator is not exposed directly
   - Only the server can access it

4. **Log safety**:
   - Do not log sensitive information (private keys, signatures, etc.)
   - Rotate/clean up log files regularly
