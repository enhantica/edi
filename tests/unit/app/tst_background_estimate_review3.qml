import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

TestCase {
    id: test
    name: "BackgroundReview3"
    when: windowShown
    property var appWindow
    Component { id: application; Main {} }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Fitted-baseline acceptance must use the production app window");
        verify(waitForRendering(appWindow.contentItem), "The fit worker's production window must render");
    }
    function cleanup() {
        Session.closeProject();appWindow.destroy();Probe.releaseScratchProjects();
    }
    function rows(kind) {
        const exp = Session.project.currentExperiment;
        return Probe.rows(kind === "line-segment" ? exp.background : exp.backgroundTerms).map(row =>
            kind === "line-segment" ? [String(row.id), row.position, row.intensity.value, row.intensity.free] :
                                      [String(row.id), row.order, row.coef.value, row.coef.free]);
    }
    function ready() {
        tryVerify(() => !Session.project.calculating && !Session.project.currentExperiment.pattern.stale,
                  1000, "A fitted Auto background must publish its calculated pattern; reason: " + Session.project.lastError);
    }
    function expectedBackground(kind, anchors, x) {
        if (kind === "line-segment") {
            if (x <= anchors[0][1]) return anchors[0][2];
            for (let i = 1; i < anchors.length; ++i) {
                if (x <= anchors[i][1]) {
                    const a = anchors[i - 1], b = anchors[i];
                    return a[2] + (b[2] - a[2]) * (x - a[1]) / (b[1] - a[1]);
                }
            }
            return anchors[anchors.length - 1][2];
        }
        const z = kind === "polynomial" ? x / 80 - 1 : 2 * (x - 8.0953) / (149.7953 - 8.0953) - 1;
        return anchors.reduce((sum, row) => {
            let term = Math.pow(z, row[1]);
            if (kind === "chebyshev") {
                let a = 1, b = z;
                for (let j = 2; j <= row[1]; ++j) { const next = 2 * z * b - a; a = b; b = next; }
                term = row[1] === 0 ? 1 : b;
            }
            return sum + row[2] * term;
        }, 0);
    }
    function pattern(kind) {
        const actual = Probe.rows(Session.project.currentExperiment.pattern).filter(row => row.calcStatus === "incl");
        verify(actual.length > 100 && actual.every(row => isFinite(row.intensityCalc) && isFinite(row.intensityBkg)),
               "Fitting free Auto background rows must retain a finite included calculated pattern");
        verify(actual.some(row => Math.abs(row.intensityCalc - row.intensityBkg) > 1e-5),
               "The Auto fit must exercise nonzero calculated crystal peaks, not a zero-scale model");
        const anchors = rows(kind);
        verify(actual.every(row => Math.abs(row.intensityBkg - expectedBackground(kind, anchors, row.x)) <=
                           1e-7 + 1e-9 * Math.abs(row.intensityBkg)),
               "The app calculated background must evaluate its actual fitted point or term values");
        return actual;
    }
    function assertRows(actual, expected, why) {
        compare(actual.length, expected.length, why + ": row count");
        actual.forEach((row, i) => {
            compare(row[0], String(expected[i][0]), why + ": stable row id");
            compare(row[1], expected[i][1], why + ": position/order");
            verify(Math.abs(row[2] - expected[i][2]) <= 1e-7 + 1e-9 * Math.abs(expected[i][2]),
                   why + ": fitted row " + i + " actual=" + row[2] + " expected=" + expected[i][2] + " (1e-7 absolute plus 1e-9 relative)");
            compare(row[3], expected[i][3], why + ": free flag");
        });
    }
    function state() {
        const e = Session.project.currentExperiment;
        return {type: e.backgroundType, mode: e.backgroundEstimateMode,
                origin: e.backgroundOrigin, low: e.backgroundXMin, high: e.backgroundXMax,
                points: Probe.rows(e.background).map(r => [String(r.id), r.position, r.intensity.value, r.intensity.free]),
                terms: Probe.rows(e.backgroundTerms).map(r => [String(r.id), r.order, r.coef.value, r.coef.free])};
    }
    function open(kind, mode, second, simulation, bounded) {
        // Lifecycle-only subsets keep the unchanged per-test deadline; full
        // fit-pin and delegated/basis comparisons keep their full measured grid.
        const family = (second && simulation) || bounded ? "fitted-auto-fast-" : "fitted-auto-";
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/" + family + kind));
        if (second) {
            let text = SettingsProof.text(input, "experiments/d20.edi").replace("data_d20", "data_other");
            text = text.replace("_background_estimate.mode auto", "_background_estimate.mode manual");
            text = text.replace(/([0-9.])\([^)]*\)/g, "$1");
            if (simulation) text = text.split("loop_\n_data.two_theta\n")[0] +
                "_data_range.two_theta_min 8.0953\n_data_range.two_theta_max 149.7953\n_data_range.two_theta_step 0.1\n";
            verify(SettingsProof.write(input, "experiments/other.edi", text),
                   "The app fixture must add a second actual current or simulation bank");
        }
        if (mode === "joint") verify(SettingsProof.write(input, "analysis/analysis.edi",
            SettingsProof.text(input, "analysis/analysis.edi").replace("_fitting_mode.type single", "_fitting_mode.type joint")),
            "The app must load the declared joint fitting path");
        verify(Session.openProject(input), "The app must load the disposable typed lifecycle input: " + Session.lastError);
        ready();return input;
    }
    function typeTransition(source, target) {
        open(source, "single", false, false, true);
        Session.project.currentExperiment.backgroundType = target;
        ready();
        compare(Session.project.currentExperiment.backgroundType, target,
                "The app's supported type selection must retain the requested type");
        compare(Session.project.currentExperiment.backgroundEstimateMode, "auto",
                "A supported type edit must not require recovery through Manual mode");
        verify(rows(target).length > 0, "Auto must estimate the newly selected type instead of refusing its own selector edit");
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "An automatic type transition must remain saveable: " + Session.lastError);
        console.log("BACKGROUND_REVIEW3_SAVED " + JSON.stringify({kind: target, state: state(),
            file: SettingsProof.text(destination, "experiments/d20.edi")}));
        console.log("BACKGROUND_REVIEW3 transition " + source + " " + target);
    }
    function undoSaveParameters() {
        const e = Session.project.currentExperiment;
        const points = e.backgroundType === "line-segment";
        return Probe.rows(points ? e.background : e.backgroundTerms).map(row => {
            const p = points ? row.intensity : row.coef;
            return {id: String(row.id), value: p.value, free: p.free,
                    hasUncertainty: p.hasUncertainty, uncertainty: p.uncertainty,
                    refinable: p.refinable};
        });
    }
    function backgroundDescriptors(s) {
        return {type: s.type, mode: s.mode, origin: s.origin, low: s.low, high: s.high,
                points: s.points.map(row => [row[0], row[1], row[3]]),
                terms: s.terms.map(row => [row[0], row[1], row[3]])};
    }
    function undoTransition(source, target) {
        open(source, "single", false, false, true);
        Session.project.currentExperiment.backgroundEstimateMode = "manual";ready();
        const original = JSON.stringify(state());
        verify(Session.project.estimateBackground(), "The actual Estimate action must record one undoable typed background");
        ready();
        Session.project.currentExperiment.backgroundType = target;ready();
        const before = JSON.stringify(state());
        Session.project.undo();
        const after = JSON.stringify(state());
        if (Session.project.lastError.length > 0) {
            compare(after, before, "Refusing an incompatible Estimate Undo must leave the current type and rows atomic");
            verify(/background|type/i.test(Session.project.lastError),
                   "An incompatible Estimate Undo refusal must name the type reason");
        } else compare(after, original,
            "Estimate Undo after a type edit must restore the entire prior typed background");
        ready();
        const expected = JSON.stringify(state()), destination = Probe.scratchProjectUrl();
        const preSave = {state: JSON.parse(expected), parameters: undoSaveParameters(),
                         suRule: Session.project.suRule};
        console.log("BACKGROUND_REVIEW3_UNDO_BEFORE_SAVE " + JSON.stringify(preSave));
        verify(preSave.parameters.every(p => p.refinable && isFinite(p.value)
               && typeof p.hasUncertainty === "boolean" && isFinite(p.uncertainty)),
               "Typed Undo supplies complete ordinary scalar parameter witnesses before Save");
        verify(Session.saveAs(destination), "Typed Undo must leave a valid saveable background: " + Session.lastError);
        const published = state();
        const parameters = undoSaveParameters();
        // The complementary existing Python owner judges every value/SU against
        // PRE-Save numbers and the committed independent decimal reference.
        console.log("BACKGROUND_REVIEW3_SAVED " + JSON.stringify({kind: published.type, state: published,
            file: SettingsProof.text(destination, "experiments/d20.edi"),
            project_file: SettingsProof.text(destination, "project.edi"),
            before_save: preSave, parameters: parameters, su_rule: Session.project.suRule}));
        compare(JSON.stringify(backgroundDescriptors(published)),
                JSON.stringify(backgroundDescriptors(preSave.state)),
                "Saving typed Undo retains exact type, mode, basis, rows, IDs, positions/orders and free flags");
        compare(Session.project.suRule, preSave.suRule, "Save retains the actual selected uncertainty rule");
        verify(parameters.every(p => isFinite(p.value) && isFinite(p.uncertainty)),
               "Adopted typed Undo values and uncertainty projections stay finite");
        console.log("BACKGROUND_REVIEW3 undo " + source + " " + target);
    }
    function basisEdit(kind, field) {
        open(kind, "single", false, false);
        const e = Session.project.currentExperiment;
        e.backgroundEstimateUseModel = "ignore";ready();
        const before = JSON.stringify(rows(kind));
        if (field === "origin") e.backgroundOrigin = 105.25;
        else if (field === "x_min") e.backgroundXMin = 3.375;
        else e.backgroundXMax = 160.625;
        ready();
        verify(JSON.stringify(rows(kind)) !== before,
               "A declared series basis change must re-estimate coefficients, not reinterpret old ones");
        console.log("BACKGROUND_REVIEW3_BASIS " + JSON.stringify({kind: kind, field: field, rows: rows(kind)}));
    }
    function mixedFit(kind, mode) {
        const input = open(kind, mode, true, true);
        const before = rows(kind), fit = Session.project.fit;
        verify(fit.available, "Mixed measured/simulation fitting must be available: " + fit.unavailableReason);
        fit.start();tryVerify(() => !fit.running, 1000, "The mixed app worker fit must finish");
        verify(fit.outcome !== "refused" && fit.outcome !== "failed",
               "The mixed app worker fit must admit free Auto rows: " + Session.project.lastError);
        ready();pattern(kind);
        const fitted = rows(kind);
        verify(fitted.some((r,i) => Math.abs(r[2]-before[i][2]) > 1e-5),
               "The mixed app worker fit must really change free background values");
        Session.project.currentStructure.cell.lengthA.value += .00025;ready();
        compare(JSON.stringify(rows(kind)), JSON.stringify(fitted),
                "The mixed worker's fitted Auto values must survive a real later calculation");
        const e = Session.project.currentExperiment;
        const uncertainties = Probe.rows(kind === "line-segment" ? e.background : e.backgroundTerms).map(row =>
            (kind === "line-segment" ? row.intensity : row.coef).uncertainty);
        const beforeSave = {state: state(), parameters: undoSaveParameters(),
                            suRule: Session.project.suRule,
                            project_file: SettingsProof.text(input, "project.edi")};
        console.log("BACKGROUND_REVIEW3_MIXED_BEFORE_SAVE " + JSON.stringify(beforeSave));
        verify(beforeSave.suRule === "iucr_19" || beforeSave.suRule === "iucr_99",
               "Mixed Save captures the actual supported project uncertainty rule");
        verify(beforeSave.parameters.every(p => p.refinable && isFinite(p.value)
               && typeof p.hasUncertainty === "boolean" && isFinite(p.uncertainty)),
               "Mixed Save supplies every original scalar value, free flag and explicit optional-SU witness");
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "The mixed worker's fitted Auto background must save: " + Session.lastError);
        // Save adopts IUCr-rounded values; the separate loader checks that exact
        // declared rounding against these pre-save values and uncertainties.
        console.log("BACKGROUND_REVIEW3_SAVED " + JSON.stringify({kind: kind, state: state(),
            live_rows: fitted, live_su: uncertainties,
            before_save: beforeSave, parameters: undoSaveParameters(),
            su_rule: Session.project.suRule,
            project_file: SettingsProof.text(destination, "project.edi"),
            file: SettingsProof.text(destination, "experiments/d20.edi")}));
        compare(Session.project.suRule, beforeSave.suRule, "Mixed Save retains its actual selected uncertainty rule");
        compare(JSON.stringify(backgroundDescriptors(state())), JSON.stringify(backgroundDescriptors(beforeSave.state)),
                "Mixed Save retains exact type, mode, basis, population, IDs, positions/orders and free flags");
        console.log("BACKGROUND_REVIEW3 mixed " + kind + " " + mode);
    }
    function delegatedSave(kind) {
        open(kind, "single", true, false);
        Session.project.currentExperiment.backgroundEstimateMaxTerms = 1;
        const destination = Probe.scratchProjectUrl();
        // Save in the same owner-thread turn, before the queued Auto preview can replace the rows.
        verify(Session.saveAs(destination), "A due series beside a current app bank must save: " + Session.lastError);
        compare(rows(kind).length, 1, "App saving must settle its pending Auto calculation using the saved cap");
        console.log("BACKGROUND_REVIEW3_SAVED " + JSON.stringify({kind: kind, state: state(),
            file: SettingsProof.text(destination, "experiments/d20.edi")}));
    }
    function test_transition_line_segment_polynomial() { typeTransition("line-segment", "polynomial"); }
    function test_undo_line_segment_polynomial() { undoTransition("line-segment", "polynomial"); }
    function test_transition_line_segment_chebyshev() { typeTransition("line-segment", "chebyshev"); }
    function test_undo_line_segment_chebyshev() { undoTransition("line-segment", "chebyshev"); }
    function test_transition_polynomial_line_segment() { typeTransition("polynomial", "line-segment"); }
    function test_undo_polynomial_line_segment() { undoTransition("polynomial", "line-segment"); }
    function test_transition_polynomial_chebyshev() { typeTransition("polynomial", "chebyshev"); }
    function test_undo_polynomial_chebyshev() { undoTransition("polynomial", "chebyshev"); }
    function test_transition_chebyshev_line_segment() { typeTransition("chebyshev", "line-segment"); }
    function test_undo_chebyshev_line_segment() { undoTransition("chebyshev", "line-segment"); }
    function test_transition_chebyshev_polynomial() { typeTransition("chebyshev", "polynomial"); }
    function test_undo_chebyshev_polynomial() { undoTransition("chebyshev", "polynomial"); }
    function test_basis_polynomial_origin() { basisEdit("polynomial", "origin"); }
    function test_basis_chebyshev_x_min() { basisEdit("chebyshev", "x_min"); }
    function test_basis_chebyshev_x_max() { basisEdit("chebyshev", "x_max"); }
    function test_mixed_line_segment_single() { mixedFit("line-segment", "single"); }
    function test_mixed_line_segment_joint() { mixedFit("line-segment", "joint"); }
    function test_mixed_polynomial_single() { mixedFit("polynomial", "single"); }
    function test_mixed_polynomial_joint() { mixedFit("polynomial", "joint"); }
    function test_mixed_chebyshev_single() { mixedFit("chebyshev", "single"); }
    function test_mixed_chebyshev_joint() { mixedFit("chebyshev", "joint"); }
    function test_delegated_polynomial() { delegatedSave("polynomial"); }
    function test_delegated_chebyshev() { delegatedSave("chebyshev"); }
}
