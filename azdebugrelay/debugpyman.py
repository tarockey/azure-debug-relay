import time
import threading
import debugpy
import logging
from .threads import StoppableThread


class DebugPy():
    """Use this class instead of debugpy.
    It provides an additional manageability layer on top of debugpy calls.
    """
    def _thread_connect_proc(*args, **_):
        try:
            debugpy.connect(args)
        except KeyboardInterrupt:
            # KeyboardInterrupt is a "legal" way to terminate this thread.
            logging.warn("Debugpy thread has been terminated.")


    def _cancelling_thread(*args, **_):
        timeout = args[0] if len(args) > 0 else 0
        if timeout is None or timeout == 0:
            return
        time.sleep(timeout)
        if not debugpy.is_client_connected() and debugpy.wait_for_client.cancel is not None:
            debugpy.wait_for_client.cancel()


    @staticmethod
    def connect(address, access_token, connect_timeout_seconds: float = None) -> bool:
        thread = StoppableThread(target=DebugPy._thread_connect_proc, args=(
            address, access_token), daemon=True)
        debugpy.os.abort()
        thread.start()
        thread.ident
        thread.join(connect_timeout_seconds)
        if(thread.is_alive()):
            # kill the thread "gracefully"!
            thread.stop()
            return False
        else:
            debugpy.debug_this_thread()
            return True


    @staticmethod
    def listen(address):
        return debugpy.listen(address)


    @staticmethod
    def wait_for_client(connect_timeout_seconds: float = None) -> bool:
        _ = threading.Thread(
            DebugPy._cancelling_thread, args=(connect_timeout_seconds))
        debugpy.wait_for_client()
        return debugpy.is_client_connected()


    @staticmethod
    def cancel_wait_for_client():
        return debugpy.wait_for_client.cancel()


    @staticmethod
    def is_client_connected():
        return debugpy.is_client_connected()


    @staticmethod
    def breakpoint():
        return debugpy.breakpoint()


    @staticmethod
    def debug_this_thread():
        return debugpy.debug_this_thread()


    @staticmethod
    def trace_this_thread(should_trace):
        return debugpy.trace_this_thread(should_trace)


    @staticmethod
    def log_to(path):
        return debugpy.log_to(path)

    @staticmethod
    def configure(properties=None, **kwargs):
        return debugpy.configure(properties, kwargs)
