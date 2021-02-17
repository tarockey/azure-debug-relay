import os
import debugpy
import argparse
from debug_utils import start_remote_debugging_from_args

def init():
    global is_debug

    parser = argparse.ArgumentParser(description="Parallel Step parameters")
    parser.add_argument('--is-debug', required=False, type=bool, default=False)
    args, _ = parser.parse_known_args()

    is_debug = args.is_debug


def run(input_rows):
    """
    Work with files
    """
    if is_debug and bool(os.environ.get('AZ_BATCH_IS_CURRENT_NODE_MASTER')):
        # debug mode and on the master node
        print("Let's start debugging")
        start_remote_debugging_from_args()
        debugpy.breakpoint()

    lines = []

    for file_item in input_rows:
        print(f"Work with a file {file_item}")

        lines.append(file_item)

    return lines
