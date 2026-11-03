// SPDX-License-Identifier: BSD-3-Clause
// Evaluated by --docs-capture; capture contains this run's isolated input/workspace paths.
(function () {
    const EXAMPLE_ID = "pd-neut-cwl_y2o3-spodi";
    return {schema: 2, inputs: "cif-and-data", example: EXAMPLE_ID, build: function (capture) {
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
    shot("04-project-created", "project", "Create the project", ["createProject.accept", "pin-time:01 Jan 2026 12:00:00"],
        ["workflow.project.mainContent", "workflow.project.manualSidebar"]);
    tabs("05-project", "project", "Project details and controls");
    shot("06-structure-import", "structure", "Load the structure into the empty project",
        ["appBar.tab.structure", "sideBar.tab.basic", "expand:group.structures"],
        ["structures.load", "workflow.structure.mainContent"]);
    shot("07-structure-loaded", "structure", "Inspect the imported crystal structure",
        ["import-structure:" + capture.structureFile],
        ["structures.list", "workflow.structure.mainContent"]);
    tabs("08-structure", "structure", "Crystal structure");
    function setValue(id, value) { return ["reveal:" + id, "fill:" + id + "=" + value, "key:Return"]; }
    function select(id, token) { return [id, "choose-token:" + id + "=" + token]; }
    shot("09-experiment-import", "experiment", "Create an experiment for the measurement",
        ["appBar.tab.experiment", "sideBar.tab.basic", "expand:group.experiments"],
        ["experiments.create"]);
    shot("09-experiment-type", "experiment", "Choose the sample form, beam mode and probe before loading data",
        ["experiments.create"].concat(select("experimentType.sampleForm", capture.fixture.values.sampleForm[0]),
          select("experimentType.beamMode", capture.fixture.values.beamMode[0]),
          select("experimentType.radiationProbe", capture.fixture.values.probe[0])),
        ["experimentType"]);
    shot("09-experiment-data", "experiment", "Load the measured angle, intensity and uncertainty columns",
        ["import-data:" + capture.dataFile], ["experiments.loadData.0", "workflow.experiment.mainContent"]);
    shot("09-wavelength", "experiment", "Set the wavelength used for this measurement",
        ["reveal:group.instrument", "expand:group.instrument"].concat(setValue("instrument.setup_wavelength", capture.wavelength)),
        ["instrument.setup_wavelength"]);
    shot("09-profile", "experiment", "Choose the peak profile and starting coefficients",
        ["reveal:group.peak", "expand:group.peak"].concat(select("peak.type", capture.profileType)), ["peak.type", "group.peak"]);
    Object.keys(capture.profileStart).forEach(function (name) {
        shot("09-profile-" + name.replace(/_/g,"-"), "experiment", "Set a starting profile coefficient",
            setValue("peak." + name, capture.profileStart[name]), ["peak." + name]);
    });
    capture.excludedRegions.forEach(function (region, index) {
        shot("09-exclusion-" + index, "experiment", "Exclude the measured regions outside the fitting range",
            ["reveal:group.excluded_region", "expand:group.excluded_region", "excludedRegions.append"].concat(
              setValue("excludedRegion.start." + index, region.start), setValue("excludedRegion.end." + index, region.end)),
            ["excludedRegions.list"]);
    });
    shot("09-background-settings", "experiment", "Choose enough background anchors for this measurement",
        ["sideBar.tab.extras", "reveal:group.background_estimate", "expand:group.background_estimate"].concat(
          setValue("background_estimate.n_points", capture.backgroundPoints)), ["background_estimate.n_points"]);
    shot("09-background-estimate", "experiment", "Estimate a starting background from the measured pattern",
        ["sideBar.tab.basic", "reveal:group.background", "expand:group.background", "reveal:background.estimate", "background.estimate"], ["background.rows", "background.estimate"]);
    shot("10-experiment-loaded", "experiment", "Inspect the starting pattern before choosing free parameters", [],
        ["workflow.experiment.mainContent", "workflow.experiment.manualSidebar"]);
    tabs("11-experiment", "experiment", "Experiment and measured data");
    function freeKind(name) {
        return ["reveal:parameters.nameFilter", "fill:parameters.nameFilter=" + name, "parameters.freeHeader", "parameters.freeHeader.free", "parameters.clearFilters"];
    }
    shot("12-analysis-choose", "analysis", "Begin with the scale and cell length; keep the other parameters fixed",
        ["appBar.tab.analysis", "sideBar.tab.basic", "parameters.clearFilters", "parameters.freeHeader", "parameters.freeHeader.fixed"].concat(freeKind("scale"), freeKind("length_a")),
        ["group.parameters", "parameters.freeHeader"]);
    steps[steps.length-1].fitPhase = "setup";
    shot("12-save-start", "analysis", "Keep the starting model for the comparison",
        ["save-as:" + capture.checkpointDirectory + "/starting"], [], "", false);
    shot("12-fit-scale-cell", "analysis", "Fit the scale and cell length first",
        ["statusBar.fit.button", "wait-fit", "close-fit-results"], ["workflow.analysis.mainContent", "group.parameters"]);
    shot("12-fit-profile", "analysis", "Add the peak widths and zero offset to the free set",
        freeKind("broad_gauss_").concat(freeKind("calib_twotheta_offset"), ["statusBar.fit.button", "wait-fit", "close-fit-results"]),
        ["workflow.analysis.mainContent", "group.parameters"]);
    shot("12-run-refinement", "analysis", "Add background and coordinates, then fit again; keep displacement parameters fixed",
        freeKind("background").concat(freeKind("fract_"), ["statusBar.fit.button", "wait-fit", "close-fit-results"]), [], "", false);
    shot("12-save-refined", "analysis", "Keep the result of staged refinement",
        ["save-as:" + capture.checkpointDirectory + "/refined"], [], "", false);
    shot("12-correlations", "analysis", "Inspect correlations after the staged refinement",
        ["mainArea.analysis.tab.correlations"], ["workflow.analysis.mainContent"]);
    shot("12-pattern-return", "analysis", "Return to the fitted pattern",
        ["mainArea.analysis.tab.fitting"], [], "", false);
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
        ["save-as:docs-saved-project", "project.open"], ["project.openChoice"]);
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
    panel("guide-structure-appearance", "structure", "extras", "group.appearance", "Choose the structure display", ["group.appearance"]);
    panel("guide-structure-scattering", "structure", "extras", "group.scattering_length", "Inspect scattering-length settings", ["group.scattering_length"]);
    panel("guide-experiment-absorption", "experiment", "extras", "group.absorption", "Inspect absorption settings", ["group.absorption"]);
    panel("guide-experiment-orientation", "experiment", "extras", "group.preferred_orientation", "Inspect preferred-orientation settings", ["group.preferred_orientation"]);
    panel("guide-experiment-scattering", "experiment", "extras", "group.scattering_source", "Inspect scattering data sources", ["group.scattering_source"]);
    panel("guide-analysis-aliases", "analysis", "extras", "group.alias", "Inspect parameter aliases", ["group.alias"]);
    shot("guide-analysis-correlations", "analysis", "Inspect correlations after fitting",
        ["appBar.tab.analysis", "sideBar.tab.basic", "mainArea.analysis.tab.correlations"], ["workflow.analysis.mainContent"]);
    panel("guide-project-uncertainties", "project", "extras", "group.su_format", "Choose how values and standard uncertainties are displayed", ["group.su_format"]);
    panel("guide-experiment-data-settings", "experiment", "extras", "group.data", "Inspect the measured range and point data", ["group.data"]);
    panel("guide-experiment-cutoff", "experiment", "extras", "group.peak", "Choose the peak calculation window", ["peak.cutoff_fwhm"]);
    panel("guide-analysis-start-values", "analysis", "extras", "group.fit_parameter", "Inspect the values before the last fit", ["fitStart.list"]);
    panel("guide-analysis-shown-parameters", "analysis", "settings", "group.shownParameters", "Choose which parameter groups appear in the table", ["group.shownParameters"]);
    panel("guide-analysis-pattern-updates", "analysis", "settings", "group.patternUpdates", "Choose how the displayed pattern updates during a scan", ["group.patternUpdates"]);
    return steps;
    }};
})();
