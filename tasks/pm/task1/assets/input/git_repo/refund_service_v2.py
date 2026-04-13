"""
FlashBuy Mall — Refund Service V2 (Balance Refund Support)
Version: v2.0
Last update: feat: add balance refund support
"""

import uuid
from datetime import datetime
from contextlib import contextmanager

from refund_model import RefundRecord, RefundStatus
from payment_gateway import PaymentGateway
from balance_service import BalanceService


class RedisLock:
    """Simple distributed lock wrapper (based on Redis SETNX)"""

    def __init__(self, redis_client, key, timeout=30):
        self.redis = redis_client
        self.key = key
        self.timeout = timeout
        self._token = None

    def acquire(self):
        self._token = str(uuid.uuid4())
        return self.redis.set(self.key, self._token, nx=True, ex=self.timeout)

    def release(self):
        if self._token:
            lua = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            self.redis.eval(lua, 1, self.key, self._token)


@contextmanager
def distributed_lock(redis_client, key, timeout=30):
    """Distributed lock context manager"""
    lock = RedisLock(redis_client, key, timeout)
    if not lock.acquire():
        raise RuntimeError(f"Failed to acquire lock: {key}")
    try:
        yield lock
    finally:
        lock.release()


class RefundServiceV2:
    """Refund Service V2

    Supports two refund methods:
    1. Original path refund — funds returned to original payment account
    2. Balance refund — funds credited to user wallet balance (real-time)

    Dependencies:
    - order_repo: Order data repository
    - gateway: PaymentGateway instance
    - balance_service: BalanceService instance
    - redis_client: Redis client (for distributed lock)
    - refund_repo: Refund record repository
    """

    def __init__(self, order_repo, gateway, balance_service, redis_client, refund_repo):
        self.order_repo = order_repo
        self.gateway = gateway
        self.balance_service = balance_service
        self.redis_client = redis_client
        self.refund_repo = refund_repo

    def apply_refund(self, order_id, amount, refund_type='original'):
        """Apply for refund

        Args:
            order_id: Order ID
            amount: Refund amount
            refund_type: 'original' or 'balance'
        """
        self._validate(order_id, amount, refund_type)

        # NOTE: lock key only uses order_id, does NOT include refund_type
        # This means two different refund types for the same order can
        # bypass the lock and execute concurrently
        lock_key = f"refund:{order_id}"
        with distributed_lock(self.redis_client, lock_key):
            record = RefundRecord(
                id=str(uuid.uuid4()),
                order_id=order_id,
                amount=amount,
                refund_type=refund_type,
                status=RefundStatus.PROCESSING,
                created_at=datetime.now()
            )
            self.refund_repo.save(record)

            try:
                if refund_type == 'original':
                    result = self.gateway.refund(order_id, amount)
                elif refund_type == 'balance':
                    result = self.balance_service.credit(order_id, amount)
                else:
                    raise ValueError(f"unsupported refund type: {refund_type}")

                if result['success']:
                    record.status = RefundStatus.SUCCESS
                    record.tx_id = result.get('tx_id')
                else:
                    record.status = RefundStatus.FAILED
                    record.failure_reason = result.get('message', 'unknown error')
            except ValueError:
                raise
            except Exception as e:
                record.status = RefundStatus.FAILED
                record.failure_reason = str(e)

            self.refund_repo.update(record)
            return record

    def _validate(self, order_id, amount, refund_type):
        """Refund parameter validation"""
        order = self.order_repo.get(order_id)
        if order is None:
            raise ValueError(f"order not found: {order_id}")
        if amount <= 0:
            raise ValueError("amount must be positive")
        if amount > order.paid_amount:
            raise ValueError(f"amount {amount} exceeds paid amount {order.paid_amount}")
        if order.status != 'paid':
            raise ValueError(f"order status is '{order.status}', expected 'paid'")
        if refund_type not in ('original', 'balance'):
            raise ValueError(f"unsupported refund type: {refund_type}")

        # 7-day refund window validation
        days_since_paid = (datetime.now() - order.paid_at).days
        if days_since_paid > 7:
            raise ValueError("refund window expired: must request within 7 days of payment")

        # Check for existing refund — BUT only checks PROCESSING status
        # BUG: Does not check SUCCESS status, so an order that already has a
        # successful refund can still initiate another refund request
        existing = self.refund_repo.find_by_order_and_status(
            order_id, RefundStatus.PROCESSING
        )
        if existing:
            raise ValueError(f"refund already in progress for order {order_id}")

    def get_refund_status(self, refund_id):
        record = self.refund_repo.get(refund_id)
        if record is None:
            raise ValueError(f"refund record not found: {refund_id}")
        return record

    def list_refunds_by_order(self, order_id):
        return self.refund_repo.list_by_order(order_id)
