"""A2A client connection wrapper for remote agents."""

from typing import Callable

import httpx
from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)

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
