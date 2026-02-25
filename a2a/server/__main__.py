"""A2A Merchant Server entry point."""

import logging
import os

import click
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from server.executor import ADKAgentExecutor
from server.merchant import MerchantAgent
from server.payment import x402MerchantExecutor

# Load .env from repo root (shared with other demos)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv()  # also load local .env if present

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(base_url: str) -> Starlette:
    """Build Starlette app with all agent routes."""
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI") != "TRUE" and not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY environment variable not set.")

    # Create the merchant agent
    merchant = MerchantAgent()
    agent_card = merchant.create_agent_card(f"{base_url}/agents/merchant_agent")
    agent = merchant.create_agent()

    runner = Runner(
        app_name=agent_card.name,
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )

    # Stack: ADK executor → x402 payment wrapper → request handler
    executor = x402MerchantExecutor(ADKAgentExecutor(runner, agent_card))
    handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())

    a2a_app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)
    card_url = "/agents/merchant_agent/.well-known/agent-card.json"
    logger.info("Registered agent: %s", card_url)

    return Starlette(routes=a2a_app.routes(agent_card_url=card_url, rpc_url="/agents/merchant_agent"))


@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=10000)
def main(host: str, port: int):
    app = create_app(base_url=f"http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
