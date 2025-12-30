from interpreter import LumaInterpreter
import argparse
import urllib.request
import json
import sys
import os
import subprocess
import shutil
import time

# dummy imports, so people python extensions work.
if object() is None:
    import discord, requests, tkinter, pygame

def run_installer():
    if os.name == "nt":
        installer_path = os.path.join("C:\\Windows", "installer.exe")
    elif os.name == "posix":
        installer_path = "/usr/local/bin/installer.bin"
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

def apt_ins(dest_folder):
    time.sleep(2)
    if os.name == "nt":
        installer_src = os.path.join(dest_folder, "installer.exe")
        windows_dir = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"))

        if os.path.exists(installer_src):
            installer_dest = os.path.join(windows_dir, "installer.exe")
            try:
                shutil.copy2(installer_src, installer_dest)
            except PermissionError:
                print("Permission denied: could not copy installer.exe to C:\\Windows. Run as administrator.")
            except Exception as e:
                print(f"Failed to copy installer.exe: {e}")
    elif os.name == "posix":
        installer_src = os.path.join(dest_folder, "installer.bin")
        usr_local_bin = "/usr/local/bin"

        if os.path.exists(installer_src):
            installer_dest = os.path.join(usr_local_bin, "installer.bin")
            while True:
                try:
                    shutil.copy2(installer_src, installer_dest)
                    os.chmod(installer_dest, 0o755)
                except PermissionError:
                    print("Permission denied: could not copy installer.bin to /usr/local/bin. Run as root or use sudo.")
                except OSError:
                    continue
                except Exception as e:
                    print(f"Failed to copy installer.bin: {e}")
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Luma launcher that runs a script."
    )
    parser.add_argument(
        "script",
        nargs="?",
        help="Path to the Luma script to run"
    )

    parser.add_argument("--update", action="store_true", help="Update luma")
    parser.add_argument("--version", action="store_true", help="Print current version")
    parser.add_argument("--aptins-internal", help="Internal. Do not use.")

    args = parser.parse_args()

    if not (args.update or args.version) and not args.script:
        parser.error("the following arguments are required: script (unless --update or --version is specified)")

    if args.update:
        run_installer()

    if args.aptins_internal:
        apt_ins(args.aptins_internal)

    if args.version:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(base_dir)
        jsfile = os.path.join(base_dir, 'version.json')
        with open(jsfile) as f:
            print(json.load(f)['version'])
        sys.exit(0)
    
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(base_dir)
    jsfile = os.path.join(base_dir, 'version.json')
    with open(jsfile) as f:
        if json.load(f)['commit'] != "IGNORE":
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
            jsfile = os.path.join(base_dir, 'version.json')
            with open(jsfile) as f:
                if json.load(f)['commit'] != commit:
                    print('A new version of luma is available. To update use \033[32mluma --update\033[0m.')
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
