import QtQuick
import QtTest
import HistoryLookupAcceptance 1.0

// The existing Qt Quick Test runner invokes C++ correctness checks. QML does
// not implement lookup, expected positions, native state or history mutation.
TestCase {
    name: "E11T5FirstHistoryRowLookup"
    when: windowShown
    function test_literal_indices() {
        const result=HistoryLookupProof.literalIndices();
        verify(result.ok, "Original typed-ID equality and FIRST old-row match must be preserved: " + (result.error || ""));
    }
    function test_publication_isolation() {
        const result=HistoryLookupProof.emptyAndPublicationIsolation();
        verify(result.ok, "An empty or separate publication must not inherit another lookup's ID authority: " + (result.error || ""));
    }
    function test_long_prefix() {
        const result=HistoryLookupProof.longPrefix();
        verify(result.ok, "Long canonical-prefix rows must retain exact first indices without mutation: " + (result.error || ""));
    }
}
