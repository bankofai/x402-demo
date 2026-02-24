# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import hashlib
import os
from typing import override

from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from bankofai.x402.types import PaymentRequirements, PaymentRequirementsExtra

# Import the custom exception and the base agent interface
from .base_agent import BaseAgent
from x402_a2a.types import x402PaymentRequiredException
from x402_a2a import x402Utils, get_extension_declaration
from bankofai.x402.tokens.registry import TokenRegistry

# Tron network config from environment (with Nile testnet defaults)
_TRON_NETWORK   = os.getenv("TRON_NETWORK", "tron:nile")
# Merchant's Tron wallet address (receives payment)
_PAY_TO_ADDRESS = os.getenv("PAY_TO_ADDRESS", "")


class AdkMerchantAgent(BaseAgent):
    """
    Defines the ADK LlmAgent for the merchant and its corresponding AgentCard.
    The business logic is implemented as tools.
    """

    def __init__(self):
        if not _PAY_TO_ADDRESS:
            raise ValueError(
                "PAY_TO_ADDRESS environment variable is not set. "
                "Please set it to the merchant's Tron wallet address."
            )
        self.x402 = x402Utils()

    def get_product_details_and_request_payment(self, product_name: str) -> dict:
        """
        This is the agent's tool. Instead of returning payment details, it raises
        an exception to signal to the x402 wrapper that payment is needed.
        """
        if not product_name:
            return {"error": "Product name cannot be empty."}

        asset_info = TokenRegistry.parse_price("0.0001 USDT", _TRON_NETWORK)

        requirements = PaymentRequirements(
            scheme="exact_permit",
            network=_TRON_NETWORK,
            amount=str(asset_info["amount"]),
            asset=asset_info["asset"],
            payTo=_PAY_TO_ADDRESS,
            maxTimeoutSeconds=1200,
            extra=PaymentRequirementsExtra(
                name=asset_info["symbol"],
                version=asset_info["version"],
            ),
        )

        # Signal to the x402ServerAgentExecutor that payment is required.
        raise x402PaymentRequiredException(product_name, requirements)

    def before_agent_callback(self, callback_context: CallbackContext):
        """
        Injects a 'virtual' tool response if payment has been verified.
        """
        payment_data = callback_context.state.get("payment_verified_data")
        if payment_data:
            # Consume the data so it's not used again in the same session.
            del callback_context.state["payment_verified_data"]

            # Create a Content object that looks like a tool call response.
            # This is a structured way to inform the LLM of the payment status.
            tool_response = types.Part(
                function_response=types.FunctionResponse(
                    name="check_payment_status",
                    response=payment_data,
                )
            )
            # Set this as the new, overriding input for this turn.
            callback_context.new_user_message = types.Content(parts=[tool_response])

    @override
    def create_agent(self) -> LlmAgent:
        """Creates the LlmAgent instance for the merchant."""
        return LlmAgent(
            model="gemini-2.5-flash",
            name="adk_merchant_agent",
            description="An agent that can sell any item by providing a price and then processing the payment using the x402 protocol.",
            instruction="""You are a helpful and friendly "Amazon" merchant agent.
- When a user asks to buy an item, use the `get_product_details_and_request_payment` tool.
- If you receive a successful result from the `check_payment_status` tool, you MUST confirm the purchase with the user and tell them their order is being prepared. Do not ask for payment again.
- If the system tells you the payment failed, relay the error clearly and politely.
""",
            tools=[self.get_product_details_and_request_payment],
            before_agent_callback=self.before_agent_callback,
        )

    @override
    def create_agent_card(self, url: str) -> AgentCard:
        """Creates the AgentCard for this agent."""
        skills = [
            AgentSkill(
                id="get_product_info",
                name="Get Product Price and Payment Info",
                description="Provides the price, SKU, and x402 payment requirements for any given product.",
                tags=["pricing", "product", "x402", "merchant"],
                examples=[
                    "How much for a new laptop?",
                    "I want to buy a red stapler.",
                    "Can you give me the price for a copy of 'Moby Dick'?",
                ],
            )
        ]
        return AgentCard(
            name="x402 Merchant Agent",
            description="This agent sells items using the clean x402 server architecture.",
            url=url,
            version="4.0.0",
            defaultInputModes=["text", "text/plain"],
            defaultOutputModes=["text", "text/plain"],
            capabilities=AgentCapabilities(
                streaming=False,
                extensions=[
                    get_extension_declaration(
                        description="Supports payments using the x402 protocol.",
                        required=True,
                    )
                ],
            ),
            skills=skills,
        )
