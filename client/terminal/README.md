# X402 TRON Demo - Terminal Client

A command-line client that demonstrates the x402 payment protocol with TRON blockchain.

## Features

- Automatic payment handling when receiving 402 Payment Required
- Uses private key for signing (no browser wallet needed)
- Downloads and saves protected resources
- Supports Nile, Shasta, and Mainnet testnets

## Usage

### Prerequisites

1. Ensure you have installed dependencies:
```bash
pip install -r ../requirements.txt
```

2. Set up environment variables in `.env` file at project root:
```bash
TRON_PRIVATE_KEY=your_private_key_here
```

### Run the Client

From the project root directory:

```bash
python client-terminal/main.py
```

Or from this directory:

```bash
python main.py
```

### Configuration

You can configure the client by setting environment variables:

- `SERVER_URL`: Server URL (default: `http://localhost:8000`)
- `TRON_PRIVATE_KEY`: Your TRON private key for signing transactions
- `TRON_NETWORK`: Network to use (default: `nile`)

### Example Output

```
================================================================================
X402 TRON Demo - Terminal Client
================================================================================
Server URL: http://localhost:8000
Endpoint: /protected
Network: nile
================================================================================

Initializing TRON signer...
✓ Buyer address: TYourAddressHere...

Initializing x402 client...
✓ Client initialized

Fetching protected resource from http://localhost:8000/protected...
(This will trigger 402 Payment Required if not paid)

================================================================================
✅ SUCCESS - Resource Retrieved
================================================================================

✓ Image saved to: /path/to/protected_image.png
  Size: 12345 bytes

================================================================================
Payment completed successfully!
================================================================================
```

## Notes

- Make sure the server and facilitator are running before starting the client
- The client will automatically handle payment approval and signing
- Protected resources are saved to the current directory
