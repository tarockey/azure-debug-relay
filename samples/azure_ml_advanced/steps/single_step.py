# This is a basic step that we are running on a compute in Azure ML
import argparse
import os
import debugpy
from debug_utils import remote_debugger_init

def main():

    print("Parsing parameters")
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-files", type=str, required=True)
    args, _ = parser.parse_known_args()

    print(f"Output folder {args.pipeline_files}")

    is_debug = remote_debugger_init()

    if is_debug:
        print("Let's start debugging")
        debugpy.breakpoint()

    os.makedirs("pipeline_files", exist_ok=True)

    # Generate 100 files to use in parallel run step later
    for i in range(0, 1000):
        file_path = os.path.join(args.pipeline_files, f"{i}.txt")
        with open(file_path, "w") as f_handler:
            f_handler.write(f"Here is the content of the file #{i}")
    print("Step has been completed")


if __name__ == "__main__":
    main()
