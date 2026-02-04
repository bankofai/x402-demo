# Server Documentation

## Overview

The **Resource Server** securely delivers resources protected by blockchain payments via the x402 payment protocol.

---

## Features

### Protected Resource Access
- Validates blockchain payments for resource delivery.
- Utilizes `/protected` endpoint to enforce access restrictions.

### Custom Resource Generation
- Generates unique images dynamically using the Pillow library.

---

## Configuration

### Environment Variables
1. **PAY_TO_ADDRESS:** TRON wallet receiving funds.
2. **FACILITATOR_URL:** Facilitator endpoint for permit validation.

Example `.env` file:
```env
PAY_TO_ADDRESS=<TRON_WALLET_ADDRESS>
FACILITATOR_URL=http://localhost:8001
```

---

## API Endpoints

| Endpoint      | Method | Description                      |
|---------------|--------|----------------------------------|
| `/`           | `GET`  | Provides server metadata.        |
| `/protected`  | `GET`  | Requires valid payment permits.  |

---

## Troubleshooting

1. **PAY_TO_ADDRESS Not Configured:**
   - Ensure `.env` file is properly set up.
   - Restart the server after any changes.

2. **Resource Delivery Errors:**
   - Check Facilitator service health using:
     ```bash
     curl http://localhost:8001/
     ```

3. **Slow Image Generation:**
   - Optimize Pillow processing by caching pre-generated assets.

4. **Service Downtime:**
   - Restart using Docker Compose:
     ```bash
     docker-compose restart server
     ```
