from collections import deque

class HistoryManager:
    """
    Mantiene un historial de snapshots (bytes PDF).
    Índice apunta al snapshot actual.
    """
    def __init__(self, limit: int = 30):
        self.limit = limit
        self._stack = deque()   # lista de bytes
        self._index = -1        # -1 => vacío

    def reset_with(self, data: bytes):
        self._stack.clear()
        self._stack.append(data)
        self._index = 0

    def push(self, data: bytes):
        if self._index >= 0 and self._stack and data == self._stack[self._index]:
            return  # sin cambios
        # Truncar redo
        while len(self._stack) - 1 > self._index:
            self._stack.pop()
        self._stack.append(data)
        self._index += 1
        # Limitar
        while len(self._stack) > self.limit:
            self._stack.popleft()
            self._index -= 1

    def can_undo(self) -> bool:
        return self._index > 0

    def can_redo(self) -> bool:
        return self._index >= 0 and self._index < len(self._stack) - 1

    def undo(self) -> bytes:
        if not self.can_undo():
            raise RuntimeError("No undo")
        self._index -= 1
        return self._stack[self._index]

    def redo(self) -> bytes:
        if not self.can_redo():
            raise RuntimeError("No redo")
        self._index += 1
        return self._stack[self._index]

    def current(self) -> bytes:
        if self._index < 0:
            raise RuntimeError("Empty history")
        return self._stack[self._index]