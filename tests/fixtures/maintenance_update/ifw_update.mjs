// SPDX-License-Identifier: BSD-3-Clause
import { existsSync, readFileSync } from "node:fs";
import { createContext, runInContext } from "node:vm";

const [phase, target, controller, componentScript] = process.argv.slice(2);
const commands = [];

function signal() {
    const callbacks = [];
    return {
        connect(...args) { callbacks.push(args); },
        emit() {
            for (const [first, second] of callbacks) {
                if (second) second.call(first);
                else first();
            }
        },
    };
}

function execute(program, args) {
    commands.push([program, ...args.map(arg => arg === "@TargetDir@" ? target : arg)]);
    return ["", 0];
}

const operations = [];
const installer = {
    installationFinished: signal(),
    updateFinished: signal(),
    uninstallationFinished: signal(),
    statusChanged: signal(),
    titleMessageChanged: signal(),
    environmentVariable: () => "",
    execute,
    fileExists: existsSync,
    isInstaller: () => false,
    isUninstaller: () => false,
    isUpdater: () => true,
    status: 0,
    value: key => key === "TargetDir" ? target : "",
    setDefaultPageVisible() {},
    setMessageBoxAutomaticAnswer() {},
};
const globals = {
    installer,
    systemInfo: { kernelType: "darwin" },
    gui: {
        showSettingsButton() {},
        pageWidgetByObjectName: () => null,
    },
    QInstaller: { Success: 0, buttons: {} },
    QMessageBox: { Ok: 0 },
    buttons: {},
    component: {
        createOperations() {},
        addOperation(...args) { operations.push(args); },
    },
};
const controllerContext = createContext({ ...globals });
runInContext(readFileSync(controller, "utf8"), controllerContext);
runInContext("new Controller()", controllerContext);

const componentContext = createContext({ ...globals });
runInContext(readFileSync(componentScript, "utf8"), componentContext);
const tool = runInContext("new Component()", componentContext);
if (phase === "claim") {
    tool.beginInstallation();
} else if (phase === "swap") {
    tool.createOperations();
    if (operations.length !== 1 || operations[0][0] !== "Execute")
        throw new Error("The repository tool component must schedule one executable swap");
    const [kind, program, ...args] = operations[0];
    const undo = args.indexOf("UNDOEXECUTE");
    if (undo === -1) throw new Error(`${kind} must offer rollback`);
    execute(program, args.slice(0, undo));
} else if (phase === "finish") {
    installer.installationFinished.emit();
    installer.updateFinished.emit();
} else {
    throw new Error(`Unknown update phase: ${phase}`);
}
process.stdout.write(JSON.stringify(commands));
