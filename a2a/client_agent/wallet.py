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
import os
from abc import ABC, abstractmethod

from bankofai.x402.clients import X402Client
from bankofai.x402.mechanisms.tron import ExactPermitTronClientMechanism
from bankofai.x402.signers.client import TronClientSigner
from bankofai.x402.types import PaymentRequired as x402PaymentRequiredResponse

from x402_a2a.types import PaymentPayload
from x402_a2a.core.wallet import process_payment_required


class Wallet(ABC):
    """
    An abstract base class for a wallet that can sign payment requirements.
    This interface allows for different wallet implementations (e.g., local, MPC, hardware)
    to be used interchangeably by the client agent.
    """

    @abstractmethod
    async def sign_payment(self, requirements: x402PaymentRequiredResponse) -> PaymentPayload:
        """
        Signs a payment requirement and returns the signed payload.
        """
        raise NotImplementedError


class TronLocalWallet(Wallet):
    """
    A local Tron wallet that signs payments using a private key from the environment.

    Reads TRON_PRIVATE_KEY and TRON_NETWORK from environment variables.
    FOR DEMONSTRATION PURPOSES ONLY. Store private keys securely in production.
    """

    def __init__(self) -> None:
        private_key = os.environ.get("TRON_PRIVATE_KEY")
        if not private_key:
            raise ValueError(
                "TRON_PRIVATE_KEY environment variable is not set. "
                "Please set it to your Tron wallet private key (hex string)."
            )
        network = os.environ.get("TRON_NETWORK", "tron:nile")

        signer = TronClientSigner.from_private_key(private_key)
        mechanism = ExactPermitTronClientMechanism(signer)

        self._client = X402Client()
        self._client.register(network, mechanism)
        self._network = network
        self._address = signer.get_address()

    async def sign_payment(self, requirements: x402PaymentRequiredResponse) -> PaymentPayload:
        """
        Signs a payment requirement using Tron ExactPermit signing.
        """
        return await process_payment_required(requirements, self._client)


# Alias for backward compatibility with demo code that references MockLocalWallet
MockLocalWallet = TronLocalWallet

