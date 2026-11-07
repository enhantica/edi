// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0
import EdiOnlineHttpFixture 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

PopupContractSession {
    function workflowFile(name) { return Qt.resolvedUrl("../../fixtures/experiment_workflow/" + name); }
    function typeOf(experiment) {
        return [experiment.sampleFormToken, experiment.beamModeToken, experiment.radiationProbeToken,
                experiment.scatteringTypeToken, experiment.dimensionalityToken, experiment.polarisationToken];
    }
    function measured(experiment) {
        return Probe.rows(experiment.pattern).map(row => [row.x, row.intensityMeas, row.intensityMeasSu]);
    }
    function normalized(value) {
        if (value === null || value === undefined) return null;
        if (typeof value === "number") return Number.isFinite(value) ? value : String(value);
        if (typeof value !== "object") return value;
        if (typeof value.value === "number" && typeof value.free === "boolean")
            return {value:normalized(value.value), free:value.free};
        return null;
    }
    function parameters(experiment) {
        const result = {};
        for (const name of ["instrument", "peak", "peakAsymmetry", "peakBackToBack", "peakGaussian", "peakLorentzian", "peakOther", "absorption", "extinction", "background", "backgroundTerms", "excludedRegions", "preferredOrientation", "linkedStructures"]) {
            const model = experiment[name];
            if (!model) continue;
            result[name] = Probe.rows(model).map(row => {
                const record = {};
                for (const key of Object.keys(row).sort()) record[key] = normalized(row[key]);
                return record;
            });
        }
        for (const key of ["scale", "cutoffFwhm", "datasetWeight", "backgroundType", "backgroundEstimateMode", "backgroundEstimateMethod", "backgroundEstimateWidth", "backgroundEstimateSmoothness", "backgroundEstimatePoints", "backgroundEstimateTolerance", "backgroundEstimateMaxTerms", "backgroundOrigin"])
            result[key] = normalized(experiment[key]);
        return result;
    }
    function check_menu_state_data() {
        return ["none", "empty", "loaded"].map(tag => ({tag:tag}));
    }
    function check_menu_state(data) {
        resetProject(false);
        const project = Session.project;
        if (data.tag !== "none") {
            verify(project.createExperiment(), "The measured-data target is explicitly created before any load");
            if (data.tag === "loaded") verify(project.loadDataInto(project.currentExperiment, workflowFile("replacement.xye")), "The Replace-label witness starts with measured data");
        }
        menuAction({page:AppState.Page.Experiment, group:"experiments", action:"experimentWeb"});
        const menu = renderedLoadMenu;
        const items = Array.from({length:menu.count}, (_, row) => menu.itemAt(row));
        for (const name of ["experimentFile", "experimentWeb"])
            verify(items.find(item => item.objectName === "experiments.load." + name).enabled,
                   "Full experiment actions stay available regardless of the current selection");
        for (const name of ["dataFile", "dataWeb"])
            compare(items.find(item => item.objectName === "experiments.load." + name).enabled, data.tag !== "none",
                    "Measured-data actions require an explicitly selected experiment");
        const text = Render.descendants(menu.contentItem).filter(item => typeof item.text === "string" && Ui.exposed(item)).map(item => item.text).join("\n");
        if (data.tag === "none") verify(text.includes("Create an experiment first to load data into it"),
                                        "The disabled measured-data section visibly explains the create-first prerequisite");
        else verify(text.includes(data.tag === "loaded" ? "Replace measured data" : "Load measured data"),
                    "The measured-data section names Load or Replace according to data presence");
    }
    function check_default_creation() {
        resetProject(false);
        const project = Session.project;
        verify(project.setNewExperimentType("sampleForm", "single crystal"), "A legacy pending type is a deliberate escape attempt against the new Create default");
        openPage({page:AppState.Page.Experiment, group:"experiments"});
        click(pageControl("experiments.create"));
        const experiment = project.currentExperiment;
        verify(experiment !== null, "The actual Create experiment action selects its new experiment");
        compare(typeOf(experiment).slice(0, 4), ["powder", "constant wavelength", "neutron", "bragg"],
                "Create always starts with the owner-declared default type instead of a retired pending selector");
        compare(experiment.instrument.parameterNamed("setup_wavelength").value, 1,
                "Every newly created constant-wavelength experiment starts at one angstrom");
        for (const name of ["sampleForm", "beamMode", "radiationProbe"])
            verify(pageControl("experimentType." + name).enabled, "The created experiment's selectors remain editable while it has no data");
        verify(project.loadDataInto(experiment, workflowFile("replacement.xye")), "The new experiment accepts its first measured dataset");
        settle();
        for (const name of ["sampleForm", "beamMode", "radiationProbe"])
            verify(!pageControl("experimentType." + name).enabled, "Measured data fixes the selected experiment's type selectors");
    }
    function check_no_new_type_group_data() { return ["none", "selected"].map(tag => ({tag:tag})); }
    function check_no_new_type_group(data) {
        resetProject(false);
        if (data.tag === "selected") verify(Session.project.createExperiment(), "The group-removal witness also covers a selected experiment");
        openPage({page:AppState.Page.Experiment, group:"experiments"});
        verify(Ui.find(pageItem(), "newExperimentType", true) === null,
               "The retired New experiment type controls are absent with and without a selection");
        verify(!Render.descendants(pageItem()).some(item => typeof item.text === "string" && item.text === "New experiment type" && Ui.exposed(item)),
               "The retired New experiment type heading is absent from the actual page");
    }
    function prepareReplacement() {
        resetProject(false);
        const project = Session.project;
        verify(project.loadStructure(fixture({file:"easydiffraction/structures/lbco.cif"})), "Replacement inputs use the retained independent LBCO structure");
        verify(project.createExperiment(), "The fresh reference is explicitly created with the same default type");
        verify(project.loadDataInto(project.currentExperiment, workflowFile("replacement.xye")), "The fresh reference loads the independent replacement file");
        const reference = measured(project.currentExperiment);
        verify(project.loadExperiments([fixture({file:"easydiffraction/experiments/lbco_hrpt.edi"})]), "The selected target starts with the retained full experiment and its parameters");
        const held = project.currentExperiment;
        held.name = "held-experiment";
        const wavelength = held.instrument.parameterNamed("setup_wavelength");
        const broadening = held.peak.parameterNamed("broad_gauss_u");
        verify(wavelength !== null && broadening !== null, "The parameter witness includes real wavelength and profile inputs");
        wavelength.value = 1.79;
        broadening.value = 0.231;
        held.datasetWeight = 1.37;
        compare(wavelength.value, 1.79, "The retained target uses a non-default wavelength before replacement");
        compare(broadening.value, 0.231, "The retained target uses a non-default profile parameter before replacement");
        verify(project.currentExperimentIndex > 0, "Replacement exercises a selected experiment after another row");
        return {reference:reference, old:measured(held), type:typeOf(held), parameters:parameters(held), input:held.text.inputText, index:project.currentExperimentIndex, count:project.experiments.count};
    }
    function proveReplacement(before) {
        const project = Session.project, held = project.currentExperiment;
        compare(project.experiments.count, before.count, "Replacing data adds no experiment");
        compare(project.currentExperimentIndex, before.index, "Replacement remains on the selected non-first row");
        compare(held.name, "held-experiment", "Replacement retains the user's experiment name");
        compare(typeOf(held), before.type, "Replacement retains every experiment type axis");
        compare(parameters(held), before.parameters, "Replacement retains the experiment's numerical parameters and settings");
        compare(measured(held), before.reference, "Replacement equals loading the same file into a fresh experiment of the same type");
        project.undo();
        compare(project.experiments.count, before.count, "Undo replacement retains both existing experiments");
        compare(typeOf(project.currentExperiment), before.type, "Undo replacement restores the original type");
        compare(parameters(project.currentExperiment), before.parameters, "Undo replacement restores the original parameter state");
        compare(measured(project.currentExperiment), before.old, "One Undo restores every previous measured point");
        compare(project.currentExperiment.text.inputText, before.input, "Undo restores the complete old persisted experiment input");
    }
    function check_replace_model() {
        const before = prepareReplacement();
        verify(Session.project.loadDataInto(Session.project.currentExperiment, workflowFile("replacement.xye")), "The ordinary selected-target loader accepts replacement data");
        proveReplacement(before);
    }
    function check_replace_ui_data() { return ["file", "web"].map(tag => ({tag:tag})); }
    function check_replace_ui(data) {
        const before = prepareReplacement();
        if (data.tag === "web") {
            const entry = sourceDocument().entries.find(row => row.kind === "data");
            entry.id = "replacement-data";
            entry.files = [{path:"data/replacement.xye", format:"xye"}];
            const search = searchDocument("data", {schema:"edi-data-index/1", entries:[entry]}, {id:entry.id});
            verify(OnlineHttpFixture.enqueueFile(200, workflowFile("replacement.xye")), "The actual web action receives the independent replacement bytes");
            loadResult(0);
            tryCompare(search, "busy", false, 3000, "The web replacement completes through the shipped file callback");
        } else {
            const route = {page:AppState.Page.Experiment, group:"experiments", action:"dataFile"};
            click(menuAction(route));
            let chooser;
            tryVerify(() => {
                chooser = Probe.objectsWithProperty(app, "selectedFile").find(item => item.visible && /measured data/i.test(item.title));
                return chooser !== undefined;
            }, 3000, "Replace From file opens the actual measured-data chooser");
            chooser.reject();
            tryCompare(chooser, "visible", false, 3000, "The chooser closes before its file input is prepared");
            chooser.currentFolder = workflowFile("");
            chooser.selectedFile = workflowFile("replacement.xye");
            click(menuAction(route));
            tryCompare(chooser, "visible", true, 3000, "The real Replace menu action reopens the prepared chooser");
            chooser.accept();
            tryCompare(chooser, "visible", false, 3000, "The actual accepted file closes its chooser");
        }
        tryVerify(() => measured(Session.project.currentExperiment).length === 4, 3000,
                  "The selected experiment adopts the replacement's four independent measured rows");
        proveReplacement(before);
    }
    function check_wrong_type_data() { return ["powder-target", "single-crystal-target"].map(tag => ({tag:tag})); }
    function check_wrong_type(data) {
        const before = prepareReplacement();
        const project = Session.project;
        const reflections = Qt.resolvedUrl("../../fixtures/single_crystal/fullprof/sc-neut-cwl_tbti_basic/tbti.int");
        // A successful same-format control proves this is a type refusal, not an unsupported-file escape.
        verify(project.createExperiment(), "The reflection-file control begins with explicit creation");
        verify(project.setExperimentType(project.currentExperimentIndex, "sampleForm", "single crystal"), "The positive reflection control uses its declared sample form");
        verify(project.loadDataInto(project.currentExperiment, reflections), "The retained FullProf reflection input is valid for a single crystal");
        let file;
        if (data.tag === "powder-target") {
            project.currentExperimentIndex = before.index;
            file = reflections;
        } else file = workflowFile("replacement.xye");
        const held = project.currentExperiment;
        const snapshot = {count:project.experiments.count, index:project.currentExperimentIndex, type:typeOf(held), parameters:parameters(held), data:measured(held), input:held.text.inputText};
        verify(!project.loadDataInto(held, file), "A different-type file is refused instead of retyping the selected experiment");
        verify(project.lastError !== "", "A type refusal returns a factual reason");
        compare(project.experiments.count, snapshot.count, "A type refusal leaves the experiment list unchanged");
        compare(project.currentExperimentIndex, snapshot.index, "A type refusal leaves the selection unchanged");
        compare(typeOf(project.currentExperiment), snapshot.type, "A type refusal preserves all type axes");
        compare(parameters(project.currentExperiment), snapshot.parameters, "A type refusal preserves all numerical inputs");
        compare(measured(project.currentExperiment), snapshot.data, "A type refusal preserves every old data point");
        compare(project.currentExperiment.text.inputText, snapshot.input, "A type refusal preserves the complete persisted experiment input");
    }
    property var lessonObservations: ({})
    property bool walkingLesson: false
    property int lessonFits: 0
    Connections {
        target: Session.project ? Session.project.fit : null
        function onRunningChanged() {
            if (walkingLesson && Session.project.fit.running) ++lessonFits;
        }
    }
    function check_prepare_lesson_data() { return ["simulation", "fitting"].map(tag => ({tag:tag})); }
    function check_prepare_lesson(data) {
        resetProject(false);
        const owner = Session.project;
        owner.description = "owner before the completed lesson";
        lessonFits = 0;
        walkingLesson = true;
        launchTutorial(data.tag);
        const panel = tutorialPanel();
        tryCompare(panel, "opened", true, 3000, "The scientific tutorial opens before its actual Next walk");
        let changes = 0;
        for (let attempt = 0; attempt < 100 && !panel.atEnd; ++attempt) {
            const dialog = SettingsProof.creationDialog(app);
            if (dialog && dialog.visible) dialog.projectParentDirectory = String(SettingsProof.emptyDirectory());
            const before = panel.step;
            click(findChild(panel, "tutorial.next"));
            tryVerify(() => { OnboardingProbe.advanceClock(16); return panel.step > before || panel.atEnd; }, 15000,
                      "A real Next action advances the scientific tutorial without an unmet-state stall: " + data.tag + " step " + before);
            if (Session.project) {
                tryCompare(Session.project.fit, "running", false, 15000, "Tutorial fits finish through the ordinary worker");
                tryCompare(Session.project, "calculating", false, 15000, "Tutorial model changes finish calculating before the next action");
            }
            ++changes;
        }
        const project = Session.project;
        const experiment = project ? project.currentExperiment : null;
        const pattern = experiment ? Probe.rows(experiment.pattern) : [];
        const observation = {
            atEnd:panel.atEnd, changes:changes, structure:project && project.currentStructure !== null,
            experiment:experiment !== null, fits:lessonFits,
            calculated:pattern.some(row => Number.isFinite(row.intensityCalc) && row.intensityCalc > 0),
            measured:experiment ? measured(experiment) : [],
            calculationOnly:experiment ? experiment.calculationOnly : true,
            wavelength:experiment ? experiment.instrument.parameterNamed("setup_wavelength").value : 0
        };
        walkingLesson = false;
        if (panel.atEnd) {
            const discard = Probe.objectsWithProperty(app, "objectName").find(item => item.objectName === "tutorial.discard" && item.visible);
            verify(discard !== undefined, "A completed lesson offers the real return-to-project action");
            click(discard);
            tryCompare(Session, "project", owner, 3000, "The completion return action restores the original project object");
        }
        observation.ownerRestored = Session.project === owner && owner.description === "owner before the completed lesson";
        const records = Object.assign({}, lessonObservations);
        records[data.tag] = observation;
        lessonObservations = records;
    }
    function check_lesson_completed_data() { return check_prepare_lesson_data(); }
    function check_lesson_completed(data) {
        const result = lessonObservations[data.tag];
        verify(result !== undefined && result.atEnd && result.changes > 0,
               "Both scientific tutorials reach their actual last step by following real Next actions");
    }
    function check_lesson_science_data() { return check_prepare_lesson_data(); }
    function check_lesson_science(data) {
        const result = lessonObservations[data.tag];
        verify(result !== undefined && result.structure && result.experiment && result.calculated,
               "The completed lesson contains its actual scientific model and a nonzero calculated pattern");
        compare(result.wavelength, 1.494, "The written HRPT lessons reach their independent 1.494 angstrom instrument setting");
        if (data.tag === "fitting") {
            verify(!result.calculationOnly && result.fits >= 2, "The completed fitting lesson runs both actual fitting stages with measured data");
            const file = SettingsProof.fileObservation(fixture({file:"easydiffraction/data/"}), "lbco_hrpt.xye");
            verify(file.exists, "The completed fitting state has an independent committed measured-data reference");
            const expected = file.text.trim().split(/\r?\n/).filter(line => /^\s*[+\-\d.]/.test(line)).map(line => line.trim().split(/\s+/).map(Number));
            compare(result.measured, expected, "The completed fitting lesson retains every independent coordinate, count and uncertainty");
        }
    }
    function check_lesson_owner_data() { return check_prepare_lesson_data(); }
    function check_lesson_owner(data) {
        const result = lessonObservations[data.tag];
        verify(result !== undefined && result.ownerRestored, "Returning after the completed lesson preserves the original user project and its unsaved description");
    }

}
