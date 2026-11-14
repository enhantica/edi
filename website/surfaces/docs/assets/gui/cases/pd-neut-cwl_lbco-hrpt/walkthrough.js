// SPDX-License-Identifier: BSD-3-Clause
// The Application tutorial of pd-neut-cwl_lbco-hrpt, written by tools/docs/app_tutorial_plan.py.
(function () {
    const EXAMPLE_ID = "pd-neut-cwl_lbco-hrpt";
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
  "capture": true
 },
 {
  "id": "project-details",
  "page": "project",
  "description": "Enter the project details",
  "actions": [
   "home.start",
   "project.create",
   "fill:createProject.name=pd-neut-cwl_lbco-hrpt",
   "fill:createProject.title=@title",
   "fill:createProject.location=@projectDirectory"
  ],
  "highlights": [
   "createProject.name",
   "createProject.title",
   "createProject.location"
  ],
  "sidebar": "",
  "capture": true
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
  "id": "structure-created",
  "page": "structure",
  "description": "Create the structure",
  "actions": [
   "appBar.tab.structure",
   "sideBar.tab.basic",
   "expand:group.structures",
   "structures.create",
   "fill:structures.name.0=lbco",
   "key:Return"
  ],
  "highlights": [
   "structures.list"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "structure-cell",
  "page": "structure",
  "description": "Space group and cell",
  "actions": [
   "reveal:group.space_group",
   "expand:group.space_group",
   "spaceGroup.nameHM",
   "type:P m -3 m",
   "key:Return",
   "reveal:group.cell",
   "expand:group.cell",
   "reveal:cell.length_a",
   "fill:cell.length_a=3.88",
   "key:Return"
  ],
  "highlights": [
   "group.space_group",
   "group.cell"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "structure-sites",
  "page": "structure",
  "description": "Add the atom sites",
  "actions": [
   "reveal:group.atom_site",
   "expand:group.atom_site",
   "fill:atomSite.label.0=La",
   "key:Return",
   "atomSite.typeSymbol.0",
   "type:La",
   "key:Return",
   "atomSite.wyckoffLetter.0",
   "type:a:",
   "key:Return",
   "reveal:atomSite.occupancy.0",
   "fill:atomSite.occupancy.0=0.5",
   "key:Return",
   "atomSites.append",
   "fill:atomSite.label.1=Ba",
   "key:Return",
   "atomSite.typeSymbol.1",
   "type:Ba",
   "key:Return",
   "atomSite.wyckoffLetter.1",
   "type:a:",
   "key:Return",
   "reveal:atomSite.occupancy.1",
   "fill:atomSite.occupancy.1=0.5",
   "key:Return",
   "atomSites.append",
   "fill:atomSite.label.2=Co",
   "key:Return",
   "atomSite.typeSymbol.2",
   "type:Co",
   "key:Return",
   "atomSite.wyckoffLetter.2",
   "type:b:",
   "key:Return",
   "atomSites.append",
   "fill:atomSite.label.3=O",
   "key:Return",
   "atomSite.typeSymbol.3",
   "type:O",
   "key:Return",
   "atomSite.wyckoffLetter.3",
   "type:c:",
   "key:Return"
  ],
  "highlights": [
   "atomSites.list"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "structure-adp",
  "page": "structure",
  "description": "Set the displacements",
  "actions": [
   "reveal:group.atom_site_aniso",
   "expand:group.atom_site_aniso",
   "reveal:atomSiteAdp.iso.0",
   "fill:atomSiteAdp.iso.0=0.5",
   "key:Return",
   "reveal:atomSiteAdp.iso.1",
   "fill:atomSiteAdp.iso.1=0.5",
   "key:Return",
   "reveal:atomSiteAdp.iso.2",
   "fill:atomSiteAdp.iso.2=0.5",
   "key:Return",
   "reveal:atomSiteAdp.iso.3",
   "fill:atomSiteAdp.iso.3=0.5",
   "key:Return"
  ],
  "highlights": [
   "atomSiteAdps.list"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "experiment-created",
  "page": "experiment",
  "description": "Create the experiment",
  "actions": [
   "appBar.tab.experiment",
   "sideBar.tab.basic",
   "expand:group.experiments",
   "experiments.create",
   "experimentType.sampleForm",
   "choose-token:experimentType.sampleForm=powder",
   "experimentType.beamMode",
   "choose-token:experimentType.beamMode=constant wavelength",
   "experimentType.radiationProbe",
   "choose-token:experimentType.radiationProbe=neutron",
   "fill:experiments.name.0=hrpt",
   "key:Return"
  ],
  "highlights": [
   "experimentType"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "data-web",
  "page": "experiment",
  "description": "Find the measured data",
  "actions": [
   "experiments.load",
   "experiments.load.dataWeb",
   "fill:onlineLoad.field.id=pd-neut-cwl_lbco-hrpt-hrpt-data",
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
  "id": "data-loaded",
  "page": "experiment",
  "description": "Load the measured data",
  "actions": [
   "onlineLoad.row.0",
   "wait-online"
  ],
  "highlights": [
   "workflow.experiment.mainContent"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "experiment-instrument",
  "page": "experiment",
  "description": "Instrument and peak widths",
  "actions": [
   "reveal:group.instrument",
   "expand:group.instrument",
   "reveal:instrument.setup_wavelength",
   "fill:instrument.setup_wavelength=1.494",
   "key:Return",
   "reveal:instrument.calib_twotheta_offset",
   "fill:instrument.calib_twotheta_offset=0.3",
   "key:Return",
   "reveal:group.peak",
   "expand:group.peak",
   "reveal:peak.broad_gauss_u",
   "fill:peak.broad_gauss_u=0.08",
   "key:Return",
   "reveal:peak.broad_gauss_v",
   "fill:peak.broad_gauss_v=-0.1",
   "key:Return",
   "reveal:peak.broad_gauss_w",
   "fill:peak.broad_gauss_w=0.1",
   "key:Return",
   "reveal:peak.broad_lorentz_y",
   "fill:peak.broad_lorentz_y=0.08",
   "key:Return"
  ],
  "highlights": [
   "group.instrument",
   "group.peak"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "experiment-background",
  "page": "experiment",
  "description": "Background and excluded regions",
  "actions": [
   "reveal:group.background",
   "expand:group.background",
   "background.append",
   "reveal:background.position.0",
   "fill:background.position.0=10",
   "key:Return",
   "reveal:background.intensity.0",
   "fill:background.intensity.0=160",
   "key:Return",
   "background.append",
   "reveal:background.position.1",
   "fill:background.position.1=30",
   "key:Return",
   "reveal:background.intensity.1",
   "fill:background.intensity.1=160",
   "key:Return",
   "background.append",
   "reveal:background.position.2",
   "fill:background.position.2=50",
   "key:Return",
   "reveal:background.intensity.2",
   "fill:background.intensity.2=160",
   "key:Return",
   "background.append",
   "reveal:background.position.3",
   "fill:background.position.3=110",
   "key:Return",
   "reveal:background.intensity.3",
   "fill:background.intensity.3=160",
   "key:Return",
   "background.append",
   "reveal:background.position.4",
   "fill:background.position.4=165",
   "key:Return",
   "reveal:background.intensity.4",
   "fill:background.intensity.4=160",
   "key:Return",
   "reveal:group.excluded_region",
   "expand:group.excluded_region",
   "excludedRegions.append",
   "reveal:excludedRegion.start.0",
   "fill:excludedRegion.start.0=0",
   "key:Return",
   "reveal:excludedRegion.end.0",
   "fill:excludedRegion.end.0=5",
   "key:Return",
   "excludedRegions.append",
   "reveal:excludedRegion.start.1",
   "fill:excludedRegion.start.1=165",
   "key:Return",
   "reveal:excludedRegion.end.1",
   "fill:excludedRegion.end.1=180",
   "key:Return"
  ],
  "highlights": [
   "excludedRegions.list"
  ],
  "sidebar": "",
  "capture": true
 },
 {
  "id": "experiment-linked",
  "page": "experiment",
  "description": "Link the structure",
  "actions": [
   "reveal:group.linked_structure",
   "expand:group.linked_structure",
   "reveal:linkedStructure.scale.0",
   "fill:linkedStructure.scale.0=9",
   "key:Return"
  ],
  "highlights": [
   "linkedStructure.list",
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
  "description": "Scale, 2θ zero and cell",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Instrument",
   "tick:experiment.instrument.calib_twotheta_offset",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Linked structures",
   "tick:experiment.linked_structures[lbco].scale",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Cell",
   "tick:structure.cell.length_a"
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
  "id": "group-filter",
  "page": "analysis",
  "description": "Filter the table to Background",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Background"
  ],
  "highlights": [
   "parameters.category"
  ],
  "sidebar": "Main",
  "capture": true,
  "fitPhase": "setup"
 },
 {
  "id": "group-free-all",
  "page": "analysis",
  "description": "Free all from the header",
  "actions": [
   "parameters.freeHeader"
  ],
  "highlights": [
   "parameters.freeHeader"
  ],
  "sidebar": "Main",
  "capture": true,
  "fitPhase": "setup"
 },
 {
  "id": "stage-2-free",
  "page": "analysis",
  "description": "Background",
  "actions": [
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
   "reveal:parameters.category",
   "parameters.category",
   "choose:Peak profile",
   "tick:experiment.peak.broad_gauss_u",
   "tick:experiment.peak.broad_gauss_v",
   "tick:experiment.peak.broad_gauss_w",
   "tick:experiment.peak.broad_lorentz_y"
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
  "description": "Displacements",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Atomic displacement",
   "tick:structure.atom_sites[Ba].adp_iso",
   "tick:structure.atom_sites[Co].adp_iso",
   "tick:structure.atom_sites[La].adp_iso",
   "tick:structure.atom_sites[O].adp_iso"
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
  "id": "stage-5-free",
  "page": "analysis",
  "description": "Constrain La and Ba",
  "actions": [
   "appBar.tab.analysis",
   "sideBar.tab.basic",
   "reveal:parameters.category",
   "parameters.category",
   "choose:Atomic displacement",
   "untick:structure.atom_sites[Ba].adp_iso",
   "appBar.tab.analysis",
   "sideBar.tab.extras",
   "reveal:group.alias",
   "expand:group.alias",
   "aliases.append",
   "show:aliases.list:0:begin",
   "reveal:alias.id.0",
   "fill:alias.id.0=biso_La",
   "key:Return",
   "alias.parameter.0",
   "type:lbco.atom_site.La.adp_iso",
   "key:Return",
   "aliases.append",
   "show:aliases.list:1:begin",
   "reveal:alias.id.1",
   "fill:alias.id.1=biso_Ba",
   "key:Return",
   "alias.parameter.1",
   "type:lbco.atom_site.Ba.adp_iso",
   "key:Return",
   "reveal:group.constraint",
   "expand:group.constraint",
   "constraints.append",
   "reveal:constraint.id.0",
   "fill:constraint.id.0=biso_Ba",
   "key:Return",
   "fill:constraint.expression.0=biso_Ba = biso_La",
   "key:Return",
   "sideBar.tab.basic"
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
  "description": "Fit: Constrain La and Ba",
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
