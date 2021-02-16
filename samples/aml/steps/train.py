import argparse
import logging
from azureml.core import Run
import debugpy
from azdebugrelay import DebugRelay, DebugMode


def init():
    pass


def run(mini_batch):
    result_list = []
    message = f'run method start: {__file__}, run({mini_batch}).'
    print(message)

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store',
                        default="", choices=['attach', 'none'], required=False)
    parser.add_argument('--debug-relay-connection-string', action='store',
                        default="", required=False)
    parser.add_argument('--debug-relay-name', action='store',
                        default="", required=False)
    options = parser.parse_known_args()

    debug_port = None
    debug_relay = None
    debug = False

    if options.debug == "attach":
        if options.debug_relay_connection_string == "" or options.debug_relay_name == "":
            err_msg = "Cannot establish debugging session: debug relay connection string or name is empty."
            logging.fatal(err_msg)
            raise ValueError(err_msg)
    
        available_ports = [5678, 5679, 5680]
        for port in available_ports:
            try:
                Run.get_context().add_properties({f"debug_port_{port}":f"{port}"})
                debug_port = port
            except Exception:
                continue
 
        if debug_port is not None:
            debug = True
            debug_message = f" With a debugging session on port {debug_port}"
            print(debug_message)
            message += debug_message

            access_key_or_connection_string = options.debug_relay_connection_string
            relay_name = options.debug_relay_name # your Hybrid Connection name
            debug_mode = DebugMode.Connect # or DebugMode.WaitForConnection if connecting from another end
            hybrid_connection_url = None # can keep it None because access_key_or_connection_string is a connection string
            host = "127.0.0.1" # local hostname or ip address the debugger starts on
            port = debug_port

            debug_relay = DebugRelay(access_key_or_connection_string, relay_name, debug_mode, hybrid_connection_url, host, port)
            debug_relay.open()
            debugpy.connect((host, port))


    do_work(mini_batch=mini_batch, debug=debug)
    result_list.append(message)

    if debug_relay is not None:
        debug_relay.close()

    return result_list


def do_work(mini_batch, debug: bool = False):
    if debug:
        debugpy.breakpoint()
    print(f"Doing my work. Debug mode is {debug}.")
    print(f"Mini-batch is {mini_batch}")