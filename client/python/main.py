#!/usr/bin/env python3
"""
X402 Demo - Terminal Client (Multi-Network)

Registers BOTH TRON and EVM mechanisms by default so the client can
handle 402 responses from any supported chain.  The server decides
which network(s) to accept; the SDK picks the best affordable option.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import httpx
import logging
from dotenv import load_dotenv
from bankofai.x402.clients import X402Client, X402HttpClient, SufficientBalancePolicy
from bankofai.x402.mechanisms.tron.exact_permit import ExactPermitTronClientMechanism
from bankofai.x402.mechanisms.tron.exact_gasfree.client import ExactGasFreeClientMechanism
from bankofai.x402.mechanisms.evm.exact_permit import ExactPermitEvmClientMechanism
from bankofai.x402.mechanisms.evm.exact import ExactEvmClientMechanism
from bankofai.x402.signers.client import TronClientSigner, EvmClientSigner
from bankofai.x402.tokens import TokenRegistry
from bankofai.x402.types import PaymentRequirements

# Custom policy to prefer exact_gasfree USDT
class PreferGasFreeUSDTPolicy:
    def __init__(self, client: X402Client) -> None:
        self._client = client

    async def apply(self, requirements: list[PaymentRequirements]) -> list[PaymentRequirements]:
        for req in requirements:
            token_info = TokenRegistry.find_by_address(req.network, req.asset)
            if req.scheme == "exact_gasfree" and token_info and token_info.symbol == "USDT":
                print(f"🎯 Policy: Force selecting {req.scheme} ({token_info.symbol})")
                return [req]
        return requirements

# Enable detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Configuration
TRON_PRIVATE_KEY = os.getenv("TRON_PRIVATE_KEY", "")
BSC_PRIVATE_KEY = os.getenv("BSC_PRIVATE_KEY", "")

# Server configuration
# Change ENDPOINT_PATH to target a different server resource.
# The server may return accepts[] spanning multiple networks.
RESOURCE_SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")
ENDPOINT_PATH = "/protected-nile"
# ENDPOINT_PATH = "/protected-mainnet"
# ENDPOINT_PATH = "/protected-bsc-testnet"
# ENDPOINT_PATH = "/protected-bsc-mainnet"
RESOURCE_URL = RESOURCE_SERVER_URL + ENDPOINT_PATH
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "60"))


if not TRON_PRIVATE_KEY:
    print("\n❌ Error: TRON_PRIVATE_KEY not set in .env file")
    print("\nPlease add your TRON private key to .env file\n")
    exit(1)

if not BSC_PRIVATE_KEY:
    print("\n❌ Error: BSC_PRIVATE_KEY not set in .env file")
    print("\nPlease add your EVM private key to .env file\n")
    exit(1)

async def main():
    print("=" * 80)
    print("X402 Payment Client (Multi-Network)")
    print("=" * 80)

    # --- Create signers for every chain family ---
    tron_signer = TronClientSigner.from_private_key(TRON_PRIVATE_KEY)
    evm_signer = EvmClientSigner.from_private_key(BSC_PRIVATE_KEY)

    # --- Register mechanisms for ALL networks ---
    x402_client = X402Client()
    x402_client.register("tron:*", ExactPermitTronClientMechanism(tron_signer))
    x402_client.register("tron:*", ExactGasFreeClientMechanism(tron_signer))
    x402_client.register("eip155:*", ExactPermitEvmClientMechanism(evm_signer))
    x402_client.register("eip155:*", ExactEvmClientMechanism(evm_signer))

    # Balance policy: auto-resolves signers from registered mechanisms
    x402_client.register_policy(SufficientBalancePolicy)
    # Register custom selection policy (AFTER balance check)
    x402_client.register_policy(PreferGasFreeUSDTPolicy)

    print(f"TRON Address: {tron_signer.get_address()}")
    print(f"EVM  Address: {evm_signer.get_address()}")
    print(f"Resource URL: {RESOURCE_URL}")

    print(f"\nSupported Networks and Tokens:")
    for network_name in ["tron:mainnet", "tron:nile", "tron:shasta", "eip155:97"]:
        tokens = TokenRegistry.get_network_tokens(network_name)
        print(f"  {network_name}:")
        if not tokens:
            print("    (no tokens registered)")
        else:
            for symbol, info in tokens.items():
                print(f"    {symbol}: {info.address} (decimals={info.decimals})")
    print("=" * 80)
    
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as http_client:
            client = X402HttpClient(http_client, x402_client)
            
            print(f"\nRequesting: {RESOURCE_URL}")
            # 发起请求（自动处理 402 支付）
            response = await client.get(RESOURCE_URL)
            print(f"\n✅ Success!")
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Content-Length: {len(response.content)} bytes")
            
            # Parse payment response if present
            payment_response = response.headers.get('payment-response')
            if payment_response:
                from bankofai.x402.encoding import decode_payment_payload
                from bankofai.x402.types import SettleResponse
                settle_response = decode_payment_payload(payment_response, SettleResponse)
                print(f"\n📋 Payment Response:")
                print(f"  Success: {settle_response.success}")
                print(f"  Network: {settle_response.network}")
                print(f"  Transaction: {settle_response.transaction}")
                if settle_response.error_reason:
                    print(f"  Error: {settle_response.error_reason}")
            
            # Handle response based on content type
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                print(f"\nResponse: {response.json()}")
            elif 'image/' in content_type:
                ext = "png"
                if "jpeg" in content_type or "jpg" in content_type:
                    ext = "jpg"
                elif "webp" in content_type:
                    ext = "webp"

                with tempfile.NamedTemporaryFile(prefix="x402_", suffix=f".{ext}", delete=False, dir="/tmp") as f:
                    f.write(response.content)
                    saved_path = f.name
                print(f"\n🖼️  Received image file, saved to: {saved_path}")
            else:
                print(f"\nResponse (first 200 chars): {response.text[:200]}")

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
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
