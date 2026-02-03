# X402-tron Demo

A complete demonstration of the **x402 payment protocol** on the TRON blockchain.

## What is this project?

This is a complete example demonstrating how to use the **x402 protocol** (HTTP 402 Payment Required) to implement "pay-first, access-later" functionality on the TRON blockchain.

**Core Components:**
- **Server**: Provides protected resources (requires payment to access)
- **Facilitator**: Handles payment verification and on-chain settlement
- **Client**: Two client implementations
  - `client/web`: React web version (payment via TronLink wallet)
  - `client/terminal`: Python CLI version (automatic payment via private key)

**Payment Flow:**
1. Client requests protected resource
2. Server returns 402 Payment Required + payment requirements
3. Client signs payment permit (PaymentPermit)
4. Facilitator verifies signature and executes on-chain transfer
5. Server returns protected resource

---

## Requirements

- **Docker** (recommended for Scenario 2)
- **Python 3.12+** (for Scenario 1 or local development)
- **Node.js 18+** (only for client web local development)
- **TRON Wallet** (TronLink browser extension for client web)

---

## Step 1: Environment Setup

### 1. Clone Repository

```bash
git clone <repo-url>
cd x402-tron-demo
```

### 2. Create `.env` File

Create a `.env` file in the project root with the following content:

```bash
# Facilitator's TRON private key (for signing and settlement)
TRON_PRIVATE_KEY=your_private_key_here

# Payment recipient address (TRON address for Server to receive payments)
PAY_TO_ADDRESS=your_tron_address_here
```

**Get Test Tokens:**
- Visit [Nile Testnet Faucet](https://nileex.io/join/getJoinPage)
- Get test TRX and USDT

---

## Scenario 1: Terminal Client + Local Services

**Best for:** Developer quick testing, automation scripts

### Step 1: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Start Backend Services

**Terminal 1 - Start Facilitator:**
```bash
./start.sh facilitator
```

**Terminal 2 - Start Server:**
```bash
./start.sh server
```

Services will print supported networks and tokens on startup.

### Step 3: Run Terminal Client

**Terminal 3:**
```bash
./start.sh client
# or directly: python client/terminal/main.py
```

The client will:
1. Automatically request protected resource
2. Automatically sign and pay upon receiving 402
3. Download and save image to `protected_image.png`

**View Result:**
```bash
open protected_image.png  # macOS
# or
xdg-open protected_image.png  # Linux
```

---

## Scenario 2: Web Client + Docker Container

**Best for:** Demo to non-technical users, production deployment

### Step 1: Ensure `.env` is Configured

Refer to "Step 1: Environment Setup".

### Step 2: Start Docker Container

```bash
docker compose up -d --build
```

This starts a container with the following services:
- **Nginx** (port 8080): Hosts client web
- **Server** (port 8000): Provides protected resources
- **Facilitator** (port 8001): Handles payments

### Step 3: Open Browser

Visit: **http://localhost:8080**

### Step 4: Connect Wallet and Pay

1. Click **"Connect Wallet"**
2. Select TronLink wallet
3. **Ensure wallet is switched to Nile or Shasta testnet**
4. Click **"Pay now"**
5. In TronLink:
   - First time: Approve USDT
   - Second time: Sign payment permit
6. Wait for transaction confirmation
7. View protected image (with request number)

### Step 5: Stop Container

```bash
docker compose down
```

---

## FAQ

### Q1: "Unsupported network" error
**A:** client web only supports **Nile** and **Shasta** testnets. Please switch network in TronLink and reconnect wallet.

### Q2: Terminal client error "TRON_PRIVATE_KEY not found"
**A:** Ensure `.env` file exists in project root and contains `TRON_PRIVATE_KEY=...`.

### Q3: Docker build fails
**A:** Ensure Docker is running and has sufficient disk space. Try:
```bash
docker system prune -a  # Clean cache
docker compose up -d --build
```

### Q4: How to view Docker logs?
**A:** 
```bash
docker compose logs -f
```

### Q5: Image not displayed after payment
**A:** Check browser console (F12) and Docker logs to confirm:
- Facilitator successfully verified signature
- On-chain transfer succeeded
- Server returned image

---

## Project Structure

```
x402-tron-demo/
├── requirements.txt          # Python dependencies (unified)
├── start.sh                  # Unified startup script
├── .env                      # Environment variables (create yourself)
├── client/                   # Clients
│   ├── terminal/             # Terminal client (CLI)
│   │   ├── main.py
│   │   └── README.md
│   └── web/                  # React web client
├── server/                   # Protected resource server
│   └── main.py
├── facilitator/              # Payment processing service
│   └── main.py
├── docker-compose.yml        # Docker orchestration
├── Dockerfile                # Multi-stage build
└── README.md                 # This file
```

---

## Tech Stack

- **Blockchain**: TRON (Nile/Shasta Testnet)
- **Protocol**: x402 (HTTP 402 Payment Required)
- **Backend**: Python + FastAPI + x402-tron SDK
- **Frontend**: React + TypeScript + TronLink Adapter
- **Signing**: EIP-712 / TIP-712 (Typed Data)
- **Container**: Docker + Nginx + Supervisord

---

## More Information

- **Architecture**: See `ARCHITECTURE.md`
- **x402 Protocol**: https://github.com/open-aibank/x402-tron
- **TRON Docs**: https://developers.tron.network/

---

## License

MIT
