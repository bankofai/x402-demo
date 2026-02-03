import os
import logging
import time
import io
import threading
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from x402.server import X402Server
from x402.fastapi import x402_protected
from x402.facilitator import FacilitatorClient
from x402.config import NetworkConfig
from x402.tokens.registry import TokenRegistry

from PIL import Image, ImageDraw, ImageFont

load_dotenv(Path(__file__).parent.parent / ".env")

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set specific loggers to DEBUG for detailed output
logging.getLogger("x402").setLevel(logging.DEBUG)
logging.getLogger("x402.server").setLevel(logging.DEBUG)
logging.getLogger("x402.fastapi").setLevel(logging.DEBUG)
logging.getLogger("x402.utils").setLevel(logging.DEBUG)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(title="X402 Server", description="Protected resource server")

# Add CORS middleware to allow cross-origin requests from client/web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Configuration
PAY_TO_ADDRESS = os.getenv("PAY_TO_ADDRESS") or "TDhj8uX7SVJwvhCUrMaiQHqPgrB6wRb3eG"
# Hardcoded server configuration
FACILITATOR_URL = "http://localhost:8001"
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# Path to protected image
PROTECTED_IMAGE_PATH = Path(__file__).parent / "protected.png"

_request_count_lock = threading.Lock()
_request_count = 0

# Initialize server (TRON mechanisms auto-registered by default)
server = X402Server()
# Add facilitator
facilitator = FacilitatorClient(base_url=FACILITATOR_URL)
server.add_facilitator(facilitator)

print(f"Server Configuration:")
print("Supported TRON networks:")
for n, cid in NetworkConfig.CHAIN_IDS.items():
    print(f"  - {n} (chainId={cid})")
    tokens = TokenRegistry.get_network_tokens(n)
    if tokens:
        print("    Tokens:")
        for sym, info in tokens.items():
            print(f"      - {sym}: {info.address} (decimals={info.decimals})")
print(f"  Network: {NetworkConfig.TRON_NILE}")
print(f"  Pay To: {PAY_TO_ADDRESS}")
print(f"  Facilitator URL: {FACILITATOR_URL}")

@app.get("/")
async def root():
    """Service info"""
    return {
        "service": "X402 Protected Resource Server",
        "status": "running",
        "pay_to": PAY_TO_ADDRESS,
        "facilitator": FACILITATOR_URL,
    }

@app.get("/protected")
@x402_protected(
    server=server,
    price="1 USDT",  # 1 USDT = 1000000 (6 decimals)
    network=NetworkConfig.TRON_NILE,
    pay_to=PAY_TO_ADDRESS,
)
async def protected_endpoint(request: Request):
    """Serve the protected image (generated dynamically)"""
    global _request_count
    if not PROTECTED_IMAGE_PATH.exists():
        return {"error": "Protected image not found"}

    with _request_count_lock:
        _request_count += 1
        request_count = _request_count

    with Image.open(PROTECTED_IMAGE_PATH) as base:
        image = base.convert("RGBA")
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 260)
        except Exception:
            font = ImageFont.load_default()
        text = f"NO. {request_count}"

        margin = 16
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = image.width - margin - text_w
        y = image.height - margin - text_h

        draw.text(
            (x, y),
            text,
            fill=(255, 0, 0, 255),
            font=font,
        )

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 80)
    print("Starting X402 Protected Resource Server")
    print("=" * 80)
    print(f"Host: {SERVER_HOST}")
    print(f"Port: {SERVER_PORT}")
    print(f"Endpoints:")
    print(f"  /protected          - Payment only (1 USDT)")
    print(f"  /protected-with-fee - Payment with fee (2 USDT + 1 USDT fee)")
    print("=" * 80 + "\n")
    
    uvicorn.run(
        app, 
        host=SERVER_HOST, 
        port=SERVER_PORT,
        log_level="info",
        access_log=True,
    )
