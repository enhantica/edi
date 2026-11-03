// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "SimulationParameterFilters"
    when: windowShown
    property var appWindow
    property var savedShow
    Component {
        id: application
        Main {}
    }
    function initTestCase() {
        Session.closeProject();
        savedShow = [Preferences.analysisShowNotMeasured, Preferences.analysisShowBySymmetry, Preferences.analysisShowByConstraint, Preferences.analysisShowFixedSettings];
        Preferences.analysisShowNotMeasured = true;
        Preferences.analysisShowBySymmetry = true;
        Preferences.analysisShowByConstraint = true;
        Preferences.analysisShowFixedSettings = true;
        appWindow = application.createObject(null);
        verify(appWindow !== null, "The availability observation uses one real application window");
        appWindow.width = 1300;
        appWindow.height = 1000;
        verify(Session.createProject("filter_witness", "", String(SettingsProof.emptyDirectory())), "The shared filter witness creates an isolated real project");
        const project = Session.project;
        verify(project.loadStructure(Probe.repoUrl("tests/fixtures/onboarding/simulation-structure.edi")), "The filter witness loads its independently authored structure");
        verify(project.createExperiment(), "The filter witness starts with a real unmeasured experiment");
        const wavelength = Probe.rows(project.currentExperiment.instrument).find(row => row.parameter && row.parameter.name === "setup_wavelength");
        verify(wavelength !== undefined, "The simulation witness has its actual wavelength input");
        wavelength.parameter.value = 1.494;
        project.currentExperiment.setRange(10, 80, 10);
    }
    function cleanupTestCase() {
        Session.closeProject();
        ["analysisShowNotMeasured", "analysisShowBySymmetry", "analysisShowByConstraint", "analysisShowFixedSettings"].forEach((name, i) => Preferences[name] = savedShow[i]);
        if (appWindow)
            appWindow.destroy();
        appWindow = null;
    }
    function control(name) {
        const found = Ui.find(Ui.page(appWindow), name, true);
        verify(found !== null, "Analysis exposes its actual filter control: " + name);
        return found;
    }
    function select(picker, text) {
        const index = Array.from({
            length: picker.count
        }, (_, i) => i).find(i => picker.textAt(i).replace(/\s*\(\d+\)$/, "") === text);
        verify(index !== undefined, "The actual filter menu offers the requested value: " + text);
        Ui.scrollIntoView(picker);
        const point = Ui.clickPoint(picker);
        verify(point !== null, "The filter selector is exposed for real pointer input");
        mouseClick(picker, point.x, point.y);
        tryCompare(picker.popup, "opened", true, 1000, "The actual filter menu opens before selection");
        const list = picker.popup.contentItem;
        list.positionViewAtIndex(index, ListView.Contain);
        verify(waitForPolish(list), "The filter option finishes layout before selection");
        const row = list.itemAtIndex(index), hit = Ui.clickPoint(row);
        verify(row !== null && hit !== null, "The requested filter has a real visible option");
        mouseClick(row, hit.x, hit.y);
        tryCompare(picker, "currentIndex", index, 1000, "Pointer input selects the requested filter option");
        tryCompare(picker.popup, "visible", false, 1000, "The real filter popup closes before the next control receives input");
    }
    function typeName(text) {
        const field = control("parameters.nameFilter");
        Ui.scrollIntoView(field);
        const point = Ui.clickPoint(field);
        verify(point !== null, "The name field is exposed before actual typing");
        mouseClick(field, point.x, point.y);
        appWindow.requestActivate();
        field.forceActiveFocus();
        tryCompare(field, "activeFocus", true, 1000, "The actual name filter receives keyboard focus");
        verify(SettingsProof.type(field, text), "The actual name filter accepts the typed query");
    }
    function test_filters_remain_usable_without_measurements_data() {
        return [
            {
                tag: "simulation",
                measured: false
            },
            {
                tag: "measured",
                measured: true
            }
        ];
    }
    function test_filters_remain_usable_without_measurements(data) {
        const project = Session.project;
        if (data.measured) {
            const folder = String(SettingsProof.emptyDirectory());
            verify(SettingsProof.write(folder, "filter.xye", "10 100 10\n20 120 11\n30 140 12\n40 110 10\n"), "The measured-data witness writes independently specified points");
            verify(project.loadDataInto(project.currentExperiment, folder + "/filter.xye"), "The same experiment loads actual measured data for the enabled control");
        }
        tryVerify(() => !project.calculating && Probe.rows(project.currentExperiment.pattern).some(row => Number.isFinite(row.intensityCalc)), 15000, "The real project has a calculated pattern before entering Analysis");
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, appWindow, "group.parameters");
        const block = control("parameters.datablock"), category = control("parameters.category"), name = control("parameters.nameFilter"), variability = control("parameters.variability");
        for (const item of [block, category, name, variability])
            verify(Ui.rendered(item), "All parameter filters remain visible without measured data: " + item.objectName);
        compare(variability.enabled, data.measured, "Only variability requires measured data; the control stays visible in simulation");
        if (!data.measured)
            verify(String(variability.toolTip || variability.ToolTip.text || "").trim().length > 0, "Disabled simulation variability has a nonempty explanation tooltip");
        for (const item of [block, category, name])
            verify(item.enabled, "Datablock, category and name filtering remain usable in simulation");
        const table = control("parameters.list"), inventory = Probe.rows(table.sourceModel);
        select(block, project.currentStructure.name);
        const structural = Probe.rows(table.sourceModel);
        verify(structural.length > 0 && structural.length < inventory.length && structural.every(row => row.parameter.blockName === project.currentStructure.name), "The datablock filter narrows actual parameters to the selected structure");
        select(category, "Cell");
        const cell = Probe.rows(table.sourceModel);
        verify(cell.length > 0 && cell.length < structural.length && cell.every(row => /^cell\./.test(row.parameter.uid)), "The Cell category narrows the actual structure parameter rows");
        typeName("length");
        const named = Probe.rows(table.sourceModel);
        verify(named.length > 0 && named.length < cell.length && named.every(row => /length/i.test(row.parameter.name)), "Typed name filtering narrows Cell rows to length parameters");
        Ui.click(test, Probe, appWindow, "parameters.clearFilters");
        compare(Probe.rows(table.sourceModel).map(row => row.parameter.uid).sort(), inventory.map(row => row.parameter.uid).sort(), "Clear restores the actual full parameter inventory with and without measurements");
    }
}
