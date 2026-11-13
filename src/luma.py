from interpreter import LumaInterpreter
import argparse
import json
import sys
import os

if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

    parser = argparse.ArgumentParser(description="Luma launcher that runs a script.")
    parser.add_argument("script", nargs="?", help="Path to the Luma script to run")

    parser.add_argument("--update", action="store_true", help="Update luma")
    parser.add_argument("--version", action="store_true", help="Print current version")

    args = parser.parse_args()

    if not (args.update or args.version) and not args.script:
        parser.error(
            "the following arguments are required: script (unless --update or --version is specified)"
        )

    if args.version:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(base_dir)
        jsfile = os.path.join(base_dir, "version.json")
        with open(jsfile) as f:
            print(json.load(f)["version"])
        sys.exit(0)

    filename: str = args.script
    interpreter = LumaInterpreter()
    if filename.endswith(".lum"):
        try:
            with open(f"{filename}") as file:
                program = file.read()
            interpreter.run(program, filename)
        except FileNotFoundError:
            print(f"The file {filename} does not exists.")
    else:
        print(f"The file {filename} is not a luma program.")
