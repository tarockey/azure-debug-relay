import * as vscode from 'vscode';
var path = require('path')

var azDebugRelayTaskExecutions: { [name: string] : any; } = {};
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

function startRelayIfCan(context: vscode.ExtensionContext, host: string, port: any) {
    hasCredentialsFile = false
    vscode.workspace.findFiles(".azrelay.json").then((files: any) => {
        hasCredentialsFile = (files != null && files.length > 0)
    }).then(async () => {
        var options = getConfigOption()
        if (options && options.length > 0) {
            await startRelay(context, options, host, String(port))
        }
    });
}

function startRelay(context: vscode.ExtensionContext, credentialOptions: string, host: string, port: string): Thenable<void> | null{
    var taskType = `azdebugrelay_${host}_${port}`;

    var pythonScriptPath = path.join(context.extensionPath, "azdebugrelay", "debug_relay.py")
    var execution =
        new vscode.ShellExecution(`python3 ${pythonScriptPath} --no-kill --mode listen ` +
            `${credentialOptions} ` +
            `--port ${port} --host ${host}`);
    var task_name = `AzureRelayBridge_${host}_${port}`
    var task = new vscode.Task({ type: taskType }, vscode.TaskScope.Workspace,
        task_name, "Azure Relay Bridge", execution)

    if(!azDebugRelayTaskExecutions.hasOwnProperty(task_name) 
        || azDebugRelayTaskExecutions[task_name] == null)
    {
        return vscode.tasks.executeTask(task).then((exec: vscode.TaskExecution) => {
            azDebugRelayTaskExecutions[task_name] = exec
        });
    }
    else
    {
        return null;
    }
}

function stopRelay(_: vscode.ExtensionContext){
    // We always terminate all debugging tasks
    for (var key in azDebugRelayTaskExecutions) {
        let execution = azDebugRelayTaskExecutions[key];
        azDebugRelayTaskExecutions[key] = null
        try {
            if(execution != null)
            {
                execution.terminate();
            }
        }
        catch { }
    }
}

export function activate(context: vscode.ExtensionContext) {
    console.log('Azure Relay Bridge extension activated.');

    readConfig()
    vscode.workspace.onDidChangeConfiguration((_: any) => {
        readConfig()
    })
    
    vscode.tasks.onDidEndTask((taskEnd: vscode.TaskEndEvent) => {
        azDebugRelayTaskExecutions[taskEnd.execution.task.name] = null
    });
    

    vscode.debug.onDidTerminateDebugSession((_: vscode.DebugSession) => {
        stopRelay(context);
    });

    vscode.debug.onDidReceiveDebugSessionCustomEvent(async (event: vscode.DebugSessionCustomEvent) => {
        if (event.event == "debugpyWaitingForServer") {
            startRelayIfCan(context, event.body.host, event.body.port);
        }
    });

    vscode.debug.registerDebugAdapterTrackerFactory('python', {
        createDebugAdapterTracker(_: vscode.DebugSession) {
            return {
                onWillReceiveMessage: (message: any) => {
                    if (message.type !== undefined && message.command !== undefined)
                    {
                        if (message.type == "request" && message.command == "disconnect") {
                            stopRelay(context);
                        }
                    }
                }
            };
        }
    });

}