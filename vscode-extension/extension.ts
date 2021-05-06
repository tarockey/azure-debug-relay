import * as vscode from 'vscode';
var path = require('path')

interface Listener {
    host: string;
    port: string;
}

var taskNamePrefix = "AzureRelayBridge_"
var listeners: Array<Listener> = new Array<Listener>()
var initialized_listeners = 0
var azDebugRelayTaskExecution: any
var hybridConnectionName = ""
var hybridConnectionConnectionString = ""
var hasCredentialsFile = false

function readConfig(){
    var config = vscode.workspace.getConfiguration("azure-debug-relay")
    if (config) {
        hybridConnectionConnectionString = config.get("azrelay-connection-string") as string
        hybridConnectionName = config.get("azrelay-connection-name") as string
    }
}


function getConfigOption(): string { 
    var option = ""
    
    if (hybridConnectionName && hybridConnectionName.length > 0 &&
        hybridConnectionConnectionString && hybridConnectionConnectionString.length > 0) {
        option = `--connection-string \"${hybridConnectionConnectionString}\" --connection-name \"${hybridConnectionName}\"`
    }
    else if (hasCredentialsFile) {
        option = "--config-file .azrelay.json"
    }

    return option
}

function getPythonPath(): string {
    var pythonPath = "python"
    var pythonConfig = vscode.workspace.getConfiguration("python")
    if (pythonConfig !== undefined) {
        var pythonPathResult = pythonConfig.get("pythonPath")
        if (pythonPathResult !== undefined) {
            pythonPath = pythonPathResult as string
        }
    }

    return pythonPath
}

function queueRelay(context: vscode.ExtensionContext, host: string, port: any) {
    listeners.push({host: host, port: String(port)})
}

function startRelayIfCan(context: vscode.ExtensionContext) {
    initialized_listeners = 0
    if (listeners.length > 0) {
        hasCredentialsFile = false
        vscode.workspace.findFiles(".azrelay.json").then((files: any) => {
            hasCredentialsFile = (files != null && files.length > 0)
        }).then(async () => {
            var options = getConfigOption()
            if (options && options.length > 0) {
                var host = listeners[0].host // single host IP, only taken from the first listener
                var ports = listeners.map(l => l.port)
                await startRelay(context, options, host, ports)
            }
            else {
                listeners = new Array<Listener>()
            }
        });
    }
}

function startRelay(context: vscode.ExtensionContext, credentialOptions: string, host: string, ports: string[]): Thenable<void> | null{
    var portsString = ports.join("_")
    var portsArgString = ports.join(",")
    var taskType = `azdebugrelay_${host}_${portsString}`;

    var pythonScriptPath = path.join(context.extensionPath, "azdebugrelay", "debug_relay.py")
    var pythonPath = getPythonPath()
    var execution =
        new vscode.ShellExecution(`"${pythonPath}" "${pythonScriptPath}" --no-kill --mode listen ` +
            `${credentialOptions} ` +
            `--ports ${portsArgString} --host ${host}`);
    var task_name = `${taskNamePrefix}${host}_${portsString}`
    var task = new vscode.Task({ type: taskType }, vscode.TaskScope.Workspace,
        task_name, "Azure Relay Bridge", execution)

    if(azDebugRelayTaskExecution == null)
    {
        azDebugRelayTaskExecution = "starting..."
        return vscode.tasks.executeTask(task).then((exec: vscode.TaskExecution) => {
            azDebugRelayTaskExecution = exec
        });
    }
    else
    {
        return null;
    }
}

function stopRelay(_: vscode.ExtensionContext){
    // We always terminate all debugging tasks
    try {
        if(azDebugRelayTaskExecution != null){
            var execution = azDebugRelayTaskExecution as vscode.TaskExecution
            azDebugRelayTaskExecution = null
            if(execution != null){
                execution.terminate();
            }
        }
    }
    catch { }

}

export function activate(context: vscode.ExtensionContext) {
    console.log('Azure Relay Bridge extension activated.');

    readConfig()
    vscode.workspace.onDidChangeConfiguration((_: any) => {
        readConfig()
    })
    
    vscode.tasks.onDidEndTask((taskEnd: vscode.TaskEndEvent) => {
        if(taskEnd.execution.task.name.startsWith(taskNamePrefix))
        azDebugRelayTaskExecution = null
    });
    

    vscode.debug.onDidTerminateDebugSession((_: vscode.DebugSession) => {
        //stopRelay(context);
    });

    vscode.debug.onDidReceiveDebugSessionCustomEvent(async (event: vscode.DebugSessionCustomEvent) => {
        //if (event.event == "debugpyWaitingForServer") {
        //    startRelayIfCan(context);
        //}
    });

    vscode.debug.registerDebugAdapterTrackerFactory('python', {
        createDebugAdapterTracker(_: vscode.DebugSession) {
            return {
                onWillReceiveMessage: (message: any) => {
                    if (message.type !== undefined && message.command !== undefined)
                    {
                        if (message.type == "request") {
                            if (message.command == "initialize") {
                                initialized_listeners++
                            }
                            else if (message.command == "attach") {
                                if (message.arguments !== undefined && message.arguments.listen !== undefined) {
                                    queueRelay(context, message.arguments.listen.host, message.arguments.listen.port);
                                }
                                else {
                                    initialized_listeners--
                                }
                            }
                            else if (message.command == "disconnect") {
                                if (listeners.length > 0) {
                                    listeners.pop()
                                }
                                if (listeners.length == 0) {
                                    initialized_listeners = 0
                                    stopRelay(context);
                                }
                            }
                            else if (message.command == "launch") {
                                initialized_listeners--
                            }
                            if (initialized_listeners > 0 && initialized_listeners == listeners.length) {
                                startRelayIfCan(context)
                            }
                        }
                    }
                }
            };
        }
    });

}