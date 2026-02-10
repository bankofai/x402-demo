#!/usr/bin/env python3
"""
X402 TRON Demo - Terminal Client
A command-line client that demonstrates x402 payment protocol with TRON.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import httpx
import logging
from dotenv import load_dotenv
from x402_tron.clients import X402Client, X402HttpClient, SufficientBalancePolicy
from x402_tron.config import NetworkConfig
from x402_tron.mechanisms.tron.exact_permit import ExactPermitTronClientMechanism
from x402_tron.mechanisms.evm.exact_permit import ExactPermitEvmClientMechanism
from x402_tron.mechanisms.evm.exact import ExactEvmClientMechanism
from x402_tron.signers.client import TronClientSigner, EvmClientSigner
from x402_tron.tokens import TokenRegistry

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

# Network selection - Change this to use different networks
# TRON options: NetworkConfig.TRON_MAINNET, NetworkConfig.TRON_NILE, NetworkConfig.TRON_SHASTA
# EVM options:  NetworkConfig.BSC_TESTNET, NetworkConfig.BSC_MAINNET
CURRENT_NETWORK = NetworkConfig.TRON_NILE
# CURRENT_NETWORK = NetworkConfig.TRON_MAINNET
# CURRENT_NETWORK = NetworkConfig.BSC_TESTNET
# CURRENT_NETWORK = NetworkConfig.BSC_MAINNET

# Server configuration
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

if CURRENT_NETWORK.startswith("eip155:") and not BSC_PRIVATE_KEY:
    print("\n❌ Error: BSC_PRIVATE_KEY not set in .env file")
    print("\nPlease add your EVM private key to .env file\n")
    exit(1)

async def main():
    print("=" * 80)
    print("X402 Payment Client - Configuration")
    print("=" * 80)

    # Setup client based on network type
    x402_client = X402Client()

    if CURRENT_NETWORK.startswith("tron:"):
        network = CURRENT_NETWORK.split(":")[-1]
        signer = TronClientSigner.from_private_key(TRON_PRIVATE_KEY, network=network)
        x402_client.register(CURRENT_NETWORK, ExactPermitTronClientMechanism(signer))
        x402_client.register_policy(SufficientBalancePolicy(signer))
    elif CURRENT_NETWORK.startswith("eip155:"):
        signer = EvmClientSigner.from_private_key(BSC_PRIVATE_KEY, network=CURRENT_NETWORK)
        x402_client.register(CURRENT_NETWORK, ExactPermitEvmClientMechanism(signer))
        x402_client.register(CURRENT_NETWORK, ExactEvmClientMechanism(signer))
    else:
        print(f"\n❌ Error: Unsupported network: {CURRENT_NETWORK}")
        exit(1)

    print(f"Current Network: {CURRENT_NETWORK}")
    print(f"Client Address: {signer.get_address()}")
    print(f"Resource URL: {RESOURCE_URL}")
    print(f"PaymentPermit Contract: {NetworkConfig.get_payment_permit_address(CURRENT_NETWORK)}")

    print(f"\nSupported Networks and Tokens:")
    for network_name in ["tron:mainnet", "tron:nile", "tron:shasta", "eip155:97"]:
        tokens = TokenRegistry.get_network_tokens(network_name)
        is_current = " (CURRENT)" if network_name == CURRENT_NETWORK else ""
        print(f"  {network_name}{is_current}:")
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
                from x402_tron.encoding import decode_payment_payload
                from x402_tron.types import SettleResponse
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
