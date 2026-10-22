import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import IntegerUncertaintyReference 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "IntegerUncertaintyPrecision"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    Component {
        id: valueCell
        ParameterCell {
            x: 200
            y: 100
            z: 10000
            width: 300
            height: 30
        }
    }
    Component {
        id: uncertaintyCell
        NumberLabel {
            property var parameterItem
            x: 200
            y: 150
            z: 10000
            width: 300
            height: 30
            number: NumberText.error(parameterItem.uncertainty, 0, parameterItem.value)
            narrow: NumberText.ownUncertainty(parameterItem.uncertainty, parameterItem.value)
        }
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Integer precision checks host actual shared numeric components");
        verify(waitForRendering(appWindow.contentItem), "The integer precision window renders before inspecting numbers");
    }
    function cleanup() {
        appWindow.destroy();
        Session.closeProject();
        Probe.releaseScratchProjects();
    }
    SignalSpy {
        id: plainChanges
        signalName: "valueTextChanged"
    }
    SignalSpy {
        id: widthChanges
        signalName: "widthChanged"
    }
    SignalSpy {
        id: fontChanges
        signalName: "fontChanged"
    }
    function openIntegers(first, second) {
        const directory = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/analysis_filters/project"));
        const file = "experiments/east.edi";
        const original = SettingsProof.text(directory, file);
        verify(original.includes("c0 0 4.0()") && original.includes("c1 1 2.0"), "Transition inputs address both independently named background coefficients");
        verify(SettingsProof.write(directory, file, original.replace("c0 0 4.0()", "c0 0 " + first.token).replace("c1 1 2.0", "c1 1 " + second.token)), "Transition inputs use independently authored integer values and uncertainties");
        verify(Session.openProject(directory), "The integer transition project loads through the production parser");
        const parameters = Probe.rows(Session.project.parameters).map(row => row.parameter);
        const items = ["c0", "c1"].map(label => parameters.find(item => item.blockName === "east" && item.uid === "background.coef" && item.rowLabel === label));
        verify(items.every(item => item !== undefined), "Both transition witnesses reach their independently named parameter identities");
        return items;
    }
    function watchStableCell(cell) {
        for (const spy of [plainChanges, widthChanges, fontChanges]) {
            spy.target = cell;
            verify(spy.valid, "Transition observers attach to real production cell notification signals");
            spy.clear();
        }
    }
    function compareStableCell(cell, width, plain) {
        compare(cell.width, width, "A precision transition retains the same cell width without resizing");
        compare(cell.valueText, plain, "A precision transition retains the same ordinary integer spelling");
        compare(plainChanges.count, 0, "No ordinary text notification can accidentally refresh the scientific form");
        compare(widthChanges.count, 0, "No width notification can accidentally refresh the scientific form");
        compare(fontChanges.count, 0, "No font notification can accidentally refresh the scientific form");
    }
    function test_rule_transition_data() {
        return [
            {
                tag: "19-to-99-and-back",
                from: "iucr_19",
                to: "iucr_99"
            },
            {
                tag: "99-to-19-and-back",
                from: "iucr_99",
                to: "iucr_19"
            }
        ];
    }
    function test_rule_transition(data) {
        const references = JSON.parse(Probe.readFile("tests/fixtures/uncertainty_display/expected.json")).integers;
        const before = references[data.from][0], after = references[data.to][0];
        compare(before.value_text, after.value_text, "The independent rule witnesses deliberately share the ordinary spelling");
        verify(before.value_scientific !== after.value_scientific, "The independent rule witnesses require different scientific precision");
        const items = openIntegers(before, before);
        Session.project.suRule = data.from;
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        const analysis = Ui.page(appWindow);
        const cell = valueCell.createObject(analysis, {
            item: items[0],
            width: 1
        });
        verify(cell !== null, "The transition retains an actual ParameterCell on the loaded Analysis page");
        tryCompare(cell, "text", before.value_scientific, 2000, "The retained cell first reaches the independently rounded scientific form");
        const width = cell.width;
        watchStableCell(cell);
        for (const rule of [data.to, data.from]) {
            Ui.click(test, Probe, appWindow, "appBar.tab.project");
            Ui.click(test, Probe, appWindow, "sideBar.tab.extras");
            Ui.expandGroup(test, Probe, appWindow, "group.su_format");
            const picker = Ui.control(Probe, appWindow, "project.suRule");
            verify(picker !== null, "The live Project page exposes its standard uncertainty rule selector");
            appWindow.requestActivate();
            picker.forceActiveFocus();
            tryCompare(picker, "activeFocus", true, 2000, "The actual Project rule selector receives keyboard focus");
            verify(SettingsProof.key(picker, Qt.Key_Home), "The Project selector receives a real Home key event");
            if (rule === "iucr_99")
                verify(SettingsProof.key(picker, Qt.Key_Down), "The Project selector receives a real Down key event");
            verify(SettingsProof.key(picker, Qt.Key_Return), "The Project selector commits its rule through a real Return key event");
            tryCompare(Session.project, "suRule", rule, 2000, "The Project selector applies the independently requested uncertainty rule");
            Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
            compare(Ui.page(appWindow), analysis, "Returning to Analysis retains the same already loaded page");
            compare(cell.item, items[0], "Changing the project rule retains the same parameter item and cell");
            compareStableCell(cell, width, before.value_text);
            tryCompare(cell, "text", references[rule][0].value_scientific, 2000, "Returning to Analysis shows the new independent scientific precision without resizing");
        }
    }
    function test_metadata_transition_data() {
        const references = JSON.parse(Probe.readFile("tests/fixtures/uncertainty_display/expected.json")).integers.iucr_19;
        const cases = [];
        for (const route of ["uncertainty", "item"])
            for (const reverse of [false, true])
                cases.push({
                    tag: route + (reverse ? "-fine-to-coarse" : "-coarse-to-fine"),
                    route,
                    before: references[reverse ? 2 : 0],
                    after: references[reverse ? 0 : 2]
                });
        return cases;
    }
    function test_metadata_transition(data) {
        compare(data.before.value, data.after.value, "The independent transition witnesses retain the identical stored value");
        compare(data.before.value_text, data.after.value_text, "The independent transition witnesses retain the identical plain spelling");
        verify(data.before.value_scientific !== data.after.value_scientific, "Different uncertainties require independent scientific precision despite equal plain text");
        const items = openIntegers(data.before, data.after);
        Session.project.suRule = "iucr_19";
        const cell = valueCell.createObject(appWindow.contentItem, {
            item: items[0],
            width: 1
        });
        verify(cell !== null, "Metadata transitions use the actual production parameter cell");
        tryCompare(cell, "text", data.before.value_scientific, 2000, "The original metadata first reaches the independent scientific precision");
        const width = cell.width;
        watchStableCell(cell);
        if (data.route === "uncertainty") {
            verify(IntegerPrecision.setUncertainty(items[0], data.after.su), "The core uncertainty alone changes and publishes on the retained ParameterItem");
            compare(cell.item, items[0], "An uncertainty publication retains the original ParameterItem identity");
        } else {
            verify(items[0] !== items[1], "The replacement route supplies another independently parsed ParameterItem");
            cell.item = items[1];
            compare(cell.item, items[1], "The retained cell now holds the other ParameterItem identity");
        }
        compareStableCell(cell, width, data.before.value_text);
        compare(cell.item.value, data.after.value, "The metadata transition preserves the independently specified stored integer");
        compare(cell.item.uncertainty, data.after.su, "The metadata transition reaches the independently specified uncertainty");
        tryCompare(cell, "text", data.after.value_scientific, 2000, "The same cell refreshes scientific precision after metadata changes with equal plain text");
    }
    function test_precision_data() {
        const references = JSON.parse(Probe.readFile("tests/fixtures/uncertainty_display/expected.json")).integers;
        const cases = [];
        for (const rule of ["iucr_19", "iucr_99"])
            for (const ref of references[rule])
                for (const column of ["value", "su"])
                    cases.push({
                        tag: rule + "-" + ref.value + "-su" + ref.su + "-" + column,
                        rule,
                        ref,
                        column
                    });
        return cases;
    }
    function test_precision(data) {
        const directory = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/analysis_filters/project"));
        const file = "experiments/east.edi";
        const original = SettingsProof.text(directory, file);
        verify(original.includes("c0 0 4.0()"), "The authored integer witness addresses the known background coefficient");
        verify(SettingsProof.write(directory, file, original.replace("c0 0 4.0()", "c0 0 " + data.ref.token)), "The disposable input receives an independently specified integer and uncertainty");
        verify(Session.openProject(directory), "The authored integer precision project loads through the actual parser");
        Session.project.suRule = data.rule;
        const item = Probe.rows(Session.project.parameters).map(row => row.parameter).find(parameter => parameter.blockName === "east" && parameter.uid === "background.coef" && parameter.rowLabel === "c0");
        verify(item !== undefined, "The integer precision witness reaches its independently named parameter");
        compare(item.value, data.ref.value, "The core retains the independently authored integer value");
        compare(item.uncertainty, data.ref.su, "The core retains the independently authored integer uncertainty");
        const cell = data.column === "value" ? valueCell.createObject(appWindow.contentItem, {
            item
        }) : uncertaintyCell.createObject(appWindow.contentItem, {
            parameterItem: item
        });
        verify(cell !== null, "The integer witness uses the production value or uncertainty component");
        tryCompare(cell, "text", data.ref[data.column + "_text"], 2000, "A wide cell preserves the independently rounded plain integer spelling");
        // Force the conversion seam; this checks precision without claiming this width is usable.
        cell.width = 1;
        verify(waitForPolish(cell), "A live width change reaches the scientific notation conversion");
        tryCompare(cell, "text", data.ref[data.column + "_scientific"], 2000, "Scientific notation retains the independent IUCr rounding place and significant integer zeros");
        compare(item.value, data.ref.value, "Scientific display preserves every stored integer value");
        compare(item.uncertainty, data.ref.su, "Scientific display preserves every stored integer uncertainty");
    }
}
