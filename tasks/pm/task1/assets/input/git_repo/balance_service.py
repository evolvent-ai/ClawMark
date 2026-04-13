"""
FlashBuy Mall — Balance Service Interface
"""

import uuid


class BalanceService:
    """User wallet balance service.

    Provides real-time refund to user wallet balance.
    """

    def __init__(self, balance_api_url: str):
        self.balance_api_url = balance_api_url

    def credit(self, order_id: str, amount: float) -> dict:
        """
        Credit refund amount to user's wallet balance.

        Args:
            order_id: The order being refunded
            amount: Amount to credit

        Returns:
            dict with keys:
            - success (bool): Whether the credit was successful
            - tx_id (str): Transaction ID
            - message (str): Error message if failed

        Note:
            Balance refund is real-time — funds are immediately available
            in the user's wallet after a successful credit.
        """
        tx_id = f"BAL-{uuid.uuid4().hex[:8]}"
        return {
            "success": True,
            "tx_id": tx_id,
            "message": ""
        }

    def get_balance(self, user_id: str) -> float:
        """Get user's current wallet balance."""
        # In production, queries the balance database
        return 0.0
