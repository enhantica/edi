// Explicitly selected external-runtime characterization; never ordinary unit discovery.
import QtQuick
import QtTest
import edi.app
import UsageAccountAcceptance 1.0

TestCase {
    id: retirementTest
    name: "E11T5ExternalContextRetirementCharacterization"
    when: windowShown
    function initTestCase() {
        verify(UsageAccountProof.bindHost(retirementTest),
               "Characterization uses the actual same-engine QuickTest window host");
    }
    function test_external_public_creation_context_retirement() {
        const result = UsageAccountProof.actualContextLookups(ApplicationInfo, true);
        compare(result.context_lookup_mode, "external-retirement-characterization");
        verify(result.ok, JSON.stringify(result));
    }
}
