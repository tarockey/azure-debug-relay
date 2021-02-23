import debugpy
import logging
import threading
from .threads import StoppableThread


class DebugPyEx():
    """Use this class instead of debugpy.
    It provides an additional manageability layer on top of debugpy calls.
    """
    _DEFAULT_CONNECT_TIMEOUT = 30
    _debugpy_connected = False
    _connect_lock = threading.Lock()

    def _thread_connect_proc(host, port):
        try:
            debugpy.connect((host, port))
            DebugPyEx._debugpy_connected = True
        except SystemExit:
            # SystemExit is a "legal" way to terminate this thread.
            logging.warn("Debugpy thread has been terminated.")


    @staticmethod
    def init():
        debugpy.connect_with_timeout = DebugPyEx.connect


    @staticmethod
    def connect(address, connect_timeout_seconds: float = _DEFAULT_CONNECT_TIMEOUT) -> bool:
        with DebugPyEx._connect_lock:
            DebugPyEx._debugpy_connected = False
            host, port = address
            thread = StoppableThread(target=DebugPyEx._thread_connect_proc, args=(
                host, port,), daemon=True)
            thread.start()
            thread.join(connect_timeout_seconds)
            if(thread.is_alive()):
                # kill the thread "gracefully"!
                thread.stop()
                return False
            elif DebugPyEx._debugpy_connected:
                debugpy.debug_this_thread()
                return True
            else:
                return False

