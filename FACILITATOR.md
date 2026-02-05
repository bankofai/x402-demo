# Facilitator Documentation

## Overview

The **Facilitator Module** handles payment validation and transaction settlement within the X402-Tron Demo. It acts as a trusted intermediary between the Resource Server and the TRON blockchain.

### Deployment Options
Developers have two choices for integrating a Facilitator:
1. **Custom Facilitator:** You can build and host your own Facilitator using the provided implementation in this repository.
2. **Official Facilitator:** Use the official X402 Facilitator service for managed settlement.
   - **Official Address:** *Coming soon...*

---

## Features

- **Permit Verification:** Validates payment requests signed by clients.
- **Transaction Settlement:** Executes TRON blockchain transactions.

---

## Configuration

### Environment Variables
1. **TRON_PRIVATE_KEY:** Used for blockchain interactions.
2. **FACILITATOR_URL:** Endpoint for permit submission.

Example `.env` configuration:
```env
TRON_PRIVATE_KEY=<private_key>
FACILITATOR_URL=http://localhost:8001
```

---

## API Endpoints

| Endpoint       | Method | Description                                |
|----------------|--------|--------------------------------------------|
| `/`            | `GET`  | Health check and system information.      |
| `/verify`      | `POST` | Verifies signed permits.                  |
| `/settle`      | `POST` | Confirms and processes blockchain payments.

**Example Request**:
```bash
curl -X POST http://localhost:8001/settle -d '{"permit": {...}}'
```

---

## Troubleshooting

1. **Invalid Permit Structure:**
   - Ensure permit follows TIP-712 standards.

2. **Fee Inaccuracy:**
   - Reconfigure `BASE_FEE` to match network conditions.

3. **Network Timeout:**
   - Increase `HTTP_TIMEOUT_SECONDS` in settings.

4. **Service Downtime:**
   - Restart using Docker Compose:
     ```bash
     docker-compose restart facilitator
     ```
