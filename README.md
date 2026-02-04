# X402-Tron Demo

## Overview

The **X402-Tron Demo** provides a practical demonstration of integrating the **x402 payment protocol** with the TRON blockchain. While not a fully-fledged application, this demo aims to showcase how decentralized micropayments can be used to enable pay-per-access workflows.

### Key Concept: Payment Workflow Simulation

The demo simulates a payment workflow involving three conceptual agents:
1. The **Client Agent** requests access to protected resources from the **Server Agent**.
2. Upon receiving a `402 Payment Required` challenge, the Client signs a cryptographic permit to meet payment requirements.
3. The **Facilitator Agent** validates the signed permit and settles the transaction on the TRON blockchain.
4. Once payment confirmation is complete, the Server delivers the requested resource.

Though the implementation relies on standard Python services, the demo is designed to illustrate the x402 payment flow conceptually. It demonstrates:
- Cryptographic payment permits (TIP-712 format).
- Blockchain transaction validation and settlement.

---

## Table of Contents
1. [Core Components](#core-components)
2. [Environment Setup](#environment-setup)
3. [Quick Start](#quick-start)
4. [License](#license)
5. [Additional Documentation](#additional-documentation)

---

## Core Components

### **Server: Resource Provider**
- **Purpose:** Hosts protected resources requiring blockchain-based payments.
- **Implementation:**
  - Verifies cryptographic payment receipts.
  - Securely delivers resources upon payment validation.

### **Facilitator: Payment Processor**
- **Purpose:** Intermediates payment validation and transaction settlement on the blockchain.
- **Implementation:**
  - Validates signed payment permits (TIP-712).
  - Settles micropayments using the TRON Nile Testnet.

### **Client: Resource Requester**
- **CLI Client:** Automates permit signing and resource retrieval workflows.
- **Web Client:** Offers a user-friendly interface for interacting with TronLink wallets.

---

## Environment Setup

### Prerequisites
- **Python 3.9+** (for local execution)
- **Node.js 18+** (for Web Client development)
- **Docker** (optional, for containerized deployment)

### Configuration
Before running the demo, create a `.env` file in the project root:

```env
# TRON private key for Facilitator's blockchain interactions.
TRON_PRIVATE_KEY=<your_tron_private_key>

# Payment recipient address for Server.
PAY_TO_ADDRESS=<server_recipient_tron_address>

# Service URLs (defaults)
SERVER_URL=http://localhost:8000
FACILITATOR_URL=http://localhost:8001
HTTP_TIMEOUT_SECONDS=60
```

---

## Quick Start

### Using Scripts
Quickly start the demo services using the provided scripts:

```bash
# Start Facilitator
./start.sh facilitator

# Start Server
./start.sh server

# Run Terminal Client
./start.sh client

# Start Web Client (Development)
cd client/web && npm run dev
```

### Using Docker
Alternatively, deploy all services with Docker Compose:
```bash
docker-compose up -d
```
Access the Web Client at `http://localhost:8080` and Server at `http://localhost:8000`.

---

## License

This project is open source under the **MIT License**. See the [LICENSE](LICENSE.md) file for more information.

---

## Additional Documentation

- **System Architecture:** Explore inter-component communication in [ARCHITECTURE.md](ARCHITECTURE.md).
- **Server Details:** Resource management info in [SERVER.md](SERVER.md).
- **Facilitator Details:** Payment processing insights in [FACILITATOR.md](FACILITATOR.md).
- **Client Details:** Instructions for CLI and web demo in [CLIENT.md](CLIENT.md).