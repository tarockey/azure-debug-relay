// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import { exception } from 'console';
import { stringify } from 'querystring';
import * as vscode from 'vscode';
var path = require('path')

const azDebugRelayTaskName: string = "azDebugRelayTask"
const azRelayDebugHostName: string = "azRelayDebugHost"
const azRelayDebugPortName: string = "azRelayDebugPort"

var azDebugRelayTask: vscode.Task

// this method is called when your extension is activated
// your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
    console.log('Azure Relay Bridge extension activated.');

    vscode.tasks.onDidEndTask((taskEnd: vscode.TaskEndEvent) => {
        if (taskEnd.execution.task == azDebugRelayTask) {
            context.workspaceState.update(azDebugRelayTaskName, null)
        }
    });

    const start = () => {
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
                "--config-file .azrelay.json " +
                `--port ${port} --host ${host}`);
        var task = new vscode.Task({ type: taskType }, vscode.TaskScope.Workspace,
            "azure-relay-bridge", "Azure Relay Bridge", execution)
        task.isBackground = true
        
        vscode.tasks.executeTask(task).then((exec: vscode.TaskExecution) => {
            context.workspaceState.update(azDebugRelayTaskName, exec)
        });
    }

    const stop = () => {
        
        var azDebugTaskExecution = context.workspaceState.get(azDebugRelayTaskName) as vscode.TaskExecution;
        if (azDebugTaskExecution != null) {
            try {
                azDebugTaskExecution.terminate();
            }
            catch { }
        }
    }

    vscode.debug.onDidTerminateDebugSession((_: vscode.DebugSession) => {
        stop();
    });

    vscode.debug.onDidReceiveDebugSessionCustomEvent((event: vscode.DebugSessionCustomEvent) => {
        if (event.event == "debugpyWaitingForServer") {
            context.workspaceState.update(azRelayDebugHostName, event.body.host);
            context.workspaceState.update(azRelayDebugPortName, String(event.body.port));
            start();
        }
    });

    vscode.debug.registerDebugAdapterTrackerFactory('python', {
        createDebugAdapterTracker(_: vscode.DebugSession) {
            return {
                onWillReceiveMessage: (message: any) => {
                    if (message.type !== undefined && message.command !== undefined)
                    {
                        if (message.type == "request" && message.command == "disconnect") {
                            stop();
                        }
                    }
                }
            };
        }
    });

}