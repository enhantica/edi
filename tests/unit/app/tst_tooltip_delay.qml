import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import TooltipAcceptance 1.0
import EasyApplication.Gui.Globals as Globals
import "NativeTurn.js" as Turn
import "TooltipDelayCases.js" as Cases
import "TooltipDelayUi.js" as DelayUi

TestCase {
    id: test
    name: "TooltipDelay"
    when: windowShown
    property string gateTurnSelector: ""
    property var app
    property var preferencesFactory
    property var preferencesDialog
    property var dialog
    property var control
    property var second
    Component { id: windowFactory; Window { visible: true; width: 1280; height: 900 } }
    function initTestCase() {
        app = windowFactory.createObject(null);
        preferencesFactory = Qt.createComponent("edi.app", "AppPreferencesDialog");
        preferencesDialog = preferencesFactory.createObject(app.contentItem);
    }
    function cleanupTestCase() {
        if (preferencesDialog) preferencesDialog.destroy();
        preferencesDialog = null;
        if (app) app.destroy();
        app = null;
    }
    function init() {
        gateTurnSelector = Turn.begin(test, Probe);
        verify(TooltipClock.isolateSettings() !== "", "ADR-0076: each live-delay case has an isolated real settings store");
        app.update();
        verify(app !== null && waitForRendering(app.contentItem), "ADR-0076: live delay changes use a rendered real window");
        Preferences.toolTipLevel = "Off";
        Preferences.toolTipLevel = "All";
        Preferences.toolTipDelay = 3000;
        verify(TooltipClock.movePointer(app.contentItem, 1100, 800), "ADR-0076: the pointer begins outside all delay witnesses");
    }
    function cleanup() {
        Preferences.dialogShown = false;
        if (control) control.destroy();
        if (second) second.destroy();
        dialog = control = second = null;
        wait(0);
        Turn.end(gateTurnSelector);
    }
    function test_editor_changes_data() { return Cases.cases.edits; }
    function test_editor_changes(data) {
        dialog = DelayUi.open(test, preferencesFactory, app, Preferences, preferencesDialog);
        DelayUi.edit(test, dialog, Probe, SettingsProof, data.tag, data.expected);
        compare(Preferences.toolTipDelay, data.expected, "ADR-0076: every Preferences edit immediately changes the actual stored delay");
        compare(Globals.Vars.toolTipDelay, data.expected, "ADR-0076: every Preferences edit immediately reaches the shared tooltip policy");
        compare(SettingsProof.value(Globals.Vars.settingsFile, "Edi.Preferences", "toolTipDelay"), data.expected, "ADR-0076: every delay editor path synchronizes its actual persisted value");
        const location = String(Globals.Vars.settingsFile);
        const parent = location.slice(0, location.lastIndexOf("/") + 1);
        const stored = SettingsProof.fileObservation(parent, SettingsProof.fileName(location));
        verify(stored.exists && new RegExp("(^|\\n)toolTipDelay="+data.expected+"(\\r?\\n|$)").test(stored.text), "ADR-0076: the independently read physical settings bytes contain the chosen delay, beyond an in-process settings cache");
        dialog.close();
        tryCompare(dialog, "visible", false, 2000, "ADR-0076: the Preferences editor is closed before its engine restart witness");
        const restored = SettingsProof.restart('import QtQuick; import edi.app; import EasyApplication.Gui.Globals as G; QtObject { property int delay: Preferences.toolTipDelay; property string level: Preferences.toolTipLevel; property int sharedDelay: G.Vars.toolTipDelay }');
        verify(!restored.error, "ADR-0076: a fresh production engine restarts with the actual saved settings: "+restored.error);
        compare(restored.level, "All", "ADR-0076: the chosen level survives the same restart as the delay");
        compare(restored.delay, data.expected, "ADR-0076: every actual Preferences editing path survives a production-engine restart");
        compare(restored.sharedDelay, data.expected, "ADR-0076: the restarted shared policy uses the saved delay immediately");
    }
    function make(data) {
        const source = 'import QtQuick; import QtQuick.Controls; import edi.app; import EasyApplication.Gui.Elements as E; import EasyApplication.Gui.Components as C; '+data.kind+' { x: 300; y: 650; width: 240; height: 40; '+data.body+' }';
        const owner = Qt.createQmlObject(source, app.contentItem);
        for (const [key, value] of Object.entries(data.after || {})) owner[key] = value;
        if (data.width) owner.width = data.width;
        verify(owner !== null && waitForPolish(owner), "ADR-0076: the live-delay witness instantiates its actual production owner: "+data.tag);
        return owner;
    }
    function activate(data, owner) {
        for (const [key, value] of Object.entries(data.after || {})) owner[key] = value;
        if (data.focus) {
            owner.forceActiveFocus();
            compare(owner.activeFocus, true, "ADR-0076: the parameter warning is requested through actual editor focus");
        }
        if (data.popup) owner.requestedTip.requested = true;
        else verify(TooltipClock.movePointer(owner, owner.width/2, owner.height/2), "ADR-0076: a real hover reaches the retained tooltip owner");
        wait(0);
    }
    function test_existing_and_new_owners_update_data() { return Cases.cases.owners; }
    function test_existing_and_new_owners_update(data) {
        control = make(data);
        activate(data, control);
        let tips = SettingsProof.tooltipObjects(control).filter(item => TooltipClock.isTooltip(item) && item.text !== "");
        verify(tips.length > 0, "ADR-0076: existing eager or lazy production tooltip objects are materialized before Preferences changes: "+data.tag);
        for (const tip of tips) {
            compare(tip.delay, 3000, "ADR-0076: the existing owner starts with the independently selected old delay");
            tip.enterAnimationDuration = tip.exitAnimationDuration = 0;
        }
        if (data.popup) control.requestedTip.requested = false;
        verify(TooltipClock.movePointer(app.contentItem, 1100, 800), "ADR-0076: leaving the owner cancels its old hover timer");
        dialog = DelayUi.open(test, preferencesFactory, app, Preferences, preferencesDialog);
        DelayUi.edit(test, dialog, Probe, SettingsProof, "typed-enter", 2371);
        dialog.close();
        tryCompare(dialog, "visible", false, 2000, "ADR-0076: closing Preferences leaves the original window and tooltip objects alive");
        compare(Preferences.toolTipDelay, 2371, "ADR-0076: the chosen delay is applied in the same live application session");
        compare(Globals.Vars.toolTipDelay, 2371, "ADR-0076: the shared delay changes without restarting the application");
        const current = SettingsProof.tooltipObjects(control);
        const retained = tips.filter(tip => current.includes(tip));
        if (!data.transient)
            compare(retained.length, tips.length, "ADR-0076: existing eager tooltip objects stay alive during a Preferences edit");
        for (const tip of retained)
            compare(tip.delay, 2371, "ADR-0076: every still-existing tooltip receives the live delay without reconstruction: "+data.tag);
        second = make(data);
        second.x = 650;
        activate(data, second);
        const created = SettingsProof.tooltipObjects(second).filter(item => TooltipClock.isTooltip(item) && item.text !== "");
        verify(created.length > 0 && created.every(tip => tip.delay === 2371), "ADR-0076: tooltips created after the edit inherit the same new delay: "+data.tag);
        if (data.popup) second.requestedTip.requested = false;
        verify(TooltipClock.movePointer(app.contentItem, 1100, 800), "ADR-0076: the pointer leaves the newly-created control before retesting the original");
        activate(data, control);
        tips = SettingsProof.tooltipObjects(control).filter(item => TooltipClock.isTooltip(item) && item.text !== "");
        verify(tips.length > 0 && tips.every(tip => tip.delay === 2371), "ADR-0076: a transient owner rematerializes its popup using the live changed delay");
        verify(tips.every(tip => !tip.visible), "ADR-0076: the retained tooltip is still hidden before its changed delay");
        verify(TooltipClock.armAll(tips) > 0, "ADR-0076: the retained owner registers a real timer with the changed delay");
        verify(TooltipClock.advanceAll(2370), "ADR-0076: the actual changed-delay timers reach one millisecond before expiry");
        verify(tips.every(tip => !tip.visible), "ADR-0076: a live delay change never allows the old hover deadline to open the tooltip early");
        verify(TooltipClock.advanceAll(1), "ADR-0076: actual changed-delay timer events are delivered at the selected boundary");
        verify(tips.some(tip => tip.visible), "ADR-0076: the same tooltip opens exactly at its newly selected delay without restart");
    }
}
