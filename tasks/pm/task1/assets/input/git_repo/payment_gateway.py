"""
FlashBuy Mall — Payment Gateway Wrapper
"""

import uuid
from typing import Optional


class PaymentGateway:
    """Payment gateway interface for third-party refund processing.

    Wraps calls to the external payment provider (e.g., Alipay, WeChat Pay, bank API).
    """

    def __init__(self, provider_url: str, api_key: str):
        self.provider_url = provider_url
        self.api_key = api_key

    def refund(self, order_id: str, amount: float) -> dict:
        """
        Initiate a refund via the third-party payment channel.

        Args:
            order_id: The order to refund
            amount: Refund amount

        Returns:
            dict with keys:
            - success (bool): Whether the refund was accepted
            - tx_id (str): Transaction ID from the payment provider
            - message (str): Error message if failed

        Note:
            This method may timeout if the third-party callback takes too long.
            Currently there is no retry mechanism for callback timeouts.
        """
        # In production, this calls the external payment API
        # Simplified implementation for development/testing
        tx_id = f"TX-{uuid.uuid4().hex[:8]}"
        return {
            "success": True,
            "tx_id": tx_id,
            "message": ""
        }
