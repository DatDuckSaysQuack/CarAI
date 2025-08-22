from __future__ import annotations

import multiprocessing as mp
import queue
from typing import Any


class BoundedQueue:
    """Drop-oldest bounded queue with a public drop counter.

    The queue wraps :class:`multiprocessing.Queue` and enforces the bound in
    user space. When the queue is full, the oldest item is discarded and a
    drop counter is incremented.
    """

    def __init__(self, maxsize: int) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be > 0")
        self._q: mp.Queue = mp.Queue(maxsize=maxsize)
        self.drop_ct = mp.Value("i", 0)

    def put(self, item: Any) -> None:
        """Put ``item`` into the queue, dropping the oldest if full."""
        try:
            self._q.put_nowait(item)
        except queue.Full:
            try:
                self._q.get_nowait()
            except queue.Empty:
                pass
            self._q.put_nowait(item)
            with self.drop_ct.get_lock():
                self.drop_ct.value += 1

    def get(self, block: bool = True, timeout: float | None = None):
        """Retrieve an item from the queue."""
        return self._q.get(block=block, timeout=timeout)

    def qsize(self) -> int:
        return self._q.qsize()

    def empty(self) -> bool:
        return self._q.empty()

    def full(self) -> bool:
        return self._q.full()
