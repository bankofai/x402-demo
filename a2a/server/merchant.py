"""Merchant agent: sells items via x402 payment protocol."""

import os

from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from bankofai.x402.types import PaymentRequirements, PaymentRequirementsExtra
from bankofai.x402.tokens.registry import TokenRegistry

from x402_a2a.types import x402PaymentRequiredException
from x402_a2a import x402Utils, get_extension_declaration

_TRON_NETWORK = os.getenv("TRON_NETWORK", "tron:nile")
_PAY_TO_ADDRESS = os.getenv("PAY_TO_ADDRESS", "")


class MerchantAgent:

    def __init__(self):
        if not _PAY_TO_ADDRESS:
            raise ValueError("PAY_TO_ADDRESS environment variable is not set.")
        self.x402 = x402Utils()

    # --- Tool ---

    def get_product_details_and_request_payment(self, product_name: str) -> dict:
        """Raises x402PaymentRequiredException to signal payment is needed."""
        if not product_name:
            return {"error": "Product name cannot be empty."}

        asset = TokenRegistry.parse_price("0.0001 USDT", _TRON_NETWORK)
        requirements = PaymentRequirements(
            scheme="exact_permit",
            network=_TRON_NETWORK,
            amount=str(asset["amount"]),
            asset=asset["asset"],
            payTo=_PAY_TO_ADDRESS,
            maxTimeoutSeconds=1200,
            extra=PaymentRequirementsExtra(name=asset["symbol"], version=asset["version"]),
        )
        raise x402PaymentRequiredException(product_name, requirements)

    # --- Callback ---

    def before_agent_callback(self, ctx: CallbackContext):
        """Injects a virtual tool response when payment has been verified."""
        data = ctx.state.get("payment_verified_data")
        if not data:
            return
        del ctx.state["payment_verified_data"]
        ctx.new_user_message = types.Content(parts=[
            types.Part(function_response=types.FunctionResponse(name="check_payment_status", response=data))
        ])

    # --- Factory ---

    def create_agent(self) -> LlmAgent:
        return LlmAgent(
            model="gemini-2.5-flash",
            name="adk_merchant_agent",
            description="Sells items using the x402 payment protocol.",
            instruction=(
                'You are a helpful "Amazon" merchant agent.\n'
                "- Use `get_product_details_and_request_payment` when the user wants to buy something.\n"
                "- On successful `check_payment_status`, confirm the purchase.\n"
                "- On failure, relay the error politely.\n"
            ),
            tools=[self.get_product_details_and_request_payment],
            before_agent_callback=self.before_agent_callback,
        )

    def create_agent_card(self, url: str) -> AgentCard:
        return AgentCard(
            name="x402 Merchant Agent",
            description="Sells items using the x402 payment protocol.",
            url=url,
            version="4.0.0",
            defaultInputModes=["text", "text/plain"],
            defaultOutputModes=["text", "text/plain"],
            capabilities=AgentCapabilities(
                streaming=False,
                extensions=[get_extension_declaration(description="Supports x402 payments.", required=True)],
            ),
            skills=[AgentSkill(
                id="buy_product",
                name="Buy Product",
                description="Provides pricing and x402 payment requirements for any product.",
                tags=["pricing", "x402", "merchant"],
                examples=["I want to buy a laptop.", "How much for a banana?"],
            )],
        )
