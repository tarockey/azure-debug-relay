from enum import Enum
import os
import sys
import logging
import subprocess
import stat
from typing import Any
import urllib.request
from pathlib import Path
import ssl
import platform
import tempfile
import tarfile
import time
import json
import zipfile


class DebugMode(Enum):
    WaitForConnection=1,
    Connect=2


class DebugRelay(object):
    relay_app_name = "azbridge"
    relay_dir_name = ".azdebugrelay"
    relay_version_name = "0.2.9"
    is_windows = platform.platform().lower().startswith("windows")

    DEFAULT_AZ_RELAY_BRIDGE_UBUNTU_DOWLOAD =\
        "https://github.com/vladkol/azure-relay-bridge/releases/download/v0.2.9/azbridge.azrelay_folder-rel.ubuntu.18.04-x64.tar.gz"
    DEFAULT_AZ_RELAY_BRIDGE_MACOS_DOWLOAD =\
        "https://github.com/vladkol/azure-relay-bridge/releases/download/v0.2.9/azbridge.0.2.9-rel.osx-x64.tar.gz"
    DEFAULT_AZ_RELAY_BRIDGE_DEBIAN_DOWLOAD =\
        "https://github.com/vladkol/azure-relay-bridge/releases/download/v0.2.9/azbridge.0.2.9-rel.debian.10-x64.tar.gz"
    DEFAULT_AZ_RELAY_BRIDGE_WINDOWS_DOWLOAD =\
        "https://github.com/vladkol/azure-relay-bridge/releases/download/v0.2.9/azbridge.0.2.9-rel.win10-x64.zip"

    _installed_az_relay = False


    def __init__(self,
                 access_key_or_connection_string: str,
                 relay_name: str,
                 debug_mode: DebugMode = DebugMode.WaitForConnection,
                 hybrid_connection_url: str = None, 
                 port: int = 5678,
                 az_relay_connection_wait_time: float = 60):
        self.relay_subprocess = None
        if access_key_or_connection_string.startswith("Endpoint="):
            have_connection_string = True
        else:
            have_connection_string = False
        if hybrid_connection_url is None or hybrid_connection_url == "":
            if not have_connection_string:
                raise ValueError(
                    "hybrid_connection_url must be specified when "\
                    "access_key_or_connection_string is not a connection string.")

        if have_connection_string:
            self.auth_option = f"-x \"{access_key_or_connection_string}\"" 
        else:
            self.auth_option = f"-E \"{hybrid_connection_url}\" -k \"{access_key_or_connection_string}\""

        if debug_mode == DebugMode.WaitForConnection:
            self.connection_option = f"-R {relay_name}:127.0.0.1:{port}"
        else:
            self.connection_option = f"-L 127.0.0.1:{port}:{relay_name}"

        self.az_relay_connection_wait_time = az_relay_connection_wait_time


    def __del__(self):
        self.close()


    def open(self):
        self.close()
        DebugRelay._install_azure_relay_bridge()
        command = f"{DebugRelay.relay_app_name} {self.connection_option} {self.auth_option}"

        self.relay_subprocess = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            shell=True, universal_newlines=True)
        
        time.sleep(1)

        start = time.perf_counter()

        remote_forward_ready = False
        local_forward_ready = False
        text_output = ""
        for line in iter(self.relay_subprocess.stdout.readline, ''):
            text_output += f"{line}\n"
            if line.find("LocalForwardHostStart") != -1:
                local_forward_ready = True
            elif line.find("RemoteForwardHostStart") != -1:
                remote_forward_ready = True
            if remote_forward_ready and local_forward_ready:
                break
            time_delta = time.perf_counter() - start
            if time_delta > self.az_relay_connection_wait_time: 
                raise TimeoutError()
        logging.info("Debugging relay is ready!")
        print(text_output)


    def close(self):
        print("Closing Debug Relay...")
        if self.is_running():
            self.relay_subprocess.terminate()
            try:
                self.relay_subprocess.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.relay_subprocess.kill()
        else:
            self._kill_relays()
        self.relay_subprocess = None


    def is_running(self) -> bool:
        return self.relay_subprocess is not None and self.relay_subprocess.poll() is None


    @staticmethod
    def from_config(config_file: str, 
                    debug_mode: DebugMode = DebugMode.WaitForConnection,
                    port=5678) -> any:
        if os.path.exists(config_file):
            with open(config_file) as cfg_file:
                config = json.load(cfg_file)
                relay_name = config["AZRELAY_NAME"]
                conn_str = config["AZRELAY_CONNECTION_STRING"]
                return DebugRelay(
                    access_key_or_connection_string=conn_str,
                    relay_name=relay_name,
                    debug_mode=debug_mode,
                    port=port)
        else:
            return None
    

    @staticmethod
    def from_environment(debug_mode: DebugMode = DebugMode.WaitForConnection,
                         port=5678) -> any:
        relay_name = os.environ.get("AZRELAY_NAME")
        conn_str = os.environ.get("AZRELAY_CONNECTION_STRING")
        if not relay_name or not conn_str:
            print("AZRELAY_CONNECTION_STRING and AZRELAY_NAME variables must be assigned.")
            return None
        else:
            return DebugRelay(
                access_key_or_connection_string=conn_str,
                relay_name=relay_name,
                debug_mode=debug_mode,
                port=port)


    @staticmethod
    def _kill_relays():
        if DebugRelay.is_windows:
            subprocess.run(
                f"taskkill /IM \"{DebugRelay.relay_app_name}.exe\" /F", shell=True)
        else:
            subprocess.run(f"pkill -9 {DebugRelay.relay_app_name}", shell=True)


    @staticmethod
    def _install_azure_relay_bridge() -> str:
        if DebugRelay._installed_az_relay:
            return

        if DebugRelay.is_windows:
            download = DebugRelay.DEFAULT_AZ_RELAY_BRIDGE_WINDOWS_DOWLOAD
        else:
            plat = platform.platform().lower()
            if plat.startswith("macos"):
                download = DebugRelay.DEFAULT_AZ_RELAY_BRIDGE_MACOS_DOWLOAD
            elif plat.startswith("ubuntu"):
                download = DebugRelay.DEFAULT_AZ_RELAY_BRIDGE_UBUNTU_DOWLOAD
            else: # assume Debian
                download = DebugRelay.DEFAULT_AZ_RELAY_BRIDGE_DEBIAN_DOWLOAD
                if not plat.startswith("debian"):
                    logging.warning(f"You are running an unsupported OS: {plat}. "\
                        "Using Debian build of Azure Relay Bridge.")
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        azrelay_folder = os.path.join(
            Path.home(), DebugRelay.relay_dir_name, DebugRelay.relay_version_name)
        
        if not os.path.exists(azrelay_folder):
            filestream = urllib.request.urlopen(download, context=ctx)
            
            if download.lower().endswith(".zip"):
                with zipfile.ZipFile(filestream, 'r') as zip_ref:
                    zip_ref.extractall(azrelay_folder)
            else:
                with tarfile.open(fileobj=filestream, mode="r|gz") as thetarfile:
                    thetarfile.extractall(azrelay_folder)

            if not DebugRelay.is_windows:
                relay_file = os.path.join(
                    azrelay_folder, DebugRelay.relay_app_name)
                st = os.stat(relay_file)
                os.chmod(relay_file, st.st_mode | stat.S_IEXEC)

        os.environ["PATH"] += os.pathsep + azrelay_folder
        return azrelay_folder


def _main(listen:bool):
    print("Debug Relay Initialization...")
    relay_dir = DebugRelay._install_azure_relay_bridge()

    config_file = "azrelay.json"
    mode = DebugMode.WaitForConnection if listen else DebugMode.Connect
    if os.path.exists(config_file):
        debug_relay = DebugRelay.from_config(config_file, debug_mode=mode)
    else:
        debug_relay = DebugRelay.from_environment(mode, debug_mode=mode)

    command = f"{os.path.join(relay_dir, DebugRelay.relay_app_name)} "\
              f"{debug_relay.connection_option} {debug_relay.auth_option}"
    print(f"Starting Debug relay...")
    process = subprocess.Popen(command,
        shell=True,
        stdin=None, stdout=None, stderr=None, close_fds=True)
    print("Relay is running.")
    process.wait()
    print("Relay has been closed.")


if __name__ == '__main__':
    DebugRelay._kill_relays()
    if len(sys.argv) > 1:
        listen = True if sys.argv[1].lower() == "--listen" else False
        _main(listen)
    else:
        print("Debug Relay Stopped.")
    
