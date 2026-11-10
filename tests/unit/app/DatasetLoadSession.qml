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

ExperimentWorkflowSession {
    function cleanup() {
        for (const dialog of Probe.objectsWithProperty(app, "objectName").filter(item => item.objectName === "datasets.choice" && item.visible)) dialog.reject();
        settle();
        cleanupOnlineControls();
    }
    property var datasetInputs
    function prepareDatasets() {
        resetProject(false);
        const project = Session.project;
        verify(project.createExperiment(), "Batch loading begins from an explicitly created experiment");
        project.currentExperiment.instrument.parameterNamed("setup_wavelength").value = 1.79;
        project.currentExperiment.peak.parameterNamed("broad_gauss_u").value = 0.231;
        const file = SettingsProof.fileObservation(mailbox, "datasets.json");
        verify(file.exists, "Batch inputs are independently authored plain data files");
        datasetInputs = JSON.parse(file.text);
        return project;
    }
    function selectedDatasetReady(project, index) {
        if (project.currentExperimentIndex !== index || project.calculating || !Probe.datasetReady(project)) return false;
        const rows = Probe.rows(project.experiments);
        const expected = decodeURIComponent(String(datasetInputs.files[index]).split("/").pop());
        return rows[index] !== undefined && rows[index].file === expected;
    }
    function selectDataset(project, index) {
        project.currentExperimentIndex = index;
        tryVerify(() => selectedDatasetReady(project, index), 5000,
                  "The requested dataset identity completes its own asynchronous read and projection");
    }
    function choice() {
        let dialog;
        tryVerify(() => {
            dialog = Probe.objectsWithProperty(app, "objectName").find(item => item.objectName === "datasets.choice" && item.visible);
            settle();
            return dialog !== undefined && dialog.opened;
        }, 3000, "The ordinary multi-file loader opens its dataset choice dialog");
        return dialog;
    }
    function askDatasetChoice() {
        openPage({page:AppState.Page.Experiment, group:"experiments"});
        pageControl("group.experiments").askDatasets(Session.project.currentExperiment, datasetInputs.files);
        return choice();
    }
    function check_dataset_defaults() {
        prepareDatasets();
        const dialog = askDatasetChoice();
        compare(dialog.asScan, datasetInputs.files.length > 5, "Separate experiments default through five files; a scan defaults above five");
        compare(dialog.copy, datasetInputs.files.length <= 20 && datasetInputs.bytes <= 50*1024*1024, "Copy defaults on only through twenty files and fifty MiB, including each exact boundary");
        const texts = Render.descendants(dialog.contentItem).filter(item => typeof item.text === "string").map(item => item.text);
        verify(texts.some(text => /Joint fit/.test(text) && /one experiment per file/.test(text)), "The separate choice names joint fitting and its one-experiment-per-file meaning");
        verify(texts.some(text => /Sequential fit/.test(text) && /template/.test(text) && /first/.test(text)), "The scan choice identifies its template and the initial single fit");
        const copy = Ui.find(dialog.contentItem, "datasets.copy");
        verify(copy !== null && copy.visible, "Copy or link remains available for either dataset organization");
        dialog.reject();
    }
    function check_dataset_separate() {
        const project = prepareDatasets();
        const selected = project.currentExperiment;
        const setup = parameters(selected);
        const reference = [];
        for (const file of datasetInputs.files) {
            project.currentExperimentIndex = 0;
            verify(project.duplicateExperiment(), "Each independent reference copies the selected experiment setup");
            verify(project.loadDataInto(project.currentExperiment, file), "Each reference uses the ordinary single-file data reader");
            reference.push(measured(project.currentExperiment));
        }
        for (let index = project.experiments.count-1; index > 0; --index) project.removeExperiment(index);
        project.currentExperimentIndex = 0;
        const before = {count:project.experiments.count, data:measured(selected), setup:parameters(selected)};
        verify(project.loadDatasets(selected, datasetInputs.files, false, true), "The separate route admits the independently authored files");
        compare(project.experiments.count, before.count + datasetInputs.files.length, "Separate loading adds exactly one experiment per file");
        compare(project.analysis.fittingMode, "joint", "Separate loading switches Analysis to joint automatically");
        for (let index = 0; index < datasetInputs.files.length; ++index) {
            project.currentExperimentIndex = before.count + index;
            compare(measured(project.currentExperiment), reference[index], "Each batch dataset equals its ordinary single-file load into a copied experiment");
            compare(parameters(project.currentExperiment), setup, "Every batch experiment retains the selected numerical setup");
            compare(project.currentExperiment.name, "sample" + index, "Every batch experiment is named after its independent input file");
        }
        project.undo();
        compare(project.experiments.count, before.count, "One Undo removes the entire separate-data batch");
        project.currentExperimentIndex = 0;
        compare(parameters(project.currentExperiment), before.setup, "Batch Undo preserves the selected template setup");
        compare(measured(project.currentExperiment), before.data, "Batch Undo preserves its previous measured data");
    }
    function check_dataset_scan() {
        const project = prepareDatasets();
        verify(project.loadDatasets(project.currentExperiment, datasetInputs.files, true, false), "A scan may link its independently authored files outside the project");
        tryCompare(project, "scan", true, 5000, "The scan choice creates a declared scan");
        compare(project.analysis.fittingMode, "single", "The scan starts in single mode until the user chooses sequential");
        compare(project.experiments.count, datasetInputs.files.length, "The Experiments table lists every scan dataset");
        for (let index = 0; index < datasetInputs.files.length; ++index) {
            selectDataset(project, index);
            compare(measured(project.currentExperiment), datasetInputs.rows[index], "Every scan row retains its independently specified x, y and uncertainty");
        }
        selectDataset(project, project.templateIndex);
        verify(Session.save(), "A linked scan saves through the ordinary project path");
        const folder = project.path;
        verify(folder !== undefined && folder !== "", "The linked project exposes its saved ordinary folder");
    }
    function check_dataset_template() {
        const project = prepareDatasets();
        verify(project.loadDatasets(project.currentExperiment, datasetInputs.files, true, false), "The template witness starts with an external linked scan");
        tryCompare(project, "scan", true, 5000, "The template scan is published before its rows are used");
        selectDataset(project, project.templateIndex);
        const old = project.templateIndex;
        const next = old === 0 ? 1 : 0;
        selectDataset(project, next);
        compare(measured(project.currentExperiment), datasetInputs.rows[next], "The new template starts from the requested independent dataset after its view is ready");
        verify(project.useAsTemplate(next), "A different dataset can become the initial single-fit template");
        compare(project.templateIndex, next, "Use as template moves the mark to the chosen dataset");
        compare(project.analysis.fittingMode, "single", "Changing the template never enables sequential mode implicitly");
        project.undo();
        compare(project.templateIndex, old, "One Undo restores the original scan template");
    }
    function check_linked_prepare() {
        const project = prepareDatasets();
        verify(project.loadDatasets(project.currentExperiment, datasetInputs.files, true, false), "The reopen witness links a folder outside the project");
        tryCompare(project, "scan", true, 5000, "The linked scan is fully published before it is saved");
        selectDataset(project, project.templateIndex);
        project.includeDataOnSave = "linked";
        compare(project.includeDataOnSave, "linked", "The relocation witness explicitly retains external links instead of relying on the small-data default");
        verify(Session.save(), "The linked project persists through the ordinary save path: " + Session.lastError);
        verify(SettingsProof.write(mailbox, "linked-project.json", JSON.stringify({path:project.path})), "The external relocation actor receives the actual saved project path");
        Session.closeProject();
    }
    function check_linked_reopen() {
        const saved = JSON.parse(SettingsProof.fileObservation(mailbox, "linked-project.json").text);
        verify(Session.openProject("file://" + saved.path), "A saved project opens while its linked folder is missing");
        verify(Session.project.missingDataFolder !== "", "The missing linked folder is marked without preventing project opening");
        verify(Session.project.locateDataFolder(datasetInputs.moved), "Locate folder restores the externally moved dataset folder");
        compare(Session.project.missingDataFolder, "", "Locate folder clears the missing-data marker");
        selectDataset(Session.project, 0);
        compare(measured(Session.project.currentExperiment), datasetInputs.rows[0], "Relocation preserves every independently authored measured value");
    }
    function check_included_prepare() {
        const project = prepareDatasets();
        verify(project.loadDatasets(project.currentExperiment, datasetInputs.files, true, false), "The include-data roundtrip starts with the same external scan inputs");
        tryCompare(project, "scan", true, 5000, "The include-data scan is published before its explicit save choice");
        selectDataset(project, project.templateIndex);
        project.includeDataOnSave = "all";
        compare(project.includeDataOnSave, "all", "The include-data witness explicitly chooses Include all");
        verify(Session.save(), "Include all saves an independent copy through the ordinary save path: " + Session.lastError);
        verify(SettingsProof.write(mailbox, "included-project.json", JSON.stringify({path:project.path})), "The include-data actor retains the actual saved project folder");
        Session.closeProject();
    }
    function check_included_reopen() {
        const saved = JSON.parse(SettingsProof.fileObservation(mailbox, "included-project.json").text);
        verify(Session.openProject("file://" + saved.path), "Included data reopen after the original external folder has moved");
        compare(Session.project.missingDataFolder, "", "Include all leaves no dependency on the removed external folder");
        for (let index = 0; index < datasetInputs.files.length; ++index) {
            selectDataset(Session.project, index);
            compare(measured(Session.project.currentExperiment), datasetInputs.rows[index], "Every included dataset preserves every independently authored x, y and uncertainty");
        }
    }
    function check_save_policy() {
        const project = prepareDatasets();
        verify(project.loadDatasets(project.currentExperiment, datasetInputs.files, true, false), "The save policy starts with external linked datasets");
        tryCompare(project, "scan", true, 5000, "The linked scan is published before its save policy is chosen");
        AppState.open(AppState.Page.Project);
        settle();
        const labels = Probe.objectsWithProperty(app, "text");
        const label = labels.find(item => String(item.text).replace(/<[^>]*>/g, "").trim() === "Include data on save");
        verify(label !== undefined, "The project exposes its Include data on save setting");
        let selector;
        for (let parent = label.parent, depth = 0; parent && depth < 3 && !selector; parent = parent.parent, ++depth)
            selector = Render.descendants(parent).find(item => typeof item.textAt === "function" && item.count >= 3);
        verify(selector !== undefined, "The include-data setting offers its three choices through a real selector");
        const options = Array.from({length:selector.count}, (_, index) => selector.textAt(index).toLowerCase());
        for (const required of ["all", "linked only", "ask"])
            verify(options.some(option => option === required), "The save policy offers all, linked only and ask");
        const small = datasetInputs.files.length <= 20 && datasetInputs.bytes <= 50*1024*1024;
        compare(selector.currentText.toLowerCase(), small ? "all" : "linked only", "Include-data defaults obey the same twenty-file and fifty-MiB boundaries as Copy");
        if (!datasetInputs.warning) return;
        const all = options.indexOf("all");
        selector.currentIndex = all;
        selector.activated(all);
        verify(Session.save(), "The ordinary save action starts the chosen all-data save or its warning");
        const dialogs = Probe.objectsWithProperty(app, "text");
        const warning = dialogs.find(item => String(item.text).includes("Keep the data linked instead?"));
        compare(warning !== undefined, datasetInputs.bytes > 100*1024*1024, "Save warns only above the hundred-MiB threshold");
        if (warning !== undefined) {
            const actions = Probe.objectsWithProperty(app, "text").filter(item => typeof item.clicked === "function" && Ui.exposed(item));
            for (const text of ["Keep linked", "Copy anyway", "Cancel"])
                verify(actions.some(item => item.text === text), "The large-save warning provides every owner-declared decision");
            click(actions.find(item => item.text === "Cancel"));
        }
    }

}
