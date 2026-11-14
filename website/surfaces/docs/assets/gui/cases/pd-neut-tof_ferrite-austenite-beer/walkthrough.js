// SPDX-License-Identifier: BSD-3-Clause
// The Application tutorial of pd-neut-tof_ferrite-austenite-beer, written by tools/docs/app_tutorial_plan.py.
(function () {
    const EXAMPLE_ID = "pd-neut-tof_ferrite-austenite-beer";
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
   "fill:createProject.name=ferrite-austenite-beer",
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
  "description": "Find the structure",
  "actions": [
   "appBar.tab.structure",
   "sideBar.tab.basic",
   "expand:group.structures",
   "structures.load",
   "structures.load.web",
   "onlineLoad.source",
   "choose:EasyDiffraction Database",
   "fill:onlineLoad.field.id=pd-neut-tof_ferrite-austenite-beer-ferrite",
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
  "description": "Load the structure ferrite",
  "actions": [
   "onlineLoad.row.0",
   "wait-online"
  ],
  "highlights": [
   "structures.list",
   "workflow.structure.mainContent"
  ],
  "sidebar": "",
  "capture": false
 },
 {
  "id": "structure-web-1",
  "page": "structure",
  "description": "Find the structure",
  "actions": [
   "appBar.tab.structure",
   "sideBar.tab.basic",
   "expand:group.structures",
   "structures.load",
   "structures.load.web",
   "onlineLoad.source",
   "choose:EasyDiffraction Database",
   "fill:onlineLoad.field.id=pd-neut-tof_ferrite-austenite-beer-austenite",
   "onlineLoad.search",
   "wait-online"
  ],
  "highlights": [
   "onlineLoad.field.id",
   "onlineLoad.results"
  ],
  "sidebar": "",
  "capture": false
 },
 {
  "id": "structure-loaded-1",
  "page": "structure",
  "description": "Load the structure austenite",
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
  "description": "Find the experiment",
  "actions": [
   "appBar.tab.experiment",
   "sideBar.tab.basic",
   "expand:group.experiments",
   "experiments.load",
   "experiments.load.experimentWeb",
   "fill:onlineLoad.field.id=pd-neut-tof_ferrite-austenite-beer-expt_s2",
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
  "description": "Load the experiment expt_s2",
  "actions": [
   "onlineLoad.row.0",
   "wait-online"
  ],
  "highlights": [
   "experiments.list",
   "workflow.experiment.mainContent"
  ],
  "sidebar": "",
  "capture": false
 },
 {
  "id": "experiment-web-1",
  "page": "experiment",
  "description": "Find the experiment",
  "actions": [
   "appBar.tab.experiment",
   "sideBar.tab.basic",
   "expand:group.experiments",
   "experiments.load",
   "experiments.load.experimentWeb",
   "fill:onlineLoad.field.id=pd-neut-tof_ferrite-austenite-beer-expt_n2",
   "onlineLoad.search",
   "wait-online"
  ],
  "highlights": [
   "onlineLoad.field.id",
   "onlineLoad.results"
  ],
  "sidebar": "",
  "capture": false
 },
 {
  "id": "experiment-loaded-1",
  "page": "experiment",
  "description": "Load the experiment expt_n2",
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
  "id": "relations-start",
  "page": "analysis",
  "description": "Add the relations",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.extras",
   "reveal:group.alias",
   "expand:group.alias",
   "aliases.append",
   "show:aliases.list:0:begin",
   "reveal:alias.id.0",
   "fill:alias.id.0=biso_ferrite",
   "key:Return",
   "alias.parameter.0",
   "type:ferrite.atom_site.Fe.adp_iso",
   "key:Return",
   "aliases.append",
   "show:aliases.list:1:begin",
   "reveal:alias.id.1",
   "fill:alias.id.1=biso_austenite",
   "key:Return",
   "alias.parameter.1",
   "type:austenite.atom_site.Fe.adp_iso",
   "key:Return",
   "aliases.append",
   "show:aliases.list:2:begin",
   "reveal:alias.id.2",
   "fill:alias.id.2=s2_ferrite_scale",
   "key:Return",
   "alias.parameter.2",
   "type:expt_s2.linked_structure.ferrite.scale",
   "key:Return",
   "aliases.append",
   "show:aliases.list:3:begin",
   "reveal:alias.id.3",
   "fill:alias.id.3=s2_austenite_scale",
   "key:Return",
   "alias.parameter.3",
   "type:expt_s2.linked_structure.austenite.scale",
   "key:Return",
   "aliases.append",
   "show:aliases.list:4:begin",
   "reveal:alias.id.4",
   "fill:alias.id.4=n2_ferrite_scale",
   "key:Return",
   "alias.parameter.4",
   "type:expt_n2.linked_structure.ferrite.scale",
   "key:Return",
   "aliases.append",
   "show:aliases.list:5:begin",
   "reveal:alias.id.5",
   "fill:alias.id.5=n2_austenite_scale",
   "key:Return",
   "alias.parameter.5",
   "type:expt_n2.linked_structure.austenite.scale",
   "key:Return",
   "reveal:group.constraint",
   "expand:group.constraint",
   "constraints.append",
   "reveal:constraint.id.0",
   "fill:constraint.id.0=1",
   "key:Return",
   "fill:constraint.expression.0=biso_austenite = biso_ferrite",
   "key:Return",
   "constraints.append",
   "reveal:constraint.id.1",
   "fill:constraint.id.1=2",
   "key:Return",
   "fill:constraint.expression.1=n2_ferrite_scale = s2_ferrite_scale",
   "key:Return",
   "constraints.append",
   "show:constraints.list:2:begin",
   "reveal:constraint.id.2",
   "fill:constraint.id.2=3",
   "key:Return",
   "fill:constraint.expression.2=n2_austenite_scale = s2_austenite_scale",
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
  "id": "joint-weights",
  "page": "analysis",
  "description": "Weigh the experiments",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.extras",
   "reveal:group.joint_fit",
   "expand:group.joint_fit",
   "fill:jointFit.weight.0=0.5",
   "fill:jointFit.weight.1=0.5"
  ],
  "highlights": [
   "group.joint_fit"
  ],
  "sidebar": "Extra",
  "capture": true,
  "fitPhase": "setup"
 },
 {
  "id": "minimizer",
  "page": "analysis",
  "description": "Set the minimizer as the project does",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.extras",
   "reveal:group.minimizer",
   "expand:group.minimizer",
   "fill:minimizer.maxIterations=1000"
  ],
  "highlights": [
   "group.minimizer"
  ],
  "sidebar": "Extra",
  "capture": true,
  "fitPhase": "setup"
 },
 {
  "id": "stage-1-free",
  "page": "analysis",
  "description": "Scales and time-of-flight calibration",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:expt_n2",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Instrument",
   "tick:experiments[expt_n2].instrument.calib_d_to_tof_offset",
   "parameters.clearFilters",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:expt_s2",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Instrument",
   "tick:experiments[expt_s2].instrument.calib_d_to_tof_offset",
   "parameters.clearFilters",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:expt_s2",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Linked structures",
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
  "description": "Fit: Scales and time-of-flight calibration",
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
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:expt_s2",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Background",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:expt_n2",
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
   "choose:expt_n2",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Peak profile",
   "tick:experiments[expt_n2].peak.broad_gauss_sigma_0",
   "tick:experiments[expt_n2].peak.broad_gauss_sigma_1",
   "tick:experiments[expt_n2].peak.broad_gauss_sigma_2",
   "tick:experiments[expt_n2].peak.broad_lorentz_gamma_0",
   "parameters.clearFilters",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:expt_s2",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Peak profile",
   "tick:experiments[expt_s2].peak.broad_gauss_sigma_0",
   "tick:experiments[expt_s2].peak.broad_gauss_sigma_1",
   "tick:experiments[expt_s2].peak.broad_gauss_sigma_2",
   "tick:experiments[expt_s2].peak.broad_lorentz_gamma_0",
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
  "description": "Displacement",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:ferrite",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Atomic displacement",
   "tick:structures[ferrite].atom_sites[Fe].adp_iso",
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
  "description": "Fit: Displacement",
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
