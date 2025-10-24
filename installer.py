import winreg
import ctypes
import sys
import win32con
import win32gui
import urllib.request
import zipfile
import os
import io
import shutil

def get_files():
    url = "https://github.com/Erri4/PyLuma/archive/refs/heads/main.zip"
    dest_folder = "C:/PyLuma"
    
    if os.name == "nt":
        dest_folder = "C:/PyLuma"
    elif os.name == "posix":
        dest_folder = "/PyLuma"

    if os.path.exists(dest_folder):
        shutil.rmtree(dest_folder)
    os.makedirs(dest_folder, exist_ok=True)

    with urllib.request.urlopen(url) as response:
        zip_data = response.read()

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
        for member in zip_ref.namelist():
            filename = "/".join(member.split("/")[1:])
            if not filename:
                continue
            target_path = os.path.join(dest_folder, filename)
            if member.endswith("/"):
                os.makedirs(target_path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "wb") as f:
                    f.write(zip_ref.read(member))
    file_path = os.path.join(dest_folder, "bin/luma" + ".exe" if os.name != "nt" else '.bin')
    if os.path.exists(file_path):
        os.remove(file_path)


def add_to_PATH(path: str):
    key = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    with winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE) as hklm:
        with winreg.OpenKey(hklm, key, 0, winreg.KEY_READ | winreg.KEY_WRITE) as env_key:
            current_path: str = winreg.QueryValueEx(env_key, "Path")[0]
            if path.lower() in current_path.lower():
                print("Already in PATH.")
                return
            new_path_value = current_path.rstrip(';') + ";" + path
            winreg.SetValueEx(env_key, "Path", 0, winreg.REG_EXPAND_SZ, new_path_value)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if is_admin():
    add_to_PATH(r"C:\PyLuma")
    add_to_PATH(r"C:\PyLuma\bin")

    win32gui.SendMessageTimeout(
        win32con.HWND_BROADCAST,
        win32con.WM_SETTINGCHANGE,
        0,
        "Environment",
        win32con.SMTO_ABORTIFHUNG,
        5000
    )
else:
    get_files()
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)