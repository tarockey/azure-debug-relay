import os
import argparse


def init():
    global is_debug

    parser = argparse.ArgumentParser(description="Parallel Step parameters")
    parser.add_argument('--is_debug', required=True, type=bool)
    args, _ = parser.parse_known_args()

    is_debug = args.is_debug


def run(input_rows):
    """
    Work with files
    """
    if is_debug and bool(os.environ.get('AZ_BATCH_IS_CURRENT_NODE_MASTER')):
        print("Debug mode is enabled")

    lines = []

    for file_item in input_rows:
        print(f"Work with a file {file_item}")

        lines.append(file_item)

    return lines