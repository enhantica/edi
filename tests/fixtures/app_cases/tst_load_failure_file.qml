// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest

import edi.app

// The error popup attaches only the file the failure it describes could not read: a later failure that read no file
// attaches nothing, and the next unreadable file replaces the first.
TestCase {
    id: test

    name: "LoadFailureFile"
    when: windowShown

    property var window: null

    SignalSpy {
        id: failures
        target: Session
        signalName: "loadFailed"
    }

    function initTestCase() {
        const component = Qt.createComponent("qrc:/qt/qml/edi/app/qml/Main.qml");
        verify(component.status === Component.Ready, component.errorString());
        window = component.createObject(null);
        verify(window);
        window.visible = true;
        tryVerify(() => findChild(window, "refusal.dialog") !== null, 10000);
    }
    function cleanupTestCase() {
        window.destroy();
    }
    function fail(open) {
        failures.clear();
        open();
        tryCompare(failures, "count", 1, 10000);
        return {
            "signal": failures.signalArguments[0][1],
            "popup": findChild(window, "refusal.dialog").file
        };
    }
    function name(path) {
        return path.split("/").pop();
    }

    function test_each_failure_attaches_its_own_file() {
        const first = fail(() => Session.openProject(Qt.resolvedUrl("load_failure/bad_structure")));
        compare(name(first.signal), "phase.edi");
        compare(first.popup, first.signal);

        const remote = fail(() => Session.openProject("https://example.org/project.zip"));
        compare(remote.signal, "");
        compare(remote.popup, "");

        const missing = fail(() => Session.openProject(Qt.resolvedUrl("load_failure/missing")));
        compare(missing.signal, "");
        compare(missing.popup, "");

        const example = fail(() => Session.openExample("no-such-example"));
        compare(example.signal, "");
        compare(example.popup, "");

        const second = fail(() => Session.openProject(Qt.resolvedUrl("load_failure/bad_experiment")));
        compare(name(second.signal), "bank.edi");
        compare(second.popup, second.signal);
    }
}
