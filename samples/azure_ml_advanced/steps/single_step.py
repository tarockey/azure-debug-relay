# This is a basic step that we are running on a compute in Azure ML
import argparse
import os
import debugpy
from samples.azure_ml_advanced.steps.amldebugutils import start_remote_debugging_from_args


def main():

    print("Parsing parameters")
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-files", type=str, required=True)
    parser.add_argument('--is-debug', type=str, required=True)
    args, _ = parser.parse_known_args()

    print(f"Output folder {args.pipeline_files}")

    if args.is_debug.lower() == 'true':
        print("Let's start debugging")
        if start_remote_debugging_from_args():
            debugpy.breakpoint()
            print("We are debugging!")
        else:
            print("Could not connect to a debugger!")

    os.makedirs(args.pipeline_files, exist_ok=True)

    # Generate 100 files to use in parallel run step later
    for i in range(0, 100):
        file_path = os.path.join(args.pipeline_files, f"{i}.txt")
        with open(file_path, "w") as f_handler:
            f_handler.write(f"Here is the content of the file #{i}")
    print("Step has been completed")


if __name__ == "__main__":
    main()
