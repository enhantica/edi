// SPDX-License-Identifier: BSD-3-Clause
// The Application tutorial of pd-neut-cwl_lmo-echidna, written by tools/docs/app_tutorial_plan.py.
(function () {
    const EXAMPLE_ID = "pd-neut-cwl_lmo-echidna";
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
   "fill:createProject.name=pd-neut-cwl_lmo-echidna",
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
  "description": "Find the structure lmo in the EasyDiffraction collection",
  "actions": [
   "appBar.tab.structure",
   "sideBar.tab.basic",
   "expand:group.structures",
   "structures.load",
   "structures.load.web",
   "onlineLoad.source",
   "choose:EasyDiffraction Database",
   "fill:onlineLoad.field.id=pd-neut-cwl_lmo-echidna-lmo",
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
  "description": "Load the structure lmo",
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
  "description": "Find the experiment echidna in the EasyDiffraction collection",
  "actions": [
   "appBar.tab.experiment",
   "sideBar.tab.basic",
   "expand:group.experiments",
   "experiments.load",
   "experiments.load.experimentWeb",
   "fill:onlineLoad.field.id=pd-neut-cwl_lmo-echidna-echidna",
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
  "description": "Load the experiment echidna",
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
  "id": "relations-start",
  "page": "analysis",
  "description": "Add the relations the project starts with",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.extras",
   "reveal:group.alias",
   "expand:group.alias",
   "aliases.append",
   "show:aliases.list:0:begin",
   "reveal:alias.id.0",
   "fill:alias.id.0=biso_Li1",
   "key:Return",
   "alias.parameter.0",
   "type:lmo.atom_site.Li1.adp_iso",
   "key:Return",
   "aliases.append",
   "show:aliases.list:1:begin",
   "reveal:alias.id.1",
   "fill:alias.id.1=biso_Li2",
   "key:Return",
   "alias.parameter.1",
   "type:lmo.atom_site.Li2.adp_iso",
   "key:Return",
   "aliases.append",
   "show:aliases.list:2:begin",
   "reveal:alias.id.2",
   "fill:alias.id.2=biso_Ni1",
   "key:Return",
   "alias.parameter.2",
   "type:lmo.atom_site.Ni1.adp_iso",
   "key:Return",
   "aliases.append",
   "show:aliases.list:3:begin",
   "reveal:alias.id.3",
   "fill:alias.id.3=biso_Ni2",
   "key:Return",
   "alias.parameter.3",
   "type:lmo.atom_site.Ni2.adp_iso",
   "key:Return",
   "aliases.append",
   "show:aliases.list:4:begin",
   "reveal:alias.id.4",
   "fill:alias.id.4=occ_Li1",
   "key:Return",
   "alias.parameter.4",
   "type:lmo.atom_site.Li1.occupancy",
   "key:Return",
   "aliases.append",
   "show:aliases.list:5:begin",
   "reveal:alias.id.5",
   "fill:alias.id.5=occ_Li2",
   "key:Return",
   "alias.parameter.5",
   "type:lmo.atom_site.Li2.occupancy",
   "key:Return",
   "aliases.append",
   "show:aliases.list:6:begin",
   "reveal:alias.id.6",
   "fill:alias.id.6=occ_Ni1",
   "key:Return",
   "alias.parameter.6",
   "type:lmo.atom_site.Ni1.occupancy",
   "key:Return",
   "aliases.append",
   "show:aliases.list:7:begin",
   "reveal:alias.id.7",
   "fill:alias.id.7=occ_Ni2",
   "key:Return",
   "alias.parameter.7",
   "type:lmo.atom_site.Ni2.occupancy",
   "key:Return",
   "reveal:group.constraint",
   "expand:group.constraint",
   "constraints.append",
   "reveal:constraint.id.0",
   "fill:constraint.id.0=1",
   "key:Return",
   "fill:constraint.expression.0=biso_Ni1 = biso_Li1",
   "key:Return",
   "constraints.append",
   "reveal:constraint.id.1",
   "fill:constraint.id.1=2",
   "key:Return",
   "fill:constraint.expression.1=biso_Li2 = biso_Ni2",
   "key:Return",
   "constraints.append",
   "show:constraints.list:2:begin",
   "reveal:constraint.id.2",
   "fill:constraint.id.2=3",
   "key:Return",
   "fill:constraint.expression.2=occ_Ni1 = 1 - occ_Li1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:3:begin",
   "reveal:constraint.id.3",
   "fill:constraint.id.3=4",
   "key:Return",
   "fill:constraint.expression.3=occ_Li2 = 1 - occ_Li1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:4:begin",
   "reveal:constraint.id.4",
   "fill:constraint.id.4=5",
   "key:Return",
   "fill:constraint.expression.4=occ_Ni2 = occ_Li1",
   "key:Return"
  ],
  "highlights": [
   "group.constraint"
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
  "description": "Scale, 2θ zero and cell",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Instrument",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=offset",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Linked structures",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
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
  "description": "Fit: Scale, 2θ zero and cell",
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
  "description": "Sample displacement and transparency",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Instrument",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=calib",
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
  "description": "Fit: Sample displacement and transparency",
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
  "id": "stage-3-fit",
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
  "id": "stage-4-free",
  "page": "analysis",
  "description": "Peak widths",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Peak broadening",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=lorentz_x",
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
  "id": "stage-5-free",
  "page": "analysis",
  "description": "Oxygen position",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Atomic coordinates",
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
  "description": "Fit: Oxygen position",
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
  "description": "Displacements",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Atomic displacement",
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
  "id": "stage-7-free",
  "page": "analysis",
  "description": "Li/Ni mixing",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Atomic occupancies",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=[Li1]",
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
  "id": "stage-7-fit",
  "page": "analysis",
  "description": "Fit: Li/Ni mixing",
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
