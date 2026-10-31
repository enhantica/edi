// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import ReportAcceptance 1.0

TestCase {
    id: test
    name: "EngineIncubationOwnership"
    when: windowShown
    function init() { failOnWarning(/.*/); }
    function test_actual_configured_engines_are_independent_data() {
        return [{tag: "destroy-A-first", destroyFirst: true},
            {tag: "destroy-B-first", destroyFirst: false}];
    }
    function assertRealWork(work, phase) {
        verify(work.started_loading && work.queued_at_start > 0,
            phase + ": the actual configured engine really admits asynchronous pending work");
        compare(work.errors.length, 0, phase + ": ordinary Qt component creation has no hidden error");
        verify(work.ready, phase + ": only the genuine production timer/event loop completes the work");
        compare(work.answer, 42, phase + ": the actual completed QObject publishes its declared result");
    }
    function test_actual_configured_engines_are_independent(data) {
        const facts = SettingsProof.incubationOwnership(test, data.destroyFirst);
        console.log("ENGINE_INCUBATION_OWNERSHIP " + JSON.stringify({caseTag: data.tag, facts}));
        verify(facts.error === undefined, "Actual configure_engine/lifecycle setup is valid: " + facts.error);
        verify(facts.a_present && facts.b_present,
            "Both real public configure_engine entries install their initially attached controller");
        verify(facts.distinct_controllers && facts.a_engine_owned && facts.b_engine_owned,
            "Simultaneously live configured engines cannot share or outlive the same static controller");
        verify(facts.a_forward_after_b && facts.independent_live_ownership,
            "Configuring B preserves A's forward pointer and actual engine-owned controller identity");
        assertRealWork(facts.a_queued_before_b, "A queued before configuring B");
        assertRealWork(facts.a_work_with_b, "A queued while B remains configured");
        assertRealWork(facts.b_work, "B queued beside A");
        verify(facts.destroyed_engine_controller_deleted && facts.survivor_controller_alive,
            "Only the destroyed engine's own controller lifetime ends after normal QObject unwind");
        verify(facts.survivor_forward_after_destroy && facts.survivor_owner_after_destroy,
            "Destroying either engine cannot clear or retarget the surviving engine's controller");
        assertRealWork(facts.survivor_work_after_destroy, "Survivor after foreign engine destruction");
        verify(facts.explicit_detach_forward_null && facts.detached_owner_still_alive,
            "Public detachment does not falsely delete the controller's live QObject owner");
        compare(facts.detached_count, 0, "The public null-safe count is observed without engine() inference");
        verify(facts.explicit_reattach_forward, "Explicit reattachment reestablishes the real live-engine forward link");
        assertRealWork(facts.reattached_work, "Survivor after explicit detach and reattachment");
        verify(facts.both_controller_lifetimes_ended,
            "Both actual controller children are gone after their engines, not retained at static finish");
        verify(facts.caller_restored, "Scoped cleanup preserves the original QuickTest caller for later cases");
    }
}
