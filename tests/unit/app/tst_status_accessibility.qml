import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import StatusAccessibilityAcceptance 1.0

Item {
    id: surface
    width: 500
    height: 160
    Component {
        id: holder
        Item { width: 500; height: 160 }
    }
    Component {
        id: status
        FitStatusItem {
            x: 25
            y: 45
            valueText: "Fit"
            keyIcon: "play-circle"
            clickable: true
            framed: true
            ToolTip.text: "Fit the free parameters"
            property bool retireAction: false
            onClicked: {
                if (retireAction)
                    clickable = false;
            }
        }
    }
    TestCase {
        id: test
        name: "StatusAccessibilityBoundary"
        when: windowShown
        SignalSpy { id: clicked; signalName: "clicked" }
        function init() {
            failOnWarning(/.*/);
        }
        function cleanup() {
            clicked.target = null;
            StatusAccessibilityProof.stopLifetimeWatch();
        }
        function createAction(framed, clickable = true) {
            const parent = createTemporaryObject(holder, surface);
            const item = createTemporaryObject(status, parent, {framed, clickable});
            verify(item !== null && waitForPolish(item), "The shared production status item reaches its real Qt window");
            compare(item.focusPolicy, Qt.NoFocus, "Accessibility does not add a keyboard or input focus proxy");
            compare(item.activeFocusOnTab, false, "The original status Control remains outside ordinary Tab focus");
            clicked.target = item;
            verify(clicked.valid, "The observer watches the actual original clicked signal");
            clicked.clear();
            return item;
        }
        function live(item, name) {
            compare(item.focusPolicy, Qt.NoFocus, "A live accessibility action preserves original Control focus policy");
            compare(item.Accessible.role, Accessible.Button, "A clickable status item declares a Button role");
            const facts = StatusAccessibilityProof.observe(item);
            verify(facts.valid && facts.button && facts.press && facts.focusable && !facts.disabled && !facts.invisible,
                "The current native interface really exposes its enabled visible Press action");
            compare(facts.name, name, "The current accessible name is the actual value caption");
            compare(facts.description, item.ToolTip.text, "The current tooltip is the action description");
            return facts.id;
        }
        function attempt(id) {
            const result = StatusAccessibilityProof.press(id);
            verify(result.valid && result.attempted, "The control reaches the actual native Qt action interface");
        }
        function passive(item, name) {
            compare(item.focusPolicy, Qt.NoFocus, "Passive retirement preserves original Control focus policy");
            compare(item.Accessible.role, Accessible.NoRole, "An unavailable/passive root keeps original Control semantics");
            compare(item.Accessible.focusable, false, "Passive retirement clears Button's sticky focusable metadata");
            const facts = StatusAccessibilityProof.observe(item);
            verify(!facts.button && !facts.press && !facts.focusable,
                "NoRole plus a still-connected Press handler must not advertise an unavailable action");
            const text = Probe.objectsWithProperty(item, "text").map(child => StatusAccessibilityProof.observe(child));
            verify(text.some(child => child.valid && child.staticText && !child.invisible && child.name === name),
                "The actual child value remains readable through native text accessibility");
        }
        function test_live_name_description_and_shared_clicked_data() {
            return [{tag: "framed", framed: true}, {tag: "unframed", framed: false}];
        }
        function test_live_name_description_and_shared_clicked(data) {
            const item = createAction(data.framed);
            let id = live(item, "Fit");
            attempt(id);
            compare(clicked.count, 1, "One native accessible Press emits the original clicked signal exactly once");
            item.valueText = "Continue";
            item.ToolTip.text = "Current continuation description";
            id = live(item, "Continue");
            attempt(id);
            compare(clicked.count, 2, "Renaming retains the same current action, with no stale callback");
            item.clickable = false;
            verify(item.enabled, "Unavailability preserves the Control's hover and tooltip behavior");
            passive(item, "Continue");
            attempt(id);
            compare(clicked.count, 2, "A cached native interface cannot activate an unavailable item");
            item.clickable = true;
            live(item, "Continue");
            item.parent.enabled = false;
            verify(StatusAccessibilityProof.observe(item).disabled, "The negative reaches actual inherited disabled state");
            const disabledFacts = StatusAccessibilityProof.observe(item);
            verify(disabledFacts.valid, "Inherited disabling preserves the actual native interface");
            compare(item.Accessible.role, Accessible.NoRole, "Inherited disabling retires the root Button role");
            compare(item.Accessible.focusable, false, "Inherited disabling clears attached focusable metadata");
            verify(!disabledFacts.button && !disabledFacts.press && !disabledFacts.focusable,
                "Inherited disabling retires native Button, advertised Press and focusability");
            attempt(id);
            compare(clicked.count, 2, "Inherited disabling refuses Press at the same actual action door");
            item.parent.enabled = true;
            item.parent.visible = false;
            verify(StatusAccessibilityProof.observe(item).invisible, "The negative reaches actual inherited hidden state");
            const hiddenFacts = StatusAccessibilityProof.observe(item);
            verify(hiddenFacts.valid, "Inherited hiding preserves the actual native interface");
            compare(item.Accessible.role, Accessible.NoRole, "Inherited hiding retires the root Button role");
            compare(item.Accessible.focusable, false, "Inherited hiding clears attached focusable metadata");
            verify(!hiddenFacts.button && !hiddenFacts.press && !hiddenFacts.focusable,
                "Inherited hiding retires native Button, advertised Press and focusability");
            attempt(id);
            compare(clicked.count, 2, "A hidden current item refuses cached native Press");
            item.parent.visible = true;
            live(item, "Continue");
            attempt(id);
            compare(clicked.count, 3, "Restoring the live owner restores exactly one working action");
        }
        function test_passive_unframed_value_never_advertises_press() {
            const item = createAction(false, false);
            item.valueText = "7";
            item.clickable = false;
            passive(item, "7");
            item.clickable = true;
            const id = live(item, "7");
            item.clickable = false;
            passive(item, "7");
            attempt(id);
            compare(clicked.count, 0, "The passive-actionable-passive roundtrip retires action and focusability without business effects");
        }
        function test_reentry_disconnects_press_and_destroyed_identity_cannot_dispatch() {
            const item = createAction(true);
            const id = live(item, "Fit");
            item.retireAction = true;
            attempt(id);
            compare(clicked.count, 1, "A reentrant unavailability transition retains the single original signal");
            passive(item, "Fit");
            attempt(id);
            compare(clicked.count, 1, "The retired signal connection cannot advertise or dispatch a later Press");
            verify(StatusAccessibilityProof.watchLifetime(item), "The lifetime gate watches actual QObject destruction");
            item.destroy();
            tryVerify(() => {
                const facts = StatusAccessibilityProof.lifetimeFacts();
                return facts.destroyed === 1 && !facts.alive;
            }, 1000, "Ordinary Qt destruction retires the actual object");
            const after = StatusAccessibilityProof.press(id);
            verify(!after.valid && !after.attempted, "A retained accessible ID cannot recover a destroyed owner");
            compare(clicked.count, 1, "No action is emitted after actual destruction");
        }
        function test_pending_delete_stays_live_before_ordinary_unwind() {
            const item = createAction(true);
            const id = live(item, "Fit");
            verify(StatusAccessibilityProof.watchLifetime(item), "The queued-owner witness watches actual QObject lifetime");
            item.destroy();
            compare(StatusAccessibilityProof.lifetimeFacts().destroyed, 0, "The same script still precedes actual QObject destruction");
            verify(StatusAccessibilityProof.lifetimeFacts().alive, "The same script retains the actual guarded native owner before deletion");
            // Public destroy() posts DeferredDelete; it does not itself retire
            // the still-live context or declared action availability.
            compare(live(item, "Fit"), id, "The pending-delete interval retains the SAME live native interface");
            attempt(id);
            compare(clicked.count, 1, "One pending-live Press emits the SAME original clicked signal exactly once");
            tryVerify(() => {
                const facts = StatusAccessibilityProof.lifetimeFacts();
                return facts.destroyed === 1 && !facts.alive;
            }, 1000, "The ordinary event unwind then deletes the same owner");
            const after = StatusAccessibilityProof.press(id);
            verify(!after.valid && !after.attempted, "The same retained ID is invalid after actual destruction");
            compare(clicked.count, 1, "The actual destroyed owner cannot emit another clicked signal");
        }
        function test_public_retirement_refuses_pending_delete_press() {
            const item = createAction(true);
            const id = live(item, "Fit");
            item.clickable = false;
            passive(item, "Fit");
            verify(StatusAccessibilityProof.watchLifetime(item), "The retired pending-delete witness watches the actual owner");
            item.destroy();
            compare(StatusAccessibilityProof.lifetimeFacts().destroyed, 0, "Retired availability is proved before actual destruction");
            verify(StatusAccessibilityProof.lifetimeFacts().alive, "The retired control is still alive in this same script");
            passive(item, "Fit");
            attempt(id);
            compare(clicked.count, 0, "Explicit public availability retirement refuses cached Press before deletion");
            tryVerify(() => {
                const facts = StatusAccessibilityProof.lifetimeFacts();
                return facts.destroyed === 1 && !facts.alive;
            }, 1000, "Ordinary event unwind deletes the genuinely retired owner");
            const after = StatusAccessibilityProof.press(id);
            verify(!after.valid && !after.attempted, "Actual destruction invalidates the retired cached interface");
            compare(clicked.count, 0, "Neither pending retired nor actually destroyed owner emits clicked");
        }
    }
}
