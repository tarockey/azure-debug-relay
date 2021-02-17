import os
import debugpy
from debug_utils import remote_debugger_init

def init():
    global is_debug

    is_debug = remote_debugger_init()


def run(input_rows):
    """
    Work with files
    """
    if is_debug and bool(os.environ.get('AZ_BATCH_IS_CURRENT_NODE_MASTER')):
        # debug mode and on the master node
        print("Let's start debugging")
        debugpy.breakpoint()

    lines = []

    for file_item in input_rows:
        print(f"Work with a file {file_item}")

        lines.append(file_item)

    return lines
