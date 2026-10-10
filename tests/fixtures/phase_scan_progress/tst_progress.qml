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
    function test_progress() {
        const expected = JSON.parse(Probe.readFile(decodeURIComponent(String(Probe.referenceUrl("expected.json")).slice(7))));
        verify(Session.openProject(Probe.referenceUrl("project")), "The partial or fresh progress witness opens in the actual app");
        tryVerify(() => !project.calculating, 3000, "The app finishes its initial calculation before observing progress");
        verify(project.fit.available, "The progress witness permits processing pending files");
        project.fit.start();
        tryVerify(() => running.count >= 2 && !project.fit.running, 3000, "The actual worker completes its rowless and fitted files");
        if (expected.channel === "public") {
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
