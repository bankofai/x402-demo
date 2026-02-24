"""ClientAgent: orchestrator that delegates tasks to remote agents with x402 payment support."""

import json
import logging
import uuid
from typing import Callable

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    JSONRPCError,
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    Part,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
)
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.tool_context import ToolContext

from .wallet import Wallet
from x402_a2a.core.utils import x402Utils
from x402_a2a.types import PaymentStatus

logger = logging.getLogger(__name__)

type TaskCallbackArg = Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
TaskUpdateCallback = Callable[[TaskCallbackArg], Task]


class RemoteAgentConnection:
    """Manages the A2A client connection to a single remote agent."""

    def __init__(self, client: httpx.AsyncClient, card: AgentCard):
        self.a2a = A2AClient(client, card)
        self.card = card

    async def send_message(
        self, id: str, request: MessageSendParams, callback: TaskUpdateCallback | None
    ) -> Task | Message | None:
        if self.card.capabilities.streaming:
            return await self._streaming(id, request, callback)
        return await self._unary(id, request, callback)

    async def _streaming(self, id, request, callback):
        task = None
        async for resp in self.a2a.send_message_streaming(SendStreamingMessageRequest(id=id, params=request)):
            if not resp.root.result:
                return resp.root.error
            event = resp.root.result
            if isinstance(event, Message):
                return event
            if callback and event:
                task = callback(event)
            if hasattr(event, "final") and event.final:
                break
        return task

    async def _unary(self, id, request, callback):
        resp = await self.a2a.send_message(SendMessageRequest(id=id, params=request))
        if isinstance(resp.root, JSONRPCErrorResponse):
            return resp.root.error
        if isinstance(resp.root.result, Message):
            return resp.root.result
        if callback:
            callback(resp.root.result)
        return resp.root.result


INSTRUCTION = """
You are an orchestrator agent. Complete user requests by delegating to specialized agents.

**SOP:**
1. Use `list_remote_agents` to discover available agents.
2. Use `send_message` to delegate the request.
3. If payment is required, present the confirmation to the user.
4. If the user confirms, call `send_message` again with: "sign_and_send_payment".
5. Report the final outcome.

**Available Agents:**
{agents_info}
"""


class ClientAgent:

    def __init__(
        self,
        remote_agent_addresses: list[str],
        http_client: httpx.AsyncClient,
        wallet: Wallet,
        task_callback: TaskUpdateCallback | None = None,
    ):
        self.task_callback = task_callback
        self.http_client = http_client
        self.wallet = wallet
        self.remote_agent_addresses = remote_agent_addresses
        self.connections: dict[str, RemoteAgentConnection] = {}
        self.cards: dict[str, AgentCard] = {}
        self._initialized = False
        self.x402 = x402Utils()

    def create_agent(self) -> Agent:
        return Agent(
            model="gemini-2.5-flash",
            name="client_agent",
            instruction=self._instruction,
            before_agent_callback=self._init_connections,
            description="An orchestrator that delegates tasks to other agents.",
            tools=[self.list_remote_agents, self.send_message],
        )

    # --- Callbacks ---

    def _instruction(self, _ctx: ReadonlyContext) -> str:
        info = json.dumps([{"name": c.name, "description": c.description} for c in self.cards.values()], indent=2)
        return INSTRUCTION.format(agents_info=info)

    async def _init_connections(self, _ctx: CallbackContext):
        if self._initialized:
            return
        for addr in self.remote_agent_addresses:
            card = await A2ACardResolver(self.http_client, addr).get_agent_card()
            self.connections[card.name] = RemoteAgentConnection(self.http_client, card)
            self.cards[card.name] = card
        self._initialized = True

    # --- Tools ---

    def list_remote_agents(self):
        """Lists available remote agents."""
        return [{"name": c.name, "description": c.description} for c in self.cards.values()]

    async def send_message(self, agent_name: str, message: str, tool_context: ToolContext):
        """Sends a message to a remote agent, handling payment flows transparently."""
        if agent_name not in self.connections:
            raise ValueError(f"Agent '{agent_name}' not found.")

        state = tool_context.state
        task_id = None
        metadata = {}

        if message == "sign_and_send_payment":
            task_id, metadata, message = await self._sign_payment(state)

        request = MessageSendParams(
            message=Message(
                messageId=str(uuid.uuid4()),
                role="user",
                parts=[Part(root=TextPart(text=message))],
                contextId=state.get("context_id"),
                taskId=task_id,
                metadata=metadata or None,
            )
        )

        resp = await self.connections[agent_name].send_message(request.message.message_id, request, self.task_callback)

        if isinstance(resp, JSONRPCError):
            logger.error("Error from %s: %s", agent_name, resp.message)
            return f"Agent '{agent_name}' error: {resp.message} (Code: {resp.code})"

        state["context_id"] = resp.context_id
        return self._handle_response(resp, agent_name, state)

    # --- Helpers ---

    async def _sign_payment(self, state: dict) -> tuple[str, dict, str]:
        data = state.get("purchase_task")
        if not data:
            raise ValueError("No purchase_task in state.")
        task = Task.model_validate(data)
        reqs = self.x402.get_payment_requirements(task)
        if not reqs:
            raise ValueError("No payment requirements found.")
        signed = await self.wallet.sign_payment(reqs)
        meta = {
            self.x402.PAYLOAD_KEY: signed.model_dump(by_alias=True),
            self.x402.STATUS_KEY: PaymentStatus.PAYMENT_SUBMITTED.value,
        }
        return task.id, meta, "send_signed_payment_payload"

    def _handle_response(self, resp: Task, agent_name: str, state: dict) -> str:
        if resp.status.state == TaskState.input_required:
            state["purchase_task"] = resp.model_dump(by_alias=True)
            reqs = self.x402.get_payment_requirements(resp)
            if not reqs or not reqs.accepts:
                raise ValueError("No valid payment options.")
            opt = reqs.accepts[0]
            name = opt.extra.name if opt.extra else "TOKEN"
            return f"The merchant is requesting payment of {opt.amount} {name}. Approve?"

        if resp.status.state in (TaskState.completed, TaskState.failed):
            return self._format_result(resp, agent_name)

        return f"Task with {agent_name}: {resp.status.state.value}"

    def _format_result(self, task: Task, agent_name: str) -> str:
        texts = [
            part.root.text
            for a in (task.artifacts or [])
            for part in a.parts
            if isinstance(part.root, TextPart)
        ]
        receipt = self.x402.get_latest_receipt(task)
        tx = getattr(receipt, "transaction", None) if receipt else None
        tx_msg = f"\nTx Hash: {tx}" if tx else ""

        if texts:
            return " ".join(texts) + tx_msg
        if self.x402.get_payment_status(task) == PaymentStatus.PAYMENT_COMPLETED:
            return f"Payment successful!{tx_msg}"
        return f"Task with {agent_name}: {task.status.state.value}."
