import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

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
    function test_precision_data() {
        const references = JSON.parse(Probe.readFile("tests/fixtures/uncertainty_display/expected.json")).integers;
        const cases = [];
        for (const rule of ["iucr_19", "iucr_99"])
            for (const ref of references[rule])
                for (const column of ["value", "su"])
                    cases.push({
                        tag: rule + "-" + ref.value + "-" + column,
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
