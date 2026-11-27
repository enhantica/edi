// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "ScanExtractionRuleEditing"
    when: windowShown
    property var app
    Component { id: windowFactory; Main {} }

    function init() {
        app = windowFactory.createObject(null);
        verify(app !== null, "Scan editing requires the production window");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "The scan editors receive keyboard input in their own window");
    }

    function cleanup() {
        Session.closeProject();
        app.destroy();
    }

    function openScan(root) {
        verify(Session.openProject(root), "Open the private scan project for rule editing");
        Ui.click(test, Probe, app, "appBar.tab.analysis");
        Ui.click(test, Probe, app, "sideBar.tab.extras");
        Ui.expandGroup(test, Probe, app, "group.sequential_fit_extract");
    }

    function rows() {
        return Probe.rows(Session.project.analysis.sequentialExtract);
    }

    function clickRuleControl(name, requirement) {
        const group = Ui.find(Ui.page(app), "group.sequential_fit_extract", true);
        verify(group !== null, "The action belongs to the scan extraction group");
        const table = findChild(group.contentItem, "sequentialExtract.list");
        verify(table !== null, "The action is on the visible extraction table or its controls");
        Ui.scrollIntoView(table);
        let item;
        let point;
        tryVerify(() => {
            const root = name === "sequentialExtract.append" ? group.contentItem : table.itemAtIndex(0);
            item = root && Ui.find(root, name, true);
            if (!item || !item.enabled)
                return false;
            Ui.scrollIntoView(item);
            point = Ui.clickPoint(item);
            return point !== null;
        }, 2000, requirement);
        mouseClick(item, point.x, point.y);
        return item;
    }

    function editRule(field, value, replacement) {
        const editor = clickRuleControl("sequentialExtract." + field + ".0",
                                        "The extraction rule has a reachable editor for " + field);
        compare(String(editor.value), value, "The editor belongs to the displayed extraction rule");
        tryCompare(editor, "activeFocus", true, 1000, "The clicked rule editor owns keyboard focus");
        verify(SettingsProof.type(editor, replacement) && SettingsProof.key(editor, Qt.Key_Return),
               "The extraction rule editor accepts real keyboard input and Return");
        return editor;
    }

    function test_edit_save_and_reopen() {
        const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/scan_template/project"));
        openScan(root);
        const original = rows()[0];
        compare(original.id, "temperature", "The fixture has its published temperature rule");
        editRule("id", original.id, "sample_temperature");
        compare(rows()[0].id, "sample_temperature", "Editing the rule renames the existing row");
        const invalid = editRule("pattern", original.pattern, "[");
        tryVerify(() => /pattern|regular expression/i.test(invalid.refusal), 1000,
                  "The invalid expression is visibly refused rather than silently left uncommitted");
        compare(rows()[0].pattern, original.pattern, "An invalid expression cannot replace the saved rule");
        const pattern = "^TEMP\\s+([0-9]+(?:\\.[0-9]+)?)";
        const valid = editRule("pattern", original.pattern, pattern);
        tryVerify(() => rows()[0].pattern === pattern, 1000,
                  "A valid expression updates the active extraction rule"
                  + "; field=" + valid.text + "; refusal=" + valid.refusal);
        verify(Session.save(), "The edited extraction rule saves with the project");
        Session.closeProject();
        openScan(root);
        compare([rows()[0].id, rows()[0].pattern], ["sample_temperature", pattern],
                "The edited name and expression both persist after reopening");
    }

    function test_append_first_rule_and_remove_it() {
        const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/scan_template/project"));
        const path = "analysis/analysis.edi";
        const source = SettingsProof.text(root, path);
        const loop = source.indexOf("loop_\n_sequential_fit_extract.id");
        verify(loop >= 0 && SettingsProof.write(root, path, source.slice(0, loop)),
               "Prepare a scan declaration that has no extraction rules yet");
        openScan(root);
        compare(rows().length, 0, "A scan without rules initially has an empty extraction table");
        clickRuleControl("sequentialExtract.append", "A scan must let the user add its very first extraction rule");
        compare(rows().length, 1, "The extraction table contains the newly appended rule");
        verify(Session.save(), "An appended extraction rule can be saved");
        Session.closeProject();
        openScan(root);
        compare(rows().length, 1, "The appended extraction rule survives reopening");
        clickRuleControl("sequentialExtract.remove.0", "The extraction table must offer removal of the new rule");
        compare(rows().length, 0, "Removing the only extraction rule leaves an empty declared scan");
        verify(Session.save(), "Removing the rule can be saved");
        Session.closeProject();
        verify(Session.openProject(root), "Reopen the scan after saving the removal");
        compare(rows().length, 0, "Reopening the scan must not restore the removed rule");
    }

}
