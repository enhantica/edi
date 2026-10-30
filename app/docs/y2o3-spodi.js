// SPDX-License-Identifier: BSD-3-Clause
// Evaluated by --docs-capture; capture contains this run's isolated input/workspace paths.
(function () {
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
        ["project.create", "fill:createProject.name=pd-neut-cwl_y2o3-spodi",
         "fill:createProject.title=Y2O3 on SPODI", "fill:createProject.authors=EasyDiffraction documentation",
         "fill:createProject.description=Constant-wavelength neutron powder diffraction from SPODI at FRM II.",
         "fill:createProject.location=" + capture.projectDirectory],
        ["createProject.name", "createProject.title", "createProject.description", "createProject.location"]);
    shot("04-project-created", "project", "Create the project", ["createProject.accept", "pin-time:2026-01-01T12:00:00"],
        ["workflow.project.mainContent", "workflow.project.manualSidebar"]);
    tabs("05-project", "project", "Project details and controls");
    shot("06-structure-import", "structure", "Load the Y2O3 structure into the empty project",
        ["appBar.tab.structure", "sideBar.tab.basic", "expand:group.structures"],
        ["structures.load", "workflow.structure.mainContent"]);
    shot("07-structure-loaded", "structure", "Inspect the imported crystal structure",
        ["import-structure:" + capture.structureFile],
        ["structures.list", "workflow.structure.mainContent"]);
    tabs("08-structure", "structure", "Crystal structure");
    shot("09-experiment-import", "experiment", "Load the SPODI experiment and measured intensities",
        ["appBar.tab.experiment", "sideBar.tab.basic", "expand:group.experiments"],
        ["experiments.load", "workflow.experiment.mainContent"]);
    shot("10-experiment-loaded", "experiment", "Compare the measured pattern with the initial calculation",
        ["import-experiment:" + capture.experimentFile],
        ["workflow.experiment.mainContent", "workflow.experiment.manualSidebar"]);
    tabs("11-experiment", "experiment", "SPODI experiment");
    shot("12-run-refinement", "analysis", "Refine the model and close the results dialog",
        ["appBar.tab.analysis", "sideBar.tab.basic", "statusBar.fit.button",
         "wait-fit", "close-fit-results"], [], "", false);
    tabs("13-analysis", "analysis", "Completed Rietveld refinement");
    tabs("14-report", "report", "Review the fitted structure and report");
    shot("15-project-examples", "project", "Browse the built-in examples",
        ["appBar.tab.project", "sideBar.tab.basic", "group.getStarted", "expand:group.examples"],
        ["group.examples"]);
    return {schema: 1, example: "pd-neut-cwl_y2o3-spodi", steps: steps};
})();
