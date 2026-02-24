import logging
import os
from typing import List, override

from a2a.server.agent_execution import AgentExecutor

from x402_a2a.executors import x402ServerExecutor
from x402_a2a.types import (
    PaymentPayload,
    PaymentRequirements,
    SettleResponse,
    VerifyResponse,
)
from x402_a2a import FacilitatorClient, x402ExtensionConfig
from bankofai.x402.types import PaymentRequirementsExtra, FeeInfo

logger = logging.getLogger(__name__)


class x402MerchantExecutor(x402ServerExecutor):
    """
    Concrete x402ServerExecutor that uses a real FacilitatorClient
    to verify and settle payments.

    The facilitator URL is read from the FACILITATOR_URL environment variable
    (default: http://0.0.0.0:8001).
    """

    def __init__(self, delegate: AgentExecutor):
        super().__init__(delegate, x402ExtensionConfig())

        facilitator_url = os.getenv("FACILITATOR_URL", "http://0.0.0.0:8001")
        print(f"--- Using Real Facilitator: {facilitator_url} ---")
        self._facilitator = FacilitatorClient(facilitator_url)

    @override
    async def _enrich_accepts(
        self, accepts_array: List[PaymentRequirements]
    ) -> List[PaymentRequirements]:
        """Call Facilitator /fee/quote to inject fee info into each requirement.

        This ensures the client signs the PaymentPermit with the correct
        fee_to address, so Facilitator verification passes.
        """
        try:
            quotes = await self._facilitator.fee_quote(accepts_array)
            # Build a lookup: (network, scheme, asset) -> FeeInfo
            quote_map = {
                (q.network, q.scheme, q.asset): q.fee for q in quotes
            }
            enriched = []
            for req in accepts_array:
                fee_info = quote_map.get((req.network, req.scheme, req.asset))
                if fee_info is not None:
                    extra = req.extra or PaymentRequirementsExtra()
                    # Rebuild extra with fee populated
                    enriched_req = req.model_copy(
                        update={
                            "extra": PaymentRequirementsExtra(
                                name=extra.name,
                                version=extra.version,
                                fee=fee_info,
                            )
                        }
                    )
                    enriched.append(enriched_req)
                    logger.info(
                        f"Enriched requirement {req.network}/{req.scheme} "
                        f"with fee: feeTo={fee_info.fee_to}, "
                        f"feeAmount={fee_info.fee_amount}"
                    )
                else:
                    logger.warning(
                        f"No fee quote returned for {req.network}/{req.scheme}/{req.asset}"
                    )
                    enriched.append(req)
            return enriched
        except Exception as e:
            logger.warning(f"fee_quote failed, proceeding without fee info: {e}")
            return accepts_array

    @override
    async def verify_payment(
        self, payload: PaymentPayload, requirements: PaymentRequirements
    ) -> VerifyResponse:
        """Verifies the payment with the facilitator."""
        response = await self._facilitator.verify(payload, requirements)
        if response.is_valid:
            print("✅ Payment Verified!")
        else:
            print(f"⛔ Payment failed verification: {response.invalid_reason}")
        return response

    @override
    async def settle_payment(
        self, payload: PaymentPayload, requirements: PaymentRequirements
    ) -> SettleResponse:
        """Settles the payment with the facilitator."""
        response = await self._facilitator.settle(payload, requirements)
        if response.success:
            print("✅ Payment Settled!")
        else:
            print(f"⛔ Payment failed to settle: {response.error_reason}")
        return response
