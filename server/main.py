import os
import logging
import io
import threading
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from bankofai.x402.server import X402Server
from bankofai.x402.fastapi import x402_protected
from bankofai.x402.facilitator import FacilitatorClient
from bankofai.x402.config import NetworkConfig
from bankofai.x402.mechanisms.evm.exact_permit import ExactPermitEvmServerMechanism
from bankofai.x402.mechanisms.evm.exact import ExactEvmServerMechanism
from bankofai.x402.tokens import TokenInfo, TokenRegistry

from PIL import Image, ImageDraw, ImageFont

load_dotenv(Path(__file__).parent.parent / ".env")

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Set specific loggers to DEBUG for detailed output
logging.getLogger("bankofai.x402").setLevel(logging.DEBUG)
logging.getLogger("bankofai.x402.server").setLevel(logging.DEBUG)
logging.getLogger("bankofai.x402.fastapi").setLevel(logging.DEBUG)
logging.getLogger("bankofai.x402.utils").setLevel(logging.DEBUG)
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
BSC_PAY_TO_ADDRESS = os.getenv("BSC_PAY_TO_ADDRESS", "")
if not PAY_TO_ADDRESS:
    raise ValueError("PAY_TO_ADDRESS environment variable is required")

# Network selection - Change this to use different networks
# Options: NetworkConfig.TRON_MAINNET, NetworkConfig.TRON_NILE,
# NetworkConfig.TRON_SHASTA
CURRENT_NETWORK = NetworkConfig.TRON_NILE

# Server configuration
FACILITATOR_URL = os.getenv("FACILITATOR_URL", "http://localhost:8001")
FACILITATOR_API_KEY = os.getenv("FACILITATOR_API_KEY", "")  # Optional: for facilitator auth
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

# Path to protected image
PROTECTED_IMAGE_PATH = Path(__file__).parent / "protected.png"

_request_count_lock = threading.Lock()
_request_count = 0

# Initialize server (TRON mechanisms auto-registered by default)
server = X402Server()
# Register BSC testnet mechanisms
server.register(NetworkConfig.BSC_TESTNET, ExactPermitEvmServerMechanism())
server.register(NetworkConfig.BSC_TESTNET, ExactEvmServerMechanism())
# Register BSC mainnet mechanisms
server.register(NetworkConfig.BSC_MAINNET, ExactPermitEvmServerMechanism())
server.register(NetworkConfig.BSC_MAINNET, ExactEvmServerMechanism())
# Add facilitator (with X-API-KEY if configured)
facilitator_headers = {"X-API-KEY": FACILITATOR_API_KEY} if FACILITATOR_API_KEY else None
facilitator = FacilitatorClient(
    base_url=FACILITATOR_URL,
    headers=facilitator_headers,
)
server.set_facilitator(facilitator)

print("=" * 80)
print("X402 Protected Resource Server - Configuration")
print("=" * 80)
print(f"Current Network: {CURRENT_NETWORK}")
print(f"Pay To Address: {PAY_TO_ADDRESS}")
print(f"Facilitator URL: {FACILITATOR_URL}")
print(f"Facilitator API Key: {'*configured*' if FACILITATOR_API_KEY else '(not set)'}")
permit_address = NetworkConfig.get_payment_permit_address(CURRENT_NETWORK)
print(f"PaymentPermit Contract: {permit_address}")

registered_networks = sorted(server._mechanisms.keys())
print(f"\nAll Registered Networks ({len(registered_networks)}):")
for net in registered_networks:
    tokens = TokenRegistry.get_network_tokens(net)
    is_current = " (CURRENT)" if net == CURRENT_NETWORK else ""
    print(f"  {net}{is_current}:")
    permit_addr = NetworkConfig.get_payment_permit_address(net)
    print(f"    PaymentPermit: {permit_addr}")
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
    prices=["0.0001 USDT", "0.0001 USDD"],
    schemes=["exact_permit", "exact_permit"],
    network=CURRENT_NETWORK,
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
    prices=["0.0001 USDT"],
    schemes=["exact_permit"],
    network=NetworkConfig.TRON_SHASTA,
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
    prices=["0.0001 USDT", "0.0001 USDD"],
    schemes=["exact_permit", "exact_permit"],
    network=NetworkConfig.TRON_MAINNET,
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


@app.get("/protected-bsc-mainnet")
@x402_protected(
    server=server,
    prices=["0.0001 USDC", "0.0001 USDT", "0.0001 EPS"],
    network=NetworkConfig.BSC_MAINNET,
    pay_to=BSC_PAY_TO_ADDRESS,
    schemes=["exact_permit", "exact_permit", "exact_permit"],
)
async def protected_bsc_mainnet_endpoint(request: Request):
    """Serve the protected image (BSC mainnet payment) - generated dynamically"""
    global _request_count
    if not PROTECTED_IMAGE_PATH.exists():
        return {"error": "Protected image not found"}

    with _request_count_lock:
        _request_count += 1
        request_count = _request_count

    buf = generate_protected_image(
        f"bsc-mainnet req: {request_count}", text_color=(255, 165, 0, 255)
    )
    return StreamingResponse(buf, media_type="image/png")


@app.get("/protected-bsc-testnet")
@x402_protected(
    server=server,
    prices=["0.0001 USDT", "0.0001 USDC", "0.0001 DHLU"],
    network=NetworkConfig.BSC_TESTNET,
    pay_to=BSC_PAY_TO_ADDRESS,
    schemes=["exact_permit", "exact_permit", "exact"],
)
async def protected_bsc_testnet_endpoint(request: Request):
    """Serve the protected image (BSC testnet payment) - generated dynamically"""
    global _request_count
    if not PROTECTED_IMAGE_PATH.exists():
        return {"error": "Protected image not found"}

    with _request_count_lock:
        _request_count += 1
        request_count = _request_count

    buf = generate_protected_image(
        f"bsc-test req: {request_count}", text_color=(0, 200, 255, 255)
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
    print("  /protected-nile         - Payment (0.0001 USDT) [Nile testnet]")
    print("  /protected-shasta       - Payment (0.0001 USDT) [Shasta testnet]")
    print("  /protected-mainnet      - Payment (0.0001 USDT/USDD) [Mainnet]")
    print("  /protected-bsc-mainnet  - Payment (0.0001 USDC/USDT/EPS) [BSC Mainnet]")
    print("  /protected-bsc-testnet  - Payment (0.0001 USDT/USDC/DHLU) [BSC Testnet]")
    print("=" * 80 + "\n")

    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        log_level="info",
        access_log=True,
    )
