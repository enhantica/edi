// SPDX-License-Identifier: BSD-3-Clause
import { spawnSync } from "node:child_process";
import { cpSync, existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { createContext, runInContext } from "node:vm";

const [target, controller, componentScript, payload, access] = process.argv.slice(2);
const protectedTarget = access === "protected";
let admin = protectedTarget;

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
    // The fixture has no downloaded signature or quarantine attribute.
    if (program === "/usr/bin/xattr") return ["", 0];
    if (protectedTarget && !admin)
        throw new Error("A protected target requires the update's rights for its filesystem actions");
    const result = spawnSync(program, args.map(arg => arg === "@TargetDir@" ? target : arg), {
        stdio: ["ignore", "pipe", "pipe"], encoding: "utf8",
    });
    if (result.error) throw new Error(`Could not launch ${program}: ${result.error.code}`);
    if (result.status !== 0) throw new Error(`The action ${program} failed: ${result.stderr}`);
    return [result.stdout, result.status];
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
    hasAdminRights: () => admin,
    gainAdminRights() {
        if (!protectedTarget) throw new Error("A writable target does not need elevation");
        admin = true;
        return true;
    },
    dropAdminRights() { admin = false; },
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
tool.beginInstallation();
const staging = join(target, "maintenance-update");
if (!existsSync(join(staging, ".claim")))
    throw new Error("The incoming component must claim staging before IFW unpacks the bundle");
cpSync(payload, staging, { recursive: true });

tool.createOperations();
if (operations.length !== 1 || operations[0][0] !== "Execute")
    throw new Error("The repository tool component must schedule one executable swap");
const [kind, program, ...args] = operations[0];
const undo = args.indexOf("UNDOEXECUTE");
if (undo === -1) throw new Error(`${kind} must offer rollback`);
execute(program, args.slice(0, undo));
const kept = readFileSync(join(target, "MaintenanceTool.app.old/Contents/MacOS/MaintenanceTool"), "utf8");
const marked = existsSync(join(target, "MaintenanceTool.app.old-token"));

// IFW releases elevated rights before emitting the completion signals.
admin = false;
installer.installationFinished.emit();
installer.updateFinished.emit();
if (admin) throw new Error("The completion handler must release the update's elevated rights");
process.stdout.write(JSON.stringify({ kept, marked }));
