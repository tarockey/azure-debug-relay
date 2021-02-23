import os
import debugpy
import argparse
from samples.azure_ml_advanced.steps.amldebugutils import *


def init():
    global is_debug

    parser = argparse.ArgumentParser(description="Parallel Step parameters")
    parser.add_argument('--is-debug', required=True, type=str)
    args, _ = parser.parse_known_args()

    is_debug = False
    # debug mode and on the master node
    if args.is_debug.lower() == 'true' and bool(os.environ.get('AZ_BATCH_IS_CURRENT_NODE_MASTER')):
        is_debug = True
        print("This is a mater node. Start a debugging session.")
        start_remote_debugging_from_args()


def run(input_rows):
    """
    Work with files
    """
    if is_debug:
        print("Debugging a parallel step")
        debugpy.breakpoint()

    lines = []

    for file_item in input_rows:
        print(f"Work with a file {file_item}")

        lines.append(file_item)

    return lines
