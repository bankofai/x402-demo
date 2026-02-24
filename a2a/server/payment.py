"""x402 payment executor: verify & settle via Facilitator service."""

import logging
import os
from typing import override

from a2a.server.agent_execution import AgentExecutor

from x402_a2a.executors import x402ServerExecutor
from x402_a2a.types import PaymentPayload, PaymentRequirements, SettleResponse, VerifyResponse
from x402_a2a import FacilitatorClient, x402ExtensionConfig
from bankofai.x402.types import PaymentRequirementsExtra

logger = logging.getLogger(__name__)


class x402MerchantExecutor(x402ServerExecutor):
    """Wraps an AgentExecutor with x402 payment verification and settlement."""

    def __init__(self, delegate: AgentExecutor):
        super().__init__(delegate, x402ExtensionConfig())
        url = os.getenv("FACILITATOR_URL", "http://0.0.0.0:8001")
        logger.info("Using Facilitator: %s", url)
        self._facilitator = FacilitatorClient(url)

    @override
    async def _enrich_accepts(self, accepts: list[PaymentRequirements]) -> list[PaymentRequirements]:
        """Inject fee info from Facilitator /fee/quote."""
        try:
            quotes = await self._facilitator.fee_quote(accepts)
            fee_map = {(q.network, q.scheme, q.asset): q.fee for q in quotes}
            enriched = []
            for req in accepts:
                fee = fee_map.get((req.network, req.scheme, req.asset))
                if fee:
                    extra = req.extra or PaymentRequirementsExtra()
                    enriched.append(req.model_copy(update={
                        "extra": PaymentRequirementsExtra(name=extra.name, version=extra.version, fee=fee)
                    }))
                else:
                    enriched.append(req)
            return enriched
        except Exception as e:
            logger.warning("fee_quote failed, proceeding without fee: %s", e)
            return accepts

    @override
    async def verify_payment(self, payload: PaymentPayload, requirements: PaymentRequirements) -> VerifyResponse:
        resp = await self._facilitator.verify(payload, requirements)
        logger.info("Payment verify: %s", "✅ valid" if resp.is_valid else f"⛔ {resp.invalid_reason}")
        return resp

    @override
    async def settle_payment(self, payload: PaymentPayload, requirements: PaymentRequirements) -> SettleResponse:
        resp = await self._facilitator.settle(payload, requirements)
        logger.info("Payment settle: %s", "✅ success" if resp.success else f"⛔ {resp.error_reason}")
        return resp
