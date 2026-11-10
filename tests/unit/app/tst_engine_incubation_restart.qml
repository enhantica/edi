// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import ReportAcceptance 1.0

Item {
    id: surface
    width: 600
    height: 400
    Component {
        id: realContent
        Item {
            width: 20
            height: 20
            property int answer: 6 * 7
        }
    }
    Loader {
        id: actualLoader
        active: false
        asynchronous: true
        sourceComponent: realContent
    }
    TestCase {
        id: test
        name: "EngineIncubationRestart"
        when: windowShown
        function init() {
            failOnWarning(/.*/);
            actualLoader.active = false;
        }
        function cleanup() {
            actualLoader.active = false;
        }
        function foreignEngine() {
            // Existing carrier really constructs/configures/destroys B. No
            // acceptanceReady property: its optional wait/pump branch is unused.
            const result = SettingsProof.restart(
                "import QtQml; QtObject { property int answer: 6 * 7 }");
            verify(result.error === undefined,
                "The existing carrier configures a genuine foreign production engine: " + result.error);
            compare(result.answer, 42,
                "The foreign engine creates its real declared QtObject before ordinary destruction");
        }
        function test_current_async_owner_survives_foreign_engine_data() {
            return [{tag: "pending-before-B", foreignBeforeLoading: false},
                {tag: "start-after-B-destroyed", foreignBeforeLoading: true}];
        }
        function test_current_async_owner_survives_foreign_engine(data) {
            if (data.foreignBeforeLoading)
                foreignEngine();
            actualLoader.active = true;
            compare(actualLoader.status, Loader.Loading,
                "The actual configured current engine genuinely arms asynchronous Loading, not synchronous Ready");
            verify(actualLoader.asynchronous && actualLoader.item === null,
                "No injected object or synchronous completion substitutes for the pending real Loader");
            if (!data.foreignBeforeLoading)
                foreignEngine();
            console.log("ENGINE_RESTART_PENDING " + JSON.stringify({caseTag: data.tag,
                statusAfterForeign: actualLoader.status, actualAsynchronous: actualLoader.asynchronous,
                currentWindowShown: windowShown}));
            tryCompare(actualLoader, "status", Loader.Ready, 5000,
                "The actual current engine's production controller completes Loading after foreign engine teardown");
            verify(actualLoader.item !== null,
                "Ready belongs to a genuinely created current-engine QObject");
            compare(actualLoader.item.answer, 42,
                "The unchanged original asynchronous component publishes its actual complete result");
        }
    }
}
