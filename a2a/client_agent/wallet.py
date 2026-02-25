import os
from abc import ABC, abstractmethod

from bankofai.x402.clients import X402Client
from bankofai.x402.mechanisms.tron import ExactPermitTronClientMechanism
from bankofai.x402.signers.client import TronClientSigner
from bankofai.x402.types import PaymentRequired as x402PaymentRequiredResponse

from x402_a2a.types import PaymentPayload
from x402_a2a.core.wallet import process_payment_required


class Wallet(ABC):
    """Abstract wallet interface for signing x402 payment requirements."""

    @abstractmethod
    async def sign_payment(self, requirements: x402PaymentRequiredResponse) -> PaymentPayload:
        raise NotImplementedError


class TronLocalWallet(Wallet):
    """
    Local Tron wallet that signs payments using a private key from env.

    Reads TRON_PRIVATE_KEY and TRON_NETWORK from environment variables.
    ⚠️ FOR DEMO ONLY — store private keys securely in production.
    """

    def __init__(self) -> None:
        private_key = os.environ.get("TRON_PRIVATE_KEY")
        if not private_key:
            raise ValueError("TRON_PRIVATE_KEY environment variable is not set.")

        network = os.environ.get("TRON_NETWORK", "tron:nile")

        signer = TronClientSigner.from_private_key(private_key)
        mechanism = ExactPermitTronClientMechanism(signer)

        self._client = X402Client()
        self._client.register(network, mechanism)

    async def sign_payment(self, requirements: x402PaymentRequiredResponse) -> PaymentPayload:
        return await process_payment_required(requirements, self._client)
