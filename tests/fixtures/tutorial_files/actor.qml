// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "FittingTutorialFiles"
    when: windowShown
    // The system actor injects the discovered bundled inputs and independent
    // example reference, not a production outcome or a fitted starting project.
    property url cifInput: "__TUTORIAL_CIF__"
    property url xyeInput: "__TUTORIAL_XYE__"
    property var app
    property var panel
    property var written
    property var claims: []
    Component {
        id: application
        Main {}
    }
    function claim(name) {
        claims.push(name);
        console.log("TUTORIAL_FILE_CLAIMS " + JSON.stringify(claims));
    }
    function named(name) {
        const items = Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === name);
        compare(items.length, 1, "The actual tutorial has one required control: " + name);
        return items[0];
    }
    function finishPages() {
        tryVerify(() => {
            for (let n = 0; n < 10 && app.pagesBuilt !== app.pagesWanted; ++n)
                OnboardingProbe.incubate(app);
            return app.pagesBuilt === app.pagesWanted;
        }, 5000, "The tutorial's asynchronous pages exist before their controls are used");
    }
    function click(item) {
        verify(waitForPolish(item), "The tutorial action finishes layout before real input");
        const point = Ui.clickPoint(item);
        verify(item.enabled && point !== null, "The tutorial action is enabled and exposed for actual input");
        mouseClick(item, point.x, point.y);
    }
    function init() {
        Session.closeProject();
        Preferences.engineThreads = 1;
        app = application.createObject(null);
        verify(app !== null, "The fitting-from-files witness uses the actual application host");
        app.width = 1440;
        app.height = 1000;
        AppState.open(AppState.Page.Home);
        verify(waitForRendering(app.contentItem), "The real Home page is ready for tutorial entry");
        const home = Probe.objectsWithProperty(app, "text").filter(item => item.text === "Tutorials" && Ui.rendered(item) && typeof item.clicked === "function");
        compare(home.length, 1, "The fitting lesson starts through Home Tutorials");
        OnboardingProbe.startClock();
        click(home[0]);
        OnboardingProbe.advanceClock(1000);
        const chooser = named("tutorials");
        tryCompare(chooser, "opened", true, 2000, "The actual Tutorials chooser opens");
        const play = findChild(chooser.contentItem, "tutorials.open.fitting");
        verify(play !== null, "The rendered Fitting row exposes its own play control");
        click(play);
        OnboardingProbe.advanceClock(1000);
        panel = named("tutorial");
        tryCompare(panel, "opened", true, 2000, "The fitting tutorial opens from its real chooser action");
        written = JSON.parse(OnboardingProbe.sourceText("app/tutorials/manifest.json")).tutorials.find(item => item.id === "fitting").steps;
    }
    function cleanup() {
        if (panel && panel.visible)
            panel.stop();
        Session.closeProject();
        if (app)
            app.destroy();
        app = null;
        panel = null;
    }
    function showInstruction(pattern) {
        const index = written.findIndex(step => pattern.test(step.text));
        verify(index >= 0, "The real written recipe includes the required instruction: " + pattern);
        panel.step = index;
        panel.show();
        finishPages();
        const target = Ui.control(Probe, app, written[index].target);
        verify(target !== null && Ui.rendered(Ui.target(target)), "Each fitting instruction names a visible actual control: " + written[index].target);
        return target;
    }
    function fit() {
        tryCompare(Session.project, "calculating", false, 15000, "The tutorial's real calculation settles before its next fit");
        AppState.open(AppState.Page.Analysis);
        finishPages();
        Ui.click(test, Probe, app, "statusBar.fit.button");
        tryVerify(() => Session.project.fit.running || Session.project.fit.canUndo, 2000, "The tutorial starts the actual fit worker through the status-bar control");
        tryCompare(Session.project.fit, "running", false, 15000, "The tutorial's actual fit completes");
        verify(Session.project.fit.canUndo && Session.project.fit.outcome !== "failed", "The tutorial's real fit publishes a usable result");
        const results = Probe.visiblePopups(app).filter(item => item !== panel && item.objectName === "fit.results");
        for (const result of results)
            result.close();
    }
    function test_saved_files_build_the_staged_fit_and_report() {
        compare(app.appBarCentralTabs.currentIndex, AppState.Page.Home, "The fitting recipe begins on Home at Start");
        Ui.click(test, Probe, app, "home.start");
        tryCompare(app.appBarCentralTabs, "currentIndex", AppState.Page.Project, 2000, "The learner's Start action opens Project");
        compare(Session.project, null, "The fitting tutorial does not create the learner project silently");
        const createIndex = written.findIndex(step => step.target === "project.create");
        verify(createIndex > 0, "The fitting Create action follows Home Start");
        tryCompare(panel, "step", createIndex, 2000, "Home Start advances the fitting lesson to its real Create action");
        Ui.click(test, Probe, app, "project.create");
        const create = SettingsProof.creationDialog(app);
        verify(create !== null, "The fitting learner opens the actual project-creation form");
        tryCompare(create, "opened", true, 2000, "The real project-name form opens before input");
        create.projectParentDirectory = String(SettingsProof.emptyDirectory());
        const name = findChild(create, "createProject.name");
        verify(name !== null && SettingsProof.type(name, "fitting_from_files"), "The learner names the new fitting project through its field");
        click(create.standardButton(Dialog.Ok));
        tryVerify(() => Session.project !== null && Session.project.name === "fitting_from_files", 3000, "Actual user creation opens the named fitting project");
        verify(Probe.rows(Session.project.structures).length === 0 && Probe.rows(Session.project.experiments).length === 0, "The learner-created fitting project starts without prepared structures or data");
        claim("new-project");
        showInstruction(/save.{0,50}(?:files|lbco\.cif)/i);
        const saveActions = Probe.objectsWithProperty(panel, "text").filter(item => item.text === "Save tutorial files" && Ui.rendered(item) && typeof item.clicked === "function");
        compare(saveActions.length, 1, "The file-saving step exposes one real Save tutorial files action");
        const saveFiles = saveActions[0];
        click(saveFiles);
        const destination = SettingsProof.emptyDirectory();
        let dialogs = [];
        tryVerify(() => {
            dialogs = SettingsProof.projectFileDialogs(app, true);
            return dialogs.length === 1;
        }, 2000, "Save tutorial files asks for a real local destination");
        verify(SettingsProof.chooseProjectLocation(dialogs[0], destination, true), "The injected chooser supplies a private tutorial-files destination");
        const actualCif = SettingsProof.text(destination, "lbco.cif"), actualXye = SettingsProof.text(destination, "hrpt.xye");
        compare(actualCif, SettingsProof.text(cifInput, "lbco.cif"), "Save tutorial files preserves the bundled CIF bytes");
        compare(actualXye, SettingsProof.text(xyeInput, "hrpt.xye"), "Save tutorial files preserves the bundled measurement bytes");
        verify(actualCif.length > 0 && actualXye.length > 0, "The real save action produces both nonempty tutorial files");
        claim("saved-files");
        showInstruction(/(?:load|open|import).{0,80}lbco\.cif/i);
        verify(Session.project.loadStructure(SettingsProof.childUrl(destination, "lbco.cif")), "The actual project loads the saved tutorial CIF through its normal import path");
        compare(Session.project.currentStructure.name, "lbco", "The saved tutorial CIF establishes the name used by later instructions");
        verify(Session.project.createExperiment(), "The learner creates the actual tutorial experiment");
        showInstruction(/(?:load|open|import).{0,80}hrpt\.xye/i);
        verify(Session.project.loadDataInto(Session.project.currentExperiment, SettingsProof.childUrl(destination, "hrpt.xye")), "The actual experiment loads the saved XYE through its normal data path");
        claim("loaded-inputs");
        const p = Session.project, e = p.currentExperiment;
        // Given values come from the independently committed example's input file.
        // Its result is never loaded into the project being fitted.
        const source = OnboardingProbe.sourceText("docs/user/cli/pd-neut-cwl_lbco-hrpt/project/experiments/hrpt.edi");
        function scalar(tag) {
            const line = source.split(/\r?\n/).find(row => row.startsWith(tag + " "));
            verify(line !== undefined, "The independent example declares the tutorial input " + tag);
            return Number(line.trim().split(/\s+/)[1].replace(/\([^)]*\)$/, ""));
        }
        for (const [model, prefix] of [[e.instrument, "instrument"], [e.peak, "peak"]])
            for (const row of Probe.rows(model)) {
                const parameter = row.parameter;
                if (!parameter)
                    continue;
                const tag = "_" + prefix + "." + parameter.name;
                if (source.includes(tag + " "))
                    parameter.value = scalar(tag);
            }
        compare(e.radiationProbeToken, "neutron", "The from-files example uses the stated neutron probe");
        compare(e.beamModeToken, "constant wavelength", "The from-files example uses the stated constant wavelength");
        compare(e.sampleFormToken, "powder", "The from-files example uses the stated powder sample");
        showInstruction(/(?:wavelength|1\.494)/i);
        claim("experiment-values");
        showInstruction(/(?:automatic|auto|estimate).{0,40}background|background.{0,40}(?:automatic|auto)/i);
        e.backgroundEstimateMode = "auto";
        verify(p.estimateBackground(), "The tutorial estimates an automatic background after setting the instrument values");
        tryCompare(p, "calculating", false, 15000, "The initial automatic background calculation completes");
        claim("background");
        const parameters = Probe.rows(p.parameters).map(row => row.parameter);
        verify(p.setParametersFree(parameters, false), "Staged fitting starts from a fixed parameter set");
        // The groups are cumulative; a real fit happens between releases.
        for (const group of [/scale|background/, /cell|calib_twotheta_offset/, /peak/, /atom_site/]) {
            const selected = parameters.filter(item => item.fittable && group.test(item.uid));
            verify(selected.length > 0, "Every staged release reaches actual parameters in its physical group: " + group);
            verify(p.setParametersFree(selected, true), "The tutorial releases a real staged group through the application's edit path");
            fit();
        }
        claim("staged-fits");
        const adps = Probe.rows(p.currentStructure.atomSiteAdps);
        const la = adps.find(row => row.label === "La"), ba = adps.find(row => row.label === "Ba");
        verify(la !== undefined && ba !== undefined && la.adpIso.free && ba.adpIso.free, "La and Ba Biso are both free in the unconstrained fit");
        verify(p.correlations.labels.length > 1 && p.correlations.values.length > 1, "The unconstrained actual fit publishes correlations before adding a constraint");
        const table = showInstruction(/s\.u\.|uncertaint/i);
        verify(typeof table.itemAtIndex === "function", "The uncertainty instruction points at the real parameter table");
        const rows = Probe.rows(table.sourceModel);
        for (const atom of ["La", "Ba"]) {
            const index = rows.findIndex(row => row.parameter && row.parameter.uid.includes("." + atom + ".adp_iso"));
            verify(index >= 0, "The diagnostics step includes the actual unconstrained Biso parameter: " + atom);
            table.positionViewAtIndex(index, ListView.Contain);
            verify(waitForPolish(table), "The fitted Biso row is instantiated before its s.u. is read");
            const cell = Render.cells(table.itemAtIndex(index))[4];
            verify(cell !== undefined && Ui.rendered(cell) && Ui.text(cell).trim() !== "", "The actual table shows each unconstrained Biso standard uncertainty");
        }
        showInstruction(/correlation/i);
        verify(p.correlations.labels.some(label => /\bLa\b/.test(label)) && p.correlations.labels.some(label => /\bBa\b/.test(label)), "The displayed correlation data includes both freely fitted La and Ba parameters");
        claim("unconstrained-diagnostics");
        showInstruction(/constraint|constrain|tie/i);
        const aliases = p.analysis.aliases;
        for (const [name, atom] of [["tutorial_la", "La"], ["tutorial_ba", "Ba"]]) {
            aliases.append();
            const index = Probe.rows(aliases).length - 1;
            verify(aliases.setText(index, "id", name) && aliases.setText(index, "parameter", "lbco.atom_site." + atom + ".adp_iso"), "The constraint aliases refer to the actual tutorial atoms");
        }
        p.analysis.constraints.append();
        verify(p.analysis.constraints.setText(Probe.rows(p.analysis.constraints).length - 1, "expression", "tutorial_ba = tutorial_la"), "The tutorial applies its La/Ba Biso equality through the real constraint table");
        verify(p.estimateBackground(), "The constrained stage obtains a new automatic background");
        fit();
        claim("constrained-fit");
        // This is explicitly the example's existing regression pin, not an
        // experimental reference; neither its value nor tolerance is regenerated.
        const pin = JSON.parse(OnboardingProbe.sourceText("docs/user/cli/pd-neut-cwl_lbco-hrpt/expected.json")).quantities.reduced_chi_square;
        const result = /_fit_result\.reduced_chi_square\s+([^\s]+)/.exec(p.analysis.text.text);
        verify(result !== null, "The final real fit records its full-precision reduced chi-square");
        const chi = Number(result[1]), tolerance = pin.tol_abs === null ? Math.abs(pin.value) * pin.tol_rel : pin.tol_abs;
        verify(Number.isFinite(chi) && Math.abs(chi - pin.value) <= tolerance, "The tutorial's final reduced chi-square reaches the saved LBCO HRPT example within its existing regression tolerance");
        claim("example-quality");
        showInstruction(/report/i);
        verify(Ui.text(Ui.page(app)).length > 0, "The fitted tutorial produces a real Report page");
        showInstruction(/save.{0,40}project/i);
        const saved = SettingsProof.emptyDirectory();
        verify(Session.saveAs(saved), "The completed tutorial saves through the real project save path");
        verify(SettingsProof.text(saved, "project.edi").length > 0, "The saved tutorial has its own project entry file");
        claim("report-and-save");
    }
}
