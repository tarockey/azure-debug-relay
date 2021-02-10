from enum import Enum
import os
import argparse
import sys
import logging
import subprocess
import stat
import urllib.request
from pathlib import Path
import ssl
import platform
import tarfile
import time
import json
import zipfile


class DebugMode(Enum):
    """Debugging mode enum:
    waiting for another machine to connect, or connect to another machine
    """
    # Start a remote forwarder with Azure Relay Bridge, another side is attaching
    WaitForConnection=1,
    # Start a local forwarder with Azure Relay Bridge, another side is listening
    Connect = 2


class DebugRelay(object):
    """Initializes and controls Azure Relay Bridge process.

    Raises:
        ValueError: Invalid arguments.
        TimeoutError: Azure Relay Bridge took too long to connect.
    """
    # Azure Relay Bridge executable name
    relay_app_name = "azbridge"
    # `~/.azdebugrelay` installation directory
    relay_dir_name = ".azdebugrelay"
    # current Azure Debug Relay build
    relay_version_name = "0.2.9"
    # are we running on Windows?
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
                 host: str ="127.0.0.1",
                 port: int = 5678,
                 az_relay_connection_wait_time: float = 60):
        """Initializes DebugRelay object. 

        Args:
            access_key_or_connection_string (str): access key or connection string for Azure Relay Hybrid Connection
            relay_name (str): name of Azure Relay Hybrid Connection
            debug_mode (DebugMode, optional): Connect or Listen (WaitForConnection). Defaults to DebugMode.WaitForConnection.
            hybrid_connection_url (str, optional): optional URL of Hybrid Connection. Defaults to None. 
                Required when access_key_or_connection_string is an access key.
            host (str, optional): Local hostname/address the debugging starts on. Defaults to "127.0.0.1".
            port (int, optional): Any available port that you can use within your machine.
                This port will be connected to or exposed by Azure Relay Bridge. Defaults to 5678.
            az_relay_connection_wait_time (float, optional): Maximum time to wait for Azure Relay Bridge
                to initialize and connect when open() is called with wait_for_connection == True. Defaults to 60.

        Raises:
            ValueError: hybrid_connection_url is None while access_key_or_connection_string is not a connection string.
        """
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
            self.connection_option = f"-R {relay_name}:{host}:{port}"
        else:
            self.connection_option = f"-L {host}:{port}:{relay_name}"

        self.az_relay_connection_wait_time = az_relay_connection_wait_time


    def __del__(self):
        """destructor
        """
        self.close()


    def az_relay_bridge_subprocess(self) -> subprocess.Popen:
        """Returns Azure Relay Bridge process subprocess.Popen object.
        None if one was not launched

        Returns:
            subprocess.Popen: Azure Relay Bridge process
        """
        return self.relay_subprocess


    def open(self, wait_for_connection: bool = True):
        """Launches Azure Relay Bridge tool with configured parameters
        (as initialized when creating DebugRelay object).
        If Azure Relay Bridge is not installed, installs it.

        Args:
            wait_for_connection (bool, optional): Wait for Azure Relay Bridge to initialize and connect. Defaults to True.

        Raises:
            TimeoutError: Raised when it takes longer than az_relay_connection_wait_time secods
                        for Azure Relay Bridge to initialize and connect.
        """
        # close existing Azure Relay Bridge process (if running)
        self.close()
        # install Azure Relay Bridge (if not yet)
        DebugRelay._install_azure_relay_bridge()

        command = f"{DebugRelay.relay_app_name} {self.connection_option} {self.auth_option}"
        # start Azure Relay Bridge
        self.relay_subprocess = subprocess.Popen(
            command, 
            stdin=None, stderr=subprocess.STDOUT, stdout=subprocess.PIPE,
            shell=True, universal_newlines=True, close_fds=True)
        # wait a second
        time.sleep(1)

        start = time.perf_counter()

        remote_forward_ready = False
        local_forward_ready = False
        over_timeout = False
        connected = False

        # If recognizing Azure Relay Bridge connection status, parse its output.
        if wait_for_connection:
            # Iterate over Azure Relay Bridge output lines, 
            # looking for lines with "LocalForwardHostStart," and "RemoteForwardHostStart," to appear.
            for line in iter(self.relay_subprocess.stdout.readline, ''):
                logging.info(line)
                if logging.root.getEffectiveLevel() != logging.INFO:
                    print(line)
                if self.relay_subprocess.poll() is not None:
                    break
                if wait_for_connection and not connected:
                    if line.find("LocalForwardHostStart,") != -1:
                        local_forward_ready = True
                    elif line.find("RemoteForwardHostStart,") != -1:
                        remote_forward_ready = True
                    if remote_forward_ready and local_forward_ready:
                        connected = True
                        break
                    time_delta = time.perf_counter() - start
                    # did take too long to initialize and connect?
                    if time_delta > self.az_relay_connection_wait_time:
                        over_timeout = True
                        break

        # Handle over-timeout status
        if over_timeout:
            msg = f"Azure Relay Bridge took too long to connect."
            logging.critical(msg)
            self.close()
            raise TimeoutError(msg)

        msg = "Azure Relay Bridge is ready!"
        logging.info(msg)
        if logging.root.getEffectiveLevel() != logging.INFO:
            print(msg)


    def close(self):
        """Stops Azure Relay Bridge process launched by this object
        """
        if self.relay_subprocess is not None:
            if self.is_running():
                print("Closing Debug Relay...")
                self.relay_subprocess.terminate()
                try:
                    self.relay_subprocess.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.relay_subprocess.kill()
            self.relay_subprocess = None


    def background_launch(self) -> subprocess.Popen:
        """Launches Azure Relay Bridge process in detached mode
        Doesn't assign self.relay_subprocess, az_relay_bridge_subprocess() will return None.
        """
        # close existing Azure Relay Bridge process (if running)
        self.close()
        # install Azure Relay Bridge (if not yet)
        DebugRelay._install_azure_relay_bridge()

        command = f"{DebugRelay.relay_app_name} {self.connection_option} {self.auth_option}"
        # start Azure Relay Bridge
        detached_relay_subprocess = subprocess.Popen(
            command,
            stdin=None, stderr=None, stdout=None,
            shell=True, close_fds=True)
        # wait a second
        time.sleep(1)
        if detached_relay_subprocess.poll() is not None:
            msg = f"Azure Relay Bridge failed to launch."
            logging.critical(msg)
            self.close()
        else:
            msg = "Azure Relay Bridge is running!"
            logging.info(msg)
            if logging.root.getEffectiveLevel() != logging.INFO:
                print(msg)

        return detached_relay_subprocess


    def wait(self):
        self.relay_subprocess.wait()
        self.relay_subprocess = None


    def is_running(self) -> bool:
        return self.relay_subprocess is not None and self.relay_subprocess.poll() is None


    @staticmethod
    def from_config(config_file: str, 
                    debug_mode: DebugMode = DebugMode.WaitForConnection,
                    host:str = "127.0.0.1",
                    port:int = 5678) -> any:
        if os.path.exists(config_file):
            with open(config_file) as cfg_file:
                config = json.load(cfg_file)
                relay_name = config["AZRELAY_NAME"]
                conn_str = config["AZRELAY_CONNECTION_STRING"]
                return DebugRelay(
                    access_key_or_connection_string=conn_str,
                    relay_name=relay_name,
                    debug_mode=debug_mode,
                    host=host,
                    port=port)
        else:
            return None
    

    @staticmethod
    def from_environment(debug_mode: DebugMode = DebugMode.WaitForConnection,
                         host: str = "127.0.0.1",
                         port: int = 5678) -> any:
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
                host=host,
                port=port)


    @staticmethod
    def _kill_relays():
        """Kills all Azure Relay Bridge processes - no matter who and how launched them
        """
        if DebugRelay.is_windows:
            subprocess.run(
                f"taskkill /IM \"{DebugRelay.relay_app_name}.exe\" /F", shell=True)
        else:
            subprocess.run(f"pkill -9 {DebugRelay.relay_app_name}", shell=True)


    @staticmethod
    def _install_azure_relay_bridge():
        """Installs or updates Azure Relay Bridge
        """
        if DebugRelay._installed_az_relay:
            return
        DebugRelay._installed_az_relay = True

        azrelay_folder = os.path.join(
            Path.home(), DebugRelay.relay_dir_name, DebugRelay.relay_version_name)
        azrelay_parent = os.path.join(
            Path.home(), DebugRelay.relay_dir_name)
        azrelay_symlink = os.path.join(
            azrelay_parent, DebugRelay.relay_app_name)
        relay_file = os.path.join(
            azrelay_folder, DebugRelay.relay_app_name)

        exists = os.path.exists(azrelay_folder)
        if not exists:
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

            filestream = urllib.request.urlopen(download, context=ctx)
            
            if download.lower().endswith(".zip"):
                with zipfile.ZipFile(filestream, 'r') as zip_ref:
                    zip_ref.extractall(azrelay_folder)
            else:
                with tarfile.open(fileobj=filestream, mode="r|gz") as thetarfile:
                    thetarfile.extractall(azrelay_folder)

            if not DebugRelay.is_windows:
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


def _main(connect: bool, host: str, port: int, connection_string: str = None, relay_name: str = None, config_file: str = None):
    """CLI main function

    Args:
        connect (bool): Connect (if True) or listen for incoming connections
        host (string): local hostname/address the debugging starts on (127.0.0.1)
        port (int): Azure Relay Bridge port
        connection_string (str): Optional connection string of an Azure Relay Hybrid Connection
        relay_name (str): Optional hybrid connection name
        config_file (str): Optional configuration file path. Only used if connection_string is None.

    Raises:
        ValueError: Invalid arguments
        Exception: Cannot load configuration
    """
    print("Debug Relay Initialization...")

    mode = DebugMode.Connect if connect else DebugMode.WaitForConnection

    if connection_string is not None:
        if relay_name is None:
            msg = "Both connection string and connection name must be provided."
            print(msg)
            raise ValueError(msg)
        debug_relay = DebugRelay(connection_string, relay_name, mode, None, host, port)
    elif config_file is not None:
        if os.path.exists(config_file):
            debug_relay = DebugRelay.from_config(config_file, debug_mode=mode, host=host, port=port)
        else:
            config_file = os.path.normpath(config_file)
            logging.warning(f"Cannot load configuration file {config_file}. Trying with environment variables.")
            debug_relay = None
    else:
        debug_relay = None
    
    if debug_relay is None:
        debug_relay = DebugRelay.from_environment(
                debug_mode=mode, host=host, port=port)
    
    if debug_relay is None:
        raise Exception("Cannot create a Debug Relay object. Configuration may be missing.")

    print(f"Starting Debug relay...")
    relay = debug_relay.background_launch()
    relay.wait()


def _cli_main(argv):
    """CLI entry function

    Args:
        argv: Command Line arguments

        --no-kill - optional,
            If presented, prevents existing Azure Relay Bridge processes from being nuked.
            If omitted, all existing Azure Azure Relay Bridge processes will be killed.
        --mode - required,
            Debugging mode: listen, connect or none (default).
        --host - optional, defaults to 127.0.0.1, 
            Local hostname/address the debugging starts on (127.0.0.1)
        --port - optional, defaults to 5678
            Azure Relay Bridge port
        --connection-string - optional, defaults to None
            Connection string of an Azure Relay Hybrid Connection
        --relay-name - optional, defaults to None
            Hybrid connection name. Required if --connection-string is specified.
        --config_file - optional, defaults to None
            Configuration file path. Only used if connection_string is not specified.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-kill', action='store_true',
                        default=False, required=False, help="Don't terminate existing azrelay processes.")
    parser.add_argument('--mode', action='store',
                        default="none", choices=['connect', 'listen', "none"], required=False,
                        help="Debugging mode: listen, connect or none")
    parser.add_argument('--port', type=int,
                        default=5678, required=False, help="Azure Relay Bridge port")
    parser.add_argument('--host', action='store',
                        default="127.0.0.1", required=False, help="Local hostname/address the debugging starts on")
    parser.add_argument('--connection-string', action='store',
                        default=None, required=False, help="Connection string of an Azure Relay Hybrid Connection")
    parser.add_argument('--relay-name', action='store',
                        default=None, required=False, help="Azure Relay Hybrid Connection name")
    parser.add_argument('--config-file', action='store',
                        default=None, required=False, help="Path to the configuration file. Defaults to None.")
    options = parser.parse_args(args=argv)

    logging.root.setLevel(logging.INFO)
    if not options.no_kill:
        print("Closing existing Azure Debug Relay processes.")
        DebugRelay._kill_relays()

    if options.mode != "none":
        connect = True if options.mode == "connect" else False
        _main(connect, options.host, options.port, options.connection_string, options.relay_name, options.config_file)


# DebugRelays can work as a CLI tool.
if __name__ == '__main__':
    _cli_main(sys.argv[1:])
    
    
    
