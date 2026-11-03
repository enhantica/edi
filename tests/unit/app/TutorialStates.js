.pragma library
.import "UiInteraction.js" as Ui

// Independently authored state setup for the written lessons. These are real public
// model edits, not emulated playback and not assignments to the tutorial controller.
function settle(t, project) {
    t.tryVerify(() => !project.calculating, 10000,
                "The lesson's actual project finishes calculating before Next is pressed");
}
function satisfy(t, app, id, index, Session, AppState, Probe, tourStep) {
    t.finishPages();
    if (id === "interface") {
        t.verify(Ui.find(Ui.windowRoot(app), tourStep.target) !== null,
                 "The Interface lesson's named visible control establishes its stated state: " + tourStep.target);
        return;
    }
    const p = Session.project;
    t.verify(p !== null, "A scientific lesson owns an actual temporary project");
    if (id === "simulation") {
        if (index === 0) {
            t.compare(app.appBarCentralTabs.currentIndex, AppState.Page.Structure, "Simulation starts on its stated Structure page");
            t.compare(Probe.rows(p.structures).length, 0, "Simulation's first stated state has no structure");
        } else if (index === 1) {
            // This gate checks Next once a state holds, not the deferred action player.
            // Import one independently authored structure into the actual temporary project.
            t.verify(p.loadStructure(Probe.repoUrl("tests/fixtures/onboarding/simulation-structure.edi")),
                     "The actual temporary project loads the independently declared tutorial structure");
            t.compare(p.currentStructure.name, "lbco", "The stated lbco structure is present");
        } else if (index === 2) {
            t.compare(p.currentStructure.spaceGroup.itNumber, 221, "The written lesson's cubic group is number 221");
        } else if (index === 3) {
            for (const parameter of [p.currentStructure.cell.lengthA, p.currentStructure.cell.lengthB, p.currentStructure.cell.lengthC])
                t.compare(parameter.value, 3.89, "The stated cubic cell has all three lengths equal to 3.89 angstroms");
        } else if (index === 4) {
            const atoms = Probe.rows(p.currentStructure.atomSites);
            const sites = [["La", 0, 0, 0, 0.5], ["Ba", 0, 0, 0, 0.5], ["Co", 0.5, 0.5, 0.5, 1], ["O", 0, 0.5, 0.5, 1]];
            t.compare(atoms.length, sites.length, "The stated simulation structure contains four atom sites");
            for (let i = 0; i < sites.length; ++i) {
                t.compare(atoms[i].label, sites[i][0], "The applied lesson state keeps every declared atom label");
                ["fractX", "fractY", "fractZ", "occupancy"].forEach((role, k) =>
                    t.compare(atoms[i][role].value, sites[i][k + 1], "The applied lesson state keeps each declared position and occupancy"));
            }
        } else if (index === 5) {
            t.verify(p.createExperiment(), "The learner creates the stated simulation experiment");
            t.compare(Probe.rows(p.experiments).length, 1, "The new simulation experiment is in its list");
            // The written lesson prescribes no scan range. A compact real pattern is sufficient.
            p.currentExperiment.setRange(10, 80, 0.25);
        } else if (index === 6) {
            const e = p.currentExperiment;
            t.compare(e.sampleFormToken, "powder", "The lesson uses a powder sample");
            t.compare(e.beamModeToken, "constant wavelength", "The lesson uses constant wavelength");
            t.compare(e.radiationProbeToken, "neutron", "The lesson uses neutrons");
        } else if (index === 7) {
            const parameters = Probe.rows(p.currentExperiment.instrument);
            const wavelength = parameters.find(row => row.name === "setup_wavelength" || (row.parameter && row.parameter.name === "setup_wavelength"));
            t.verify(wavelength !== undefined, "The real instrument exposes the lesson's wavelength parameter");
            wavelength.parameter.value = 1.494;
            t.compare(wavelength.parameter.value, 1.494, "The stated wavelength is 1.494 angstroms");
        } else if (index === 8) {
            const links = Probe.rows(p.currentExperiment.linkedStructures);
            t.verify(links.length === 1 && links[0].structureId === "lbco", "The stated lbco structure is linked to the simulation");
        } else {
            settle(t, p);
            t.verify(Probe.rows(p.currentExperiment.pattern).some(row => Number.isFinite(row.intensityCalc) && row.intensityCalc > 0),
                     "The final simulation state contains an actual nonzero calculated pattern");
        }
        settle(t, p);
        return;
    }
    if (index === 0) {
        t.verify(p.description.length > 0, "The Fitting lesson starts with its real example description");
        t.verify(Ui.find(Ui.windowRoot(app), "workflow.project.mainContent") !== null,
                 "The example's description page is visible before Next");
    } else if (index === 1) {
        let ba = Probe.rows(p.currentStructure.atomSiteAdps).find(site => site.label === "Ba");
        t.verify(ba !== undefined, "The stated example contains Ba's displacement parameter");
        ba.adpIso.free = true;
        // A supplied example may already satisfy the lesson; do not add a duplicate constraint.
        if (ba.adpIso.free) {
            const aliases = p.analysis.aliases;
            for (const [id, atom] of [["tutorial_la", "La"], ["tutorial_ba", "Ba"]]) {
                aliases.append();
                const row = Probe.rows(aliases).length - 1;
                t.verify(aliases.setText(row, "id", id), "The learner names the displacement alias");
                t.verify(aliases.setText(row, "parameter", "lbco.atom_site." + atom + ".adp_iso"),
                         "The displacement alias names the actual lesson atom");
            }
            const constraints = p.analysis.constraints;
            constraints.append();
            const row = Probe.rows(constraints).length - 1;
            t.verify(constraints.setText(row, "expression", "tutorial_ba = tutorial_la"),
                     "The learner declares the tutorial's actual shared displacement constraint");
        }
        settle(t, p);
        ba = Probe.rows(p.currentStructure.atomSiteAdps).find(site => site.label === "Ba");
        ba.adpIso.free = true;
        t.verify(!ba.adpIso.free && Probe.rows(p.analysis.constraints).length > 0,
                 "The stated dependent Ba displacement refuses a real attempt to free it");
    } else if (index === 2) {
        p.currentExperiment.backgroundEstimateMode = "auto";
        t.compare(p.currentExperiment.backgroundEstimateMode, "auto", "The stated automatic background mode is selected");
    } else if (index === 3 || index === 6) {
        t.verify(p.estimateBackground(), "The learner estimates the real measured background before Next");
        settle(t, p);
        t.verify(Probe.rows(p.currentExperiment.background).length > 1, "The stated estimated background has actual points");
    } else if (index === 4) {
        const parameters = Probe.rows(p.parameters).map(row => row.parameter);
        t.verify(p.setParametersFree(parameters, true), "The learner frees every fittable parameter through the real app edit");
        t.verify(parameters.filter(item => item.fittable && item.refinable).every(item => item.free), "The written free-column state holds before Next");
    } else if (index === 5 || index === 7) {
        settle(t, p);
        p.fit.start();
        t.verify(p.fit.running, "The fitting lesson starts the actual fit worker");
        t.tryCompare(p.fit, "running", false, 10000, "The fitting lesson waits for an actual completed fit");
        t.verify(p.fit.canUndo && p.fit.status.length > 0, "The stated completed fit has a published result: " + p.fit.outcome + " " + p.lastError);
    } else {
        settle(t, p);
        t.verify(Probe.rows(p.currentExperiment.pattern).some(row => Number.isFinite(row.intensityCalc)),
                 "The last Fitting step displays the actual calculated and measured pattern");
    }
    settle(t, p);
}
