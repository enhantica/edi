// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "NativeTurn.js" as Turn
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import "AtomsSelector.js" as Atoms

TestCase {
    id: test
    name: "PostReleaseStability"
    when: windowShown
    property var app
    property string gateTurnSelector: ""
    Component {
        id: application
        Main {}
    }
    function named(name) {
        const found = Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === name);
        verify(found.length === 1, "The production flow exposes exactly one control named " + name);
        return found[0];
    }
    function initTestCase() {
        RunLog.dismissCrash();
        AppState.reset();
        app = application.createObject(null);
        verify(app !== null && waitForRendering(app.contentItem), "Stability cases use the rendered production application");
        app.requestActivate();
        tryCompare(app, "active", true, 2000, "Actual keyboard input reaches the production window");
        named("feedback.form").transport = function () {
            fail("Stability cases never send a network request");
        };
        if (Qt.application.arguments.includes("PostReleaseStability::test_a_series_survive_hover_and_analysis_switch"))
            prepareHoverInput();
    }
    function prepareHoverInput() {
        const folder = SettingsProof.copyProject(Probe.referenceUrl("hover"));
        verify(Session.openProject(folder), "The six-structure hover input loads through the production session");
        compare(Session.project.structures.count, 6, "The hover rebuild begins with every declared structure present");
        tryCompare(Session.project, "calculating", false, 10000, "The actual calculation settles before the chart hover");
        Ui.click(test, Probe, app, "appBar.tab.experiment");
    }
    function init() {
        gateTurnSelector = Turn.begin(test, Probe, message => test.warn(message));
        RunLog.dismissCrash();
    }
    function cleanup() {
        named("feedback.form").close();
        Turn.end(gateTurnSelector, message => test.warn(message));
    }
    function cleanupTestCase() {
        Session.closeProject();
        if (app)
            app.destroy();
        app = null;
    }
    function openInput(name) {
        verify(Session.openProject(SettingsProof.copyProject(Probe.referenceUrl(name))), "The case opens a private independently authored stability input: " + name);
        tryCompare(Session.project, "calculating", false, 10000, "The initial input calculation settles before the regression trigger");
    }
    function structureView() {
        Ui.click(test, Probe, app, "appBar.tab.structure");
        let view;
        tryVerify(() => {
            view = Render.descendants(app.contentItem).find(item => item.objectName === "structure.view" && Ui.rendered(item));
            return view && view.structure === Session.project.currentStructure && view.current;
        }, 10000, "The real Structure page publishes its current atom drawing");
        return view;
    }
    function test_a_series_survive_hover_and_analysis_switch() {
        let chart;
        tryVerify(() => {
            chart = Render.descendants(app.contentItem).find(item => item.objectName === "chart" && item.shown && Ui.rendered(item));
            return chart && Render.series(chart).some(series => String(series.objectName).startsWith("chart.series.bragg."));
        }, 5000, "The actual experiment chart contains populated Bragg series before hover");
        const series = Render.series(chart).filter(item => String(item.objectName).startsWith("chart.series.bragg."));
        verify(series.length >= 6, "The hover witness reaches all six actual Bragg series before rebuilding");
        const pointer = findChild(chart, "chart.pointer.bragg");
        verify(pointer && pointer.width > 0 && pointer.height > 0, "The regression enters the actual Bragg hover area");
        mouseMove(pointer, pointer.width / 2, pointer.height / 2);
        const experiment = chart.experiment;
        chart.experiment = null;
        wait(0);
        // A hover event already queued for the old drawing must never hold a deleted QObject.
        verify(series.every(item => Qt.isQtObject(item) && Render.series(chart).includes(item)), "Queued chart hover retains live Qt series while its input is rebuilt");
        chart.experiment = experiment;
        Ui.click(test, Probe, app, "appBar.tab.analysis");
        tryVerify(() => Render.descendants(app.contentItem).some(item => item.pageName === "analysis" && item.current), 5000, "Switching to Analysis after a hover and rebuild leaves the application responsive");
        verify(waitForRendering(app.contentItem), "Analysis completes a frame after the chart input is rebuilt");
    }
    function test_b_broken_relation_is_a_reportable_popup() {
        openInput("relations");
        const structure = Session.project.currentStructure;
        const before = structure.atomSites.count;
        structure.atomSites.remove(0);
        compare(structure.atomSites.count, before - 1, "The structural edit really removes the site referenced by the alias");
        const remaining = structure.atomSiteMoments.components(0, "crystal_axes");
        verify(remaining.length > 0, "The remaining magnetic moment exercises its actual uncertainty getter after relation invalidation");
        let send;
        tryVerify(() => {
            send = Probe.objectsWithProperty(app, "text").find(item => item.text === "Send to developers" && Ui.rendered(item) && typeof item.clicked === "function");
            return send;
        }, 3000, "Invalid aliases and constraints are announced through the production error popup");
        const diagnostic = Probe.objectsWithProperty(app, "text").filter(item => Ui.rendered(item) && typeof item.text === "string").map(item => item.text).find(text => /alias|constraint/i.test(text));
        verify(diagnostic !== undefined, "The popup describes the alias or constraint that no longer holds");
        verify(Probe.objectsWithProperty(app, "text").some(item => item.text === "OK" && Ui.rendered(item)), "The invalid-relation popup offers OK");
        verify(!Probe.objectsWithProperty(app, "text").some(item => item.text === "Copy error message" && Ui.rendered(item)), "Error popups expose Send and OK without the retired Copy action");
        const point = Ui.clickPoint(send);
        verify(point !== null, "The visible Send action accepts actual pointer input");
        mouseClick(send, point.x, point.y);
        const form = named("feedback.form");
        tryCompare(form, "opened", true, 2000, "Send opens the existing feedback form without sending it");
        compare(named("feedback.kind").currentValue, "problem", "Invalid relations prefill the Problem report kind");
        verify(/alias|constraint/i.test(named("feedback.text").text), "The report text carries the actual invalid-relation diagnostic");
    }
    function test_c_typing_with_attachment_remains_responsive() {
        const folder = SettingsProof.emptyDirectory();
        verify(SettingsProof.write(folder, "attachment.bin", "x".repeat(1024 * 1024)), "The typing witness is a real admitted one MiB file");
        const form = named("feedback.form");
        form.openAs("feedback", "", "", []);
        tryCompare(form, "opened", true, 2000, "Typing is measured in the opened production feedback form");
        console.info("Attachment typing stage: attach");
        form.attach([folder + "/attachment.bin"]);
        console.info("Attachment typing stage: attached");
        compare(form.attachedFiles.length, 1, "The real attachment reader admits the file before typing");
        compare(form.attachmentError, "", "The responsiveness case stays within all named attachment limits");
        const field = named("feedback.text");
        field.text = "";
        field.forceActiveFocus();
        tryCompare(field, "activeFocus", true, 1000, "The opened feedback editor owns real keyboard focus before timing");
        console.info("Attachment typing stage: keyboard");
        const start = Date.now();
        for (let index = 0; index < 24; ++index) {
            verify(SettingsProof.key(field, Qt.Key_A), "Every keystroke reaches the real feedback editor");
            wait(0);
            verify(Date.now() - start < 5000, "Typing with an admitted attachment stays inside the five-second system interaction budget");
        }
        const elapsed = Date.now() - start;
        compare(field.text, "a".repeat(24), "Attachment processing never loses or defers typed characters");
        verify(elapsed < 5000, "Typing with an admitted attachment stays inside the five-second system interaction budget");
        compare(form.payload.attachments.length, 1, "Responsive editing retains the attached report file");
    }
    function test_d_asymmetric_unit_keeps_cobalt_sites() {
        const proof = JSON.parse(Probe.readReferenceFile("inputs.json")).cobalt;
        fuzzyCompare(proof.translated_z + proof.period, proof.original_z, 1e-12, "The Co2 input differs from its independently published position by exactly one lattice period");
        openInput("cobalt");
        const view = structureView();
        const atoms = findChild(view, "structure.toolbar.atoms");
        verify(atoms !== null, "The actual Structure toolbar exposes the atom-population selector");
        Atoms.select(test, Probe, app, atoms, "Asymmetric unit (crystal)");
        tryVerify(() => view.current && view.controller.spheres.count > 0, 5000, "The selected crystal asymmetric unit publishes its drawn spheres");
        const labels = [];
        for (let index = 0; index < view.controller.spheres.count; ++index)
            labels.push(view.controller.hoverAtSphere(index));
        for (const site of ["Co1", "Co2"])
            verify(labels.some(label => new RegExp("\\b" + site + "\\b").test(label)), "The independently authored " + site + " site remains present in the actual asymmetric-unit drawing");
    }
    function test_e_magnetic_cif_menu_and_drop_data() {
        return [
            {
                tag: "0-menu"
            },
            {
                tag: "1-drop"
            }
        ];
    }
    function test_e_magnetic_cif_menu_and_drop(data) {
        openInput("empty");
        Ui.click(test, Probe, app, "appBar.tab.structure");
        const project = Session.project;
        const before = project.structures.count;
        const file = Probe.repoUrl("tests/fixtures/magnetic_pnma/cosio/cosio1.mcif");
        if (data.tag === "0-menu") {
            Ui.click(test, Probe, app, "structures.load");
            tryCompare(named("structures.load.menu"), "opened", true, 2000, "The actual Load menu opens before its file action");
            const action = named("structures.load.file");
            verify(Ui.rendered(action) && action.enabled, "The real structure file action is enabled and rendered in the popup");
            mouseClick(action, action.width / 2, action.height / 2);
            const dialogs = Array.from(SettingsProof.projectFileDialogs(app, false)).filter(item => Array.from(item.nameFilters).some(filter => filter.includes("*.cif")));
            compare(dialogs.length, 1, "The actual structure menu opens its desktop file chooser");
            const dialog = dialogs[0];
            verify(Array.from(dialog.nameFilters).some(filter => filter.includes("*.mcif")), "The real structure chooser admits magnetic CIF files by extension");
            verify(SettingsProof.chooseProjectLocation(dialog, file, false), "The native chooser accepts the magnetic CIF and dispatches its original accepted handler");
        } else {
            verify(Session.save(), "The drop begins from a saved private project without an unrelated unsaved-work prompt");
            compare(project.modified, false, "The native drop fixture is clean before its actual event");
            verify(SettingsProof.dropProject(app, file), "The actual application drop entrance accepts a native magnetic CIF event");
        }
        tryVerify(() => Session.project === project && project.structures.count === before + 1, 5000, "Both magnetic CIF entrances add the structure to the initiating project");
        compare(project.currentStructure.atomSites.count, 6, "The admitted magnetic CIF retains all six independently authored sites");
        const moments = project.currentStructure.atomSiteMoments;
        const magnetic = Array.from({
            length: moments.count
        }, (_, index) => moments.components(index, "crystal_axes")).filter(components => components.length > 0);
        compare(magnetic.length, 2, "The admitted magnetic CIF retains both authored cobalt moments among the six site rows");
    }
}
