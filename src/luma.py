from interpreter import LumaInterpreter
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Luma launcher that runs a script."
    )
    parser.add_argument(
        "script",
        help="Path to the Luma script to run"
    )

    args = parser.parse_args()
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
