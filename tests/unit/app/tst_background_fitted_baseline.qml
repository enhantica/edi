import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

TestCase {
    id: test
    name: "BackgroundFittedBaseline"
    when: windowShown
    property var appWindow
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Fitted-baseline acceptance must use the production app window");
        verify(waitForRendering(appWindow.contentItem), "The fit worker's production window must render");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
        Probe.releaseScratchProjects();
    }
    function rows(kind) {
        const exp = Session.project.currentExperiment;
        return Probe.rows(kind === "line-segment" ? exp.background : exp.backgroundTerms).map(row => kind === "line-segment" ? [String(row.id), row.position, row.intensity.value, row.intensity.free] : [String(row.id), row.order, row.coef.value, row.coef.free]);
    }
    function ready() {
        tryVerify(() => !Session.project.calculating && !Session.project.currentExperiment.pattern.stale, 1000, "A fitted Auto background must publish its calculated pattern; reason: " + Session.project.lastError);
    }
    function expectedBackground(kind, anchors, x) {
        if (kind === "line-segment") {
            if (x <= anchors[0][1])
                return anchors[0][2];
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
                for (let j = 2; j <= row[1]; ++j) {
                    const next = 2 * z * b - a;
                    a = b;
                    b = next;
                }
                term = row[1] === 0 ? 1 : b;
            }
            return sum + row[2] * term;
        }, 0);
    }
    function pattern(kind) {
        const actual = Probe.rows(Session.project.currentExperiment.pattern).filter(row => row.calcStatus === "incl");
        verify(actual.length > 100 && actual.every(row => isFinite(row.intensityCalc) && isFinite(row.intensityBkg)), "Fitting free Auto background rows must retain a finite included calculated pattern");
        verify(actual.some(row => Math.abs(row.intensityCalc - row.intensityBkg) > 1e-5), "The Auto fit must exercise nonzero calculated crystal peaks, not a zero-scale model");
        const anchors = rows(kind);
        verify(actual.every(row => Math.abs(row.intensityBkg - expectedBackground(kind, anchors, row.x)) <= 1e-7 + 1e-9 * Math.abs(row.intensityBkg)), "The app calculated background must evaluate its actual fitted point or term values");
        return actual;
    }
    function assertRows(actual, expected, why) {
        compare(actual.length, expected.length, why + ": row count");
        actual.forEach((row, i) => {
            compare(row[0], String(expected[i][0]), why + ": stable row id");
            compare(row[1], expected[i][1], why + ": position/order");
            verify(Math.abs(row[2] - expected[i][2]) <= 1e-7 + 1e-9 * Math.abs(expected[i][2]), why + ": fitted row " + i + " actual=" + row[2] + " expected=" + expected[i][2] + " (1e-7 absolute plus 1e-9 relative)");
            compare(row[3], expected[i][3], why + ": free flag");
        });
    }
    function fittedRun(kind, manual) {
        const input = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/fitted-auto-" + kind));
        verify(Session.openProject(input), "The app must load an authored free Auto background: " + Session.lastError);
        ready();
        if (manual) {
            Session.project.currentExperiment.backgroundEstimateMode = "manual";
            ready();
        }
        // A changed digest encoding legitimately re-estimates old saved inputs on
        // opening. Free the current rows through the permitted recorded action,
        // rather than assuming an older provenance record remains current.
        const exp = Session.project.currentExperiment;
        const parameters = Probe.rows(kind === "line-segment" ? exp.background : exp.backgroundTerms).map(row => kind === "line-segment" ? row.intensity : row.coef);
        verify(parameters.length > 0, "The real Auto fit must address actual current background parameters");
        verify(Session.project.setParametersFree(parameters, true), "A user must be able to free the current Auto or Manual background through the recorded batch action");
        const before = rows(kind);
        verify(before.every(row => row[3]), "Every current point or term must be free before the real fit");
        console.log("BACKGROUND_FIT_FREE_ACTION setParametersFree=true");
        const fit = Session.project.fit;
        verify(fit.available, "A single-experiment Auto background fit must be available: " + fit.unavailableReason);
        fitRefusals.clear();
        fit.start();
        try {
            tryVerify(() => !fit.running, 1000, "The actual bounded Auto fit must finish rather than refuse");
        } finally {
            console.log("BACKGROUND_FIT_OBSERVATION " + JSON.stringify({
                kind,
                manual,
                running: fit.running,
                outcome: fit.outcome,
                status: fit.status,
                lastError: Session.project.lastError,
                refusals: fitRefusals.signalArguments,
                iterations: fit.iterations,
                calculating: Session.project.calculating,
                structureCurves: Preferences.structureCurves
            }));
        }
        verify(Session.project.lastError.length === 0 && fit.outcome !== "failed" && fit.outcome !== "refused", "Fitting permitted free Auto rows must not refuse; reason: " + Session.project.lastError + " / " + fit.status);
        ready();
        pattern(kind);
        const fitted = rows(kind);
        verify(fitted.some((row, i) => Math.abs(row[2] - before[i][2]) > 1e-5), "The real Auto fit must change background values so a discarded fit cannot pass");
        compare(Session.project.currentExperiment.backgroundEstimateMode, manual ? "manual" : "auto", "The fit's own write-back must retain the chosen estimation mode");
        return fitted;
    }
    SignalSpy {
        id: fitRefusals
        target: Session.project ? Session.project.fit : null
        signalName: "refused"
    }
    SignalSpy {
        id: recalculated
        target: Session.project
        signalName: "recalculated"
    }
    function exercise(kind, flow) {
        // REGRESSION PIN: a same-input Manual fit, not a claim of physical fit correctness.
        const manifest = JSON.parse(Probe.readFile("tests/fixtures/background_estimate/fitted-baseline.json"));
        const control = manifest.cases[kind].manual_fitted_regression_pin;
        const fitted = fittedRun(kind, flow === "manual-control");
        assertRows(fitted, control, "The app must match the labelled same-input Manual-fit regression pin");
        if (flow === "manual-control") {
            console.log("BACKGROUND_FITTED_BASELINE " + kind + " manual-control fit=retained pattern=present mode=manual");
            return;
        }
        if (flow === "retain") {
            recalculated.clear();
            Session.project.currentStructure.cell.lengthA.value += 0.00025;
            tryVerify(() => recalculated.count > 0 && !Session.project.calculating, 1000, "An unrelated fixed cell edit must cause a real later calculation with unchanged data/settings");
            ready();
            pattern(kind);
            compare(JSON.stringify(rows(kind)), JSON.stringify(fitted), "A real later calculation must retain fitted Auto rows and values exactly");
        } else {
            Session.loadWarnings.dismissAll();
            recalculated.clear();
            const exp = Session.project.currentExperiment;
            if (flow === "settings") {
                if (kind === "line-segment") {
                    verify(typeof exp.backgroundEstimatePoints === "number", "The declared point-count property backgroundEstimatePoints must exist before writing it");
                    exp.backgroundEstimatePoints = 11;
                    compare(exp.backgroundEstimatePoints, 11, "The real ExperimentViewModel point-count setter must retain the requested 11 points");
                    console.log("BACKGROUND_POINT_COUNT_SET backgroundEstimatePoints=11");
                } else
                    exp.backgroundEstimateMaxTerms = 1;
            } else {
                verify(Session.project.loadDataInto(exp, Probe.repoUrl("tests/fixtures/background_estimate/fitted-baseline-shifted.xye")), "The actual data loader must replace measured data after fitting: " + Session.project.lastError);
            }
            tryVerify(() => {
                const current = Session.project.currentExperiment;
                const settled = !Session.project.calculating && !current.pattern.stale;
                const changed = JSON.stringify(rows(kind)) !== JSON.stringify(fitted);
                if (settled && !changed)
                    console.log("BACKGROUND_REFRESH_OBSERVATION " + JSON.stringify({
                        type: kind,
                        trigger: flow,
                        requested: current.backgroundEstimatePoints,
                        rows: rows(kind).length,
                        publications: recalculated.count,
                        reason: Session.project.lastError
                    }));
                return settled && changed;
            }, 1000, "Changed measured data or estimate settings must replace fitted Auto rows with a fresh estimate; " + "reason=" + Session.project.lastError + " requested=" + Session.project.currentExperiment.backgroundEstimatePoints + " rows=" + JSON.stringify(rows(kind)));
            pattern(kind);
            const refreshed = rows(kind);
            verify(refreshed.length !== fitted.length || refreshed.some((row, i) => Math.abs(row[2] - fitted[i][2]) > 1e-5), "A due app refresh must replace fitted numeric values, not merely change ids or free flags");
            const information = Probe.rows(Session.loadWarnings).filter(row => row.severity === "information");
            verify(information.some(row => /fit/i.test(row.message) && /background/i.test(row.message) && /replac|re.estimat/i.test(row.message)), "A post-fit Auto refresh must post an information entry saying the fitted background values were replaced");
            if (flow === "settings")
                compare(rows(kind).length, kind === "line-segment" ? 11 : 1, "A post-fit settings refresh must obey the new point count or one-term cap");
        }
        compare(Session.project.currentExperiment.backgroundEstimateMode, "auto", "Retaining or replacing the fitted background must leave Auto estimation mode selected");
        console.log("BACKGROUND_FITTED_BASELINE " + kind + " " + flow + " fit=retained pattern=present mode=auto");
    }
    function test_points_manual() {
        exercise("line-segment", "manual-control");
    }
    function test_polynomial_manual() {
        exercise("polynomial", "manual-control");
    }
    function test_chebyshev_manual() {
        exercise("chebyshev", "manual-control");
    }
    function test_points_retain() {
        exercise("line-segment", "retain");
    }
    function test_points_settings() {
        exercise("line-segment", "settings");
    }
    function test_points_measured() {
        exercise("line-segment", "data");
    }
    function test_polynomial_retain() {
        exercise("polynomial", "retain");
    }
    function test_polynomial_settings() {
        exercise("polynomial", "settings");
    }
    function test_polynomial_measured() {
        exercise("polynomial", "data");
    }
    function test_chebyshev_retain() {
        exercise("chebyshev", "retain");
    }
    function test_chebyshev_settings() {
        exercise("chebyshev", "settings");
    }
    function test_chebyshev_measured() {
        exercise("chebyshev", "data");
    }
}
