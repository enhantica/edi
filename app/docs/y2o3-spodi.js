// SPDX-License-Identifier: BSD-3-Clause
// Evaluated by --docs-capture; capture contains this run's isolated input/workspace paths.
(function () {
    const EXAMPLE_ID = "pd-neut-cwl_y2o3-spodi";
    return {schema: 2, example: EXAMPLE_ID, build: function (capture) {
    const steps = [];
    function shot(id, page, description, actions, highlights, sidebar, captureImage) {
        steps.push({id: id, page: page, description: description, actions: actions,
            highlights: highlights || [], sidebar: sidebar || "", capture: captureImage !== false});
    }
    function tabs(prefix, page, description) {
        const modes = [["basic", "Main"], ["extras", "Extra"], ["text", "Text"], ["settings", "Settings"]];
        modes.forEach(function (mode) {
            shot(prefix + "-" + mode[0], page, description + " — " + mode[1],
                ["appBar.tab." + page, "if-enabled:sideBar.tab." + mode[0], "sideBar.tab." + mode[0]],
                ["appBar", "workflow." + page + ".mainContent", "workflow." + page + ".manualSidebar", "statusBar"],
                mode[1]);
        });
    }
    shot("01-home", "home", "Start a new diffraction analysis", ["platform:light", "theme:light"],
        ["appBar", "workflow.home.mainContent", "home.start"]);
    shot("02-project-start", "project", "Choose Create a new project", ["home.start"],
        ["project.create", "group.getStarted"]);
    shot("03-project-details", "project", "Enter the project details and choose its location",
        ["project.create", "fill:createProject.name=" + capture.name,
         "fill:createProject.title=" + capture.title, "fill:createProject.authors=EasyDiffraction documentation",
         "fill:createProject.description=" + capture.description,
         "fill:createProject.location=" + capture.projectDirectory],
        ["createProject.name", "createProject.title", "createProject.description", "createProject.location"]);
    shot("04-project-created", "project", "Create the project", ["createProject.accept", "pin-time:2026-01-01T12:00:00"],
        ["workflow.project.mainContent", "workflow.project.manualSidebar"]);
    tabs("05-project", "project", "Project details and controls");
    shot("06-structure-import", "structure", "Load the structure into the empty project",
        ["appBar.tab.structure", "sideBar.tab.basic", "expand:group.structures"],
        ["structures.load", "workflow.structure.mainContent"]);
    shot("07-structure-loaded", "structure", "Inspect the imported crystal structure",
        ["import-structure:" + capture.structureFile],
        ["structures.list", "workflow.structure.mainContent"]);
    tabs("08-structure", "structure", "Crystal structure");
    shot("09-experiment-import", "experiment", "Load the experiment and measured intensities",
        ["appBar.tab.experiment", "sideBar.tab.basic", "expand:group.experiments"],
        ["experiments.load", "workflow.experiment.mainContent"]);
    shot("10-experiment-loaded", "experiment", "Compare the measured pattern with the initial calculation",
        ["import-experiment:" + capture.experimentFile],
        ["workflow.experiment.mainContent", "workflow.experiment.manualSidebar"]);
    tabs("11-experiment", "experiment", "Experiment and measured data");
    shot("12-run-refinement", "analysis", "Refine the model and close the results dialog",
        ["appBar.tab.analysis", "sideBar.tab.basic", "statusBar.fit.button",
         "wait-fit", "close-fit-results"], [], "", false);
    tabs("13-analysis", "analysis", "Completed Rietveld refinement");
    tabs("14-report", "report", "Review the fitted structure and report");
    shot("15-project-examples", "project", "Browse the built-in examples",
        ["appBar.tab.project", "sideBar.tab.basic", "group.getStarted", "expand:group.examples"],
        ["group.examples"]);
    function panel(id, page, mode, group, description, targets) {
        const actions = ["appBar.tab." + page, "sideBar.tab." + mode,
            "reveal:" + group, "expand:" + group, "reveal:" + targets[0]];
        shot(id, page, description, actions, targets);
    }
    shot("guide-project-actions", "project", "Open or save the current project",
        ["appBar.tab.project", "sideBar.tab.basic", "reveal:group.getStarted", "expand:group.getStarted"],
        ["project.open", "project.saveAs"]);
    shot("guide-project-open", "project", "Choose a project folder or archive",
        ["appBar.button.save", "project.open"], ["project.openChoice"]);
    shot("guide-project-save", "project", "Choose a save format or save a copy",
        ["key:Escape", "project.saveAs"], ["project.saveChoice"]);
    shot("guide-project-recent", "project", "Find recent projects",
        ["key:Escape", "reveal:group.recentProjects", "expand:group.recentProjects"], ["group.recentProjects"]);
    panel("guide-structure-symmetry", "structure", "basic", "group.space_group", "Choose the crystal symmetry and setting", ["spaceGroup.itNumber", "spaceGroup.nameHM"]);
    panel("guide-structure-cell", "structure", "basic", "group.cell", "Inspect the unit-cell parameters", ["cell.length_a", "cell.length_b", "cell.length_c"]);
    panel("guide-structure-atoms", "structure", "basic", "group.atom_site", "Inspect atom sites, coordinates and occupancies", ["atomSites.list"]);
    panel("guide-structure-displacement", "structure", "basic", "group.atom_site_aniso", "Inspect anisotropic atomic displacement", ["group.atom_site_aniso"]);
    panel("guide-structure-create", "structure", "basic", "group.structures", "Load, create or duplicate a structure", ["structures.load", "structures.create", "structures.duplicate"]);
    panel("guide-experiment-data", "experiment", "basic", "group.experiments", "Select an experiment or load measured data", ["experiments.list", "experiments.loadData.0"]);
    panel("guide-experiment-create", "experiment", "basic", "group.experiments", "Load or create an experiment", ["experiments.load", "experiments.create"]);
    panel("guide-experiment-instrument", "experiment", "basic", "group.instrument", "Inspect instrument parameters", ["group.instrument"]);
    panel("guide-experiment-profile", "experiment", "basic", "group.peak", "Choose and inspect a peak profile", ["group.peak"]);
    panel("guide-experiment-background", "experiment", "basic", "group.background", "Inspect the background representation and values", ["background.type", "background.rows"]);
    panel("guide-experiment-exclusions", "experiment", "basic", "group.excluded_region", "Inspect excluded fitting intervals", ["excludedRegions.list"]);
    panel("guide-experiment-links", "experiment", "basic", "group.linked_structure", "Link structures and inspect phase scales", ["linkedStructure.list"]);
    panel("guide-experiment-estimation", "experiment", "extras", "group.background_estimate", "Inspect background estimation settings", ["group.background_estimate"]);
    panel("guide-analysis-modes", "analysis", "extras", "group.fitting_mode", "Choose a fitting mode supported by the project", ["fittingMode.type"]);
    panel("guide-analysis-minimizer", "analysis", "extras", "group.minimizer", "Inspect minimizer settings", ["group.minimizer"]);
    panel("guide-analysis-constraints", "analysis", "extras", "group.constraint", "Inspect parameter constraints", ["group.constraint"]);
    panel("guide-report-contents", "report", "basic", "group.reportContents", "Choose which sections appear in the report", ["group.reportContents"]);
    panel("guide-report-export", "report", "basic", "group.reportExport", "Choose report formats and export", ["report.writesHtml", "report.writesPdf", "report.writesCif", "report.save"]);
    shot("guide-report-saved", "report", "Review the saved report status", ["report.save"], ["group.reportExport"]);
    return steps;
    }};
})();
