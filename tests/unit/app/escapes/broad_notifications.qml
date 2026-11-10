import QtQuick
import QtTest
import EdiAcceptance 1.0
import "../SignalContract.js" as Contract
TestCase {
    name: "E04BroadNotificationEscape"
    QtObject {
        id: bad
        property real value: 3.88
        property bool free: false
        signal wholeObjectChanged()
    }
    function test_every_property() {
        const handle = Probe.watch(bad);
        bad.value = 4.125;
        bad.freeChanged();
        compare(Contract.violation(Probe.events(handle), ["valueChanged"]), "",
                "I3: the production predicate rejects re-emitting unchanged properties");
    }
    function test_whole_object() {
        const handle = Probe.watch(bad);
        bad.value = 4.375;
        bad.wholeObjectChanged();
        compare(Contract.violation(Probe.events(handle), ["valueChanged"]), "",
                "I3: the production predicate rejects an added whole-object refresh signal");
    }
}
