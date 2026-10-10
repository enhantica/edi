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
