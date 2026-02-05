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
from x402_tron.mechanisms.facilitator import UptoTronFacilitatorMechanism
from x402_tron.signers.facilitator import TronFacilitatorSigner
from x402_tron.config import NetworkConfig
from x402_tron.tokens import TokenRegistry
from x402_tron.types import (
    PaymentPayload,
    PaymentRequirements,
    VerifyResponse,
    SettleResponse,
    FeeQuoteResponse,
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

# Network selection - Change this to use different networks
# Options: "mainnet", "nile", "shasta"
TRON_NETWORK = "nile"
CURRENT_NETWORK = f"tron:{TRON_NETWORK}"

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

# Initialize facilitator
facilitator_signer = TronFacilitatorSigner.from_private_key(
    TRON_PRIVATE_KEY,
    network=TRON_NETWORK,
)
facilitator_address = facilitator_signer.get_address()
facilitator_mechanism = UptoTronFacilitatorMechanism(
    facilitator_signer,
    fee_to=facilitator_address,
    base_fee=BASE_FEE,
)

print("=" * 80)
print("X402 Payment Facilitator - Configuration")
print("=" * 80)
print(f"Current Network: {CURRENT_NETWORK}")
print(f"Facilitator Address: {facilitator_address}")
print(f"Base Fee: {BASE_FEE} (0.0001 USDT)")
print(f"PaymentPermit Contract: {NetworkConfig.get_payment_permit_address(CURRENT_NETWORK)}")

print(f"\nSupported Networks and Tokens:")
for network in ["tron:mainnet", "tron:nile", "tron:shasta"]:
    tokens = TokenRegistry.get_network_tokens(network)
    is_current = " (CURRENT)" if network == CURRENT_NETWORK else ""
    print(f"  {network}{is_current}:")
    if not tokens:
        print("    (no tokens registered)")
    else:
        for symbol, info in tokens.items():
            print(f"    {symbol}: {info.address} (decimals={info.decimals})")
print("=" * 80)


@app.get("/")
async def root():
    """Service info endpoint"""
    return {
        "service": "X402 Facilitator",
        "status": "running",
        "facilitator_address": facilitator_address,
        "network": TRON_NETWORK,
        "base_fee": BASE_FEE,
    }


@app.get("/supported")
async def supported():
    """Get supported capabilities"""
    from x402_tron.types import SupportedResponse, SupportedKind, SupportedFee
    
    return SupportedResponse(
        kinds=[
            SupportedKind(
                x402Version=1,
                scheme="exact",
                network=f"tron:{TRON_NETWORK}"
            ),
        ],
        fee=SupportedFee(
            feeTo=facilitator_address,
            pricing="flat"
        )
    )


@app.post("/fee/quote", response_model=FeeQuoteResponse)
async def fee_quote(request: FeeQuoteRequest):
    """
    Get fee quote for payment requirements
    
    Args:
        request: Fee quote request with payment requirements
        
    Returns:
        Fee quote response with fee details
    """
    try:
        result = await facilitator_mechanism.fee_quote(request.accept)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verify", response_model=VerifyResponse)
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
        result = await facilitator_mechanism.verify(request.paymentPayload, request.paymentRequirements)
        logger.info(f"[VERIFY RESULT] {result.model_dump(by_alias=True)}")
        return result
    except Exception as e:
        logger.error(f"[VERIFY ERROR] {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/settle", response_model=SettleResponse)
async def settle(request: SettleRequest):
    """
    Settle payment on-chain
    
    Args:
        request: Settle request with payment payload and requirements
        
    Returns:
        Settlement result with transaction hash
    """
    try:
        result = await facilitator_mechanism.settle(request.paymentPayload, request.paymentRequirements)
        return result
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
    print(f"Network: {TRON_NETWORK}")
    print("=" * 80)
    print("\nEndpoints:")
    print(f"  GET  http://{FACILITATOR_HOST}:{FACILITATOR_PORT}/")
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
