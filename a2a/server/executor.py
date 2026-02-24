"""AgentExecutor that bridges A2A requests to an ADK Runner."""

import logging
from collections.abc import AsyncGenerator

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import AgentCard, TaskState, UnsupportedOperationError
from a2a.utils.errors import ServerError
from google.adk import Runner
from google.adk.events import Event
from google.genai import types

from server.parts import a2a_to_genai, genai_to_a2a
from x402_a2a.types import x402PaymentRequiredException

logger = logging.getLogger(__name__)


class ADKAgentExecutor(AgentExecutor):

    def __init__(self, runner: Runner, card: AgentCard):
        self.runner = runner
        self._card = card

    # --- Public ---

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        task_updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        session = await self._upsert_session(context.context_id)

        # If the x402 wrapper has verified a payment, inject it into session state
        if context.current_task and context.current_task.metadata.get("x402_payment_verified"):
            session.state["payment_verified_data"] = {"status": "SUCCESS"}
            session = await self._upsert_session(session.id)
            user_message = types.UserContent(parts=[types.Part(text="Payment verified. Please proceed.")])
        else:
            user_message = types.UserContent(parts=a2a_to_genai(context.message.parts))

        await self._run_to_completion(user_message, session.id, task_updater)

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise ServerError(error=UnsupportedOperationError())

    # --- Internal ---

    async def _run_to_completion(
        self, message: types.Content, session_id: str, task_updater: TaskUpdater
    ) -> None:
        """Drive the ADK agent through its tool-call loop until done."""
        current = message

        while True:
            calls = []
            async for event in self._stream(session_id, current):
                if event.is_final_response():
                    parts = genai_to_a2a(event.content.parts) if event.content and event.content.parts else []
                    if parts:
                        await task_updater.add_artifact(parts)
                    await task_updater.complete()
                    return

                if event.get_function_calls():
                    calls.extend(event.get_function_calls())
                elif event.content and event.content.parts:
                    await task_updater.update_status(
                        TaskState.working,
                        message=task_updater.new_agent_message(genai_to_a2a(event.content.parts)),
                    )

            if not calls:
                logger.warning("Agent stream ended without final response.")
                await task_updater.complete()
                return

            current = types.Content(parts=self._exec_tools(calls), role="tool")

    def _stream(self, session_id: str, message: types.Content) -> AsyncGenerator[Event, None]:
        return self.runner.run_async(session_id=session_id, user_id="self", new_message=message)

    def _exec_tools(self, calls: list) -> list[types.Part]:
        results = []
        for call in calls:
            tool = next((t for t in self.runner.agent.tools if getattr(t, "__name__", None) == call.name), None)
            if not tool:
                raise ValueError(f"Tool '{call.name}' not found.")
            try:
                result = tool(**dict(call.args))
                results.append(types.Part(function_response=types.FunctionResponse(name=call.name, response={"result": result})))
            except x402PaymentRequiredException:
                raise
            except Exception as e:
                logger.error("Tool '%s' failed: %s", call.name, e, exc_info=True)
                results.append(types.Part(function_response=types.FunctionResponse(name=call.name, response={"error": str(e)})))
        return results

    async def _upsert_session(self, session_id: str):
        svc = self.runner.session_service
        session = await svc.get_session(app_name=self.runner.app_name, user_id="self", session_id=session_id)
        if session:
            return session
        return await svc.create_session(app_name=self.runner.app_name, user_id="self", session_id=session_id)
