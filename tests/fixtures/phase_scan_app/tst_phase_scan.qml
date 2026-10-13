import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0

TestCase {
    id: test
    name: "PhaseScanState"
    when: windowShown
    visible: true
    width: 1000
    height: 800
    property var project: Session.project
    SignalSpy {
        id: running
        target: test.project ? test.project.fit : null
        signalName: "runningChanged"
    }
    SignalSpy {
        id: rereadRefused
        target: test.project
        signalName: "refused"
    }
    EvolutionChart {
        id: chart
        width: 800
        height: 500
        project: test.project
    }
    property int largestFitted: 0
    Connections {
        target: test.project ? test.project.fit : null
        function onScanFittedChanged() {
            test.largestFitted = Math.max(test.largestFitted, test.project.fit.scanFitted);
        }
    }
    function test_observe() {
        const expected = JSON.parse(Probe.readFile(decodeURIComponent(String(Probe.referenceUrl("expected.json")).slice(7))));
        Session.openProject(Probe.referenceUrl("project"));
        if (expected.kind === "state-open") {
            if (expected.valid) {
                verify(Session.hasProject, "Absent and regular symlink state opens through the actual app");
                compare(Probe.scanIndexError(project), "", "Supported state kinds produce a valid complete app index");
            } else {
                const diagnostic = Session.hasProject ? project.fit.unavailableReason : Session.lastError;
                verify(diagnostic.includes(expected.filename), "App open identifies an unsupported results or provenance path");
                if (Session.hasProject)
                    verify(!project.fit.available, "Unsupported retained state prevents a misleading app run");
            }
            return;
        }
        if (expected.kind === "reread") {
            verify(Session.hasProject, "The post-index witness first opens regular complete results");
            tryVerify(() => !project.calculating && Probe.datasetReady(project), 3000, "Initial regular dataset projection finishes before path replacement");
            compare(project.fit.scanFitted, 3, "The actual app accepts three complete rows before the path changes");
            compare(Probe.scanIndexError(project), "", "The reread witness starts with a valid index");
            if (expected.reader === "evolution") {
                compare(project.lastError, "", "The Evolution witness begins without an earlier project error");
                compare(project.evolution.count, 3, "Regular complete results initially draw all three Evolution points");
                rereadRefused.clear();
            }
            verify(Probe.replaceState(Probe.referenceUrl("project/analysis/results.csv"), Probe.referenceUrl("replacement")), "The authored replacement changes the results path after successful indexing");
            const diagnostic = Probe.scanReread(project, expected.reader);
            if (expected.valid)
                compare(diagnostic, "", "A regular symlink remains readable through every post-index reader");
            else
                verify(diagnostic.includes("results.csv"), "Post-index row and Evolution readers explicitly refuse unsupported results paths before opening streams");
            if (expected.reader === "evolution") {
                compare(rereadRefused.count, expected.valid ? 0 : 1, "Evolution rereads report exactly one project refusal only for unsupported paths");
                compare(project.evolution.count, expected.valid ? 3 : 0, "Evolution rereads retain valid points and clear every point after a refusal");
                if (!expected.valid)
                    compare(rereadRefused.signalArguments[0][0], diagnostic, "The project refusal signal and lastError carry the same actual reread diagnostic");
            }
            return;
        }
        if (expected.kind === "retained-scan" || expected.kind === "single-after-skips") {
            verify(Session.hasProject, "The actual app opens retained rowless completed scan history");
            tryVerify(() => !project.calculating && Probe.datasetReady(project), 3000, "The initial retained dataset view finishes before persistence actions");
            compare(project.fit.scanFitted, 0, "The retained all-skipped scan has no fitted result rows");
            compare(project.fit.scanProgress, 1, "All-skipped retained history still accounts for the entire population");
            const wasScan = project.fit.scanSummary;
            if (expected.kind === "single-after-skips") {
                project.currentExperimentIndex = 0;
                project.analysis.fittingMode = "single";
                tryVerify(() => !project.calculating && Probe.datasetReady(project) && project.fit.available, 3000, "A positive selected dataset permits an actual single fit after rowless scan history");
                project.fit.start();
                tryVerify(() => running.count >= 2 && !project.fit.running, 3000, "The actual single-fit worker finishes after the all-skipped scan");
                verify(project.fit.canUndo, "The single fit produced a real accepted record rather than a refusal");
            }
            const lastSingle = Probe.scanLastSingle(project);
            const outcome = project.fit.outcome;
            verify(Session.saveAs(Probe.referenceUrl("saved")), "The actual app saves the newest run over all-skipped history");
            Session.closeProject();
            verify(Session.openProject(Probe.referenceUrl("saved")), "The saved all-skipped history reopens through actual indexing");
            if (expected.kind === "single-after-skips") {
                verify(lastSingle && Probe.scanLastSingle(project), "A single fit after an all-skipped scan persists last_single and reopens as the latest run");
                verify(!project.fit.scanSummary, "Reopen selects the last single fit rather than an older rowless scan summary");
                compare(project.fit.outcome, outcome, "The reopened single fit retains its actual terminal record");
            } else {
                verify(wasScan && project.fit.scanSummary, "All-skipped scan summary survives actual app save and reopen");
                compare(project.fit.scanFitted, 0, "Reopened all-skipped summary retains its rowless fitted count");
                compare(project.fit.scanProgress, 1, "Reopened all-skipped summary retains complete processed progress");
                compare(project.fit.outcome, outcome, "All-skipped round trip retains its real scan outcome");
            }
            return;
        }
        if (expected.kind === "notes") {
            const diagnostic = Session.hasProject ? project.fit.unavailableReason : Session.lastError;
            verify(diagnostic.includes("scan-notes.csv"), "Malformed persisted notes require one explicit core/app diagnostic");
            compare(diagnostic.split("\n").filter(s => s.trim()).length, 1, "Malformed notes produce one diagnostic instead of a partial recovered state");
            if (Session.hasProject)
                verify(!project.fit.available, "Unrecoverable notes must prevent a misleading scan start");
            return;
        }
        verify(Session.hasProject, "The authored multiphase scan opens through the actual app session");
        tryVerify(() => !project.calculating, 3000, "Initial app calculation finishes before the scan starts");
        verify(project.fit.available, "A fresh or partially completed scan permits a run");
        compare(project.fit.continuable, expected.resume, "A partially processed scan offers Continue");
        project.fit.start();
        tryVerify(() => running.count >= 2 && !project.fit.running, 3000, "The real app worker enters and completes the entire scan");
        verify(!project.fit.available, "Fitted and skipped files together disable Start on completion");
        verify(!project.fit.continuable, "A scan with every file processed offers no Continue");
        verify(project.fit.canReset, "A completed scan, including an all-skipped scan, permits Reset");
        compare(project.fit.scanProgress, 1, "All processed files contribute to completed progress");
        compare(project.fit.scanFitted, expected.values.length, "The fitted count excludes rowless skipped files");
        verify(largestFitted <= expected.values.length, "Live fitted counts must never include skipped files");
        verify(project.fit.scanSummary, "An all-skipped completion still has a completed scan summary");
        if (expected.values.length) {
            const names = Probe.rows(project.evolution.parameters).map(row => row.name);
            compare(names.length, 2, "Every free phase scale appears in the Evolution selector");
            ["alpha", "beta"].forEach((phase, component) => {
                const name = "pattern.linked_structure." + phase + ".scale";
                verify(names.includes(name), "Per-phase Evolution names are unambiguous: " + name);
                project.evolution.currentParameter = names.indexOf(name);
                project.evolution.xMode = 1;
                compare(project.evolution.count, expected.values.length, "Evolution retains every successful result point");
                expected.values.forEach((row, index) => {
                    compare(project.evolution.datasetAt(expected.places[index] + 1, row[component], .001, .000002), expected.places[index], "Evolution points recover the independently authored phase coefficient");
                });
                const layer = Probe.visibleControl(chart, "evolution.points");
                verify(layer !== null, "The visible Evolution chart owns the measured point layer");
                compare(layer.count, expected.values.length, "The visible layer receives every per-phase result point");
            });
        }
        verify(Session.saveAs(Probe.referenceUrl("saved")), "The app saves completed multiphase results");
        Session.closeProject();
        verify(Session.openProject(Probe.referenceUrl("saved")), "Saved multiphase scan results reopen in the app");
        verify(!project.fit.available && !project.fit.continuable && project.fit.canReset, "Reopen preserves completed fitted-plus-skipped control state");
        project.fit.reset();
        verify(project.fit.available && !project.fit.continuable && !project.fit.canReset, "Reset clears fitted and rowless skipped completion state together");
        compare(project.fit.scanProgress, 0, "Reset returns processed progress to zero");
        Session.closeProject();
    }
}
