// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiOnlineHttpFixture 1.0
import ReportAcceptance 1.0

OnlineLoadSession {
    SignalSpy { id: finished; target: Session; signalName: "exampleOpenFinished" }

    function input(name) { return Qt.resolvedUrl(mailbox + "/inputs/" + name); }
    function document() {
        const file = SettingsProof.fileObservation(input("online/"), "index.json");
        verify(file.exists, "ADR-0068: the authored collection index exists before discovery");
        return file.text;
    }
    function prepare(offline) {
        verify(OnlineHttpFixture.attachExamples(Session), "ADR-0068: only the example network transport is injected");
        OnlineHttpFixture.clearExamples();
        OnlineHttpFixture.exampleText(offline ? 503 : 200, offline ? "" : document());
        OnlineHttpFixture.exampleLocations(Session, input("bundle/"));
        tryVerify(() => OnlineHttpFixture.exampleKnown(Session, "bundle-small")
                  && OnlineHttpFixture.exampleKnown(Session, "bundle-large"), 3000,
                  "ADR-0068: both omitted and included examples remain discoverable");
        wait(50);
        compare(OnlineHttpFixture.exampleRequests(), ["https://collection.invalid/index.json"],
                "ADR-0068: discovering an omitted large example does not download its payload");
        finished.clear();
        const refusal = findChild(app, "refusal.dialog");
        if (refusal && refusal.visible) refusal.close();
    }
    function open(id) {
        verify(Session.openExample(id), "ADR-0068: Open admits the collection example request");
        tryCompare(finished, "count", 1, 5000, "ADR-0068: each first open completes visibly");
        tryCompare(Session, "openingExample", false, 3000, "ADR-0068: acquisition leaves no stuck opening state");
    }
    function check_small_offline() {
        prepare(true);
        const before = OnlineHttpFixture.exampleRequests().length;
        open("bundle-small");
        verify(Session.project !== null && Session.project.experiments.count > 0,
               "ADR-0068: a small bundled project opens fully offline");
        compare(OnlineHttpFixture.exampleRequests().length, before,
                "ADR-0068: a small bundled open never waits for or fetches an online payload");
    }
    function check_large_online() {
        prepare(false);
        OnlineHttpFixture.exampleText(200, document());
        verify(OnlineHttpFixture.exampleFile(200, input("online/projects/large.zip")),
               "ADR-0068: the first-open download serves the independent large project bytes");
        open("bundle-large");
        compare(OnlineHttpFixture.exampleRequests(), [
            "https://collection.invalid/index.json",
            "https://collection.invalid/index.json",
            "https://collection.invalid/projects/large.zip"
        ], "ADR-0068: an omitted large project is acquired only by the first Open");
        verify(Session.project !== null && Session.project.experiments.count > 0,
               "ADR-0068: the downloaded large archive opens through the ordinary project loader");
    }
    function check_large_offline() {
        prepare(true);
        const original = Session.project;
        OnlineHttpFixture.exampleText(503, "");
        open("bundle-large");
        compare(Session.project, original, "ADR-0068: an offline large open preserves the current project");
        const refusal = findChild(app, "refusal.dialog");
        verify(refusal !== null && refusal.visible, "ADR-0068: an offline omitted example has a visible error dialog");
        verify(/offline|internet|connect|network|download|reach/i.test(refusal.message),
               "ADR-0068: the offline error explains that the example needs a connection or download");
    }
}
