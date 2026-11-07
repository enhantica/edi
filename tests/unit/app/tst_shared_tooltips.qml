import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import TooltipAcceptance 1.0
import EasyApplication.Gui.Elements as Elements
import EasyApplication.Gui.Globals as Globals
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "SharedTooltips"
    when: windowShown
    property var app
    Component {
        id: mainFactory
        Main {}
    }
    Component {
        id: buttonFactory
        Elements.ToolButton {
            width: 100
            height: 40
            text: "OK"
            ToolTip.text: "Choose a project first. Open or create a project to enable this control."
        }
    }
    function key(pattern) {
        const keys = Object.keys(Preferences).filter(k => pattern.test(k));
        compare(keys.length, 1, "Preferences exposes one shared tooltip setting matching " + pattern);
        return keys[0];
    }
    function levelKey() {
        return key(/^tooltips?level$/i);
    }
    function delayKey() {
        return key(/^tooltips?delay(?:ms)?$/i);
    }
    function setLevel(value) {
        Preferences[levelKey()] = value;
    }
    function fresh() {
        const result = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property var snapshot: { const r = {}; for (const k of Object.keys(Preferences)) if (/^tooltips?(?:level|delay(?:ms)?|last.*level)$/i.test(k)) r[k] = Preferences[k]; return r; } }');
        verify(!result.error, "A fresh production engine restores the tooltip settings: " + result.error);
        return result.snapshot;
    }
    function freshValue(snapshot, pattern) {
        const keys = Object.keys(snapshot).filter(k => pattern.test(k));
        compare(keys.length, 1, "The restarted Preferences exposes the shared setting " + pattern);
        return snapshot[keys[0]];
    }
    function start() {
        app = mainFactory.createObject(null, {
            visible: true,
            width: 1280,
            height: 720
        });
        verify(app !== null, "The tooltip controls run in the actual application host");
        verify(waitForRendering(app.contentItem), "The real application presents a frame before pointer input");
    }
    function init() {
        const location = TooltipClock.isolateSettings();
        verify(location !== "", "Each tooltip case owns a fresh temporary settings store");
        compare(Globals.Vars.settingsFile, location, "The production Preferences points at this case's isolated store");
        setLevel("Important");
        Preferences[delayKey()] = 1500;
        const last = Object.keys(Preferences).filter(k => /^tooltips?last.*level$/i.test(k));
        for (const k of last)
            Preferences[k] = "Important";
        for (const k of Object.keys(Preferences).filter(k => /^tooltips?(?:level|delay(?:ms)?|last.*level)$/i.test(k)))
            SettingsProof.erase(Globals.Vars.settingsFile, "Edi.Preferences", k);
        SettingsProof.erase(Globals.Vars.settingsFile, "Edi.Preferences", "toolTips");
    }
    function cleanup() {
        SettingsProof.endAnimationClock();
        if (app) {
            app.close();
            app.destroy();
        }
        app = null;
    }
    function test_defaults() {
        const snapshot = fresh();
        compare(freshValue(snapshot, /^tooltips?level$/i), "Important", "The default tooltip level is Important");
        compare(freshValue(snapshot, /^tooltips?delay(?:ms)?$/i), 1500, "The default tooltip delay is 1500 milliseconds");
    }
    function test_migration_data() {
        return [
            {
                tag: "false",
                old: false,
                level: "Off"
            },
            {
                tag: "true",
                old: true,
                level: "Important"
            }
        ];
    }
    function test_migration(data) {
        SettingsProof.erase(Globals.Vars.settingsFile, "Edi.Preferences", levelKey());
        SettingsProof.seed(Globals.Vars.settingsFile, "Edi.Preferences", "toolTips", data.old);
        compare(freshValue(fresh(), /^tooltips?level$/i), data.level, "The saved legacy flag migrates to the declared level");
    }
    function test_persistence() {
        setLevel("Off");
        setLevel("All");
        Preferences[delayKey()] = 2371;
        const snapshot = fresh();
        compare(freshValue(snapshot, /^tooltips?level$/i), "All", "A restart restores the chosen nondefault level");
        compare(freshValue(snapshot, /^tooltips?delay(?:ms)?$/i), 2371, "A restart restores a nontrivial delay without a unit conversion");
    }
    function test_levels_data() {
        const data = [];
        for (const level of ["Off", "Important", "All"])
            for (const self of [false, true])
                for (const enabled of [false, true])
                    data.push({
                        tag: level + "-" + self + "-" + enabled,
                        level,
                        self,
                        enabled
                    });
        return data;
    }
    function test_levels(data) {
        start();
        setLevel(data.level);
        Preferences[delayKey()] = 0;
        const button = buttonFactory.createObject(app.contentItem, {
            x: 300,
            y: 200,
            enabled: data.enabled
        });
        const tips = SettingsProof.tooltipObjects(button).filter(t => TooltipClock.isTooltip(t) && t.text === button.ToolTip.text);
        verify(tips.length > 0, "The real shared control owns an actual tooltip");
        for (const tip of tips) {
            const names = Object.keys(tip).filter(k => /self.?explanatory/i.test(k) && typeof tip[k] === "boolean");
            compare(names.length, 1, "Each actual Qt tooltip exposes one boolean self-explanatory declaration, excluding change signals");
            tip[names[0]] = data.self;
        }
        mouseMove(button, 40, 20);
        const shown = data.level !== "Off" && (data.level === "All" || !data.self || !data.enabled);
        compare(tips.some(t => t.visible), shown, "Off hides all; Important includes unexplained and disabled controls; All includes every control");
        if (!data.enabled && shown) {
            verify(tips.some(t => /project/i.test(t.text) && /open|create/i.test(t.text)), "A disabled tooltip retains both the reason and the enabling action");
        }
        button.destroy();
    }
    function test_disabled_app_control() {
        start();
        Preferences[delayKey()] = 0;
        const save = findChild(app, "appBar.button.save");
        verify(save !== null && !save.enabled, "A new application has an actual disabled Save control");
        for (const level of ["Important", "All"]) {
            mouseMove(app.contentItem, 600, 400);
            setLevel(level);
            mouseMove(save, save.width / 2, save.height / 2);
            const tips = SettingsProof.tooltipObjects(app).filter(t => t.visible && /sav/i.test(t.text));
            verify(tips.length > 0, level + " displays the actual disabled Save control's tooltip");
            verify(tips.some(t => /no project|unchanged|no changes|nothing to save/i.test(t.text) && /open|create|change|edit/i.test(t.text)), "Disabled Save names its reason and an action that enables saving");
        }
    }
    function test_delay_clock() {
        start();
        setLevel("All");
        Preferences[delayKey()] = 1500;
        const button = buttonFactory.createObject(app.contentItem, {
            x: 300,
            y: 200
        });
        mouseMove(button, 40, 20);
        const tip = SettingsProof.tooltipObjects(button).find(t => t.text === button.ToolTip.text);
        verify(tip !== undefined, "The delay witness reaches the shared production tooltip");
        compare(tip.delay, 1500, "The production tooltip receives the preference in milliseconds");
        verify(TooltipClock.arm(tip), "The injected clock observes the actual registered Qt delay timer");
        verify(TooltipClock.advance(1499), "Advance the injected delay clock to one millisecond before expiry");
        verify(!tip.visible, "The tooltip has not started before the full delay");
        verify(TooltipClock.advance(1), "Deliver the actual Qt timer event at exactly the configured delay");
        verify(tip.visible, "The actual tooltip starts when the delay expires without a wall-clock sleep");
        compare(tip.enterAnimationDuration, 1000, "The tooltip keeps its original fade independently of its delay");
        button.destroy();
    }
    function tooltipButton() {
        const items = Array.from(app.appBarRightButtons);
        const button = items.find(item => /tooltip/i.test(item.objectName));
        verify(button !== undefined, "The actual right app bar exposes its tooltip button");
        return button;
    }
    function test_app_bar() {
        start();
        const left = Array.from(app.appBarLeftButtons).map(item => item.objectName);
        compare(JSON.stringify(left), JSON.stringify(["appBar.button.save", "appBar.button.undo", "appBar.button.redo", "appBar.button.reset"]), "Save, Undo, Redo and Clear retain their left app-bar positions");
        const right = Array.from(app.appBarRightButtons);
        compare(right.length, 3, "The right app bar contains exactly assistant, tooltips and Preferences");
        compare(right[0].objectName, "assistant.toggle", "The assistant stays first on the right");
        compare(right[1], tooltipButton(), "Tooltips sits between assistant and Preferences");
        compare(right[2].objectName, "appBar.button.preferences", "Preferences stays last on the right");
        verify(findChild(app, "appBar.button.help") === null && findChild(app, "appBar.button.bug") === null, "Help and bug actions leave the app bar");
        const bar = findChild(app, "appBar"), status = findChild(app, "statusBar");
        verify(bar !== null && status !== null, "Both actual bars are present for separator comparison");
        const borders = item => Render.descendants(item).filter(r => r.width >= item.width * .8 && r.height > 0 && r.height <= 2 && r.color !== undefined);
        const appLines = borders(bar), statusLines = borders(status);
        verify(appLines.length > 0 && statusLines.length > 0, "The app bar and status bar each expose their faint separator");
        verify(appLines.some(a => statusLines.some(b => String(a.color) === String(b.color) && a.height === b.height && a.opacity === b.opacity)), "The app bar uses the status bar separator's colour, opacity and thickness");
        Ui.click(test, Probe, app, "appBar.tab.home");
        const links = Probe.objectsWithProperty(app, "text");
        verify(links.some(item => item.text === "Documentation" && Ui.exposed(item)), "Home retains its visible Documentation route");
        const feedback = links.find(item => item.text === "Help and feedback" && Ui.exposed(item) && typeof item.clicked === "function");
        verify(feedback !== undefined, "Home retains its Help and feedback route");
        mouseClick(feedback, feedback.width / 2, feedback.height / 2);
        verify(Probe.visibleDialogs(app).some(item => /feedback/i.test(item.objectName)), "Home's feedback link opens the real feedback form without network access");
    }
    function test_button_clicks() {
        start();
        setLevel("All");
        const button = tooltipButton();
        mouseClick(button, button.width / 2, button.height / 2, Qt.LeftButton);
        compare(Preferences[levelKey()], "Off", "Left click switches the chosen level Off");
        const snapshot = fresh();
        compare(freshValue(snapshot, /^tooltips?level$/i), "Off", "Off persists across a restart");
        const restarted = TooltipClock.restartAndClick();
        verify(!restarted.error && restarted.clicked, "A fresh production window accepts a real left click on its tooltip button: " + restarted.error);
        compare(restarted.level, "All", "After restart, the first left click restores the last enabled All level");
        mouseClick(button, button.width / 2, button.height / 2, Qt.LeftButton);
        compare(Preferences[levelKey()], "All", "The next left click restores the previous All level");
        setLevel("Important");
        mouseClick(button, button.width / 2, button.height / 2, Qt.LeftButton);
        mouseClick(button, button.width / 2, button.height / 2, Qt.LeftButton);
        compare(Preferences[levelKey()], "Important", "The toggle also remembers Important");
        mouseClick(button, button.width / 2, button.height / 2, Qt.RightButton);
        verify(Preferences.dialogShown, "Right click opens tooltip settings");
        const dialog = findChild(app, "preferences");
        verify(dialog !== null && dialog.visible, "The actual Preferences dialog opens from the tooltip button");
        const controls = Probe.objectsWithProperty(dialog, "visible").filter(item => Ui.exposed(item));
        verify(controls.some(item => typeof item.textAt === "function" && ["All", "Important", "Off"].every(label => {
                for (let i = 0; i < item.count; ++i)
                    if (item.textAt(i) === label)
                        return true;
                return false;
            })), "Right click exposes a real level chooser with All, Important and Off");
        verify(controls.some(item => typeof item.value === "number" && /tooltip.*delay|delay.*tooltip/i.test(item.objectName)), "Right click also exposes the actual tooltip delay input");
    }
}
