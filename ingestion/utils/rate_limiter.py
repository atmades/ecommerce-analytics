"""
Token bucket rate limiter для MercadoLibre API.
Лимит: 600 запросов в минуту согласно документации.
"""
import time
import threading
import logging

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    def __init__(self, rate: int = 600, per: int = 60):
        self.rate = rate
        self.per = per
        self.tokens = float(rate)
        self.last_check = time.time()
        self._lock = threading.Lock()

    def acquire(self):
        with self._lock:
            now = time.time()
            elapsed = now - self.last_check
            self.tokens = min(
                self.rate,
                self.tokens + elapsed * (self.rate / self.per)
            )
            self.last_check = now

            if self.tokens < 1:
                sleep_time = (1 - self.tokens) / (self.rate / self.per)
                logger.debug(f"Rate limit: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
                self.tokens = 0
            else:
                self.tokens -= 1
