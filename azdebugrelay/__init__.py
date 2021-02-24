from .debug_relay import DebugRelay, DebugMode
from .debugpyex import DebugPyEx

__all__ = [
    "DebugRelay",
    "DebugMode",
    "debugpy_connect_with_timeout"
]


def debugpy_connect_with_timeout(host, port, connect_timeout_seconds):
    return DebugPyEx.connect(str(host), int(port), float(connect_timeout_seconds))