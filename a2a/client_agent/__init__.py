"""Client agent package — exports root_agent for ADK web UI."""

import os
import httpx

from .client import ClientAgent
from .task_store import TaskStore
from .wallet import TronLocalWallet

server_port = os.getenv("SERVER_PORT", "8000")

root_agent = ClientAgent(
    remote_agent_addresses=[f"http://localhost:{server_port}/agents/merchant_agent"],
    http_client=httpx.AsyncClient(timeout=30),
    wallet=TronLocalWallet(),
    task_callback=TaskStore().update_task,
).create_agent()

__all__ = ["root_agent"]
