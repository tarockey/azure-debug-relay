from enum import Enum
import os
import logging
import subprocess
import stat
import urllib.request
from pathlib import Path
import ssl
import platform
import tarfile
import threading
import time
import zipfile


def static_init(cls):
    if getattr(cls, "_static_init", None):
        cls._static_init()
    return cls


@static_init
class _AzRelay(object):
    _class_init = False
    _init_lock = threading.Lock()
    _install_lock = threading.Lock()
    # Azure Relay Bridge executable name
    relay_app_name = "azbridge"
    # `~/.az_AzRelay` installation directory
    relay_dir_name = ".az_AzRelay"
    # current Azure Debug Relay build
    relay_version_name = "0.2.9"
    # are we on Windows?
    is_windows = False

    DEFAULT_AZ_RELAY_BRIDGE_UBUNTU_DOWLOAD =\
        "https://github.com/vladkol/azure-relay-bridge/releases/download/v0.2.9/azbridge.azrelay_folder-rel.ubuntu.18.04-x64.tar.gz"
    DEFAULT_AZ_RELAY_BRIDGE_MACOS_DOWLOAD =\
        "https://github.com/vladkol/azure-relay-bridge/releases/download/v0.2.9/azbridge.0.2.9-rel.osx-x64.tar.gz"
    DEFAULT_AZ_RELAY_BRIDGE_DEBIAN_DOWLOAD =\
        "https://github.com/vladkol/azure-relay-bridge/releases/download/v0.2.9/azbridge.0.2.9-rel.debian.10-x64.tar.gz"
    DEFAULT_AZ_RELAY_BRIDGE_WINDOWS_DOWLOAD =\
        "https://github.com/vladkol/azure-relay-bridge/releases/download/v0.2.9/azbridge.0.2.9-rel.win10-x64.zip"

    _installed_az_relay = False


    @classmethod
    def _static_init(cls):
        if not cls._class_init:
            with cls._init_lock:
                if not cls._class_init:  # check one more time after a lock
                    system = platform.system().lower()
                    cls.is_windows = system.startswith(
                        "windows") or system.startswith("cygwin")
                    cls._install_azure_relay_bridge()
                    cls._class_init = True


    @staticmethod
    def kill_relays():
        """Kills all Azure Relay Bridge processes (azrelay) - no matter who and how launched them
        """
        if _AzRelay.is_windows:
            subprocess.run(
                f"taskkill /IM \"{_AzRelay.relay_app_name}.exe\" /F", shell=True)
        else:
            subprocess.run(f"pkill -9 {_AzRelay.relay_app_name}", shell=True)


    @staticmethod
    def _install_azure_relay_bridge():
        """Installs or updates Azure Relay Bridge
        """
        with _AzRelay._install_lock:
            if _AzRelay._installed_az_relay:
                return
            _AzRelay._installed_az_relay = True

            azrelay_folder = os.path.join(
                Path.home(), _AzRelay.relay_dir_name, _AzRelay.relay_version_name)
            azrelay_parent = os.path.join(
                Path.home(), _AzRelay.relay_dir_name)
            azrelay_symlink = os.path.join(
                azrelay_parent, _AzRelay.relay_app_name)
            relay_file = os.path.join(
                azrelay_folder, _AzRelay.relay_app_name)

            exists = os.path.exists(azrelay_folder)
            if not exists:
                if _AzRelay.is_windows:
                    download = _AzRelay.DEFAULT_AZ_RELAY_BRIDGE_WINDOWS_DOWLOAD
                else:
                    plat = platform.platform().lower()
                    if plat.startswith("macos"):
                        download = _AzRelay.DEFAULT_AZ_RELAY_BRIDGE_MACOS_DOWLOAD
                    elif "-ubuntu" in plat or plat.startswith("ubuntu"):
                        download = _AzRelay.DEFAULT_AZ_RELAY_BRIDGE_UBUNTU_DOWLOAD
                    else:  # assume Debian
                        download = _AzRelay.DEFAULT_AZ_RELAY_BRIDGE_DEBIAN_DOWLOAD
                        if "debian" not in plat:
                            logging.warning(f"You are running an unsupported OS: {plat}. "
                                            "Using Debian build of Azure Relay Bridge.")

                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                filestream = urllib.request.urlopen(download, context=ctx)

                if download.lower().endswith(".zip"):
                    with zipfile.ZipFile(filestream, 'r') as zip_ref:
                        zip_ref.extractall(azrelay_folder)
                else:
                    with tarfile.open(fileobj=filestream, mode="r|gz") as thetarfile:
                        thetarfile.extractall(azrelay_folder)

                if not _AzRelay.is_windows:
                    st = os.stat(relay_file)
                    os.chmod(relay_file, st.st_mode | stat.S_IEXEC)

            if not exists or not os.path.exists(azrelay_symlink):
                tmp_link = f"{azrelay_symlink}.tmp"
                os.symlink(relay_file, tmp_link)
                os.replace(tmp_link, azrelay_symlink)
                st = os.stat(azrelay_symlink)
                os.chmod(azrelay_symlink, st.st_mode | stat.S_IEXEC)

            existing_path_var = os.environ["PATH"]
            paths = existing_path_var.split(os.pathsep)
            if azrelay_parent not in paths:
                os.environ["PATH"] += os.pathsep + azrelay_parent


    def __init__(self):
        pass
