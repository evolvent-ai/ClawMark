"""
FlashBuy Mall — Refund Data Model
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RefundStatus(str, Enum):
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class RefundRecord:
    id: str
    order_id: str
    amount: float
    refund_type: str = "original"  # 'original' or 'balance'
    status: RefundStatus = RefundStatus.PROCESSING
    created_at: datetime = field(default_factory=datetime.now)
    tx_id: Optional[str] = None
    failure_reason: Optional[str] = None
