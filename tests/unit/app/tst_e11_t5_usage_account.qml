// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import UsageAccountAcceptance 1.0

TestCase {
    id: usageTest
    name: "E11T5UsageAccount"
    when: windowShown
    Component { id: detachedHost; Item {} }
    function initTestCase() {
        verify(!UsageAccountProof.bindHost(null), "Null cannot supply the required visual host");
        const detached = detachedHost.createObject(null);
        verify(detached !== null, "A genuine detached Item exists for the windowless control");
        try {
            verify(!UsageAccountProof.bindHost(detached), "A windowless Item cannot supply the host");
        } finally {
            detached.destroy();
        }
        verify(UsageAccountProof.bindHost(usageTest), "Actual same-engine QuickTest Item/window host");
    }
    function test_original_reset_literal_types_and_boundaries() {
        const result = UsageAccountProof.resetLiterals(ApplicationInfo);
        verify(result.ok, JSON.stringify(result));
    }
    function test_original_color_coercion_and_same_engine_throw_identity() {
        const result = UsageAccountProof.colorsAndThrows(ApplicationInfo);
        verify(result.ok, JSON.stringify(result));
    }
    function test_original_translation_and_actual_binding_dependencies() {
        const result = UsageAccountProof.translationAndBindings(ApplicationInfo);
        verify(result.ok, JSON.stringify(result));
    }
}
