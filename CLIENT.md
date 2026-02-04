# Client Documentation

## Overview

The **Client Module** enables direct user interaction with resources protected by the x402 payment protocol. Two implementations are provided: **Terminal Client (CLI)** and **Web Client**.

## Configuration

### Environment Variables
1. **SERVER_URL:** Address of the Resource Server.
2. **TRON_PRIVATE_KEY:** Used for CLI transactions.
3. **FACILITATOR_URL:** Facilitator API endpoint.

Example `.env` configuration:
```env
SERVER_URL=http://localhost:8000
TRON_PRIVATE_KEY=<private_key>
FACILITATOR_URL=http://localhost:8001
```

---

## Usage

### Terminal Client

**Features**:
- Automated transaction submissions.
- Automatic resource retrieval upon payment.

**Workflow**:
1. Requests `/protected` endpoint triggering `402 Payment Required`.
2. Signs payment permits.
3. Submits permits to Facilitator.
4. Retrieves resource once validated.

**Run Command**:
```bash
./start.sh client
```

### Web Client

**Features**:
- User-friendly interface powered by React.
- Wallet integration using TronLink.
- Permit signing via Web UI.

**Run Locally**:
```bash
cd client/web
npm install
npm run dev
```
Access Web Client at `http://localhost:5173`.

---

## Troubleshooting

### Terminal Client

1. **TRON_PRIVATE_KEY Not Found:**
   - Ensure `.env` file exists in project root with the correct key.

2. **HTTP Timeout:**
   - If on-chain settlement is slow, increase `HTTP_TIMEOUT_SECONDS` in `.env`.

### Web Client

1. **Unsupported Network:**
   - Ensure TronLink is set to **Nile** or **Shasta** testnet.

2. **CORS Errors:**
   - Check if Server and Facilitator have CORSMiddleware configured (they are by default in this demo).
