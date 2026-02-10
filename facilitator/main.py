"""
Facilitator Main Entry Point
Starts a FastAPI server for facilitator operations with full payment flow support.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from x402_tron.logging_config import setup_logging
from x402_tron.facilitator import X402Facilitator
from x402_tron.mechanisms.facilitator import ExactTronFacilitatorMechanism, ExactEvmFacilitatorMechanism
from x402_tron.mechanisms.native_exact import NativeExactEvmFacilitatorMechanism
from x402_tron.signers.facilitator import TronFacilitatorSigner, EvmFacilitatorSigner
from x402_tron.config import NetworkConfig
from x402_tron.tokens import TokenRegistry
from x402_tron.types import (
    PaymentPayload,
    PaymentRequirements,
    SupportedFee,
)
from pydantic import BaseModel


class VerifyRequest(BaseModel):
    """Verify request model"""
    paymentPayload: PaymentPayload
    paymentRequirements: PaymentRequirements


class SettleRequest(BaseModel):
    """Settle request model"""
    paymentPayload: PaymentPayload
    paymentRequirements: PaymentRequirements


class FeeQuoteRequest(BaseModel):
    """Fee quote request model"""
    accepts: list[PaymentRequirements]
    paymentPermitContext: dict | None = None

# Setup logging
setup_logging()

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")

# Configuration
TRON_PRIVATE_KEY = os.getenv("TRON_PRIVATE_KEY", "")
BSC_PRIVATE_KEY = os.getenv("BSC_PRIVATE_KEY", "")

# Facilitator configuration
FACILITATOR_HOST = "0.0.0.0"
FACILITATOR_PORT = 8001
# TRON supported networks
TRON_NETWORKS = ["mainnet", "shasta", "nile"]

# Fee config per token (smallest unit)
TRON_BASE_FEE = {
    "USDT": 100,       # 0.0001 USDT (6 decimals)
    "USDD": 100_000_000_000_000,  # 0.0001 USDD (18 decimals)
}
BSC_BASE_FEE = {
    "USDT": 100_000_000_000_000,      # 0.0001 USDT (18 decimals on BSC testnet)
    "USDC": 100_000_000_000_000,      # 0.0001 USDC (18 decimals on BSC testnet)
}
BSC_MAINNET_BASE_FEE = {
    "EPS": 100_000_000_000_000,       # 0.0001 EPS (18 decimals on BSC mainnet)
}

if not TRON_PRIVATE_KEY:
    raise ValueError("TRON_PRIVATE_KEY environment variable is required")
if not BSC_PRIVATE_KEY:
    raise ValueError("BSC_PRIVATE_KEY environment variable is required")

# Initialize FastAPI app
app = FastAPI(
    title="X402 Facilitator",
    description="Facilitator service for X402 payment protocol",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get facilitator addresses
bsc_signer = EvmFacilitatorSigner.from_private_key(
    BSC_PRIVATE_KEY,
    network=NetworkConfig.BSC_TESTNET,
)
bsc_facilitator_address = bsc_signer.get_address()

# Initialize X402Facilitator
facilitator = X402Facilitator()

# Register TRON mechanisms
for network in TRON_NETWORKS:
    signer = TronFacilitatorSigner.from_private_key(
        TRON_PRIVATE_KEY,
        network=network,
    )
    mechanism = ExactTronFacilitatorMechanism(
        signer,
        base_fee=TRON_BASE_FEE,
    )
    facilitator.register([f"tron:{network}"], mechanism)

# Register BSC testnet mechanisms (exact + native_exact)
bsc_exact_mechanism = ExactEvmFacilitatorMechanism(
    bsc_signer,
    fee_to=bsc_facilitator_address,
    base_fee=BSC_BASE_FEE,
)
facilitator.register([NetworkConfig.BSC_TESTNET], bsc_exact_mechanism)

bsc_native_mechanism = NativeExactEvmFacilitatorMechanism(
    bsc_signer,
)
facilitator.register([NetworkConfig.BSC_TESTNET], bsc_native_mechanism)

# Register BSC mainnet mechanisms (exact + native_exact)
bsc_mainnet_signer = EvmFacilitatorSigner.from_private_key(
    BSC_PRIVATE_KEY,
    network=NetworkConfig.BSC_MAINNET,
)
bsc_mainnet_facilitator_address = bsc_mainnet_signer.get_address()

bsc_mainnet_exact_mechanism = ExactEvmFacilitatorMechanism(
    bsc_mainnet_signer,
    fee_to=bsc_mainnet_facilitator_address,
    base_fee=BSC_MAINNET_BASE_FEE,
)
facilitator.register([NetworkConfig.BSC_MAINNET], bsc_mainnet_exact_mechanism)

bsc_mainnet_native_mechanism = NativeExactEvmFacilitatorMechanism(
    bsc_mainnet_signer,
)
facilitator.register([NetworkConfig.BSC_MAINNET], bsc_mainnet_native_mechanism)

print("=" * 80)
print("X402 Payment Facilitator - Configuration")
print("=" * 80)
print(f"BSC  Facilitator Address: {bsc_facilitator_address}")
print(f"TRON Base Fee: {TRON_BASE_FEE}")
print(f"BSC  Base Fee: {BSC_BASE_FEE}")

all_networks = [f"tron:{n}" for n in TRON_NETWORKS] + [NetworkConfig.BSC_MAINNET, NetworkConfig.BSC_TESTNET]
print(f"Supported Networks: {', '.join(all_networks)}")

print(f"\nNetwork Details:")
for network_key in all_networks:
    print(f"  {network_key}:")
    print(f"    PaymentPermit: {NetworkConfig.get_payment_permit_address(network_key)}")
    tokens = TokenRegistry.get_network_tokens(network_key)
    if tokens:
        for symbol, info in tokens.items():
            print(f"    {symbol}: {info.address} (decimals={info.decimals})")
print("=" * 80)

@app.get("/supported")
def supported():
    """Get supported capabilities"""
    return facilitator.supported(pricing="flat")


@app.post("/fee/quote")
async def fee_quote(request: FeeQuoteRequest):
    """
    Get fee quote for payment requirements
    
    Args:
        request: Fee quote request with payment requirements
        
    Returns:
        Fee quote response with fee details
    """
    try:
        return await facilitator.fee_quote(request.accepts, request.paymentPermitContext)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verify")
async def verify(request: VerifyRequest):
    """
    Verify payment payload
    
    Args:
        request: Verify request with payment payload and requirements
        
    Returns:
        Verification result
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[VERIFY REQUEST] Payload: {request.paymentPayload.model_dump(by_alias=True)}")
    
    try:
        result = await facilitator.verify(request.paymentPayload, request.paymentRequirements)
        logger.info(f"[VERIFY RESULT] {result.model_dump(by_alias=True)}")
        return result
    except Exception as e:
        logger.error(f"[VERIFY ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/settle")
async def settle(request: SettleRequest):
    """
    Settle payment on-chain
    
    Args:
        request: Settle request with payment payload and requirements
        
    Returns:
        Settlement result with transaction hash
    """
    try:
        return await facilitator.settle(request.paymentPayload, request.paymentRequirements)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Start the facilitator server"""
    print("\n" + "=" * 80)
    print("Starting X402 Facilitator Server")
    print("=" * 80)
    print(f"Host: {FACILITATOR_HOST}")
    print(f"Port: {FACILITATOR_PORT}")
    print(f"BSC  Facilitator Address: {bsc_facilitator_address}")
    print(f"Supported Networks: {', '.join(all_networks)}")
    print("=" * 80)
    print("\nEndpoints:")
    print(f"  GET  http://{FACILITATOR_HOST}:{FACILITATOR_PORT}/supported")
    print(f"  POST http://{FACILITATOR_HOST}:{FACILITATOR_PORT}/fee/quote")
    print(f"  POST http://{FACILITATOR_HOST}:{FACILITATOR_PORT}/verify")
    print(f"  POST http://{FACILITATOR_HOST}:{FACILITATOR_PORT}/settle")
    print("=" * 80 + "\n")
    
    uvicorn.run(
        app,
        host=FACILITATOR_HOST,
        port=FACILITATOR_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
