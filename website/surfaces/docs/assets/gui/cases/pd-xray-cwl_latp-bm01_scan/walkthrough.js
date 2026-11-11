// SPDX-License-Identifier: BSD-3-Clause
// The Application tutorial of pd-xray-cwl_latp-bm01_scan, written by tools/docs/app_tutorial_plan.py.
(function () {
    const EXAMPLE_ID = "pd-xray-cwl_latp-bm01_scan";
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
  "id": "example-open",
  "page": "project",
  "description": "Open the example from Examples",
  "actions": [
   "home.start",
   "sideBar.tab.basic",
   "reveal:group.examples",
   "expand:group.examples",
   "reveal:examples.search",
   "fill:examples.search=pd-xray-cwl_latp-bm01_scan",
   "reveal:examples.open.pd-xray-cwl_latp-bm01_scan",
   "examples.open.pd-xray-cwl_latp-bm01_scan",
   "pin-time:01 Jan 2026 12:00:00"
  ],
  "highlights": [
   "workflow.project.mainContent"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "fitting-mode-single",
  "page": "analysis",
  "description": "Fit the template pattern alone first",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.extras",
   "reveal:group.fitting_mode",
   "expand:group.fitting_mode",
   "fittingMode.type",
   "choose-token:fittingMode.type=single"
  ],
  "highlights": [
   "group.fitting_mode"
  ],
  "sidebar": "Extra",
  "capture": true,
  "fitPhase": "setup"
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
  "description": "Scales, 2θ zero and cells",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:bm01",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Instrument",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=calib",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:bm01",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Linked structures",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:alpo4_c2221",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Cell",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:alpo4_p63mc",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Cell",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:latp",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Cell",
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
  "description": "Fit: Scales, 2θ zero and cells",
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
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:bm01",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Peak broadening",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:bm01",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Peak mixing",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=eta_0",
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
  "description": "Peak asymmetry",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:bm01",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Peak asymmetry",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=a1",
   "parameters.freeHeader",
   "parameters.freeHeader.fixed",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=b1",
   "parameters.freeHeader",
   "parameters.freeHeader.fixed",
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
  "description": "Fit: Peak asymmetry",
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
  "description": "LATP positions",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:latp",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Atomic coordinates",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=[Li3]",
   "parameters.freeHeader",
   "parameters.freeHeader.fixed",
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
  "description": "Fit: LATP positions",
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
  "description": "LATP displacements",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:latp",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Atomic displacement",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=[L",
   "parameters.freeHeader",
   "parameters.freeHeader.fixed",
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
  "description": "Fit: LATP displacements",
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
  "id": "scan-mode",
  "page": "analysis",
  "description": "Back to the sequential mode",
  "actions": [
   "sideBar.tab.extras",
   "reveal:group.fitting_mode",
   "expand:group.fitting_mode",
   "fittingMode.type",
   "choose-token:fittingMode.type=sequential"
  ],
  "highlights": [
   "group.fitting_mode"
  ],
  "sidebar": "Extra",
  "capture": true,
  "fitPhase": "setup"
 },
 {
  "id": "scan-fit",
  "page": "analysis",
  "description": "Fit the scan",
  "actions": [
   "sideBar.tab.basic",
   "statusBar.fit.button",
   "wait-fit",
   "close-fit-results"
  ],
  "highlights": [
   "workflow.analysis.mainContent"
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
