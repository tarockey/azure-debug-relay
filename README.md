# Azure Debug Relay for Python

AzDebugRelay - a Python module for cross-network remote debugging in [Visual Studio Code](https://code.visualstudio.com/). 

AzDebugRelay uses [debugpy](https://github.com/microsoft/debugpy) and [Azure Relay](https://docs.microsoft.com/en-us/azure/azure-relay/relay-what-is-it) service to create a debugging tunnel between 2 machines:

1. You local Visual Studio Code debugger in `listen` mode.
2. You remote code in `attach` mode.

The debugging tunnel is handled by [Azure Relay Bridge](https://github.com/vladkol/azure-relay-bridge) utility which is downloaded and installed autimatically by AzDebugRelay.

## Requirements

* Python 3.6+
* debugpy

### Supported Operating Systems 

* Ubuntu 18+
* Debian 10+
* macOS 10+
* Windows 10

## Usage

Before you start debugging with AzDebugRelay, there are 3 places you configure it:

1. Azure Portal.
1. Local machine where you run Visual Studio Code and its Python debugger.
1. Remote machine where you run the same code files that open locally in VS Code.

### In Azure Portal
1. [Create Azure Relay resource](https://ms.portal.azure.com/#create/Microsoft.Relay).
2. Once created, switch to the resource, and select `Hybrid Connections` option in the vertical panel.
3. Add a hybrid connection (`+ Hybrid Connection` button), give it a memorable name (e.g. `test`) - this is your **Relay Name**.
4. Switch to that new hybrid connection, then select `Shared Access Policies` in the vertical panel.
5. Add a new policy with `Send` and `Listen` permissions.
6. Once created, copy its `Primary Connection String`, this is your **Connection String**.

Every debug session requires a separate hybrid connection. Once a session is over, that hybrid connection can be used for another one.

### Locally and Remotely

Create `azrelay.json` file in your workspace directory (next to `remote_server_demo.py` files),
and set 2 variables:

1. `AZRELAY_CONNECTION_STRING` to your **Connection String**.
1. `AZRELAY_NAME` to your **Releay Name**.

For example:

```json
{
  "AZRELAY_CONNECTION_STRING": "Endpoint=sb://vladkol-relay.servicebus.windows.net/;SharedAccessKeyName=default;SharedAccessKey=REDACTED;EntityPath=test",
  "AZRELAY_NAME": "test"
}
```

`azrelay.json` is added in `.gitignore`, and won't be committed. 

> Alternatively, you can assign these 2 variables as environment variables.

### Locally in Visual Studio Code

This step must be done before launching the remote demo.

1. Configure `.vscode/tasks.json` with `azrelaybridge-listen` and `azrelaybridge-stop` tasks as in this repo's `.vscode/tasks.json`.
1. Configure `.vscode/launch.json` with `Python: Listen` configuration as in this repo's `.vscode/launch.json`.
1. Open `remote_server_demo.py` and put a breakpoint in `do_work()` function.
1. Start debugging in your local Visual Studio Code in `Python: Listen` configuration.

### Remote Demo

1. Clone the repo.
2. Start `python3 remote_server_demo.py --debug=attach`.

If everything works as it's supposed to, you will hit a breakpoint in your local Visual Studio Code.

## AzDebugRelay API

`remote_server_demo.py` shows how you can use AzDebugRelay with your code.

azdebugrelay package contains DebugRelay class that install and launches Azure Relay Bridge: 

```python
from azdebugrelay import DebugRelay, DebugMode

debug_relay = DebugRelay(access_key_or_connection_string, relay_name, debug_mode, hybrid_connection_url, port)
debug_relay.open()

# attach to a remote debugger (usually from remote server code) with debug_mode = DebugMode.Connect
debugpy.connect(("127.0.0.1", 5678))

# Debug, debug, debug
# ...
# ...

debug_relay.close()
```

* `access_key_or_connection_string` - Access Key or Connection String for Azure Relay Hybrid Connection. Must have `Send` and `Listen` permisisons
* `relay_name` - name of the Hybrid Connection
* `debug_mode` - debug connection mode. `DebugMode.WaitForConnection` when starting in listening mode, `DebugMode.Connect` for attaching to a remote debugger.
* `hybrid_connection_url` - Hybrid Connection URL. Required when access_key_or_connection_string as an access key, otherwise is ignored and may be None.
* `port` - debugging port, `5678` by default
