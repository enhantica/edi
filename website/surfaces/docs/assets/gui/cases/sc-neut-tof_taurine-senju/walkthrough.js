// SPDX-License-Identifier: BSD-3-Clause
// The Application tutorial of sc-neut-tof_taurine-senju, written by tools/docs/app_tutorial_plan.py.
(function () {
    const EXAMPLE_ID = "sc-neut-tof_taurine-senju";
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
   "fill:createProject.name=sc-neut-tof_taurine-senju",
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
  "description": "Find the structure taurine in the EasyDiffraction collection",
  "actions": [
   "appBar.tab.structure",
   "sideBar.tab.basic",
   "expand:group.structures",
   "structures.load",
   "structures.load.web",
   "onlineLoad.source",
   "choose:EasyDiffraction Database",
   "fill:onlineLoad.field.id=sc-neut-tof_taurine-senju-taurine",
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
  "description": "Load the structure taurine",
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
  "description": "Find the experiment senju_1 in the EasyDiffraction collection",
  "actions": [
   "appBar.tab.experiment",
   "sideBar.tab.basic",
   "expand:group.experiments",
   "experiments.load",
   "experiments.load.experimentWeb",
   "fill:onlineLoad.field.id=sc-neut-tof_taurine-senju-senju_1",
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
  "description": "Load the experiment senju_1",
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
  "description": "Find the experiment senju_2 in the EasyDiffraction collection",
  "actions": [
   "appBar.tab.experiment",
   "sideBar.tab.basic",
   "expand:group.experiments",
   "experiments.load",
   "experiments.load.experimentWeb",
   "fill:onlineLoad.field.id=sc-neut-tof_taurine-senju-senju_2",
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
  "description": "Load the experiment senju_2",
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
  "id": "experiment-web-2",
  "page": "experiment",
  "description": "Find the experiment senju_3 in the EasyDiffraction collection",
  "actions": [
   "appBar.tab.experiment",
   "sideBar.tab.basic",
   "expand:group.experiments",
   "experiments.load",
   "experiments.load.experimentWeb",
   "fill:onlineLoad.field.id=sc-neut-tof_taurine-senju-senju_3",
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
  "id": "experiment-loaded-2",
  "page": "experiment",
  "description": "Load the experiment senju_3",
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
  "id": "experiment-web-3",
  "page": "experiment",
  "description": "Find the experiment senju_4 in the EasyDiffraction collection",
  "actions": [
   "appBar.tab.experiment",
   "sideBar.tab.basic",
   "expand:group.experiments",
   "experiments.load",
   "experiments.load.experimentWeb",
   "fill:onlineLoad.field.id=sc-neut-tof_taurine-senju-senju_4",
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
  "id": "experiment-loaded-3",
  "page": "experiment",
  "description": "Load the experiment senju_4",
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
  "id": "experiment-web-4",
  "page": "experiment",
  "description": "Find the experiment senju_5 in the EasyDiffraction collection",
  "actions": [
   "appBar.tab.experiment",
   "sideBar.tab.basic",
   "expand:group.experiments",
   "experiments.load",
   "experiments.load.experimentWeb",
   "fill:onlineLoad.field.id=sc-neut-tof_taurine-senju-senju_5",
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
  "id": "experiment-loaded-4",
  "page": "experiment",
  "description": "Load the experiment senju_5",
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
  "id": "experiment-web-5",
  "page": "experiment",
  "description": "Find the experiment senju_6 in the EasyDiffraction collection",
  "actions": [
   "appBar.tab.experiment",
   "sideBar.tab.basic",
   "expand:group.experiments",
   "experiments.load",
   "experiments.load.experimentWeb",
   "fill:onlineLoad.field.id=sc-neut-tof_taurine-senju-senju_6",
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
  "id": "experiment-loaded-5",
  "page": "experiment",
  "description": "Load the experiment senju_6",
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
   "fill:alias.id.0=x11_1",
   "key:Return",
   "alias.parameter.0",
   "type:senju_1.extinction.coefficient_11",
   "key:Return",
   "aliases.append",
   "show:aliases.list:1:begin",
   "reveal:alias.id.1",
   "fill:alias.id.1=x22_1",
   "key:Return",
   "alias.parameter.1",
   "type:senju_1.extinction.coefficient_22",
   "key:Return",
   "aliases.append",
   "show:aliases.list:2:begin",
   "reveal:alias.id.2",
   "fill:alias.id.2=x33_1",
   "key:Return",
   "alias.parameter.2",
   "type:senju_1.extinction.coefficient_33",
   "key:Return",
   "aliases.append",
   "show:aliases.list:3:begin",
   "reveal:alias.id.3",
   "fill:alias.id.3=x11_2",
   "key:Return",
   "alias.parameter.3",
   "type:senju_2.extinction.coefficient_11",
   "key:Return",
   "aliases.append",
   "show:aliases.list:4:begin",
   "reveal:alias.id.4",
   "fill:alias.id.4=x22_2",
   "key:Return",
   "alias.parameter.4",
   "type:senju_2.extinction.coefficient_22",
   "key:Return",
   "aliases.append",
   "show:aliases.list:5:begin",
   "reveal:alias.id.5",
   "fill:alias.id.5=x33_2",
   "key:Return",
   "alias.parameter.5",
   "type:senju_2.extinction.coefficient_33",
   "key:Return",
   "aliases.append",
   "show:aliases.list:6:begin",
   "reveal:alias.id.6",
   "fill:alias.id.6=x11_3",
   "key:Return",
   "alias.parameter.6",
   "type:senju_3.extinction.coefficient_11",
   "key:Return",
   "aliases.append",
   "show:aliases.list:7:begin",
   "reveal:alias.id.7",
   "fill:alias.id.7=x22_3",
   "key:Return",
   "alias.parameter.7",
   "type:senju_3.extinction.coefficient_22",
   "key:Return",
   "aliases.append",
   "show:aliases.list:8:begin",
   "reveal:alias.id.8",
   "fill:alias.id.8=x33_3",
   "key:Return",
   "alias.parameter.8",
   "type:senju_3.extinction.coefficient_33",
   "key:Return",
   "aliases.append",
   "show:aliases.list:9:begin",
   "reveal:alias.id.9",
   "fill:alias.id.9=x11_4",
   "key:Return",
   "alias.parameter.9",
   "type:senju_4.extinction.coefficient_11",
   "key:Return",
   "aliases.append",
   "show:aliases.list:10:begin",
   "reveal:alias.id.10",
   "fill:alias.id.10=x22_4",
   "key:Return",
   "alias.parameter.10",
   "type:senju_4.extinction.coefficient_22",
   "key:Return",
   "aliases.append",
   "show:aliases.list:11:begin",
   "reveal:alias.id.11",
   "fill:alias.id.11=x33_4",
   "key:Return",
   "alias.parameter.11",
   "type:senju_4.extinction.coefficient_33",
   "key:Return",
   "aliases.append",
   "show:aliases.list:12:begin",
   "reveal:alias.id.12",
   "fill:alias.id.12=x11_5",
   "key:Return",
   "alias.parameter.12",
   "type:senju_5.extinction.coefficient_11",
   "key:Return",
   "aliases.append",
   "show:aliases.list:13:begin",
   "reveal:alias.id.13",
   "fill:alias.id.13=x22_5",
   "key:Return",
   "alias.parameter.13",
   "type:senju_5.extinction.coefficient_22",
   "key:Return",
   "aliases.append",
   "show:aliases.list:14:begin",
   "reveal:alias.id.14",
   "fill:alias.id.14=x33_5",
   "key:Return",
   "alias.parameter.14",
   "type:senju_5.extinction.coefficient_33",
   "key:Return",
   "aliases.append",
   "show:aliases.list:15:begin",
   "reveal:alias.id.15",
   "fill:alias.id.15=x11_6",
   "key:Return",
   "alias.parameter.15",
   "type:senju_6.extinction.coefficient_11",
   "key:Return",
   "aliases.append",
   "show:aliases.list:16:begin",
   "reveal:alias.id.16",
   "fill:alias.id.16=x22_6",
   "key:Return",
   "alias.parameter.16",
   "type:senju_6.extinction.coefficient_22",
   "key:Return",
   "aliases.append",
   "show:aliases.list:17:begin",
   "reveal:alias.id.17",
   "fill:alias.id.17=x33_6",
   "key:Return",
   "alias.parameter.17",
   "type:senju_6.extinction.coefficient_33",
   "key:Return",
   "reveal:group.constraint",
   "expand:group.constraint",
   "constraints.append",
   "reveal:constraint.id.0",
   "fill:constraint.id.0=x11_2",
   "key:Return",
   "fill:constraint.expression.0=x11_2 = x11_1",
   "key:Return",
   "constraints.append",
   "reveal:constraint.id.1",
   "fill:constraint.id.1=x22_2",
   "key:Return",
   "fill:constraint.expression.1=x22_2 = x22_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:2:begin",
   "reveal:constraint.id.2",
   "fill:constraint.id.2=x33_2",
   "key:Return",
   "fill:constraint.expression.2=x33_2 = x33_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:3:begin",
   "reveal:constraint.id.3",
   "fill:constraint.id.3=x11_3",
   "key:Return",
   "fill:constraint.expression.3=x11_3 = x11_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:4:begin",
   "reveal:constraint.id.4",
   "fill:constraint.id.4=x22_3",
   "key:Return",
   "fill:constraint.expression.4=x22_3 = x22_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:5:begin",
   "reveal:constraint.id.5",
   "fill:constraint.id.5=x33_3",
   "key:Return",
   "fill:constraint.expression.5=x33_3 = x33_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:6:begin",
   "reveal:constraint.id.6",
   "fill:constraint.id.6=x11_4",
   "key:Return",
   "fill:constraint.expression.6=x11_4 = x11_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:7:begin",
   "reveal:constraint.id.7",
   "fill:constraint.id.7=x22_4",
   "key:Return",
   "fill:constraint.expression.7=x22_4 = x22_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:8:begin",
   "reveal:constraint.id.8",
   "fill:constraint.id.8=x33_4",
   "key:Return",
   "fill:constraint.expression.8=x33_4 = x33_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:9:begin",
   "reveal:constraint.id.9",
   "fill:constraint.id.9=x11_5",
   "key:Return",
   "fill:constraint.expression.9=x11_5 = x11_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:10:begin",
   "reveal:constraint.id.10",
   "fill:constraint.id.10=x22_5",
   "key:Return",
   "fill:constraint.expression.10=x22_5 = x22_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:11:begin",
   "reveal:constraint.id.11",
   "fill:constraint.id.11=x33_5",
   "key:Return",
   "fill:constraint.expression.11=x33_5 = x33_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:12:begin",
   "reveal:constraint.id.12",
   "fill:constraint.id.12=x11_6",
   "key:Return",
   "fill:constraint.expression.12=x11_6 = x11_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:13:begin",
   "reveal:constraint.id.13",
   "fill:constraint.id.13=x22_6",
   "key:Return",
   "fill:constraint.expression.13=x22_6 = x22_1",
   "key:Return",
   "constraints.append",
   "show:constraints.list:14:begin",
   "reveal:constraint.id.14",
   "fill:constraint.id.14=x33_6",
   "key:Return",
   "fill:constraint.expression.14=x33_6 = x33_1",
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
  "description": "Scales, every site isotropic",
  "actions": [
   "appBar.tab.structure",
   "sideBar.tab.basic",
   "reveal:group.atom_site_aniso",
   "expand:group.atom_site_aniso",
   "show:atomSiteAdps.list:0:begin",
   "atomSiteAdp.type.0",
   "choose:Biso",
   "show:atomSiteAdps.list:1:begin",
   "atomSiteAdp.type.1",
   "choose:Biso",
   "show:atomSiteAdps.list:2:begin",
   "atomSiteAdp.type.2",
   "choose:Biso",
   "show:atomSiteAdps.list:3:begin",
   "atomSiteAdp.type.3",
   "choose:Biso",
   "show:atomSiteAdps.list:4:begin",
   "atomSiteAdp.type.4",
   "choose:Biso",
   "show:atomSiteAdps.list:5:begin",
   "atomSiteAdp.type.5",
   "choose:Biso",
   "show:atomSiteAdps.list:6:begin",
   "atomSiteAdp.type.6",
   "choose:Biso",
   "show:atomSiteAdps.list:7:begin",
   "atomSiteAdp.type.7",
   "choose:Biso",
   "show:atomSiteAdps.list:8:begin",
   "atomSiteAdp.type.8",
   "choose:Biso",
   "show:atomSiteAdps.list:9:begin",
   "atomSiteAdp.type.9",
   "choose:Biso",
   "show:atomSiteAdps.list:10:begin",
   "atomSiteAdp.type.10",
   "choose:Biso",
   "show:atomSiteAdps.list:11:begin",
   "atomSiteAdp.type.11",
   "choose:Biso",
   "show:atomSiteAdps.list:12:begin",
   "atomSiteAdp.type.12",
   "choose:Biso",
   "show:atomSiteAdps.list:13:begin",
   "atomSiteAdp.type.13",
   "choose:Biso",
   "appBar.tab.analysis",
   "sideBar.tab.basic",
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
  "description": "Fit: Scales, every site isotropic",
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
  "description": "Isotropic displacements",
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
  "id": "stage-2-fit",
  "page": "analysis",
  "description": "Fit: Isotropic displacements",
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
  "description": "Extinction",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiments[senju_1].extinction.coefficient_11",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiments[senju_1].extinction.coefficient_22",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.nameFilter",
   "fill:parameters.nameFilter=experiments[senju_1].extinction.coefficient_33",
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
  "description": "Fit: Extinction",
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
  "description": "Positions",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:taurine",
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
  "id": "stage-4-fit",
  "page": "analysis",
  "description": "Fit: Positions",
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
  "description": "Anisotropic displacements",
  "actions": [
   "appBar.tab.structure",
   "sideBar.tab.basic",
   "reveal:group.atom_site_aniso",
   "expand:group.atom_site_aniso",
   "show:atomSiteAdps.list:0:begin",
   "atomSiteAdp.type.0",
   "choose:beta",
   "show:atomSiteAdps.list:1:begin",
   "atomSiteAdp.type.1",
   "choose:beta",
   "show:atomSiteAdps.list:2:begin",
   "atomSiteAdp.type.2",
   "choose:beta",
   "show:atomSiteAdps.list:3:begin",
   "atomSiteAdp.type.3",
   "choose:beta",
   "show:atomSiteAdps.list:4:begin",
   "atomSiteAdp.type.4",
   "choose:beta",
   "show:atomSiteAdps.list:5:begin",
   "atomSiteAdp.type.5",
   "choose:beta",
   "show:atomSiteAdps.list:6:begin",
   "atomSiteAdp.type.6",
   "choose:beta",
   "show:atomSiteAdps.list:7:begin",
   "atomSiteAdp.type.7",
   "choose:beta",
   "show:atomSiteAdps.list:8:begin",
   "atomSiteAdp.type.8",
   "choose:beta",
   "show:atomSiteAdps.list:9:begin",
   "atomSiteAdp.type.9",
   "choose:beta",
   "show:atomSiteAdps.list:10:begin",
   "atomSiteAdp.type.10",
   "choose:beta",
   "show:atomSiteAdps.list:11:begin",
   "atomSiteAdp.type.11",
   "choose:beta",
   "show:atomSiteAdps.list:12:begin",
   "atomSiteAdp.type.12",
   "choose:beta",
   "show:atomSiteAdps.list:13:begin",
   "atomSiteAdp.type.13",
   "choose:beta",
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Atomic displacement",
   "parameters.freeHeader",
   "parameters.freeHeader.free",
   "parameters.clearFilters",
   "reveal:parameters.datablock",
   "parameters.datablock",
   "choose:taurine",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Atomic displacement",
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
  "description": "Fit: Anisotropic displacements",
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
   "mainArea.analysis.tab.correlations"
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
   "mainArea.analysis.tab.fitting",
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
