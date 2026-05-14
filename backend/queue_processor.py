from collections import deque
import threading

class MessageQueue:
    def __init__(self):
        self._queue = deque()
        self._lock  = threading.Lock()

    def enqueue(self, message: dict):
        with self._lock:
            self._queue.append(message)

    def dequeue(self) -> dict | None:
        with self._lock:
            return self._queue.popleft() if self._queue else None

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0

    def clear(self):
        with self._lock:
            self._queue.clear()

message_queue = MessageQueue()
