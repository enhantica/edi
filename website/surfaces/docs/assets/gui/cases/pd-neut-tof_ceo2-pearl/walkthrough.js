// SPDX-License-Identifier: BSD-3-Clause
// The Application tutorial of pd-neut-tof_ceo2-pearl, written by tools/docs/app_tutorial_plan.py.
(function () {
    const EXAMPLE_ID = "pd-neut-tof_ceo2-pearl";
    const STEPS = [
 {
  "id": "home",
  "page": "home",
  "description": "Start a new analysis",
  "actions": [
   "platform:light",
   "theme:light"
  ],
  "highlights": [
   "home.start"
  ],
  "sidebar": "",
  "capture": false
 },
 {
  "id": "project-details",
  "page": "project",
  "description": "Enter the project details",
  "actions": [
   "home.start",
   "project.create",
   "fill:createProject.name=pd-neut-tof_ceo2-pearl",
   "fill:createProject.title=@title",
   "fill:createProject.location=@projectDirectory"
  ],
  "highlights": [
   "createProject.name",
   "createProject.title",
   "createProject.location"
  ],
  "sidebar": "",
  "capture": false
 },
 {
  "id": "project-created",
  "page": "project",
  "description": "Create the project",
  "actions": [
   "createProject.accept",
   "pin-time:01 Jan 2026 12:00:00"
  ],
  "highlights": [
   "workflow.project.mainContent"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "structure-web-0",
  "page": "structure",
  "description": "Find the structure ceo2 in the EasyDiffraction collection",
  "actions": [
   "appBar.tab.structure",
   "sideBar.tab.basic",
   "expand:group.structures",
   "structures.load",
   "structures.load.web",
   "onlineLoad.source",
   "choose:EasyDiffraction Database",
   "fill:onlineLoad.field.id=pd-neut-tof_ceo2-pearl-ceo2",
   "onlineLoad.search",
   "wait-online"
  ],
  "highlights": [
   "onlineLoad.field.id",
   "onlineLoad.results"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "structure-loaded-0",
  "page": "structure",
  "description": "Load the structure ceo2",
  "actions": [
   "onlineLoad.row.0",
   "wait-online"
  ],
  "highlights": [
   "structures.list",
   "workflow.structure.mainContent"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "experiment-web-0",
  "page": "experiment",
  "description": "Find the experiment pearl in the EasyDiffraction collection",
  "actions": [
   "appBar.tab.experiment",
   "sideBar.tab.basic",
   "expand:group.experiments",
   "experiments.load",
   "experiments.load.experimentWeb",
   "fill:onlineLoad.field.id=pd-neut-tof_ceo2-pearl-pearl",
   "onlineLoad.search",
   "wait-online"
  ],
  "highlights": [
   "onlineLoad.field.id",
   "onlineLoad.results"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "experiment-loaded-0",
  "page": "experiment",
  "description": "Load the experiment pearl",
  "actions": [
   "onlineLoad.row.0",
   "wait-online"
  ],
  "highlights": [
   "experiments.list",
   "workflow.experiment.mainContent"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "nothing-free",
  "page": "analysis",
  "description": "Start with every parameter fixed",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "parameters.clearFilters",
   "parameters.freeHeader",
   "parameters.freeHeader.fixed"
  ],
  "highlights": [
   "group.parameters",
   "parameters.freeHeader"
  ],
  "sidebar": "Main",
  "capture": true,
  "fitPhase": "setup"
 },
 {
  "id": "stage-1-free",
  "page": "analysis",
  "description": "Scale and time-of-flight calibration",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiment.instrument.calib_d_to_tof_linear",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiment.instrument.calib_d_to_tof_offset",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiment.instrument.calib_d_to_tof_quadratic",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiment.linked_structures[ceo2].scale",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters"
  ],
  "highlights": [
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": false,
  "fitPhase": "setup"
 },
 {
  "id": "stage-1-fit",
  "page": "analysis",
  "description": "Fit: Scale and time-of-flight calibration",
  "actions": [
   "statusBar.fit.button",
   "wait-fit",
   "close-fit-results"
  ],
  "highlights": [
   "workflow.analysis.mainContent",
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": true
 },
 {
  "id": "stage-2-free",
  "page": "analysis",
  "description": "Background",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Background",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters"
  ],
  "highlights": [
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": false,
  "fitPhase": "setup"
 },
 {
  "id": "stage-2-fit",
  "page": "analysis",
  "description": "Fit: Background",
  "actions": [
   "statusBar.fit.button",
   "wait-fit",
   "close-fit-results"
  ],
  "highlights": [
   "workflow.analysis.mainContent",
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": true
 },
 {
  "id": "stage-3-free",
  "page": "analysis",
  "description": "Peak widths",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiment.peak.broad_gauss_sigma_1",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiment.peak.broad_gauss_sigma_2",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiment.peak.broad_lorentz_gamma_1",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters"
  ],
  "highlights": [
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": false,
  "fitPhase": "setup"
 },
 {
  "id": "stage-3-fit",
  "page": "analysis",
  "description": "Fit: Peak widths",
  "actions": [
   "statusBar.fit.button",
   "wait-fit",
   "close-fit-results"
  ],
  "highlights": [
   "workflow.analysis.mainContent",
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": true
 },
 {
  "id": "stage-4-free",
  "page": "analysis",
  "description": "Rise and decay",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiment.peak.decay_beta_0",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiment.peak.decay_beta_1",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiment.peak.rise_alpha_1",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters"
  ],
  "highlights": [
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": false,
  "fitPhase": "setup"
 },
 {
  "id": "stage-4-fit",
  "page": "analysis",
  "description": "Fit: Rise and decay",
  "actions": [
   "statusBar.fit.button",
   "wait-fit",
   "close-fit-results"
  ],
  "highlights": [
   "workflow.analysis.mainContent",
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": true
 },
 {
  "id": "stage-5-free",
  "page": "analysis",
  "description": "Displacements",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=structure.atom_sites[Ce].adp_iso",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=structure.atom_sites[O].adp_iso",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters"
  ],
  "highlights": [
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": false,
  "fitPhase": "setup"
 },
 {
  "id": "stage-5-fit",
  "page": "analysis",
  "description": "Fit: Displacements",
  "actions": [
   "statusBar.fit.button",
   "wait-fit",
   "close-fit-results"
  ],
  "highlights": [
   "workflow.analysis.mainContent",
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": true
 },
 {
  "id": "stage-6-free",
  "page": "analysis",
  "description": "Absorption",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiment.absorption.abscor1",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters"
  ],
  "highlights": [
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": false,
  "fitPhase": "setup"
 },
 {
  "id": "stage-6-fit",
  "page": "analysis",
  "description": "Fit: Absorption",
  "actions": [
   "statusBar.fit.button",
   "wait-fit",
   "close-fit-results"
  ],
  "highlights": [
   "workflow.analysis.mainContent",
   "group.parameters"
  ],
  "sidebar": "Main",
  "capture": true
 },
 {
  "id": "correlations",
  "page": "analysis",
  "description": "Inspect the correlations",
  "actions": [
   "mainArea.tab.correlations"
  ],
  "highlights": [
   "workflow.analysis.mainContent"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "report",
  "page": "report",
  "description": "Review the report",
  "actions": [
   "mainArea.tab.pattern",
   "appBar.tab.report",
   "sideBar.tab.basic"
  ],
  "highlights": [
   "workflow.report.mainContent"
  ],
  "sidebar": "Main",
  "capture": true
 }
];
    return {schema: 2, workflow: "tutorial", example: EXAMPLE_ID, build: function (capture) {
        return STEPS.map(function (step) {
            const actions = step.actions.map(function (action) {
                return action.replace("@title", capture.title)
                    .replace("@projectDirectory", capture.projectDirectory);
            });
            return Object.assign({}, step, {actions: actions});
        });
    }};
})();
