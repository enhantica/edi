import QtQuick
import "UiInteraction.js" as Ui
import QtTest
import edi.app
import EdiAcceptance 1.0

TestCase {
    id: test
    name: "E04T1OwnerAmendments"
    when: windowShown
    property var appWindow
    Component { id: application; Main {} }
    function initTestCase() {
        failOnWarning(/.*/);
        appWindow = application.createObject(null);
        verify(appWindow !== null, "owner amendments: production Main must load");
        verify(waitForRendering(appWindow.contentItem), "owner amendments: the real window is ready for input");
    }
    function init() {
        // Qt Graphs probes a temporary GLES2 context once per process, even
        // with the software backend. Only this first Graphs user may lack GL.
        const firstGraphsUse = qtest_results.functionName
            === "test_library_settable_scalars_and_derived_readonly";
        failOnWarning(firstGraphsUse
            ? /\A(?!QRhiGles2: Failed to create (?:temporary context|context)\z)[\s\S]*\z/
            : /.*/);
        Session.closeProject();
        Probe.clearWatches();
    }
    function cleanupTestCase() {
        Probe.clearWatches();
        Session.closeProject();
        verify(waitForRendering(appWindow.contentItem),
               "I10: pending page loads settle before the test window is destroyed");
        appWindow.destroy();
    }
    function open(name) {
        Session.openProject(Probe.repoUrl("tests/fixtures/e04_t1/" + name));
        verify(Session.hasProject, "owner amendments: independent fixture opens: " + Session.lastError);
        return Session.project;
    }
    function same(actual, expected, requirement) {
        compare(JSON.stringify(actual), JSON.stringify(expected), requirement);
    }
    function visibleControl(name) { return Ui.control(Probe, appWindow, name); }
    function click(name) { Ui.click(test, Probe, appWindow, name); }

    function reveal(group, field) {
        Ui.expandGroup(test, Probe, appWindow, "group." + group);
        tryVerify(() => visibleControl(field) !== null, 2000,
                  "owner amendments: expanded category exposes its fields: " + field);
    }
    function tokens(model) { return Probe.rows(model).map(r => r.token); }
    function renderedCategories(basic, extras) {
        [{tier: "basic", expected: basic}, {tier: "extras", expected: extras}].forEach(step => {
            click("sideBar.tab." + step.tier);
            // Wait on the selected pane's actual contents, not the checked button:
            // SwipeView's animation starts after its currentIndex changes.
            tryVerify(() => {
                const actual = Ui.groupNames(Ui.page(appWindow))
                    .filter(name => !["structures", "experiments"].includes(name));
                return JSON.stringify(actual.sort()) === JSON.stringify(step.expected.slice().sort());
            }, 2000, "owner category record: selected " + step.tier
               + " pane contains exactly the independently declared categories, without duplicates");
        });
    }
    function containsField(text, field, value, requirement) {
        verify(new RegExp("(?:^|\\n)_" + field.replace(/\./g, "\\.") + "\\s+" + value + "(?:\\s|$)").test(text), requirement);
    }
    function scalar(object, name, value, text, field) {
        verify(Probe.writable(object, name), "owner editability: library-settable property is writable: " + name);
        verify(Probe.writeProperty(object, name, value), "owner editability: valid property write succeeds: " + name);
        compare(object[name], value, "owner editability: property retains the requested nontrivial value");
        containsField(text.text, field, String(value), "owner editability: write reaches the core block, not just the widget");
    }
    function row(model, index, role, value) {
        verify(Probe.writeRole(model, index, role, value), "owner editability: library-settable table role accepts writes: " + role);
        compare(Probe.rows(model)[index][role], value, "owner editability: table edit is retained");
    }
    function test_library_settable_scalars_and_derived_readonly() {
        const p = open("editable-project");
        scalar(p.currentExperiment, "cutoffFwhm", 13.75, p.currentExperiment.text, "peak.cutoff_fwhm");
        scalar(p.analysis, "maxIterations", 73, p.analysis.text, "minimizer.max_iterations");
        scalar(p.analysis, "chiSquareTolerance", 0.0025, p.analysis.text, "minimizer.chi_square_tolerance");
        verify(Probe.writable(p, "name"), "owner editability: project name is editable");
        verify(Probe.writable(p.currentStructure, "name"), "owner editability: structure name is editable");
        verify(Probe.writable(p.currentExperiment, "name"), "owner editability: experiment name is editable");
        verify(Probe.writeProperty(p, "name", "acceptance_renamed"), "owner editability: project name accepts a real edit");
        verify(p.metadataText.text.includes("acceptance_renamed"), "owner editability: project rename reaches the core metadata");
        const sg = p.currentStructure.spaceGroup;
        verify(Probe.writable(sg, "nameHM") && Probe.writable(sg, "coordSystemCode"),
               "owner editability: space-group name and setting follow edi's settable fields");
        verify(!Probe.writable(sg, "crystalSystem"), "owner editability: derived crystal system has no writer");
        verify(Probe.writable(sg, "itNumber"), "owner editability: the library-settable IT number is editable");
        ["sampleForm", "beamMode", "radiationProbe", "scatteringType"].forEach(name => {
            verify(!Probe.writable(p.currentExperiment, name), "owner editability: experiment type is immutable: " + name);
            verify(!Probe.writable(p.currentExperiment, name + "Token"), "owner editability: token alias cannot mutate type");
        });
        // International Tables: P1 is triclinic; this expectation is not obtained from the app.
        // Its sole Wyckoff letter is a: retain a serializable structure after the edit.
        Probe.rows(p.currentStructure.atomSites).forEach((atom, index) =>
            row(p.currentStructure.atomSites, index, "wyckoffLetter", "a"));
        verify(Probe.writeProperty(sg, "coordSystemCode", ""), "owner editability: setting can be cleared");
        const handle = Probe.watch(sg);
        verify(Probe.writeProperty(sg, "nameHM", "P 1"), "owner editability: space-group edit is implemented now");
        compare(sg.crystalSystem, "triclinic", "owner editability: crystal system follows a non-cubic space-group edit");
        verify(p.currentStructure.text.text.includes('P 1'), "owner editability: space-group edit reaches the core");
        const events = Probe.events(handle);
        compare((events.nameHMChanged || []).length, 1, "I3: edited space-group name emits once");
        compare((events.crystalSystemChanged || []).length, 1, "I3: dependent derived crystal system emits once");
        verify(!events.coordSystemCodeChanged, "I3: unrelated setting is not re-notified");
    }
    function test_library_settable_table_columns_reach_core() {
        const p = open("editable-project");
        const s = p.currentStructure, e = p.currentExperiment;
        row(s.atomSites, 0, "label", "LaEdited");
        row(s.atomSites, 0, "typeSymbol", "Ce");
        row(s.atomSites, 0, "wyckoffLetter", "b");
        verify(s.text.text.includes("LaEdited") && s.text.text.includes("Ce"), "owner editability: atom identity and element writes reach core");
        row(e.background, 0, "position", 9.75);
        verify(e.text.text.includes("9.75"), "owner editability: background abscissa writes reach core");
        row(e.excludedRegions, 0, "start", 0.125);
        row(e.excludedRegions, 0, "end", 4.875);
        verify(e.text.text.includes("0.125") && e.text.text.includes("4.875"), "owner editability: excluded-region endpoints reach core");
        row(e.preferredOrientation, 0, "indexH", 2);
        row(e.preferredOrientation, 0, "indexK", 1);
        row(e.preferredOrientation, 0, "indexL", 3);
        verify(/lbco\s+[^\n]*\b2\s+1\s+3(?:\s|$)/.test(e.text.text), "owner editability: nontrivial orientation axis reaches core");
        row(s.scatteringLengths, 0, "lengthFm", 7.125);
        verify(s.text.text.includes("7.125"), "owner editability: custom scattering length reaches core");
    }
    function test_settable_fields_are_editable_in_the_page() {
        const p = open("editable-project");
        const pages = [
            {page: "structure", tier: "basic", group: "space_group", fields: ["spaceGroup.nameHM", "spaceGroup.coordSystemCode"]},
            {page: "structure", tier: "basic", group: "atom_site", fields: ["atomSite.label.0", "atomSite.typeSymbol.0"]},
            {page: "structure", tier: "extras", group: "scattering_length", fields: ["scatteringLength.lengthFm.0"]},
            {page: "experiment", tier: "basic", group: "background", fields: ["background.position.0"]},
            {page: "experiment", tier: "extras", group: "excluded_region", fields: ["excludedRegion.start.0", "excludedRegion.end.0"]},
            {page: "experiment", tier: "extras", group: "preferred_orientation", fields: ["preferredOrientation.indexH.0", "preferredOrientation.indexK.0", "preferredOrientation.indexL.0"]},
            {page: "analysis", tier: "extras", group: "minimizer", fields: ["minimizer.maxIterations", "minimizer.chiSquareTolerance"]},
            {page: "experiment", tier: "extras", group: "peak", fields: ["peak.cutoff_fwhm"]}
        ];
        pages.forEach(step => {
            click("appBar.tab." + step.page);
            click("sideBar.tab." + step.tier);
            reveal(step.group, step.fields[0]);
            step.fields.forEach(name => {
                tryVerify(() => visibleControl(name) !== null, 2000,
                          "owner editability: each editor is exposed after group expansion: " + name);
                const control = visibleControl(name);
                verify(control !== null && control.enabled && control.readOnly === false,
                       "owner editability: each library-settable field is an enabled editor, not just a writable VM: " + name);
            });
        });
        const cutoff = visibleControl("peak.cutoff_fwhm");
        cutoff.forceActiveFocus();
        keyClick(Qt.Key_A, Qt.ControlModifier);
        [Qt.Key_1, Qt.Key_3, Qt.Key_Period, Qt.Key_7, Qt.Key_5, Qt.Key_Return].forEach(key => keyClick(key));
        compare(p.currentExperiment.cutoffFwhm, 13.75, "owner editability: real typing edits the core peak cutoff");
    }
    function test_visible_xray_and_background_selectors_and_no_split_groups() {
        const p = open("xray-project"), e = p.currentExperiment;
        compare(e.radiationProbeToken, "xray", "owner X-ray record: real  X-ray project opens");
        click("appBar.tab.experiment");
        click("sideBar.tab.extras");
        reveal("scattering_source", "scatteringSource.xray_form_factor");
        // Option expectations: edi core/src/io.cpp admitted lists and model.hpp defaults.
        const choices = {
            xray_form_factor: ["wk1995", "it1992"],
            xray_dispersion: ["cromer-liberman", "sasaki1989", "it1992", "none"]
        };
        Object.keys(choices).forEach(name => {
            tryVerify(() => visibleControl("scatteringSource." + name) !== null, 2000,
                      "owner X-ray record: each selector is exposed after the group expands");
            const combo = visibleControl("scatteringSource." + name);
            verify(combo !== null && combo.enabled, "owner X-ray record: each X-ray selector is visible and editable");
            same(tokens(combo.model), choices[name], "owner X-ray record: every independently declared option is shown");
            compare(tokens(combo.model)[combo.currentIndex], name === "xray_form_factor" ? "it1992" : "sasaki1989",
                    "owner X-ray record: loaded nondefault selection is displayed");
            // Pointer selection reaches the real popup on both portable and drawn hosts;
            // key events otherwise depend on activation of a different test window.
            click("scatteringSource." + name);
            tryCompare(combo.popup, "opened", true, 2000,
                       "owner X-ray record: real pointer input opens the selector");
            const targetIndex = name === "xray_form_factor" ? 0 : choices[name].length - 1;
            const list = combo.popup.contentItem;
            tryVerify(() => list.itemAtIndex(targetIndex) !== null, 2000,
                      "owner X-ray record: the requested popup choice is materialised");
            const entry = list.itemAtIndex(targetIndex);
            mouseClick(entry, entry.width / 2, entry.height / 2);
            tryCompare(combo, "currentIndex", targetIndex, 2000,
                       "owner X-ray record: real pointer input selects the independently named choice");
            const wanted = name === "xray_form_factor" ? "wk1995" : "none";
            containsField(e.text.text, "scattering_source." + name, wanted,
                          "owner X-ray record: a real selector event updates the core declaration");
        });
        verify(visibleControl("scatteringSource.neutron_scattering_length") === null,
               "owner X-ray record: a neutron-only option is not shown for X-rays");
        click("sideBar.tab.basic");
        reveal("background", "background.type");
        const background = visibleControl("background.type");
        verify(background !== null, "owner background record: a visible selector leads the Background group");
        //  admits both polynomial forms; exact equality still hides every reserved family.
        same(tokens(background.model), ["line-segment", "chebyshev", "polynomial"],
             ": exactly the computable background families are offered; reserved families stay hidden");
        same(Probe.rows(e.categories).map(r => r.categoryId),
             ["experiment_type", "data", "background", "instrument", "peak", "linked_structure", "excluded_region", "absorption", "preferred_orientation", "scattering_source"],
             "owner category record: experiment groups are exactly the admitted edi categories");
        e.peakType = "cwl-thompson-cox-hastings";
        reveal("peak", "peak.asym_fcj_1");
        const peak = visibleControl("group.peak");
        ["asym_fcj_1", "asym_fcj_2"].forEach(field =>
            tryVerify(() => Ui.find(peak, "peak." + field) !== null, 2000,
                      "owner category record: asymmetry stays inside Basic Peak"));
        click("appBar.tab.structure");
        click("sideBar.tab.basic");
        same(Probe.rows(p.currentStructure.categories).map(r => r.categoryId),
             ["space_group", "cell", "atom_site", "scattering_length"],
             "owner category record: ADP never creates a separate category");
        reveal("atom_site", "atomSite.adpIso.0");
        const atoms = visibleControl("group.atom_site");
        verify(Ui.find(atoms, "atomSite.adpIso.0") !== null,
               "owner category record: ADP is visibly inside Atom sites");
        //  D11 adds the view-only Appearance group to Structure Extras.
        renderedCategories(["space_group", "cell", "atom_site"], ["scattering_length", "appearance"]);
        click("appBar.tab.experiment");
        renderedCategories(["experiment_type", "background", "instrument", "peak", "linked_structure"],
                           ["data", "excluded_region", "absorption", "preferred_orientation", "scattering_source", "peak"]);
    }
}
