# A2A Demo Architecture & Flow

This document provides a high-level overview of the Agent-to-Agent (A2A) and X402 payment protocol integration.

## Conceptual Model

The conceptual model illustrates the main components involved in the A2A interaction.

```mermaid
graph TD
    User((User))
    
    subgraph "Client Side (a2a/client_agent)"
        ClientAgent[Client Agent UI]
        TaskStore[(Task Store)]
    end
    
    subgraph "Server Side (a2a/server)"
        MerchantServer[Merchant Server Agent]
        ServiceLogic[Business Logic]
    end
    
    subgraph "Blockchain Infrastructure"
        Facilitator[Payment Facilitator]
        Tron[(Tron Network)]
    end

    User <-->|Chat / Intent| ClientAgent
    ClientAgent <-->|Read / Write| TaskStore
    
    ClientAgent <-->|A2A RPC Protocol| MerchantServer
    MerchantServer <--> ServiceLogic
    
    MerchantServer -->|Submit Signed Tx / Verify Receipt| Facilitator
    Facilitator <-->|Verify / Settle| Tron
```

## Sequence Diagram

The following sequence diagram demonstrates a typical high-level flow when a Client Agent interacts with the Merchant Server, encountering an X402 Payment requirement.

```mermaid
sequenceDiagram
    actor User
    participant Client as Client Agent
    participant Server as Merchant Server
    participant Fac as Facilitator

    User->>Client: "I want to buy a banana"
    
    %% Initial Task Request
    Client->>Server: Create Task (A2A RPC Request)
    activate Server
    Server-->>Client: 402 Payment Required (X402 Payload)
    deactivate Server
    
    %% Payment Phase
    Note over Client: Client signs transaction<br/>using local private key
    Client->>Server: Submit Signed Transaction (RPC Request)
    activate Server
    Server->>Fac: Forward Signed Transaction
    activate Fac
    Fac-->>Server: Payment Receipt / Token
    deactivate Fac
    
    %% Resume Task with Payment
    Server->>Fac: Verify Receipt Validity
    Fac-->>Server: Valid
    
    %% Task Execution & Async Updates
    Server-->>Client: Task Created (Status: Pending)
    deactivate Server
    
    Note over Client, Server: Async Task Execution
    Server-->>Client: Task Status Update (Running)
    Server-->>Client: Task Artifact (e.g., Image/Text chunk)
    Server-->>Client: Task Status Update (Completed)
    
    %% Store updates and show to user
    Note over Client: Task Store updates state
    Client->>User: Display Result ("Here is your banana")
```
