# Architecture

## Overview
This demo implements the **x402 payment protocol** to monetize resources on the TRON blockchain. It consists of three lightweight components interacting via HTTP and on-chain transactions.

## Workflow

```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant Facilitator
    participant TRON

    Client->>Server: Request /protected
    Server-->>Client: 402 Payment Required
    Client->>Client: Sign Permit (TIP-712)
    Client->>Facilitator: Settle Payment
    Facilitator->>TRON: Broadcast Transaction
    Facilitator-->>Client: Payment Receipt
    Client->>Server: Request with Receipt
    Server-->>Client: Resource Delivered
```

## Components

| Component | Role | Tech Stack |
|-----------|------|------------|
| **Client** | Requests resources & signs payments | Python CLI / React + TronLink |
| **Server** | Hosts protected resources | Python (FastAPI) |
| **Facilitator** | Verifies & settles payments on-chain | Python (FastAPI) |
