import os
import sys
import argparse
import debugpy
import platform
import pathlib

### This block is only for debugging from samples/simple_demo directory.
### You don't need it when have azdebugrelay module installed.
import pkg_resources
_AZDEBUGRELYNAME = "azdebugrelay"
_required_azdebugrelay = {_AZDEBUGRELYNAME}
_installed_azdebugrelay = {pkg.key for pkg in pkg_resources.working_set}
_missing_azdebugrelay = _required_azdebugrelay - _installed_azdebugrelay

if _missing_azdebugrelay:
    _workspace_dir = pathlib.Path(__file__).parent.parent.parent.absolute()
    _azdebugrelay_dir = os.path.dirname(
        os.path.join(_workspace_dir, "azdebugrelay"))
    sys.path.insert(0, _azdebugrelay_dir)
###############  

from azdebugrelay import DebugRelay, DebugMode


def do_work():
    """Just a demo function. We debug it.
    """
    print("Hello world!")
    plat = platform.platform()
    debugpy.breakpoint() # you can put a real VSCode breakpoint
    print(plat) # the debugger will stop here because debugpy.breakpoint() call above


def _check_for_debugging(args) -> DebugRelay:
    """An over-engineered debugger initialization function.
    Parses command-line arguments looking for `--debug` option.
    If found option's value defines debugging behaviour:
     * `attach` - connects to a remote debugger (your VS Code in `listen` mode)
     * `listen` - starts listening for a remote debugger to connect
     * `none` (default) - do not start a DebugRelay

    Args:
        args: Command line arguments

    Returns:
        DebugRelay: running DebugRelay object
    """
    debug_relay = None
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store',
                        default="none", choices=['attach', 'listen', 'none'], required=False)
    options = parser.parse_args(args=args)
    if options.debug != "none":
        print(f"Starting DebugRelay in `{options.debug}` mode.")

        config_file = "./.azrelay.json"

        mode = DebugMode.Connect if options.debug == "attach" else DebugMode.WaitForConnection
        if os.path.exists(config_file):
            debug_relay = DebugRelay.from_config(config_file, debug_mode=mode)
        else:
            debug_relay = DebugRelay.from_environment(debug_mode=mode)
        
        # you can also create DebugRelay directly by providing connection string and the rest of its configuration:
        # debug_relay = DebugRelay(access_key_or_connection_string, relay_name, debug_mode, hybrid_connection_url, port)
        
        if debug_relay is None:
            print("Cannot create Debug Relay due to missing configuration.")
            return None

        DebugRelay.kill_relays()
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
    """CLI entry point

    Args:
        args: Command Line arguments
    """
    debug_relay = _check_for_debugging(args)

    do_work()

    if debug_relay is not None:
        debug_relay.close()


if __name__ == '__main__':
    _main(sys.argv[1:])
