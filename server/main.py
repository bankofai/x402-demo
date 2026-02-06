import os
import logging
import io
import threading
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from x402_tron.server import X402Server
from x402_tron.fastapi import x402_protected
from x402_tron.facilitator import FacilitatorClient
from x402_tron.config import NetworkConfig
from x402_tron.tokens import TokenRegistry

from PIL import Image, ImageDraw, ImageFont

load_dotenv(Path(__file__).parent.parent / ".env")

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Set specific loggers to DEBUG for detailed output
logging.getLogger("x402_tron").setLevel(logging.DEBUG)
logging.getLogger("x402_tron.server").setLevel(logging.DEBUG)
logging.getLogger("x402_tron.fastapi").setLevel(logging.DEBUG)
logging.getLogger("x402_tron.utils").setLevel(logging.DEBUG)
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
PAY_TO_ADDRESS = os.getenv("PAY_TO_ADDRESS")
if not PAY_TO_ADDRESS:
    raise ValueError("PAY_TO_ADDRESS environment variable is required")

# Network selection - Change this to use different networks
# Options: NetworkConfig.TRON_MAINNET, NetworkConfig.TRON_NILE, NetworkConfig.TRON_SHASTA
CURRENT_NETWORK = NetworkConfig.TRON_NILE

# Server configuration
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

print("=" * 80)
print("X402 Protected Resource Server - Configuration")
print("=" * 80)
print(f"Current Network: {CURRENT_NETWORK}")
print(f"Pay To Address: {PAY_TO_ADDRESS}")
print(f"Facilitator URL: {FACILITATOR_URL}")
print(
    f"PaymentPermit Contract: {NetworkConfig.get_payment_permit_address(CURRENT_NETWORK)}"
)

registered_networks = sorted(server._mechanisms.keys())
print(f"\nAll Registered Networks ({len(registered_networks)}):")
for net in registered_networks:
    tokens = TokenRegistry.get_network_tokens(net)
    is_current = " (CURRENT)" if net == CURRENT_NETWORK else ""
    print(f"  {net}{is_current}:")
    if not tokens:
        print("    (no tokens registered)")
        continue
    for symbol, info in tokens.items():
        print(f"    {symbol}: {info.address} (decimals={info.decimals})")
print("=" * 80)


def generate_protected_image(
    text: str, text_color: tuple[int, int, int, int] = (255, 255, 0, 255)
) -> io.BytesIO:
    """Generate a protected image with custom text and color"""
    with Image.open(PROTECTED_IMAGE_PATH) as base:
        image = base.convert("RGBA")
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("DejaVuSans.ttf", 50)
        except Exception:
            font = ImageFont.load_default()

        x = 16
        y = 16
        padding = 6

        bbox = draw.textbbox((x, y), text, font=font)
        bg = (
            bbox[0] - padding,
            bbox[1] - padding,
            bbox[2] + padding,
            bbox[3] + padding,
        )
        draw.rectangle(bg, fill=(0, 0, 0, 160))
        draw.text(
            (x, y),
            text,
            fill=text_color,
            font=font,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return buf


@app.get("/")
async def root():
    """Service info"""
    return {
        "service": "X402 Protected Resource Server",
        "status": "running",
        "pay_to": PAY_TO_ADDRESS,
        "facilitator": FACILITATOR_URL,
    }


@app.get("/protected-nile")
@x402_protected(
    server=server,
    price="0.0001 USDT",  # Price format: "<amount> <token_symbol>"
    # Currently only USDT is supported
    # Token must be registered in TokenRegistry for the network
    network=CURRENT_NETWORK,  # Uses the network configured above
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

    buf = generate_protected_image(
        f"req: {request_count}", text_color=(255, 255, 0, 255)
    )
    return StreamingResponse(buf, media_type="image/png")


@app.get("/protected-shasta")
@x402_protected(
    server=server,
    price="0.0001 USDT",  # Price format: "<amount> <token_symbol>"
    network=NetworkConfig.TRON_SHASTA,  # Uses TRON shasta testnet
    pay_to=PAY_TO_ADDRESS,
)
async def protected_shasta_endpoint(request: Request):
    """Serve the protected image (shasta payment) - generated dynamically"""
    global _request_count
    if not PROTECTED_IMAGE_PATH.exists():
        return {"error": "Protected image not found"}

    with _request_count_lock:
        _request_count += 1
        request_count = _request_count

    buf = generate_protected_image(
        f"shasta req: {request_count}", text_color=(0, 255, 0, 255)
    )
    return StreamingResponse(buf, media_type="image/png")


@app.get("/protected-mainnet")
@x402_protected(
    server=server,
    price="0.0001 USDT",  # Price format: "<amount> <token_symbol>"
    network=NetworkConfig.TRON_MAINNET,  # Uses TRON mainnet
    pay_to=PAY_TO_ADDRESS,
)
async def protected_mainnet_endpoint(request: Request):
    """Serve the protected image (mainnet payment) - generated dynamically"""
    global _request_count
    if not PROTECTED_IMAGE_PATH.exists():
        return {"error": "Protected image not found"}

    with _request_count_lock:
        _request_count += 1
        request_count = _request_count

    buf = generate_protected_image(
        f"mainnet req: {request_count}", text_color=(255, 0, 0, 255)
    )
    return StreamingResponse(buf, media_type="image/png")


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 80)
    print("Starting X402 Protected Resource Server")
    print("=" * 80)
    print(f"Host: {SERVER_HOST}")
    print(f"Port: {SERVER_PORT}")
    print("Endpoints:")
    print("  /protected-nile     - Payment (0.0001 USDT) [Nile testnet]")
    print("  /protected-shasta   - Payment (0.0001 USDT) [Shasta testnet]")
    print("  /protected-mainnet  - Payment (0.0001 USDT) [Mainnet]")
    print("=" * 80 + "\n")

    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info",
        access_log=True,
    )
