import QtQuick
import "UiInteraction.js" as Ui
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiSymmetryReference 1.0
import "SignalContract.js" as SignalContract
import "ExperimentText.js" as ExperimentText
import "../../fixtures/e04_t1/oracle.js" as Oracle

TestCase {
    id: test
    name: "E04T1Acceptance"
    when: windowShown
    property var appWindow
    // A JS field records evaluations without creating a QML NOTIFY dependency
    // on the counter itself (which would manufacture a binding loop).
    property var unrelatedEvaluations: ({
            count: 0
        })
    property var unrelatedParameter: null
    property real unrelatedValue: {
        if (!unrelatedParameter)
            return 0;
        unrelatedEvaluations.count++;
        return unrelatedParameter.value;
    }
    Component {
        id: application
        Main {}
    }

    function initTestCase() {
        failOnWarning(/.*/);
        appWindow = application.createObject(null);
        verify(appWindow !== null, "gate 2: production Main loads under the actual registered module");
    }
    function init() {
        failOnWarning(qtest_results.functionName === "test_add_requires_explicit_complete_experiment_type"
            ? /\A(?!QRhiGles2: Failed to create (?:temporary context|context)\z)[\s\S]*\z/ : /.*/);
        Probe.clearWatches();
        unrelatedParameter = null;
        Session.closeProject();
    }
    function cleanupTestCase() {
        Probe.clearWatches();
        Session.closeProject();
        verify(waitForRendering(appWindow.contentItem), "I10: pending page loads settle before the test window is destroyed");
        appWindow.destroy();
    }
    function open(path) {
        Session.openProject(Probe.repoUrl(path));
        verify(Session.hasProject, "gate 3: committed project loads: " + path + " " + Session.lastError);
        return Session.project;
    }
    function example(index) {
        const project = open("docs/user/cli/" + Oracle.frozen.examples[index].id + "/project");
        tryVerify(() => Probe.computedCurrent(project.currentExperiment), 10000,
                  "I9: the committed example completes its initial calculation");
        return project;
    }
    function rows(model) {
        return Probe.rows(model);
    }
    function fieldNames(model) {
        return rows(model).map(r => r.parameter.name);
    }
    function visibleControl(name) {
        return Ui.control(Probe, appWindow, name);
    }
    function click(name) {
        Ui.click(test, Probe, appWindow, name);
    }

    function ordered(actual, expected, requirement) {
        compare(JSON.stringify(actual), JSON.stringify(expected), requirement);
    }
    function tokens(model) {
        return rows(model).map(r => r.token);
    }
    function onlyEvents(handle, names, requirement) {
        const events = Probe.events(handle);
        compare(SignalContract.violation(events, names), "", requirement);
        return events;
    }
    function findParameter(project, path) {
        const matches = rows(project.parameters).filter(r => r.path === path);
        compare(matches.length, 1, "I4: each canonical parameter path resolves exactly once: " + path);
        return matches[0].parameter;
    }
    function categories(model, expected) {
        const actual = rows(model);
        ordered(actual.map(r => [r.categoryId, r.tier]), expected, "I7: category identities, presentation tiers and order equal frozen declarations");
        compare(new Set(actual.map(r => r.categoryId)).size, actual.length, "I7: every present category occurs exactly once");
        return actual;
    }
    function test_loaded_category_models_and_type_change() {
        // CW -> TOF -> CW in ONE session, deliberately without closing between opens.
        for (let i = 0; i < Oracle.frozen.examples.length; ++i) {
            const expected = Oracle.frozen.examples[i];
            const project = example(i);
            const structure = project.currentStructure;
            const experiment = project.currentExperiment;
            categories(structure.categories, [["space_group", "Basic"], ["cell", "Basic"], ["atom_site", "Basic"], ["atom_site_aniso", "Basic"], ["scattering_length", "Extras"]]);
            //  owner-confirmed ADR-0017 §3: Measured data is Extras;
            // Background precedes Instrument. All other membership/order stays exact.
            const expCategories = [["experiment_type", "Basic"], ["data", "Extras"], ["background", "Basic"], ["instrument", "Basic"], ["peak", "Basic"], ["excluded_region", "Basic"], ["linked_structure", "Basic"], ["absorption", "Extras"]];
            if (i !== 1)
                expCategories.push(["preferred_orientation", "Extras"]);
            expCategories.push(["scattering_source", "Extras"]);
            //  note 6: the SEPD and D20 files carry _refln.id;
            // the HRPT fixture does not. Keep the exact order and absence check.
            if (i !== 0)
                expCategories.push(["refln", "Extras"]);
            const actual = categories(experiment.categories, expCategories);
            const counts = {
                background: expected.background,
                excluded_region: expected.excluded,
                linked_structure: 1,
                preferred_orientation: expected.texture
            };
            Object.keys(counts).forEach(key => {
                if (counts[key] !== undefined)
                    compare(actual.find(r => r.categoryId === key).itemCount, counts[key], "I7: category row counts come from committed project loops: " + key);
            });
            categories(project.analysis.categories, [["minimizer", "Extras"], ["fitting_mode", "Extras"], ["joint_fit", "Extras"]]);
            // : the frozen universe is retained in the editors, while Analysis
            // omits the symmetry-dependent subset supplied independently by crysta.
            const dependent = SymmetryOracle.structure(Probe.repoUrl("docs/user/cli/" + expected.id + "/project").toString().replace("file://", "")).filter(row => !row.independent);
            verify(dependent.length > 0, "I15/: independent reference supplies symmetry-dependent fields");
            const dependentFree = dependent.filter(row => row.category === "cell" ? expected.structureScalars["_cell." + row.name].free : expected.structureLoops.atom_site.find(atom => atom.id === row.row)[row.name].free).length;
            const analysisRows = expected.rows - dependent.length;
            const analysisFree = expected.free - dependentFree;
            compare(rows(project.parameters).length, analysisRows, "I15/: Analysis retains exactly the frozen universe minus crysta's dependent fields");
            compare(project.parameters.freeCount, analysisFree, "I7/: bracket-derived free count excludes dependent fields");
            compare(project.parameters.fixedCount, analysisRows - analysisFree, "I7/: independent fixed count complements independent free count");
            const atoms = rows(structure.atomSites);
            compare(atoms.length, expected.atoms, "I7: all committed atoms are shown");
            const atomFields = {
                fractX: "fract_x",
                fractY: "fract_y",
                fractZ: "fract_z",
                occupancy: "occupancy",
                adpIso: "adp_iso"
            };
            atoms.forEach((atom, index) => {
                const frozen = expected.structureLoops.atom_site[index];
                compare(atom.label, frozen.id, "I7: atom order and label match the committed loop");
                compare(atom.typeSymbol, frozen.type_symbol, "I7: atom species matches the committed loop");
                compare(atom.wyckoffLetter, frozen.wyckoff_letter, "I7: Wyckoff letter matches the committed loop");
                compare(atom.adpType, frozen.adp_type, "I7: displacement type matches the committed loop");
                Object.keys(atomFields).forEach(role => {
                    const value = frozen[atomFields[role]];
                    compare(atom[role].value, value.value, "I7: every atom parameter retains its committed value");
                    compare(atom[role].free, value.free, "I7: every atom parameter retains its free flag");
                });
            });
            const cellFields = {
                lengthA: "length_a",
                lengthB: "length_b",
                lengthC: "length_c",
                angleAlpha: "angle_alpha",
                angleBeta: "angle_beta",
                angleGamma: "angle_gamma"
            };
            Object.keys(cellFields).forEach(role => {
                const frozen = expected.structureScalars["_cell." + cellFields[role]];
                compare(structure.cell[role].value, frozen.value, "I7: all cell fields equal committed values");
                compare(structure.cell[role].free, frozen.free, "I7: all cell fields retain free flags");
            });
            compare(project.name, expected.projectScalars["_metadata.name"], "I7: Project Description uses loaded metadata");
            compare(structure.spaceGroup.nameHM, expected.spaceGroup, "I7: loaded space-group spelling");
            compare(structure.spaceGroup.coordSystemCode, expected.code, "I7: loaded setting code");
            compare(structure.spaceGroup.crystalSystem, expected.system, "I7: International Tables crystal system");
            ["minimum", "maximum", "step", "points"].forEach((name, j) => fuzzyCompare(experiment.measuredRange[name], expected.range[j], 1e-12, "seam 9: nominal range and nonuniform D20 axis: " + name));
        }
    }
    function test_all_committed_profiles_and_current_experiment() {
        Oracle.frozen.corpus.forEach(expected => {
            const project = open(expected.project);
            const experiments = rows(project.experiments);
            const index = experiments.findIndex(r => r.name === expected.experiment);
            verify(index >= 0, "I7: frozen experiment exists in the project");
            project.currentExperimentIndex = index;
            const experiment = project.currentExperiment;
            compare(experiment.name, expected.experiment, "I7: current-experiment selection changes the rendered object");
            compare(experiment.peakType, expected.peakType, "I7: the selector shows the loaded profile");
            ordered(fieldNames(experiment.instrument), expected.instrumentFields, "I15: mode-specific instrument fields");
            const peakRows = rows(experiment.peak).concat(rows(experiment.peakAsymmetry));
            const wanted = expected.peakFields.concat(expected.unusedFreeFields);
            ordered(peakRows.map(r => r.parameter.name).sort(), wanted.slice().sort(), "I15: no inert storage fields, no hidden free parameters");
            peakRows.forEach(row => {
                const frozen = expected.scalars["_peak." + row.parameter.name];
                verify(frozen !== undefined, "I7: displayed peak field has an independent fixture value");
                compare(row.parameter.value, frozen.value, "I7: displayed value equals project text");
                compare(row.parameter.free, frozen.free, "I7: displayed free flag equals bracket rule");
                compare(row.usedByProfile, !expected.unusedFreeFields.includes(row.parameter.name), "I15: unused free storage is explicitly marked");
            });
            rows(experiment.instrument).forEach(row => {
                const frozen = expected.scalars["_instrument." + row.parameter.name];
                compare(row.parameter.value, frozen.value, "I7: every instrument value equals the committed input");
            });
            if (expected.loops.background !== undefined) {
                const background = rows(experiment.background);
                const frozenBackground = expected.loops.background;
                compare(background.length, frozenBackground.length, "I7: complete background loop is shown");
                background.forEach((row, index) => {
                    compare(row.position, frozenBackground[index].position.value, "I7: background abscissa is unchanged");
                    compare(row.intensity.value, frozenBackground[index].intensity.value, "I7: background ordinate is unchanged");
                    compare(row.intensity.free, frozenBackground[index].intensity.free, "I7: background free flag is unchanged");
                });
            }
            const prefix = expected.mode === "cwl" ? "cwl-" : "tof-";
            ordered(tokens(experiment.peakTypeOptions).sort(), Object.keys(Oracle.frozen.profiles).filter(p => p.startsWith(prefix)).sort(), "I17: exactly independently declared profiles for this loaded experiment type");
            ordered(tokens(experiment.backgroundTypeOptions), ["line-segment", "chebyshev", "polynomial"], "C13-T6: background selector offers all three declared families");
            ordered(tokens(project.analysis.minimizerTypeOptions), ["crysta"], "I17: minimizer selector offers exactly the supported engine");
            ordered(tokens(project.analysis.fittingModeOptions).sort(), ["independent", "joint", "sequential", "single"], "I17: fitting mode selector offers exactly the declared vocabulary");
            ordered(tokens(experiment.absorptionTypeOptions).sort(), (expected.mode === "cwl" ? ["none", "cylinder-hewat", "cylinder-lobanov"] : ["none", "cylinder"]).sort(), "I17: exactly the beam-scoped absorption families");
            compare(experiment.beamModeToken, expected.mode === "cwl" ? "constant wavelength" : "time-of-flight", "seam 7: spaced token and effective undeclared beam mode");
        });
    }
    function test_parameter_identity_uncertainty_ranges_and_units() {
        let project = example(0);
        const cell = project.currentStructure.cell;
        compare(cell.lengthA, findParameter(project, "structure.cell.length_a"), "I4: sidebar and Analysis share identity");
        compare(cell.lengthA.value, 3.88, "seam 1: no length conversion");
        compare(cell.lengthA.displayUnits, "Å", "seam 1: Angstrom presentation");
        compare(cell.angleGamma.value, 90, "seam 11: no radians cross the boundary");
        compare(cell.angleGamma.displayUnits, "deg", "seam 11: degree presentation");
        verify(!cell.lengthA.hasUncertainty, "seam 2: empty parentheses mean absent uncertainty");
        verify(cell.lengthB.hasUncertainty, "seam 2: bare fixed value carries present-zero uncertainty");
        compare(cell.lengthB.uncertainty, 0, "seam 2: present-zero remains distinguishable");
        const la = rows(project.currentStructure.atomSites)[0];
        compare(la.occupancy.minimum, 0, "seam 4: bounded occupancy lower endpoint");
        compare(la.occupancy.maximum, 1, "seam 4: bounded occupancy upper endpoint");
        compare(project.currentExperiment.scale.minimum, -Infinity, "seam 4: scale has no lower bound");
        compare(project.currentExperiment.scale.maximum, Infinity, "seam 4: scale has no upper bound");
        const absorption = rows(project.currentExperiment.absorption)[0].parameter;
        compare(absorption.minimum, 0, "seam 4: absorption is half bounded");
        compare(absorption.maximum, Infinity, "seam 4: absorption has no upper bound");
        project = example(1);
        compare(project.currentStructure.cell.lengthA.uncertainty, 0.001, "seam 2: decimal uncertainty expansion");
        compare(findParameter(project, "experiment.peak.decay_beta_0").uncertainty, 0.01, "seam 2: nonidentity decimal uncertainty expansion");
        compare(findParameter(project, "experiment.instrument.calib_d_to_tof_linear").value, 7476.91, "seam 1: TOF calibration retains stored units");
    }
    function test_invalid_write_is_silent_and_state_preserving() {
        const project = example(0);
        const occupancy = rows(project.currentStructure.atomSites)[0].occupancy;
        const handle = Probe.watch(occupancy);
        occupancy.value = 1.5;
        compare(occupancy.value, 0.5, "I6: refused write preserves state");
        compare(occupancy.lastError, "occupancy value 1.500000 is outside the declared admissible range [0.000000, 1.000000]", "I6: refusal matches Python's shared admissible-range message");
        const events = Probe.events(handle);
        verify(events.valueChanged === undefined, "I6: refused write emits no value change");
        Object.keys(events).forEach(name => compare(name, "lastErrorChanged", "I6: no state signal after refusal"));
    }
    function test_one_value_notifies_only_its_dependents() {
        const project = example(0);
        const parameterRows = rows(project.parameters);
        const targetRow = parameterRows.findIndex(r => r.path === "experiment.peak.broad_gauss_u");
        verify(targetRow >= 0, "I4: tested parameter exists");
        const target = parameterRows[targetRow].parameter;
        unrelatedParameter = project.currentStructure.cell.lengthA;
        const handles = parameterRows.map(r => Probe.watch(r.parameter));
        const tableWatch = Probe.watch(project.parameters);
        const projectWatch = Probe.watch(Session);
        const objectWatch = Probe.watch(project);
        const experimentWatch = Probe.watch(project.currentExperiment);
        const patternWatch = Probe.watch(project.currentExperiment.pattern);
        const before = unrelatedEvaluations.count;
        compare(project.modified, false, " saving: opening starts unmodified");
        target.value = 0.173;
        compare(target.value, 0.173, "I6: parameter write reaches the core");
        parameterRows.forEach((row, i) => onlyEvents(handles[i], i === targetRow ? ["valueChanged"] : [], "I3: a single value cannot refresh unrelated fields or objects: " + row.path));
        compare(unrelatedEvaluations.count, before, "I3: unrelated binding never re-evaluates");
        onlyEvents(projectWatch, [], "I5: a parameter write cannot replace Session.project");
        //  ADR-0017 §13: the first edit sets only the dependent dirty flag.
        compare(project.modified, true, " saving: a successful edit marks the project modified");
        onlyEvents(objectWatch, ["modifiedChanged"], "I3/: first edit changes only the project modified flag");
        onlyEvents(experimentWatch, [], "I3: a parameter write cannot refresh the whole experiment");
        const events = onlyEvents(tableWatch, ["dataChanged"], "I3: one table update, no reset/layout change");
        compare(events.dataChanged[0].first, targetRow, "I3: changed row starts at edited parameter");
        compare(events.dataChanged[0].last, targetRow, "I3: no other row is invalidated");
        ordered(events.dataChanged[0].roles, [Probe.roleNumber(project.parameters, "value")], "I3: only the changed value role is invalidated");
        tryVerify(() => Probe.events(patternWatch).dataChanged !== undefined, 5000, "I3/I9: a coalesced edit publishes a recalculated pattern");
        const patternEvents = onlyEvents(patternWatch, ["dataChanged", "staleChanged"], "I3: recalculation updates values and currentness without resetting axes");
        ordered(patternEvents.dataChanged[0].roles, [Probe.roleNumber(project.currentExperiment.pattern, "intensityCalc")], "I3: recalculation only invalidates intensityCalc");
        Probe.clearWatches();
        const noOp = Probe.watch(target);
        const modifiedWatch = Probe.watch(project);
        target.value = 0.173;
        onlyEvents(noOp, [], "I3: assigning the same value emits nothing");
        onlyEvents(modifiedWatch, [], "I3/: a no-op cannot re-notify the modified flag");
        target.value = 0.174;
        onlyEvents(noOp, ["valueChanged"], "I3: a later changed value still emits exactly once");
        onlyEvents(modifiedWatch, [], "I3/: an already modified project cannot re-notify its dirty flag");
    }
    function test_table_write_shares_parameter_identity() {
        const project = example(0);
        const table = rows(project.parameters);
        const row = table.findIndex(r => r.path === "experiment.peak.broad_gauss_u");
        const parameter = table[row].parameter;
        const handle = Probe.watch(parameter);
        verify(Probe.writeRole(project.parameters, row, "value", 0.247), "I6: Analysis table supports value edits");
        compare(parameter.value, 0.247, "I4: table edit reaches the same sidebar object");
        onlyEvents(handle, ["valueChanged"], "I3: table write has the same narrow notification contract");
    }
    function test_profile_and_absorption_round_trip() {
        let project = example(0);
        let exp = project.currentExperiment;
        const originalText = exp.text.text;
        const before = rows(exp.peak).map(r => [r.parameter.name, r.parameter.value, r.parameter.free]);
        exp.peakType = "cwl-thompson-cox-hastings";
        ordered(fieldNames(exp.peakAsymmetry), ["asym_fcj_1", "asym_fcj_2"], "I17: FCJ fields engage");
        rows(exp.peakAsymmetry).forEach(r => {
            compare(r.parameter.value, 0, "I17: new FCJ field uses loader default");
            verify(!r.parameter.free, "I17: new FCJ field starts fixed");
        });
        exp.peakType = "cwl-pseudo-voigt-berar-baldinozzi-asymmetry";
        ordered(fieldNames(exp.peakAsymmetry), Oracle.frozen.profiles[exp.peakType].slice(5), "I17: BeBa replaces FCJ");
        compare(rows(exp.peakAsymmetry)[4].parameter.value, 180, "I17: BeBa limit loader default");
        verify(!exp.text.text.includes("_peak.asym_fcj_"), "I17: disengaged fields disappear from persisted Text");
        exp.peakType = "cwl-pseudo-voigt";
        ordered(rows(exp.peak).map(r => [r.parameter.name, r.parameter.value, r.parameter.free]), before, "I17 D-j: profile switches retain shared values and free flags");
        verify(!exp.text.text.includes("_data.intensity_calc"), "I17: the returned profile is stale until its queued recalculation publishes");
        tryVerify(() => exp.text.text.includes("_data.intensity_calc"), 5000, "I17: the queued recalculation republishes the computed experiment text");
        compare(exp.text.text, originalText, "I17: profile round trip restores Experiment Text byte for byte");
        ["none", "cylinder-lobanov", "cylinder-hewat"].forEach(token => {
            exp.absorptionType = token;
            ordered(fieldNames(exp.absorption), token === "none" ? [] : ["mu_r"], "I17: absorption switches shown fields");
        });
        project.analysis.fittingMode = "joint";
        ordered(rows(project.analysis.jointWeights).map(r => [r.experiment, r.weight]), [["hrpt", 1]], "I17: joint mode exposes the current experiment's weight");
        project.analysis.fittingMode = "sequential";
        verify(rows(project.analysis.categories).some(r => r.categoryId === "sequential_fit"), "I17: scan declaration is shown");
        project.analysis.fittingMode = "single";
        categories(project.analysis.categories, [["minimizer", "Extras"], ["fitting_mode", "Extras"], ["joint_fit", "Extras"]]);
        ordered(rows(project.analysis.jointWeights).map(r => [r.experiment, r.weight]), [["hrpt", 1]], "I17/ note 6: single mode retains the joint table and excludes scan categories");
        project = example(1);
        exp = project.currentExperiment;
        exp.peakType = "tof-jorgensen";
        const unused = rows(exp.peak).filter(r => !r.usedByProfile);
        ordered(unused.map(r => r.parameter.name), ["broad_lorentz_gamma_1"], "I15: free Lorentzian survives Jorgensen switch");
        exp.peakType = "tof-pseudo-voigt";
        ordered(rows(exp.peak).filter(r => !r.usedByProfile).map(r => r.parameter.name).sort(), ["decay_beta_0", "decay_beta_1"], "I15: free decay fields survive pseudo-Voigt switch");
        exp.absorptionType = "cylinder";
        ordered(fieldNames(exp.absorption), ["abscor1", "abscor2"], "I17: TOF cylinder exposes the ABSCOR pair");
    }
    function test_pattern_and_saved_text_through_independent_surface() {
        // Frozen separate-surface regression pins, not independent physics claims.
        const references = Probe.reference();
        compare(references.length, 3, "I8/I9: unchanged Python surface produced every reference");
        const linkedSha = Probe.linkedCrystaSha();
        compare(linkedSha.length, 40, "I8: the app build carries a full linked crysta source stamp");
        const witness = references[0].texts["experiments/hrpt.edi"];
        const marker = "_data.calc_status\n";
        const start = witness.indexOf(marker) + marker.length;
        verify(start >= marker.length, "I8: calculated data loop has the declared status column");
        const firstRow = witness.substring(start, witness.indexOf("\n", start));
        const cells = firstRow.split(" ");
        const near = cells.slice();
        near[2] = String(Number(cells[2]) * (1 + 1e-14));
        compare(ExperimentText.problem(witness.replace(firstRow, near.join(" ")), witness), "", "I8: harmless last-digit calculated d-spacing variation is portable");
        const far = cells.slice();
        far[2] = String(Number(cells[2]) + 0.001);
        verify(ExperimentText.problem(witness.replace(firstRow, far.join(" ")), witness) !== "", "I8: material calculated d-spacing changes still fail");
        const measured = cells.slice();
        measured[3] = String(Number(cells[3]) + 1);
        verify(ExperimentText.problem(witness.replace(firstRow, measured.join(" ")), witness) !== "", "I8: measured data remains byte-exact");
        const status = cells.slice();
        status[7] = "excl";
        verify(ExperimentText.problem(witness.replace(firstRow, status.join(" ")), witness) !== "", "I8: calculation status remains byte-exact");
        const reflnStart = witness.indexOf("_refln.two_theta\n") + "_refln.two_theta\n".length;
        verify(reflnStart >= "_refln.two_theta\n".length, "I8: calculated reflection loop has the declared angle column");
        const firstRefln = witness.substring(reflnStart, witness.indexOf("\n", reflnStart));
        const refln = firstRefln.split(" ");
        const reflnNear = refln.slice();
        reflnNear[7] = String(Number(refln[7]) * (1 + 1e-14));
        compare(ExperimentText.problem(witness.replace(firstRefln, reflnNear.join(" ")), witness), "", "I8: harmless last-digit reflection variation is portable");
        const reflnFar = refln.slice();
        reflnFar[7] = String(Number(refln[7]) + 0.001);
        verify(ExperimentText.problem(witness.replace(firstRefln, reflnFar.join(" ")), witness) !== "", "I8: material reflection changes still fail");
        verify(!witness.includes("_edi.calc_fingerprint") && !witness.includes("_edi.calc_version"), " unit 0 the Python writer reference carries no retired calculation identity");
        const structureWitness = references[1].texts["structures/si.edi"];
        const atomMarker = "_expanded_atom_site.cluster_id\n";
        const atomStart = structureWitness.indexOf(atomMarker) + atomMarker.length;
        verify(atomStart >= atomMarker.length, ": structure witness declares the expanded-atom columns");
        const atomRow = structureWitness.substring(atomStart, structureWitness.indexOf("\n", atomStart));
        const atomCells = atomRow.split(" ");
        for (const column of [6, 7, 8]) {
            const nearAtom = atomCells.slice();
            nearAtom[column] = String(Number(atomCells[column]) + 1e-13);
            compare(ExperimentText.structureProblem(structureWitness.replace(atomRow, nearAtom.join(" ")), structureWitness), "", ": last-digit Cartesian variation is portable");
            const farAtom = atomCells.slice();
            farAtom[column] = String(Number(atomCells[column]) + 0.001);
            verify(ExperimentText.structureProblem(structureWitness.replace(atomRow, farAtom.join(" ")), structureWitness) !== "", ": material Cartesian changes fail");
        }
        const atomId = atomCells.slice();
        atomId[0] = "changed-id";
        verify(ExperimentText.structureProblem(structureWitness.replace(atomRow, atomId.join(" ")), structureWitness) !== "", ": expanded-atom identity remains byte-exact");
        const atomSpacing = atomCells.join("  ");
        verify(ExperimentText.structureProblem(structureWitness.replace(atomRow, atomSpacing), structureWitness) !== "", ": expanded-atom row spacing remains byte-exact");
        const bondMarker = "_geom_bond.distance\n";
        const bondStart = structureWitness.indexOf(bondMarker) + bondMarker.length;
        verify(bondStart >= bondMarker.length, ": structure witness declares the bond-distance column");
        const bondRow = structureWitness.substring(bondStart, structureWitness.indexOf("\n", bondStart));
        const bondCells = bondRow.split(" ");
        const nearBond = bondCells.slice();
        nearBond[7] = String(Number(bondCells[7]) + 1e-13);
        compare(ExperimentText.structureProblem(structureWitness.replace(bondRow, nearBond.join(" ")), structureWitness), "", ": last-digit bond-distance variation is portable");
        const farBond = bondCells.slice();
        farBond[7] = String(Number(bondCells[7]) + 0.001);
        verify(ExperimentText.structureProblem(structureWitness.replace(bondRow, farBond.join(" ")), structureWitness) !== "", ": material bond-distance changes fail");
        const bondLabel = bondCells.slice();
        bondLabel[3] = "changed-label";
        verify(ExperimentText.structureProblem(structureWitness.replace(bondRow, bondLabel.join(" ")), structureWitness) !== "", ": bond labels remain byte-exact");
        verify(ExperimentText.structureProblem(structureWitness.replace("_geom_bond.distance", "_geom_bond.separation"), structureWitness) !== "", ": structure column declarations remain byte-exact");
        references.forEach((reference, index) => {
            const project = example(index);
            const experiment = project.currentExperiment;
            tryCompare(experiment.pattern, "count", reference.axis.length, 5000, "I9: initial project calculation publishes its pattern");
            const pattern = rows(experiment.pattern);
            compare(pattern.length, reference.axis.length, "I9: pattern point count equals Python calculate");
            for (let point = 0; point < pattern.length; ++point) {
                compare(pattern[point].x, reference.axis[point], "I9: sample axis is unchanged");
                compare(pattern[point].intensityCalc, reference.calculated[point], "I9: every calculated sample equals the unchanged Python surface");
            }
            const expected = Oracle.frozen.examples[index];
            compare(ExperimentText.structureProblem(project.currentStructure.text.text, reference.texts["structures/" + expected.structure + ".edi"]), "", "I8: structure Text keeps exact writer fields and tolerant calculated columns");
            const frozenExperiment = reference.texts["experiments/" + expected.experiment + ".edi"];
            compare(ExperimentText.problem(experiment.text.text, frozenExperiment), "", " experiment Text equals Python writer bytes without identity masking");
            compare(project.analysis.text.text, reference.texts["analysis/analysis.edi"], "I8: Analysis Text equals the Python writer bytes");
        });
    }
    function test_encoded_url_and_unused_free_field() {
        Session.openProject(Probe.referenceUrl("p q/project"));
        verify(Session.hasProject, "seam 13: an encoded-space local URL loads successfully");
        compare(Session.project.currentExperiment.name, "hrpt", "seam 13: local path decoding selects the right project");
        Session.openProject(Probe.referenceUrl("unused-free"));
        verify(Session.hasProject, "I15: unused-free witness loads");
        const peak = rows(Session.project.currentExperiment.peak);
        const field = peak.find(r => r.parameter.name === "broad_lorentz_gamma_1");
        verify(field !== undefined, "I15: an unused free Lorentzian field must remain visible");
        verify(!field.usedByProfile, "I15: an unused free field is marked unused by the profile");
        compare(field.parameter.value, 0.1, "I15: unused field retains its loaded value");
        verify(rows(Session.project.parameters).some(r => r.parameter === field.parameter), "I15: Analysis includes the same unused free parameter object");
    }
    function test_loaded_edi_blocks_and_refused_duplicate() {
        Session.createProject("loaded-blocks", " declared .edi input");
        verify(Session.hasProject, "D12: an empty project is available for block loading");
        const project = Session.project;
        verify(project.canLoadStructure, "D12: an empty project permits its first structure");
        const base = "docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project/";
        verify(project.loadStructure(Probe.repoUrl(base + "structures/lbco.edi")), "D12: a committed .edi structure block loads through the core");
        verify(project.canLoadStructure, "C12-T4: a loaded project permits another distinct structure");
        compare(project.currentStructure.spaceGroup.nameHM, "P m -3 m", "D12: loaded structure categories retain file values");
        verify(project.loadExperiments([Probe.repoUrl(base + "experiments/hrpt.edi")]), "D12: a complete .edi experiment loads with its declared type");
        compare(project.currentExperiment.beamModeToken, "constant wavelength", "D12: loaded CW type is preserved");
        const oldCount = rows(project.experiments).length;
        verify(!project.loadExperiments([Probe.repoUrl(base + "experiments/hrpt.edi")]), "D12: duplicate block identity is refused");
        compare(rows(project.experiments).length, oldCount, "D12: duplicate refusal does not mutate the collection");
        verify(project.loadExperiments([Probe.repoUrl("docs/user/cli/pd-neut-tof_si-sepd_start-2/project/experiments/sepd.edi")]), "D12: a complete TOF .edi block loads without changing its type");
        compare(project.currentExperiment.beamModeToken, "time-of-flight", "D12: the newly loaded experiment becomes current");
        verify(!rows(project.currentExperiment.categories).some(r => r.categoryId === "preferred_orientation"), "I7: selecting the loaded TOF block removes the CW-only category");
        ordered(fieldNames(project.currentExperiment.instrument), Oracle.frozen.instrument.tof, "I7: block-file loading uses the same frozen TOF field expectation");
        verify(!project.loadStructure(Probe.repoUrl(base + "structures/lbco.edi")), "C12-T4: a duplicate structure identity is refused without replacement");
        compare(rows(project.structures).length, 1, "D12: refused second structure preserves the first");
    }
    function test_edi_batch_refusals_are_atomic() {
        const project = open("docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/project");
        const before = rows(project.experiments).map(r => r.name);
        const current = project.currentExperiment;
        const third = Probe.repoUrl("docs/user/cli/pd-neut-tof_ncaf-wish-3bank_start-5/project/experiments/wish_2_9.edi");
        ["d20.cif", "d20.edi"].forEach(file => {
            const watch = Probe.watch(project.experiments);
            verify(!project.loadExperiments([third, Probe.referenceUrl(file)]), "I18: wrong extension or classic CIF content refuses the entire .edi batch");
            verify(Session.lastError.includes(file), "I18: refusal identifies its offending input");
            ordered(rows(project.experiments).map(r => r.name), before, "I18: failed batch inserts no earlier valid file");
            compare(project.currentExperiment, current, "I18: failed batch preserves current experiment identity");
            onlyEvents(watch, [], "I18: a refused batch emits no model update");
        });
        verify(!project.loadExperiments([third, third]), "I18: duplicates within a new batch refuse atomically");
        ordered(rows(project.experiments).map(r => r.name), before, "I18: batch-local duplicate inserts nothing");
        const sessionWatch = Probe.watch(Session);
        const modelWatch = Probe.watch(project.experiments);
        verify(project.loadExperiments([third]), "I18: valid NCAF third bank loads through the GUI view-model");
        compare(rows(project.experiments).length, 3, "seam 19: successful add produces three experiments");
        compare(project.currentExperiment.name, "wish_2_9", "seam 19: added third bank is current");
        compare(project.currentExperiment.beamModeToken, "time-of-flight", "I18: loaded type is unchanged");
        const signals = Probe.events(modelWatch);
        verify(signals.modelReset === undefined && signals.layoutChanged === undefined, "I5/I18: block addition extends models without a reset");
        verify(signals.rowsInserted !== undefined, "I18: block addition uses row insertion");
        verify(Probe.events(sessionWatch).projectChanged === undefined, "I5: adding a block cannot replace the whole project");
        verify(rows(project.parameters).some(r => r.path === "experiments[wish_2_9].instrument.calib_d_to_tof_linear"), "seam 5/I18: added bank extends canonical parameter identities");
    }
    function test_add_requires_explicit_complete_experiment_type() {
        const project = open("docs/user/cli/pd-neut-tof_ncaf-wish-2bank_start-3/project");
        const before = rows(project.experiments).map(r => r.name);
        const current = project.currentExperiment;
        const complete = Probe.repoUrl("docs/user/cli/pd-neut-tof_ncaf-wish-3bank_start-5/project/experiments/wish_2_9.edi");
        const dream = Probe.repoUrl("docs/user/cli/pd-neut-tof_diamond-dream_basic/project/experiments/dream.edi");
        const incomplete = [dream].concat(["sample_form", "beam_mode", "radiation_probe", "scattering_type"].map(axis => Probe.referenceUrl("missing-" + axis + ".edi")));
        incomplete.forEach(file => {
            [[file], [complete, file]].forEach(batch => {
                const watch = Probe.watch(project.experiments);
                verify(!project.loadExperiments(batch), "I18/review F1: add-from-file requires all four explicit experiment-type axes");
                verify(Session.lastError.length > 0, "I18: declaration refusal explains the failed input");
                ordered(rows(project.experiments).map(r => r.name), before, "I18: missing type leaves every existing and staged row untouched");
                compare(project.currentExperiment, current, "I18: refused type declaration preserves selection");
                onlyEvents(watch, [], "I18: missing declaration never emits an insertion or reset");
            });
        });
        verify(project.loadExperiments([complete]), "I18: the fully declared NCAF block is the positive control");
        compare(rows(project.experiments).length, 3, "I18: valid declared type appends exactly one row");
        const legacy = open("docs/user/cli/pd-neut-tof_diamond-dream_basic/project");
        compare(legacy.currentExperiment.beamModeToken, "time-of-flight", "I18 boundary: whole-project loading retains prior loader-derived type behavior");
    }
    function test_nonlocal_urls_preserve_project() {
        const project = example(0);
        ["https://example.org/p", "qrc:/x"].forEach(url => {
            Session.openProject(url);
            compare(Session.project, project, "seam 13: nonlocal URL refusal preserves project identity");
            verify(Session.lastError.includes(url), "seam 13: URL refusal identifies the unsupported URL");
        });
    }
    function test_smoke_all_pages_and_disabled_experiment_type() {
        Oracle.frozen.examples.forEach((expected, index) => {
            example(index);
            ["home", "project", "structure", "experiment", "analysis", "report"].forEach(page => {
                click("appBar.tab." + page);
                if (page !== "home") {
                    ["basic", "text"].forEach(tab => click("sideBar.tab." + tab));
                    if (["structure", "experiment", "analysis"].includes(page))
                        click("sideBar.tab.extras");
                }
            });
            click("appBar.tab.experiment");
            click("sideBar.tab.basic");
            Ui.expandGroup(test, Probe, appWindow, "group.experiment_type");
            ["sampleForm", "beamMode", "radiationProbe", "scatteringType"].forEach(axis => {
                tryVerify(() => visibleControl("experimentType." + axis) !== null, 2000, "owner seq 2: each immutable axis is exposed after group expansion: " + axis);
                const control = visibleControl("experimentType." + axis);
                verify(control !== null, "owner seq 2: experiment axis is a visible combo box: " + axis);
                verify(!control.enabled, "owner seq 2: loaded experiment type cannot be edited: " + axis);
                verify(control.currentIndex !== undefined && control.model !== undefined, "owner seq 2: read-only axes retain the combo-box presentation");
            });
        });
        compare(appWindow.title, ApplicationInfo.name, "I12: window identity comes from ApplicationInfo");
        compare(ApplicationInfo.name, "EasyDiffraction", "I12: no base fallback brand");
        verify(ApplicationInfo.version.length > 0, "I12: configured app version is present");
    }
}
