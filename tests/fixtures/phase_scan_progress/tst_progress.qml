import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0

TestCase {
    id: test
    name: "ScanProcessedProgress"
    when: windowShown
    visible: true
    width: 1200
    height: 300
    property var project: Session.project
    property var samples: []
    property real largestBar: -1
    property int visibleSamples: 0
    property var expectation: ({})
    property bool injected: false
    property bool faultReported: false
    property bool invalidOnReport: false
    property bool publishedAfterFault: false
    property bool cancellationRequested: false
    SignalSpy {
        id: running
        target: test.project ? test.project.fit : null
        signalName: "runningChanged"
    }
    StatusBar {
        id: status
        width: test.width
        visible: true
    }
    Connections {
        target: test.project ? test.project.fit : null
        function onRefused(message) {
            test.recordFault(message);
        }
        function onRunningChanged() {
            if (test.project.fit.running && test.expectation.ending === "cancel") {
                test.cancellationRequested = true;
                test.project.fit.cancel();
            }
        }
        function onScanFittedChanged() {
            if (test.faultReported && test.project.fit.running && test.project.fit.scanFitted > 2)
                test.publishedAfterFault = true;
            // The completed second row proves the native notes stream is open. A preamble injection
            // races its initial truncation; this signal is before the third row reaches the GUI index.
            if (test.expectation.channel === "incremental" && !test.injected && test.project.fit.running && test.project.fit.scanFitted === 2) {
                const bad = test.expectation.fault === "fraction" ? "experiments/scan/03.xy,1.5,True,\n" : "experiments/scan/foreign.xy,0,True,\n";
                test.injected = Probe.appendNotes(Probe.referenceUrl("project/analysis/scan-notes.csv"), "experiments/scan/02.xy,0,False,\n" + bad);
            }
        }
        function onScanTextChanged() {
            if (!test.project.fit.running || !test.project.fit.scanning)
                return;
            const match = test.project.fit.scanText.match(/^(\d+)\/(\d+)/);
            if (match)
                test.samples.push({
                    processed: Number(match[1]),
                    total: Number(match[2]),
                    fitted: test.project.fit.scanFitted
                });
        }
    }
    Connections {
        target: findChild(status, "statusBar.fit.progress")
        function onFractionChanged() {
            const bar = findChild(status, "statusBar.fit.progress");
            if (bar && bar.visible && test.project && test.project.fit.running) {
                test.visibleSamples += 1;
                test.largestBar = Math.max(test.largestBar, bar.fraction);
            }
        }
    }
    function recordFault(text) {
        if (text.includes("scan-notes.csv")) {
            if (!faultReported)
                invalidOnReport = Probe.scanIndexError(project).includes("scan-notes.csv");
            faultReported = true;
        }
    }
    Connections {
        target: test.project
        function onLastErrorChanged() {
            test.recordFault(test.project.lastError);
        }
        function onRefused(message) {
            test.recordFault(message);
        }
        function onMessage(text) {
            test.recordFault(text);
        }
    }
    function test_progress() {
        const expected = JSON.parse(Probe.readFile(decodeURIComponent(String(Probe.referenceUrl("expected.json")).slice(7))));
        expectation = expected;
        verify(Session.openProject(Probe.referenceUrl("project")), "The partial or fresh progress witness opens in the actual app");
        tryVerify(() => !project.calculating, 3000, "The app finishes its initial calculation before observing progress");
        verify(project.fit.available, "The progress witness permits processing pending files");
        if (expected.channel === "incremental") {
            compare(project.fit.scanFitted, 1, "The actual app accepts one retained results row before the injected notes failure");
            compare(Probe.scanIndexError(project), "", "Initial complete notes history produces a valid app index");
        }
        project.fit.start();
        tryVerify(() => running.count >= 2 && !project.fit.running, 3000, "The actual worker completes its rowless and fitted files");
        if (expected.channel === "ending") {
            compare(project.fit.outcome, expected.ending === "cancel" ? "stopped" : "failed", "Terminal presentation retains the actual cancellation or failure outcome");
            verify(project.fit.scanProgress < 1, "An interrupted run does not fabricate complete processed progress");
            verify(largestBar <= project.fit.scanProgress, "The live bar does not publish completion beyond the interrupted run's real population");
            if (expected.ending === "cancel")
                verify(cancellationRequested, "The actual running worker received a cancellation request");
        } else if (expected.channel === "incremental") {
            verify(injected, "A complete later notes line and a bad following line were appended after the app accepted history");
            verify(faultReported, "The actual incremental notes refusal is reported through the app's actual error channel");
            if (expected.check === "index") {
                verify(invalidOnReport, "An incremental notes failure invalidates the live index before reporting recovered state");
                verify(Probe.scanIndexError(project).includes("scan-notes.csv"), "The failed incremental index remains invalid until a successful complete reindex");
            } else {
                verify(!publishedAfterFault, "Failed incremental recovery must never publish fitted progress from its partially accepted facts");
            }
        } else if (expected.channel === "public") {
            compare(project.fit.scanProgress, 1, "The public scanProgress fraction counts fitted and rowless skipped files");
        } else if (expected.channel === "status-bar") {
            verify(visibleSamples > 0, "The actual visible status bar was observed during the running scan");
            compare(largestBar, 1, "The visible scan progress bar reaches completion with any arrangement of rowless skips");
        } else {
            verify(samples.length > 0, "The partial resume publishes live population samples through the app");
            samples.forEach(sample => {
                verify(sample.processed <= sample.total, "Live fitted-plus-skipped population never exceeds the dataset total");
                verify(sample.fitted <= sample.processed, "Every live fitted dataset belongs to the processed population");
                if (sample.fitted === 3)
                    compare(sample.processed, 3, "A converted skipped dataset must leave the skipped population exactly once");
            });
            const last = samples[samples.length - 1];
            compare(last.processed, 3, "The last live count includes each dataset once after converting a skip");
            compare(last.fitted, 3, "The resumed run fits the formerly skipped dataset and the pending dataset");
            verify(Session.saveAs(Probe.referenceUrl("saved")), "The converted-skip run saves its completed state");
            Session.closeProject();
            verify(Session.openProject(Probe.referenceUrl("saved")), "The converted-skip result reopens through full indexing");
            compare(project.fit.scanFitted, last.fitted, "Live fitted counts agree with reopened full indexing");
            compare(project.fit.scanProgress * project.fit.scanTotal, last.processed, "Live fitted-plus-skipped counts agree with reopened full indexing");
        }
        Session.closeProject();
    }
}
