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
    function test_original_projection_catch_reentry_and_detached_owner_lifetime() {
        const result = UsageAccountProof.projectionAndOwnerLifetime(ApplicationInfo);
        verify(result.ok, JSON.stringify(result));
    }

    function test_original_null_member_receiver_descriptions() {
        const result = UsageAccountProof.nullMemberReceivers(ApplicationInfo);
        verify(result.ok, JSON.stringify(result));
    }
    function test_original_actual_context_lookup_and_notifications() {
        const result = UsageAccountProof.actualContextLookups(ApplicationInfo);
        verify(result.ok, JSON.stringify(result));
    }

    function test_original_dot_and_name_lookup_order() {
        const result = UsageAccountProof.callLookupOrder(ApplicationInfo);
        verify(result.ok, JSON.stringify(result));
    }

    function test_native_context_storage_lifetime_data() {
        return [
            {tag: "scalar-known-retired"}, {tag: "scalar-found-undefined"},
            {tag: "scalar-absent-global"},
            {tag: "id-precedence"}, {tag: "scalar-reentry-replace"},
            {tag: "list-replace"},
            {tag: "list-negative-index"}, {tag: "list-at-end"},
            {tag: "list-maximum-index"}, {tag: "list-shrink"},
            {tag: "list-type-change"}, {tag: "list-type-change-pending"},
            {tag: "list-owner-destroyed"}
        ];
    }
    function test_native_context_storage_lifetime(data) {
        const result = UsageAccountProof.contextStorageLifetime(ApplicationInfo, data.tag);
        verify(result.ok, JSON.stringify(result));
    }

    function test_native_context_conversion_lifetime_data() {
        return [{tag: "default-conversion"}, {tag: "native-reference-gc"}];
    }
    function test_native_context_conversion_lifetime(data) {
        const result = UsageAccountProof.contextConversionLifetime(ApplicationInfo, data.tag);
        verify(result.ok, JSON.stringify(result));
    }
}
