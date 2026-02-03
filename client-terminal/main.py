#!/usr/bin/env python3
"""
X402 TRON Demo - Terminal Client
A command-line client that demonstrates x402 payment protocol with TRON.
"""

import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from x402.clients import X402Client
from x402.clients import X402HttpClient
from x402.mechanisms.client.tron_upto import UptoTronClientMechanism
from x402.signers.client import TronClientSigner

# Load environment variables
load_dotenv()

# Configuration
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
PROTECTED_ENDPOINT = "/protected"
TRON_PRIVATE_KEY = os.getenv("TRON_PRIVATE_KEY", "")
TRON_NETWORK = "nile"  # Default to Nile testnet
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "60"))


async def main():
    """Main entry point for terminal client"""
    print("=" * 80)
    print("X402 TRON Demo - Terminal Client")
    print("=" * 80)
    print(f"Server URL: {SERVER_URL}")
    print(f"Endpoint: {PROTECTED_ENDPOINT}")
    print(f"Network: {TRON_NETWORK}")
    print("=" * 80)
    print()

    # Check for private key
    if not TRON_PRIVATE_KEY:
        print("❌ Error: TRON_PRIVATE_KEY not found in environment")
        print()
        print("Please set TRON_PRIVATE_KEY in .env file or environment:")
        print("  export TRON_PRIVATE_KEY=your_private_key_here")
        print()
        print("You can get test TRX and USDT from:")
        print("  https://nileex.io/join/getJoinPage")
        sys.exit(1)

    try:
        # Initialize TRON signer
        print("Initializing TRON signer...")
        signer = TronClientSigner.from_private_key(
            TRON_PRIVATE_KEY,
            network=TRON_NETWORK,
        )
        buyer_address = signer.get_address()
        print(f"✓ Buyer address: {buyer_address}")
        print()

        # Initialize x402 client
        print("Initializing x402 client...")
        x402_client = X402Client()
        x402_client.register("tron:*", UptoTronClientMechanism(signer))

        timeout = httpx.Timeout(HTTP_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as http_client:
            client = X402HttpClient(http_client=http_client, x402_client=x402_client)
            print("✓ Client initialized")
            print()

            # Fetch protected resource
            print(f"Fetching protected resource from {SERVER_URL}{PROTECTED_ENDPOINT}...")
            print("(This will trigger 402 Payment Required if not paid)")
            print()

            result = await client.get(f"{SERVER_URL}{PROTECTED_ENDPOINT}")

        print("=" * 80)
        print("✅ SUCCESS - Resource Retrieved")
        print("=" * 80)
        print()

        # Check if result is an image
        content_type = result.headers.get("content-type", "")
        if content_type.startswith("image/"):
            # Save image to file
            output_file = Path("protected_image.png")
            output_file.write_bytes(result.content)
            print(f"✓ Image saved to: {output_file.absolute()}")
            print(f"  Size: {len(result.content)} bytes")
        else:
            # Print text/JSON response
            print("Response:")
            print(result.text)

        print()
        print("=" * 80)
        print("Payment completed successfully!")
        print("=" * 80)

    except httpx.ReadTimeout:
        print()
        print("=" * 80)
        print("❌ ERROR")
        print("=" * 80)
        print(
            "Error: HTTP request timed out. This can happen during on-chain settlement. "
            f"Try increasing HTTP_TIMEOUT_SECONDS (current: {HTTP_TIMEOUT_SECONDS})."
        )
        print()
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ERROR")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
