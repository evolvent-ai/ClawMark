"""
FlashBuy Mall — Refund Service Main Logic
Version: v1.3 (after commit 3)
Last update: fix: add distributed lock for concurrent refund (#22)
"""

import time
import uuid
from datetime import datetime
from contextlib import contextmanager

from refund_model import RefundRecord, RefundStatus
from payment_gateway import PaymentGateway


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


class RefundService:
    """Refund Service

    Currently only supports "original path refund" as the refund method.

    Dependencies:
    - order_repo: Order data repository
    - gateway: PaymentGateway instance
    - redis_client: Redis client (for distributed lock)
    - refund_repo: Refund record repository
    """

    def __init__(self, order_repo, gateway, redis_client, refund_repo):
        self.order_repo = order_repo
        self.gateway = gateway
        self.redis_client = redis_client
        self.refund_repo = refund_repo

    def apply_refund(self, order_id, amount):
        """Apply for refund (original path refund)"""
        self._validate(order_id, amount)

        lock_key = f"refund:{order_id}"
        with distributed_lock(self.redis_client, lock_key):
            record = RefundRecord(
                id=str(uuid.uuid4()),
                order_id=order_id,
                amount=amount,
                refund_type='original',
                status=RefundStatus.PROCESSING,
                created_at=datetime.now()
            )
            self.refund_repo.save(record)

            try:
                result = self.gateway.refund(order_id, amount)
                if result['success']:
                    record.status = RefundStatus.SUCCESS
                    record.tx_id = result.get('tx_id')
                else:
                    record.status = RefundStatus.FAILED
                    record.failure_reason = result.get('message', 'unknown error')
            except Exception as e:
                record.status = RefundStatus.FAILED
                record.failure_reason = str(e)

            self.refund_repo.update(record)
            return record

    def _validate(self, order_id, amount):
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
        # TODO: 7-day refund window validation (required by PRD but not yet implemented)

    def get_refund_status(self, refund_id):
        record = self.refund_repo.get(refund_id)
        if record is None:
            raise ValueError(f"refund record not found: {refund_id}")
        return record

    def list_refunds_by_order(self, order_id):
        return self.refund_repo.list_by_order(order_id)
