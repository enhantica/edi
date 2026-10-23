import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0

TestCase {
    id: test
    name: "BackgroundEstimateLifecycle"
    when: windowShown
    property var appWindow
    Component { id: application; Main {} }
    function init() {
        Session.closeProject();
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Lifecycle gates must use the production app window");
        verify(waitForRendering(appWindow.contentItem), "The lifecycle app window must render");
    }
    function cleanup() {
        Session.closeProject();
        appWindow.destroy();
        Probe.releaseScratchProjects();
    }
    function points() {
        return Probe.rows(Session.project.currentExperiment.background).map(row => [row.position, row.intensity.value]);
    }
    function open(name, calculated) {
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/background_estimate/projects/" + name))),
               "The app must open the authored lifecycle project: " + name);
        if (calculated) {
            tryVerify(() => !Session.project.calculating && !Session.project.currentExperiment.pattern.stale,
                      2000, "The app must finish the actual lifecycle calculation");
            const rows = Probe.rows(Session.project.currentExperiment.pattern);
            verify(rows.some(row => row.calcStatus === "incl" && Math.abs(row.intensityCalc - row.intensityBkg) > 1e-8),
                   "The lifecycle witness must have nonzero model peaks; zero-scale controls hide conversion defects");
        }
    }
    function guided() {
        open("lifecycle-model", true);
        const before = JSON.stringify(points());
        Session.project.currentExperiment.backgroundEstimateMode = "auto";
        tryVerify(() => !Session.project.calculating && !Session.project.currentExperiment.pattern.stale &&
                  JSON.stringify(points()) !== before, 2000,
                  "Choosing auto must publish a genuine model-guided estimate in the app");
    }
    function interpolate(anchors, x) {
        if (x <= anchors[0][0]) return anchors[0][1];
        for (let i = 1; i < anchors.length; ++i) {
            if (x <= anchors[i][0]) {
                const left = anchors[i - 1], right = anchors[i];
                return left[1] + (right[1] - left[1]) * (x - left[0]) / (right[0] - left[0]);
            }
        }
        return anchors[anchors.length - 1][1];
    }
    function storedPoints(destination) {
        const result = [], tags = [];
        let active = false;
        SettingsProof.text(destination, "experiments/hrpt.edi").split(/\r?\n/).forEach(line => {
            const words = line.trim().split(/\s+/);
            if (words[0] === "loop_") { tags.length = 0; active = true; }
            else if (active && words[0].startsWith("_")) {
                if (words.length === 1) tags.push(words[0]); else active = false;
            } else if (active && words.length === tags.length && tags.indexOf("_background.position") >= 0) {
                result.push([parseFloat(words[tags.indexOf("_background.position")]),
                             parseFloat(words[tags.indexOf("_background.intensity")])]);
            }
        });
        return result;
    }
    function test_guided_preview_uses_the_visible_points() {
        guided();
        const anchors = points();
        const rows = Probe.rows(Session.project.currentExperiment.pattern).filter(row => row.calcStatus === "incl");
        verify(rows.length > 0, "The actual preview must publish included background samples");
        verify(rows.every(row => Math.abs(row.intensityBkg - interpolate(anchors, row.x)) <=
                          1e-9 + 1e-12 * Math.abs(row.intensityBkg)),
               "Preview intensityBkg must interpolate the visible guided points without a second engine estimate");
    }
    function test_delegated_save_keeps_the_visible_guided_points() {
        guided();
        const before = points(), destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "The guided app estimate must save through the real project writer");
        compare(JSON.stringify(storedPoints(destination)), JSON.stringify(before),
                "Delegated app saving must retain exactly the visible guided points");
    }
    function test_open_unchanged_auto_preserves_saved_model_guided_points() {
        const manifest = JSON.parse(Probe.readFile("tests/fixtures/background_estimate/lifecycle-cases.json"));
        const before = manifest.cases["lifecycle-guided"].points;
        open("lifecycle-guided", true);
        compare(JSON.stringify(points()), JSON.stringify(before),
                "Opening and calculating an unchanged nonzero-model auto project must retain its saved points");
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "The unchanged auto app project must save");
        compare(JSON.stringify(storedPoints(destination)), JSON.stringify(before),
                "Re-saving unchanged automatic points must retain the same persisted rows");
    }
    function firstEdit(name) {
        open(name, false);
        const rows = Probe.rows(Session.project.currentExperiment.background);
        verify(rows.length > 0, "The no-data app project must retain editable loaded points");
        const expected = rows[0].intensity.value + 0.125;
        // Auto is read-only even before an estimate; the user explicitly chooses Manual.
        Session.project.currentExperiment.backgroundEstimateMode = "manual";
        rows[0].intensity.value = expected;
        compare(Session.project.currentExperiment.backgroundEstimateMode, "manual",
                "An explicit Manual choice must permit a first app point edit with no included data");
        const destination = Probe.scratchProjectUrl();
        verify(Session.saveAs(destination), "The first no-data point edit must save");
        verify(/_background_estimate.mode\s+manual/.test(SettingsProof.text(destination, "experiments/hrpt.edi")),
               "The no-data app edit must persist manual mode");
        compare(points()[0][1], expected, "No delayed preview may discard the first manual point edit");
    }
    function test_first_edit_with_excluded_data_selects_manual() { firstEdit("lifecycle-excluded"); }
    function invalid(field, value) {
        open("lifecycle-model", true);
        const experiment = Session.project.currentExperiment;
        const before = experiment[field], beforePoints = JSON.stringify(points());
        experiment[field] = value;
        verify(isNaN(before) ? isNaN(experiment[field]) : experiment[field] === before,
               "The public app property " + field + " must refuse a nonfinite or overflowing override before mutation");
        verify(experiment.lastError.length > 0,
               "An invalid app estimate override must expose its ordinary lastError refusal");
        verify(isFinite(experiment.estimateWidth), "App defaults must remain finite after refusing an invalid override");
        compare(JSON.stringify(points()), beforePoints, "Refusing an app override must preserve all point rows");
    }
    function test_infinite_width_is_refused_before_defaults() { invalid("backgroundEstimateWidth", Infinity); }
    function test_overflowing_width_is_refused_before_defaults() { invalid("backgroundEstimateWidth", 8589934592.25); }
    function test_infinite_smoothness_is_refused_before_defaults() { invalid("backgroundEstimateSmoothness", Infinity); }
    function scan(mode) {
        open("lifecycle-scan-" + mode, true);
        const before = JSON.stringify(points());
        const fit = Session.project.fit;
        verify(fit.available, "Both lifecycle scan modes must be available through the real app fit action");
        console.log("BACKGROUND_LIFECYCLE_SCAN_ENTER " + mode);
        fit.start();
        console.log("BACKGROUND_LIFECYCLE_SCAN_STARTED " + mode + " running=" + fit.running + " status=" + fit.status);
        tryVerify(() => !fit.running, 2500,
                  "The real app scan worker must finish without retaining replaced background rows");
        verify(Session.project.lastError.length === 0 && fit.status.toLowerCase().indexOf("failed") < 0,
               "Changing per-file anchor counts must not fail the delegated app scan: " +
               Session.project.lastError + " / " + fit.status);
        compare(fit.scanFitted, 3, "The real app must fit all three distinct measured files");
        compare(JSON.stringify(points()), before,
                "An app scan must preserve its template's point positions, heights and layout");
        compare(Session.project.currentExperiment.backgroundEstimateMode, "auto",
                "Delegated scan write-back must keep the template in auto mode");
    }
    function test_independent_scan_preserves_the_template() { scan("independent"); }
    function test_sequential_scan_preserves_the_template() { scan("sequential"); }

}
