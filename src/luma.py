from interpreter import LumaInterpreter
import argparse
import urllib.request
import json
import sys
import os
import subprocess


def run_installer(): # DO NOT USE YET
    if os.name == "nt":
        installer_path = os.path.join("C:\\PyLuma", "installer.exe")
    elif os.name == "posix":
        installer_path = os.path.join(os.path.expanduser("~/PyLuma"), 'installer.bin')
    else:
        return

    if not os.path.exists(installer_path):
        print(f"Installer not found at {installer_path}")
        return

    try:
        if os.name == "nt":
            subprocess.run([installer_path], check=True)
        else:
            subprocess.run(["sudo", installer_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Installer failed with exit code {e.returncode}")
    except Exception as e:
        print(f"Failed to run installer: {e}")
    sys.exit()

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

    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(base_dir)
    jsfile = os.path.join(base_dir, "version.json")
    with open(jsfile) as f:
        if json.load(f)["commit"] != "IGNORE":
            repo = "Erri4/PyLuma"
            url = f"https://api.github.com/repos/{repo}/commits/main"
            with urllib.request.urlopen(url) as response:
                data = json.load(response)

            commit = data["sha"]
            if getattr(sys, "frozen", False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(base_dir)
            jsfile = os.path.join(base_dir, "version.json")
            with open(jsfile) as f:
                if json.load(f)["commit"] != commit:
                    if args.update:
                        run_installer()
                    else:
                        print(
                            "A new version of luma is available. To update use \033[32mluma --update\033[0m."
                        )
                else:
                    if args.update:
                        print("No now version was found. Interpreter wasn't updated.")
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
