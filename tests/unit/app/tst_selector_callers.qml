import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtTest
import "NativeTurn.js" as Turn
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import TooltipAcceptance 1.0
import "SelectorCallers.js" as Inventory
import "RenderedTable.js" as Render
import "ExampleProjects.js" as Examples

TestCase {
    id: test
    property string gateTurnSelector: ""
    name: "SelectorCallers"
    when: windowShown
    property var app
    property var group
    property var factories: ({})
    property url magneticSource
    Component {
        id: application
        Window {}
    }
    function test_caller_policy_data() {
        const data = [];
        for (const item of Inventory.callers)
            for (const level of ["Off", "Important", "All"])
                data.push({
                    tag: item.component + "-" + level,
                    record: item,
                    level
                });
        return data;
    }
    function selectors() {
        return Array.from(new Set(Render.descendants(group).concat(Probe.objectsWithProperty(group, "refusal")))).filter(item => typeof item.refusal === "string" && typeof item.token === "string" && item.popup && item.options !== undefined);
    }
    function initTestCase() {
        magneticSource = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/selector_callers/project"));
        verify(magneticSource.toString() !== "", "ADR-0070: this actor owns one immutable-input magnetic project copy");
        for (const record of Inventory.callers) {
            const component = Qt.createComponent("edi.app", record.component);
            compare(component.status, Component.Ready, "ADR-0076: each real caller type compiles before rows share its factory: " + record.path);
            factories[record.component] = component;
        }
        app = application.createObject(null, {
            visible: true,
            width: 1280,
            height: 720
        });
    }
    function cleanupTestCase() {
        if (app) {
            app.close();
            app.destroy();
        }
        app = null;
    }
    function init() {
        gateTurnSelector = Turn.begin(test, Probe);
        verify(TooltipClock.isolateSettings() !== "", "Each caller witness has isolated real settings");
        app.update();
        verify(app !== null && waitForRendering(app.contentItem), "ADR-0076: the original caller runs in a rendered real Qt window");
        Preferences.toolTipDelay = 0;
        Preferences.toolTipLevel = "All";
    }
    function cleanup() {
        if (group)
            group.destroy();
        group = null;
        SettingsProof.endAnimationClock();
        Session.closeProject();
        Turn.end(gateTurnSelector);
    }
    function caller(data) {
        const record = data.record;
        if (record.magnetic) {
            const source = magneticSource;
            verify(Session.openProject(source), "ADR-0070: the committed cobalt fixture supplies real magnetic selector owners");
            verify(Session.project.currentStructure.magnetic && Session.project.analysis.magnetic, "ADR-0070: the moment and near-zero selectors have actual magnetic model inputs");
        } else {
            verify(Session.openExample("pd-neut-cwl_lbco_simulation"), "Real caller models come from the bundled calculation-only project");
            Examples.waitForOpen(test, Session, "pd-neut-cwl_lbco_simulation");
        }
        verify(SettingsProof.beginAnimationClock(), "The public animation clock settles exposed caller layouts");
        group = factories[record.component].createObject(app.contentItem);
        verify(group !== null, "The sweep instantiates the original production caller " + record.path);
        group.width = 400;
        group.z = 1000;
        if (record.owner === "analysis")
            group.analysis = Session.project.analysis;
        else if (record.owner === "appearance") {
            group.options = Session.project.structureViewOptions;
            group.structure = Session.project.currentStructure;
            group.collapsed = false;
        } else if (record.owner === "moments") {
            group.options = Session.project.structureViewOptions;
            group.structure = Session.project.currentStructure;
        } else if (record.owner === "generated") {
            const source = Session.project.currentExperiment.text;
            group.source = source;
            group.categoryId = "experiment_type";
        } else {
            group.experiment = Session.project.currentExperiment;
            if (record.component === "ExperimentTypeGroup") {
                group.project = Session.project;
                group.experimentIndex = 0;
            }
        }
        function matches(name, pattern) {
            return pattern.endsWith("*") ? name.startsWith(pattern.slice(0, -1)) : name === pattern;
        }
        tryVerify(() => record.names.every(pattern => selectors().some(item => matches(item.objectName, pattern))), 3000, "Every declared SelectorField caller is actually instantiated: " + record.path);
        verify(waitForPolish(group), "The production caller completes its initial layout");
        verify(SettingsProof.stepAnimationClock(2000), "Caller folds and layout animations settle on the injected clock");
        if (record.component === "FittingModeGroup")
            verify(group.onlyMode, "The fitting-mode witness reaches the disabled single-mode reason wrapper");
        Preferences.toolTipLevel = data.level;
    }
    function test_caller_policy(data) {
        caller(data);
        const failures = [];
        for (const control of selectors()) {
            for (let item = control; item && item !== group; item = item.parent)
                item.visible = true;
            verify(waitForPolish(control.parent), "ADR-0076: a newly exposed selector finishes its actual row positioning before pointer coordinates are chosen");
            verify(waitForPolish(group), "A declared caller is exposed without changing its tooltip or refusal bindings");
            verify(SettingsProof.stepAnimationClock(2000), "Exposing the actual caller settles its geometry");
            const at = control.mapToItem(app.contentItem, 0, 0);
            group.x += 400 - at.x;
            group.y += 180 - at.y;
            verify(control.width > 0 && control.height > 0, "The actual caller has positive hover geometry: " + control.objectName);
            const tips = SettingsProof.tooltipObjects(group).filter(t => TooltipClock.isTooltip(t));
            for (const tip of tips) {
                tip.enterAnimationDuration = 0;
                tip.exitAnimationDuration = 0;
            }
            wait(0);
            verify(SettingsProof.stepAnimationClock(2000), "ADR-0076: the exposed caller and its model finish pending layout transitions before refusal input");
            wait(0);
            for (const level of [data.level]) {
                Preferences.toolTipLevel = level;
                for (const mode of ["help", "refusal"]) {
                    control.popup.close();
                    verify(SettingsProof.stepAnimationClock(1000), "The previous list finishes closing and releases its input grab");
                    wait(0);
                    verify(TooltipClock.movePointer(app.contentItem, 1100, 600), "Pointer input leaves the previous caller popup");
                    const refusal = "This choice was refused. Select a supported value";
                    control.refusal = mode === "refusal" ? refusal : "";
                    verify(TooltipClock.movePointer(control, control.width / 2, control.height / 2), "Pointer input reaches the actual caller and its surrounding reason wrapper");
                    wait(0);
                    const visible = tips.filter(t => t.visible);
                    const wantsHelp = control.ToolTip.text !== "";
                    const count = level === "Off" ? 0 : mode === "refusal" || wantsHelp ? 1 : 0;
                    if (visible.length !== count || (mode === "refusal" && !visible.every(t => t.text === refusal)))
                        failures.push(control.objectName + " " + level + " " + mode + " refusal=" + control.refusal + " token=" + control.token + " popup texts=" + JSON.stringify(visible.map(t => t.text)));
                }
            }
            control.popup.close();
            control.refusal = "";
        }
        verify(failures.length === 0, "Every real SelectorField caller preserves refusal priority and one popup owner, including custom help and reason wrappers: " + failures.join("; "));
    }
    function test_declared_choice_writeback_data() {
        const data = [];
        for (const record of Inventory.callers)
            for (const [name, choice] of Object.entries(record.choices || {}))
                for (const token of choice.tokens)
                    for (const level of ["Off", "Important", "All"])
                        data.push({tag: name + "-" + token + "-" + level, record, name, choice, token, level});
        return data;
    }
    function test_declared_choice_writeback(data) {
        Preferences.toolTipDelay = 1000;
        caller(data);
        const control = selectors().find(item => item.objectName === data.name);
        verify(control !== undefined && control.visible && control.enabled, "ADR-0017/0070: the declared magnetic selector is naturally visible and actionable: " + data.name);
        compare(JSON.stringify(Probe.rows(control.options).map(row => row.token)), JSON.stringify(data.choice.tokens), "ADR-0017/0070: the selector offers exactly its declared choices: " + data.name);
        const owner = data.record.owner === "analysis" ? Session.project.analysis : Session.project.structureViewOptions;
        const start = data.choice.tokens.find(token => token !== data.token);
        owner[data.choice.property] = start;
        tryCompare(control, "token", start, 2000, "ADR-0017/0070: each selection starts from a different real owner token");
        verify(waitForPolish(control.parent), "ADR-0017/0070: the declared selector finishes layout before real pointer input");
        const at = control.mapToItem(app.contentItem, 0, 0);
        group.x += 400 - at.x;
        group.y += 180 - at.y;
        SettingsProof.endAnimationClock();
        control.popup.enter = null;
        control.popup.exit = null;
        mouseClick(control, control.width / 2, control.height - 8);
        tryCompare(control.popup, "opened", true, 2000, "ADR-0017/0070: pointer input opens the actual declared selector list: " + data.name);
        const index = control.options.indexOf(data.token), list = control.popup.contentItem;
        list.positionViewAtIndex(index, ListView.Contain);
        list.forceLayout();
        tryVerify(() => list.itemAtIndex(index) !== null, 2000, "ADR-0017/0070: the selected declared token has a real popup delegate");
        const entry = list.itemAtIndex(index);
        mouseClick(entry, entry.width / 2, entry.height / 2);
        tryCompare(owner, data.choice.property, data.token, 2000, "ADR-0017/0070: the selected token reaches its real model owner: " + data.name);
        tryCompare(control, "token", data.token, 2000, "ADR-0017/0070: the caller reads back its selected model token");
        tryCompare(control.popup, "visible", false, 2000, "ADR-0076: a selected token closes its actual list");
    }
}
