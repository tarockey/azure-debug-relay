// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import { exception } from 'console';
import { getuid } from 'process';
import { stringify } from 'querystring';
import * as vscode from 'vscode';
var path = require('path')


const azRelayDebugHostName: string = "azRelayDebugHost"
const azRelayDebugPortName: string = "azRelayDebugPort"

var azDebugRelayTask: vscode.Task
var currentAzDebugRelayTaskExecution: any
var hybridConnectionName = ""
var hybridConnectionConnectionString = ""
var hasCredentialsFile = false

function readConfig(){
    var config = vscode.workspace.getConfiguration("azure-debug-relay")
    if (config) {
        hybridConnectionConnectionString = config.get("hybrid-connection-string") as string
        hybridConnectionName = config.get("hybrid-connection-name") as string
    }
}


function getConfigOption(): string { 
    var option = ""
    
    if (hybridConnectionName && hybridConnectionName.length > 0 &&
        hybridConnectionConnectionString && hybridConnectionConnectionString.length > 0) {
        option = `--connection-string \"${hybridConnectionConnectionString}\" --relay-name \"${hybridConnectionName}\"`
    }
    else if (hasCredentialsFile) {
        option = "--config-file .azrelay.json"
    }

    return option
}

function startRelayIfCan(context: vscode.ExtensionContext) {
    hasCredentialsFile = false
    vscode.workspace.findFiles(".azrelay.json").then((_: any) => {
        hasCredentialsFile = true
    }).then(() => {
        var options = getConfigOption()
        if (options && options.length > 0) {
            startRelay(context, options)
        }
    });
}

function startRelay(context: vscode.ExtensionContext, credentialOptions: string) {
    var host = context.workspaceState.get(azRelayDebugHostName) as string;
    var port = context.workspaceState.get(azRelayDebugPortName) as string;
    if (host === undefined || host == null) {
        host = "127.0.0.1"
    }
    if (port === undefined || port == null) {
        port = "5678"
    }
    var taskType = "azdebugrelay";

    var pythonScriptPath = path.join(context.extensionPath, "azdebugrelay", "debug_relay.py")
    var execution =
        new vscode.ShellExecution(`python3 ${pythonScriptPath} --no-kill --mode listen ` +
            `${credentialOptions} ` +
            `--port ${port} --host ${host}`);
    var task = new vscode.Task({ type: taskType }, vscode.TaskScope.Workspace,
        "azure-relay-bridge", "Azure Relay Bridge", execution)
    task.isBackground = true

    vscode.tasks.executeTask(task).then((exec: vscode.TaskExecution) => {
        currentAzDebugRelayTaskExecution = exec
    });
}

function stopRelay (context: vscode.ExtensionContext){

    var azDebugTaskExecution = currentAzDebugRelayTaskExecution as vscode.TaskExecution;
    currentAzDebugRelayTaskExecution = null
    if (azDebugTaskExecution != null) {
        try {
            azDebugTaskExecution.terminate();
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
        if (taskEnd.execution.task == azDebugRelayTask) {
            currentAzDebugRelayTaskExecution = null
        }
    });
    

    vscode.debug.onDidTerminateDebugSession((_: vscode.DebugSession) => {
        stopRelay(context);
    });

    vscode.debug.onDidReceiveDebugSessionCustomEvent((event: vscode.DebugSessionCustomEvent) => {
        if (event.event == "debugpyWaitingForServer") {
            context.workspaceState.update(azRelayDebugHostName, event.body.host);
            context.workspaceState.update(azRelayDebugPortName, String(event.body.port));
            startRelayIfCan(context);
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