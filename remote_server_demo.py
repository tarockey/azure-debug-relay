import os
import sys
import argparse
import debugpy
import platform
from azdebugrelay import DebugRelay, DebugMode


def do_work():
    print("Hello world!")
    plat = platform.platform()
    print(plat)


def _check_for_debugging(args) -> DebugRelay:
    debug_relay = None
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store',
                        default="no", choices=['attach', 'listen', 'none'], required=False)
    options = parser.parse_args(args=args)
    if options.debug != "none":
        print(f"Starting DebugRelay in `{options.debug}` mode.")

        config_file = "azrelay.json"
        mode = DebugMode.Connect if options.debug == "attach" else DebugMode.WaitForConnection
        if os.path.exists(config_file):
            debug_relay = DebugRelay.from_config(config_file, debug_mode=mode)
        else:
            debug_relay = DebugRelay.from_environment(mode, debug_mode=mode)
        
        # you can also create DebugRelay directly by providing connection string and the rest of its configuration:
        # debug_relay = DebugRelay(access_key_or_connection_string, relay_name, debug_mode, hybrid_connection_url, port)
        
        if debug_relay is None:
            print("Cannot create Debug Relay due to missing configuration.")

        debug_relay.open()

        if debug_relay.is_running():
            print("Connecting to the remote host...")
            if options.debug == "attach":
                debugpy.connect(("127.0.0.1", 5678))
            else:
                debugpy.listen(("127.0.0.1", 5678))
                debugpy.wait_for_client()
            print("Connected!!!")
    return debug_relay


def _main(args):
    debug_relay = _check_for_debugging(args)

    do_work()

    if debug_relay is not None:
        debug_relay.close()


if __name__ == '__main__':
    _main(sys.argv[1:])
