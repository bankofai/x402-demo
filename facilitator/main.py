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
from x402_tron.mechanisms.facilitator import ExactTronFacilitatorMechanism
from x402_tron.signers.facilitator import TronFacilitatorSigner
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
    accept: PaymentRequirements
    paymentPermitContext: dict | None = None

# Setup logging
setup_logging()

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")

# Configuration
TRON_PRIVATE_KEY = os.getenv("TRON_PRIVATE_KEY", "")

# Supported networks
SUPPORTED_NETWORKS = ["shasta", "nile"]

# Facilitator configuration
FACILITATOR_HOST = "0.0.0.0"
FACILITATOR_PORT = 8001
BASE_FEE = 100  # 0.0001 USDT (6 decimals) - Fee charged per transaction

if not TRON_PRIVATE_KEY:
    raise ValueError("TRON_PRIVATE_KEY environment variable is required")

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

# Get facilitator address from first signer
first_signer = TronFacilitatorSigner.from_private_key(
    TRON_PRIVATE_KEY,
    network=SUPPORTED_NETWORKS[0],
)
facilitator_address = first_signer.get_address()

# Initialize X402Facilitator
facilitator = X402Facilitator()

# Register mechanisms for each network
for network in SUPPORTED_NETWORKS:
    signer = TronFacilitatorSigner.from_private_key(
        TRON_PRIVATE_KEY,
        network=network,
    )
    mechanism = ExactTronFacilitatorMechanism(
        signer,
        fee_to=facilitator_address,
        base_fee=BASE_FEE,
    )
    facilitator.register([f"tron:{network}"], mechanism)

print("=" * 80)
print("X402 Payment Facilitator - Configuration")
print("=" * 80)
print(f"Facilitator Address: {facilitator_address}")
print(f"Base Fee: {BASE_FEE} (0.0001 USDT)")
print(f"Supported Networks: {', '.join(SUPPORTED_NETWORKS)}")

print(f"\nNetwork Details:")
for network in SUPPORTED_NETWORKS:
    network_key = f"tron:{network}"
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
    return facilitator.supported(fee_to=facilitator_address, pricing="flat")


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
        return await facilitator.fee_quote(request.accept, request.paymentPermitContext)
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
    print(f"Facilitator Address: {facilitator_address}")
    print(f"Supported Networks: {', '.join(SUPPORTED_NETWORKS)}")
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
