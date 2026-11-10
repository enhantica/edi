import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtTest
import "NativeTurn.js" as Turn
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
    property string gateTurnSelector: ""
    name: "SharedTooltips"
    when: windowShown
    property var app
    Component {
        id: mainFactory
        Main {}
    }
    Component {
        id: windowFactory
        Window {}
    }
    Component {
        id: classifiedButtonFactory
        Elements.Button {
            width: 100
            height: 40
            text: "OK"
            ToolTip.text: "Choose a project first. Open or create a project to enable this control."
        }
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
    function start(fullApplication = false) {
        app = (fullApplication ? mainFactory : windowFactory).createObject(null, {
            visible: true,
            width: 1280,
            height: 720
        });
        verify(app !== null, "ADR-0076: a real window hosts the original production control");
        verify(waitForRendering(app.contentItem), "ADR-0076: the real window presents a frame before pointer input");
        verify(TooltipClock.movePointer(app.contentItem, 1100, 650), "ADR-0076: every fresh window begins with the physical pointer outside its control targets");
    }
    function init() {
        gateTurnSelector = Turn.begin(test, Probe);
        const location = TooltipClock.isolateSettings();
        verify(location !== "", "Each tooltip case owns a fresh temporary settings store");
        compare(Globals.Vars.settingsFile, location, "The production Preferences points at this case's isolated store");
        setLevel("Important");
        Preferences[delayKey()] = 1000;
        const last = Object.keys(Preferences).filter(k => /^tooltips?last.*level$/i.test(k));
        for (const k of last)
            Preferences[k] = "Important";
    }
    function eraseTooltipSettings() {
        for (const k of Object.keys(Preferences).filter(k => /^tooltips?(?:level|delay(?:ms)?|last.*level)$/i.test(k)))
            SettingsProof.erase(Globals.Vars.settingsFile, "Edi.Preferences", k);
        SettingsProof.erase(Globals.Vars.settingsFile, "Edi.Preferences", "toolTips");
    }
    function cleanup() {
        Preferences.dialogShown = false;
        if (app)
            for (const dialog of Probe.visibleDialogs(app))
                if (typeof dialog.close === "function")
                    dialog.close();
        wait(0);
        SettingsProof.beginAnimationClock();
        SettingsProof.stepAnimationClock(2000);
        wait(0);
        SettingsProof.endAnimationClock();
        if (app) {
            app.close();
            app.destroy();
        }
        app = null;
        Turn.end(gateTurnSelector);
    }
    function test_defaults() {
        eraseTooltipSettings();
        const snapshot = fresh();
        compare(freshValue(snapshot, /^tooltips?level$/i), "Important", "The default tooltip level is Important");
        compare(freshValue(snapshot, /^tooltips?delay(?:ms)?$/i), 1000, "ADR-0076: the amended default tooltip delay is 1000 milliseconds");
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
        const button = classifiedButtonFactory.createObject(app.contentItem, {
            x: 300,
            y: 200,
            enabled: data.enabled
        });
        compare(typeof button.toolTipSelfExplanatory, "boolean", "ADR-0076: the owner exposes the caller classification input");
        button.toolTipSelfExplanatory = data.self;
        verify(waitForPolish(button), "ADR-0076: classification input and button geometry settle before physical hover");
        const tips = SettingsProof.tooltipObjects(button).filter(t => TooltipClock.isTooltip(t) && t.text === button.ToolTip.text);
        verify(tips.length > 0, "The real shared control owns an actual tooltip");
        verify(TooltipClock.movePointer(button, 40, 20), "Pointer input reaches the actual control window");
        wait(0);
        const shown = data.level !== "Off" && (data.level === "All" || !data.self || !data.enabled);
        compare(tips.some(t => t.visible), shown, "ADR-0076: Off hides all, Important includes unexplained and disabled controls, All includes every control: " + JSON.stringify({
            level: Preferences.toolTipLevel,
            sharedLevel: Globals.Vars.toolTipLevel,
            delay: Preferences.toolTipDelay,
            sharedDelay: Globals.Vars.toolTipDelay,
            hovered: button.hovered,
            handlers: Probe.objectsWithProperty(button, "hovered").map(t => t.hovered),
            tips: tips.map(t => ({
                        visible: t.visible,
                        text: t.text,
                        requested: t.requested,
                        delay: t.delay
                    }))
        }));
        if (!data.enabled && shown) {
            verify(tips.some(t => /project/i.test(t.text) && /open|create/i.test(t.text)), "A disabled tooltip retains both the reason and the enabling action");
        }
        button.destroy();
    }
    function test_disabled_app_control() {
        start(true);
        Preferences[delayKey()] = 0;
        const failures = [];
        const kinds = ["Elements.ToolButton", "Elements.CheckBox", "Elements.SideBarButton", "Elements.StatusBarItem", "Elements.TabButton", "Parts.TableViewAdvancedLabel", "Parts.TableViewLabelControl", "Parts.TableViewTwoRowsAdvancedLabel", "SelectorField", "ChartToolButton"];
        const help = "Choose a project first. Open or create a project to enable this control.";
        for (const kind of kinds) {
            const extra = kind === "SelectorField" ? 'options: null; ToolTip.text: "' + help + '";' : kind === "ChartToolButton" ? 'toolTip: "' + help + '";' : 'ToolTip.text: "' + help + '";';
            const source = 'import QtQuick; import QtQuick.Controls; import edi.app; import EasyApplication.Gui.Elements as Elements; import EasyApplication.Gui.Components as Parts; Item { width: 180; height: 50; property alias witness: c; ' + kind + ' { id: c; width: 150; height: 40; ' + extra + ' } }';
            const host = Qt.createQmlObject(source, app.contentItem);
            host.x = 300;
            host.y = 200;
            const control = host.witness;
            if (control.text !== undefined)
                control.text = "A long control label that is truncated inside its available width";
            if (control.valueText !== undefined)
                control.valueText = "Value";
            for (const mode of ["disabled", "ancestor", "unavailable"]) {
                if (mode === "unavailable" && kind !== "ChartToolButton")
                    continue;
                host.enabled = mode !== "ancestor";
                control.enabled = mode !== "disabled";
                if (kind === "ChartToolButton")
                    control.available = mode !== "unavailable";
                for (const level of ["Off", "Important", "All"]) {
                    for (const tip of SettingsProof.tooltipObjects(host).filter(t => TooltipClock.isTooltip(t))) {
                        tip.enterAnimationDuration = 0;
                        tip.exitAnimationDuration = 0;
                    }
                    verify(TooltipClock.movePointer(app.contentItem, 600, 400), "Pointer input reaches the actual control window");
                    setLevel(level);
                    verify(TooltipClock.movePointer(control, control.width / 2, control.height / 2), "Pointer input reaches the actual control window");
                    wait(0);
                    const tips = SettingsProof.tooltipObjects(host).filter(t => TooltipClock.isTooltip(t) && t.text === help);
                    if (tips.some(t => t.visible) !== (level !== "Off"))
                        failures.push(kind + " " + mode + " " + level);
                }
            }
            host.destroy();
        }
        const save = findChild(app, "appBar.button.save");
        verify(save !== null && !save.enabled, "A new application has an actual disabled Save control");
        for (const level of ["Important", "All"]) {
            verify(TooltipClock.movePointer(app.contentItem, 600, 400), "Pointer input reaches the actual control window");
            setLevel(level);
            verify(TooltipClock.movePointer(save, save.width / 2, save.height / 2), "Pointer input reaches the actual control window");
            const tips = SettingsProof.tooltipObjects(app).filter(t => TooltipClock.isTooltip(t) && t.visible && /sav/i.test(t.text));
            if (!tips.some(t => /no project|unchanged|no changes|nothing to save/i.test(t.text) && /open|create|change|edit/i.test(t.text)))
                failures.push("Save reason and enabling action " + level);
        }
        verify(failures.length === 0, "Disabled controls request real popups at Important and All, including disabled ancestors and visually unavailable controls: " + failures.join(", "));
    }
    function test_help_controls() {
        start(true);
        Preferences[delayKey()] = 0;
        const failures = [];
        for (const kind of ["Elements.ComboBox", "Elements.SpinBox", "RowBox"]) {
            const help = "Choose how this preference applies to new projects";
            const source = 'import QtQuick; import QtQuick.Controls; import edi.app; import EasyApplication.Gui.Elements as Elements; ' + kind + ' { width: 200; height: 40; ToolTip.text: "' + help + '" }';
            let control;
            if (kind === "RowBox") {
                Preferences.dialogShown = true;
                wait(0);
                control = findChild(app, "preferences.toolTipLevel");
                verify(control !== null, "The help witness reaches the actual Preferences RowBox");
                control.ToolTip.text = help;
            } else {
                control = Qt.createQmlObject(source, app.contentItem);
                control.x = 300;
                control.y = 200;
            }
            for (const tip of SettingsProof.tooltipObjects(control).filter(t => TooltipClock.isTooltip(t))) {
                tip.enterAnimationDuration = 0;
                tip.exitAnimationDuration = 0;
            }
            for (const level of ["Off", "Important", "All"]) {
                verify(TooltipClock.movePointer(app.contentItem, 600, 400), "Pointer input reaches the actual control window");
                setLevel(level);
                verify(TooltipClock.movePointer(control, control.width / 2, control.height / 2), "Pointer input reaches the actual control window");
                wait(0);
                const tips = SettingsProof.tooltipObjects(control).filter(t => TooltipClock.isTooltip(t) && t.text === help);
                if (tips.some(t => t.visible) !== (level !== "Off"))
                    failures.push(kind + " " + level);
            }
            if (kind !== "RowBox")
                control.destroy();
        }
        verify(failures.length === 0, "ComboBox, SpinBox and the Preferences RowBox display their actual help popups through the level policy: " + failures.join(", "));
    }
    function test_selector_popup_owner_data() {
        return ["Off", "Important", "All"].map(level => ({
                    tag: level,
                    level
                }));
    }
    function test_selector_popup_owner(data) {
        start();
        setLevel(data.level);
        Preferences[delayKey()] = 0;
        const help = "Choose a project and open its settings";
        const refusal = "This choice is unavailable. Choose a supported value";
        const control = Qt.createQmlObject('import QtQuick; import QtQuick.Controls; import edi.app; SelectorField { options: null; width: 240; height: 40 }', app.contentItem);
        control.x = 300;
        control.y = 200;
        control.z = 1000;
        control.disabledReason = help;
        const tips = SettingsProof.tooltipObjects(control).filter(t => TooltipClock.isTooltip(t));
        compare(tips.filter(t => t.text === help).length, 1, "SelectorField constructs exactly one owner of its help popup");
        for (const tip of tips) {
            tip.enterAnimationDuration = 0;
            tip.exitAnimationDuration = 0;
        }
        verify(waitForPolish(control), "The standalone selector is laid out before pointer input");
        for (const mode of ["help", "refusal", "open-list"]) {
            verify(TooltipClock.movePointer(app.contentItem, 1100, 500), "The pointer starts outside the selector before entering it");
            control.refusal = mode === "refusal" ? refusal : "";
            compare(control.ToolTip.text, help, "ADR-0076: semantic help stays populated while the warned base yields to the refusal owner");
            if (mode === "open-list")
                control.popup.open();
            verify(TooltipClock.movePointer(control, 100, 20), "Selector hover reaches its own actual QQuickWindow");
            wait(0);
            const visible = tips.filter(t => t.visible);
            const wanted = data.level === "Off" || mode === "open-list" ? [] : [mode === "refusal" ? refusal : help];
            compare(JSON.stringify(visible.map(t => t.text).sort()), JSON.stringify(wanted), "SelectorField owns exactly one help popup, refusal suppresses help, and an open list suppresses help: " + mode);
        }
        control.destroy();
    }
    function test_experiment_selector_owners_data() {
        return ["powder", "single crystal"].map(sample => ({
                    tag: sample,
                    sample
                }));
    }
    function test_experiment_selector_owners(data) {
        start();
        setLevel("All");
        Preferences[delayKey()] = 0;
        verify(Session.createProject("Tooltip ownership", ""), "The selector witness creates a real empty project");
        verify(Session.project.createExperiment(), "The selector witness creates a real calculation-only experiment");
        if (data.sample === "single crystal")
            verify(Session.project.setExperimentType(Session.project.experiments.count - 1, "sampleForm", "single crystal"), "The actual experiment enters the single-crystal reason state");
        compare(Session.project.currentExperiment.sampleFormToken, data.sample, "The ExperimentType witness reaches the requested real sample-form state");
        const group = Qt.createQmlObject('import QtQuick; import edi.app; ExperimentTypeGroup { project: Session.project; experiment: Session.project.currentExperiment; experimentIndex: Session.project.experiments.count - 1 }', app.contentItem);
        group.x = 300;
        group.y = 200;
        group.z = 1000;
        verify(waitForPolish(group), "The real ExperimentType selectors and reason wrappers finish layout");
        const tips = SettingsProof.tooltipObjects(group).filter(t => TooltipClock.isTooltip(t));
        for (const tip of tips) {
            tip.enterAnimationDuration = 0;
            tip.exitAnimationDuration = 0;
        }
        const failures = [];
        for (const level of ["Off", "Important", "All"]) {
            setLevel(level);
            for (const name of ["sampleForm", "beamMode", "radiationProbe", "scatteringType", "dimensionality", "polarisation"]) {
                const control = findChild(group, "experimentType." + name);
                verify(control !== null, "The actual ExperimentType group exposes selector " + name);
                for (const refused of [false, true]) {
                    verify(TooltipClock.movePointer(app.contentItem, 1100, 500), "The pointer leaves the previous ExperimentType selector");
                    const refusal = "This choice is blocked. Choose a supported value";
                    control.refusal = refused ? refusal : "";
                    verify(TooltipClock.movePointer(control, control.width / 2, control.height / 2), "Pointer hover reaches the actual selector through its reason wrapper");
                    wait(0);
                    const visible = tips.filter(t => t.visible);
                    if (visible.length !== (level === "Off" ? 0 : 1))
                        failures.push(name + " refused=" + refused + " popup count=" + visible.length);
                    if (level !== "Off" && refused && !visible.every(t => t.text === refusal))
                        failures.push(name + " leaves help or an outer reason visible beside its refusal");
                    if (level !== "Off" && !refused && !visible.some(t => t.text.length > 0))
                        failures.push(name + " lacks its enabled help or disabled reason");
                }
            }
        }
        group.destroy();
        Session.closeProject();
        verify(failures.length === 0, "ExperimentType's selectors and reason wrappers share one popup with refusal priority: " + failures.join(", "));
    }
    function test_group_boundary() {
        start();
        const host = Qt.createQmlObject('import QtQuick; import EasyApplication.Gui.Elements as Elements; Flickable { width: 250; height: 150; contentHeight: 800; clip: true; property alias group: group; Elements.GroupBox { id: group; y: 80; width: 240; title: "Boundary witness"; collapsed: false; contentItem: Item { implicitHeight: 300; Rectangle { width: 100; height: 300; clip: true } } } }', app.contentItem);
        host.x = 300;
        host.y = 200;
        verify(SettingsProof.beginAnimationClock(), "The public animation clock controls the actual group fold");
        const failures = [];
        for (const collapsed of [false, true]) {
            host.group.collapsed = collapsed;
            wait(0);
            verify(SettingsProof.stepAnimationClock(1000), "The group reaches its expanded or folded resting state");
            for (const scroll of [0, 100, 220]) {
                host.contentY = scroll;
                wait(0);
                if (!host.group.layer.enabled)
                    failures.push("collapsed=" + collapsed + " scroll=" + scroll);
            }
        }
        host.destroy();
        verify(failures.length === 0, "GroupBox retains a layer at expanded and folded rest and while crossing its scrolling parent's clip: " + failures.join(", "));
    }
    function test_supported_only_selectors() {
        start();
        Preferences[delayKey()] = 0;
        verify(Session.createProject("Disabled selector reasons", ""), "The supported-only witness creates an actual project");
        verify(Session.project.createExperiment(), "The supported-only witness creates an actual calculation-only experiment");
        const group = Qt.createQmlObject('import QtQuick; import edi.app; ExperimentTypeGroup { project: Session.project; experiment: Session.project.currentExperiment; experimentIndex: Session.project.experiments.count - 1 }', app.contentItem);
        group.x = 300;
        group.y = 200;
        group.z = 1000;
        verify(waitForPolish(group), "The actual supported-only selectors finish layout before hover");
        const tips = SettingsProof.tooltipObjects(group).filter(t => TooltipClock.isTooltip(t));
        for (const tip of tips) {
            tip.enterAnimationDuration = 0;
            tip.exitAnimationDuration = 0;
        }
        const failures = [];
        for (const name of ["scatteringType", "dimensionality", "polarisation"]) {
            const control = findChild(group, "experimentType." + name);
            verify(control !== null, "The real ExperimentType group exposes its supported-only selector " + name);
            verify(!control.enabled, "A supported-only selector remains disabled while there is no alternative value");
            for (const level of ["Off", "Important", "All"]) {
                verify(TooltipClock.movePointer(app.contentItem, 1100, 500), "The pointer leaves the prior supported-only selector");
                setLevel(level);
                verify(TooltipClock.movePointer(control, control.width / 2, control.height / 2), "The pointer enters the disabled supported-only selector through its production hover route");
                wait(0);
                const visible = tips.filter(t => t.visible);
                if (visible.length !== (level === "Off" ? 0 : 1))
                    failures.push(name + " " + level + " count=" + visible.length);
                for (const tip of visible) {
                    const reason = name === "scatteringType" ? /only.*bragg.*support/i : /only.*one.*support/i;
                    if (!reason.test(tip.text))
                        failures.push(name + " " + level + " missing restriction in " + tip.text);
                }
            }
        }
        group.destroy();
        verify(failures.length === 0, "Supported-only selectors show their actual restriction in one popup at Important and All, and no popup at Off: " + failures.join(", "));
    }
    function test_disabled_slider_reason_data() {
        return [
            {
                tag: "unbound-alias",
                alias: null
            },
            {
                tag: "empty-alias",
                alias: ""
            },
            {
                tag: "value-alias",
                alias: "0.3700"
            }
        ];
    }
    function test_disabled_slider_reason(data) {
        start();
        Preferences[delayKey()] = 0;
        const control = Qt.createQmlObject('import QtQuick; import QtQuick.Controls; import EasyApplication.Gui.Elements as Elements; Elements.Slider { width: 240; height: 40; enabled: false; value: 0.37 }', app.contentItem);
        control.x = 300;
        control.y = 200;
        control.z = 1000;
        const reason = "This value is constrained. Remove its constraint to enable the slider.";
        // This is the existing caller input. It must not replace disabled-reason precedence.
        if (data.alias !== null)
            control.toolTipText = data.alias;
        control.ToolTip.text = reason;
        const tips = SettingsProof.tooltipObjects(control).filter(t => TooltipClock.isTooltip(t));
        verify(tips.length > 0, "The shared Slider owns an actual popup for the reason witness");
        for (const tip of tips) {
            tip.enterAnimationDuration = 0;
            tip.exitAnimationDuration = 0;
        }
        const failures = [];
        for (const level of ["Off", "Important", "All"]) {
            verify(TooltipClock.movePointer(app.contentItem, 1100, 500), "The pointer leaves the disabled slider between policy levels");
            setLevel(level);
            verify(TooltipClock.movePointer(control, control.width / 2, control.height / 2), "Pointer hover reaches the disabled shared Slider");
            wait(0);
            const visible = tips.filter(t => t.visible);
            if (visible.length !== (level === "Off" ? 0 : 1))
                failures.push(level + " count=" + visible.length);
            if (visible.some(t => t.text !== reason))
                failures.push(level + " displayed=" + visible.map(t => t.text).join("|"));
        }
        control.destroy();
        verify(failures.length === 0, "A disabled Slider shows its enabling reason ahead of an empty or nonempty caller alias at Important and All, and hides it at Off: " + failures.join(", "));
    }
    function test_delay_clock() {
        start();
        setLevel("All");
        Preferences[delayKey()] = 1000;
        const button = buttonFactory.createObject(app.contentItem, {
            x: 300,
            y: 200
        });
        verify(TooltipClock.movePointer(button, 40, 20), "Pointer input reaches the actual control window");
        const tip = SettingsProof.tooltipObjects(button).find(t => t.text === button.ToolTip.text);
        verify(tip !== undefined, "The delay witness reaches the shared production tooltip");
        compare(tip.delay, 1000, "The production tooltip receives the preference in milliseconds");
        verify(TooltipClock.arm(tip), "The injected clock observes the actual registered Qt delay timer");
        verify(TooltipClock.advance(999), "Advance the injected delay clock to one millisecond before expiry");
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
        start(true);
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
        start(true);
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
