import QtQuick
import QtQuick.Controls
import QtQuick.Window
import QtTest
import "NativeTurn.js" as Turn
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import TooltipAcceptance 1.0
import "../../fixtures/shared_ui/TooltipContractCases.js" as Matrix
import EasyApplication.Gui.Elements as Elements
import EasyApplication.Gui.Components as Components

TestCase {
    id: test
    property string gateTurnSelector: ""
    name: "TooltipContract"
    when: windowShown
    property var host
    property var surface
    property var control
    readonly property int chosenDelay: 2371
    readonly property string help: "Open the project settings to choose another value."
    readonly property string reason: "This control is disabled. Open a project to enable it."
    readonly property string refusal: "This value was refused. Choose another supported value."
    readonly property string rule: "Start with ok to enter a supported label."
    property bool ownsProject: false
    Component {
        id: windowFactory
        Window {
            width: 900
            height: 700
            visible: true
            Item {
                objectName: "tooltip.surface"
                anchors.fill: parent
                property real spacing: 4
                focus: true
            }
        }
    }
    function init() {
        gateTurnSelector = Turn.begin(test, Probe);
        verify(TooltipClock.isolateSettings() !== "", "ADR-0076: each ownership witness uses isolated real settings");
        host = windowFactory.createObject(null);
        verify(host !== null, "ADR-0076: ownership witnesses use a real Qt window");
        surface = findChild(host, "tooltip.surface");
        verify(surface !== null && waitForRendering(surface), "ADR-0076: pointer input reaches a rendered control surface");
        Preferences.toolTipLevel = "All";
        Preferences.toolTipDelay = chosenDelay;
        verify(SettingsProof.beginAnimationClock(), "ADR-0076: animation settlement uses the public injected clock");
        leave();
    }
    function cleanup() {
        if (control)
            control.destroy();
        control = null;
        if (ownsProject)
            Session.closeProject();
        ownsProject = false;
        SettingsProof.endAnimationClock();
        if (host)
            host.destroy();
        host = null;
        surface = null;
        Turn.end(gateTurnSelector);
    }
    function leave() {
        verify(TooltipClock.movePointer(surface, 850, 650), "ADR-0076: the physical pointer leaves the previous control");
        surface.forceActiveFocus();
        verify(SettingsProof.stepAnimationClock(1000), "ADR-0076: obsolete popup exit animations settle on the injected clock");
        wait(0);
    }
    function make(kind, body) {
        const imports = 'import QtQuick; import QtQuick.Controls; import edi.app; import EasyApplication.Gui.Elements as E; import EasyApplication.Gui.Components as C; ';
        control = Qt.createQmlObject(imports + kind + ' { x: 100; y: 100; width: 240; height: 40; ' + (body || '') + ' }', surface);
        verify(control !== null && waitForPolish(control), "ADR-0076: the original production owner has valid geometry before input");
        return control;
    }
    function input(name, value, type) {
        compare(typeof control[name], type, "ADR-0076: the base exposes its declared caller input " + name);
        control[name] = value;
    }
    function hover(focus) {
        if (focus) {
            control.forceActiveFocus();
            compare(control.activeFocus, true, "ADR-0076: focus cases exercise actual editor focus");
        }
        verify(TooltipClock.movePointer(control, control.width / 2, control.height / 2), "ADR-0076: real pointer input reaches the owner including disabled hover");
        wait(0);
    }
    function popups() {
        return SettingsProof.tooltipObjects(control).filter(t => TooltipClock.isTooltip(t));
    }
    function shown() {
        return popups().filter(t => t.visible && t.opacity > 0).map(t => t.text).sort();
    }
    function observation() {
        const at = control.mapToItem(surface, 0, 0);
        return JSON.stringify({
            kind: String(control),
            x: at.x,
            y: at.y,
            width: control.width,
            height: control.height,
            enabled: control.enabled,
            hovered: control.hovered,
            focus: control.activeFocus,
            classification: control.toolTipSelfExplanatory,
            tips: popups().map(t => ({
                        kind: String(t),
                        text: t.text,
                        visible: t.visible,
                        opacity: t.opacity,
                        requested: t.requested,
                        delay: t.delay
                    })),
            hoverObjects: Probe.objectsWithProperty(control, "hovered").map(t => ({
                        kind: String(t),
                        hovered: t.hovered
                    }))
        });
    }
    function settleAnimations() {
        wait(0);
        verify(SettingsProof.stepAnimationClock(1000), "ADR-0076: the first public clock tick starts or advances pending popup transitions");
        wait(0);
        verify(SettingsProof.stepAnimationClock(1000), "ADR-0076: the next public clock tick completes pending popup transitions");
        wait(0);
    }
    function expect(wanted, context) {
        verify(waitForPolish(control), "ADR-0076: layout completes before counting popup owners");
        settleAnimations();
        compare(JSON.stringify(shown()), "[]", "ADR-0076: no ordinary or warning popup precedes the chosen delay: " + context + " " + observation());
        const armed = TooltipClock.armAll(popups());
        if (wanted.length)
            verify(armed > 0, "ADR-0076: the requested popup uses an actual registered Qt delay timer: " + context + " " + observation());
        verify(TooltipClock.advanceAll(chosenDelay - 1), "ADR-0076: advance every actual owner timer to just before expiry");
        settleAnimations();
        compare(JSON.stringify(shown()), "[]", "ADR-0076: every competing popup remains hidden before expiry: " + context);
        verify(TooltipClock.advanceAll(1), "ADR-0076: deliver every actual owner timer at the chosen delay");
        settleAnimations();
        compare(JSON.stringify(shown()), JSON.stringify(wanted.slice().sort()), "ADR-0076: exactly the independently expected ordinary or warning text is shown: " + context);
    }
    function compositionRows() {
        const title = "A complete descriptive cell label";
        return [
            {
                tag: "button",
                kind: "E.Button",
                body: 'text: "Run"; ToolTip.text: ' + JSON.stringify(help),
                wanted: [help]
            },
            {
                tag: "group-button",
                kind: "E.GroupButton",
                body: 'text: "Run"; ToolTip.text: ' + JSON.stringify(help),
                wanted: [help]
            },
            {
                tag: "fitting-label-help",
                kind: "C.ListViewLabel",
                body: 'text: "Header"; ToolTip.text: ' + JSON.stringify(help),
                wanted: [help]
            },
            {
                tag: "fitting-label-no-help",
                kind: "C.ListViewLabel",
                body: 'text: "Header"',
                wanted: []
            },
            {
                tag: "elided-label-help",
                kind: "C.ListViewLabel",
                body: 'text: ' + JSON.stringify(title) + '; ToolTip.text: ' + JSON.stringify(help),
                width: 36,
                elided: true,
                wanted: [title + "\n" + help]
            },
            {
                tag: "elided-label-deduplicated",
                kind: "C.ListViewLabel",
                body: 'text: ' + JSON.stringify(title) + '; ToolTip.text: ' + JSON.stringify(title + ": _test.label"),
                width: 36,
                elided: true,
                wanted: [title + ": _test.label"]
            },
            {
                tag: "elided-label-no-help",
                kind: "C.ListViewLabel",
                body: 'text: ' + JSON.stringify(title),
                width: 36,
                elided: true,
                wanted: [title]
            },
            {
                tag: "fitting-table-help",
                kind: "C.ListViewTextInput",
                body: 'text: "Header"; ToolTip.text: ' + JSON.stringify(help),
                wanted: [help]
            },
            {
                tag: "overflow-table-help",
                kind: "C.ListViewTextInput",
                body: 'text: ' + JSON.stringify(title) + '; ToolTip.text: ' + JSON.stringify(help),
                width: 36,
                overflow: true,
                wanted: [title + "\n" + help]
            },
            {
                tag: "overflow-table-no-help",
                kind: "C.ListViewTextInput",
                body: 'text: ' + JSON.stringify(title),
                width: 36,
                overflow: true,
                wanted: [title]
            },
            {
                tag: "fitting-table-no-help",
                kind: "C.ListViewTextInput",
                body: 'text: "Header"',
                wanted: []
            },
            {
                tag: "field-help",
                kind: "E.TextField",
                body: 'text: "Value"; ToolTip.text: ' + JSON.stringify(help),
                wanted: [help]
            },
            {
                tag: "field-no-help",
                kind: "E.TextField",
                body: 'text: "Value"',
                wanted: []
            },
            {
                tag: "combo-help",
                kind: "E.ComboBox",
                body: 'model: ["First", "Second"]; ToolTip.text: ' + JSON.stringify(help),
                wanted: [help]
            },
            {
                tag: "combo-no-help",
                kind: "E.ComboBox",
                body: 'model: ["First", "Second"]',
                wanted: []
            }
        ];
    }
    function test_composition_data() {
        return Matrix.cases.composition;
    }
    function test_composition(data) {
        const spec = compositionRows().find(item => item.tag === data.spec);
        verify(spec !== undefined, "ADR-0076: every composition matrix row names its declared independent input scenario");
        data = Object.assign({}, spec, data);
        make(data.kind, data.body);
        if (data.width)
            control.width = data.width;
        control.enabled = data.enabled;
        Preferences.toolTipLevel = data.level;
        verify(waitForPolish(control), "ADR-0076: composition uses the actual fitted or shortened layout");
        if (data.elided)
            compare(control.truncated, true, "ADR-0076: the label witness really is elided");
        if (data.overflow)
            compare(control.overflows, true, "ADR-0076: the input witness really overflows");
        hover(false);
        expect(data.level === "Off" ? [] : data.wanted, data.tag);
    }
    function test_explicit_full_text_data() {
        return Matrix.cases.explicit_full_text;
    }
    function test_explicit_full_text(data) {
        make(data.kind, 'text: "1.23"');
        input("fullText", data.fullText, "string");
        input("shortened", data.shortened, "boolean");
        control.ToolTip.text = data.withHelp ? help : "";
        hover(false);
        const text = [data.shortened ? data.fullText : "", data.withHelp ? help : ""].filter(x => x !== "").join("\n");
        expect(text === "" ? [] : [text], data.tag);
    }
    function test_number_label_data() {
        return Matrix.cases.number_label;
    }
    function test_number_label(data) {
        make("NumberLabel", 'number: "123456789.123456"; narrow: "1.23e8"; full: "123456789.123456"');
        control.width = data.width;
        control.enabled = data.enabled;
        Preferences.toolTipLevel = data.level;
        verify(waitForPolish(control), "ADR-0076: the number label completes its actual compaction layout");
        compare(control.shown !== control.number, data.width < 600, "ADR-0076: compact and unchanged number witnesses are distinguishable");
        compare(control.truncated, data.width === 18, "ADR-0076: compact witnesses cover both fitting and elided display");
        hover(false);
        expect(data.level === "Off" || data.width === 600 ? [] : ["123456789.123456"], data.tag);
    }
    function test_classification_data() {
        return Matrix.cases.classification;
    }
    function test_classification(data) {
        make(data.kind, data.kind === "E.ComboBox" ? 'model: ["First", "Second"]' : data.kind === "E.Slider" ? 'from: 0; to: 10; value: 3.25; toolTipText: "Caller slider value"' : 'text: "Value"');
        compare(typeof control.toolTipSelfExplanatory, "boolean", "ADR-0076: classification is a public input on every base owner");
        compare(control.toolTipSelfExplanatory, false, "ADR-0076: caller classification defaults to non-self-explanatory");
        control.toolTipSelfExplanatory = data.self;
        control.enabled = data.enabled;
        control.ToolTip.text = data.enabled ? help : reason;
        Preferences.toolTipLevel = data.level;
        hover(false);
        const wanted = data.level !== "Off" && (data.level === "All" || !data.self || !data.enabled);
        expect(wanted ? [data.kind === "E.Slider" && data.enabled ? "Caller slider value" : data.enabled ? help : reason] : [], data.tag);
    }
    function test_fixed_and_standalone_data() {
        return Matrix.cases.fixed_and_standalone;
    }
    function test_fixed_and_standalone(data) {
        make(data.kind, data.kind === "E.TabButton" ? 'text: "Tab"' : data.kind === "StatusBarItem" ? 'valueText: "Status"' : 'fontIcon: "?"');
        control.enabled = data.enabled;
        const text = data.enabled ? help : reason;
        if (data.kind === "ChartToolButton")
            control.toolTip = text;
        else
            control.ToolTip.text = text;
        Preferences.toolTipLevel = data.level;
        hover(false);
        const wants = data.level !== "Off" && (data.kind !== "E.TabButton" || data.level === "All" || !data.enabled);
        expect(wants ? [text] : [], data.tag);
    }
    function test_focus_and_warning_input_data() {
        return Matrix.cases.focus_and_warning_input;
    }
    function test_focus_and_warning_input(data) {
        make(data.kind, 'text: "1.23"; ToolTip.text: ' + JSON.stringify(help));
        input("fullText", "1.234567890123", "string");
        input("shortened", true, "boolean");
        input("warned", data.warned, "boolean");
        if (data.focus) {
            control.forceActiveFocus();
            compare(control.activeFocus, true, "ADR-0076: focus suppression uses actual active editor focus");
        }
        if (data.hovering)
            hover(data.focus);
        const wants = data.hovering && !data.warned && !(data.kind === "C.ListViewTextInput" && data.focus);
        expect(wants ? ["1.234567890123\n" + help] : [], data.tag);
    }
    function test_base_warning_clearance_data() {
        return Matrix.cases.base_warning_clearance;
    }
    function test_base_warning_clearance(data) {
        make(data.kind, (data.kind === "E.ComboBox" ? 'model: ["First", "Second"];' : 'text: "Value";') + ' ToolTip.text: ' + JSON.stringify(help));
        input("warned", true, "boolean");
        if (data.focus) {
            control.forceActiveFocus();
            compare(control.activeFocus, true, "ADR-0076: warning clearance retains actual editor focus");
        }
        if (data.hovering)
            hover(data.focus);
        expect([], data.tag + " warned");
        control.warned = false;
        wait(0);
        const eligible = data.hovering && !(data.kind === "C.ListViewTextInput" && data.focus);
        expect(eligible ? [help] : [], data.tag + " cleared without leaving hover or focus");
    }
    function test_combo_open_data() {
        return Matrix.cases.combo_open;
    }
    function test_combo_open(data) {
        make("E.ComboBox", 'model: ["First", "Second"]; ToolTip.text: ' + JSON.stringify(help));
        input("warned", data.warned, "boolean");
        hover(false);
        expect(data.warned ? [] : [help], "closed combo");
        control.popup.open();
        verify(SettingsProof.stepAnimationClock(1000), "ADR-0076: the actual selector list opens through its public popup API");
        compare(control.popup.visible, true, "ADR-0076: the selector list is genuinely open");
        wait(0);
        settleAnimations();
        compare(JSON.stringify(shown()), "[]", "ADR-0076: an open selector list suppresses every ordinary popup");
    }
    function test_slider_value_data() {
        return Matrix.cases.slider_value;
    }
    function test_slider_value(data) {
        make("E.Slider", 'from: 0; to: 10; value: 3.25');
        if (data.alias !== "untouched")
            control.toolTipText = data.alias === "empty" ? "" : "Caller slider value";
        control.ToolTip.text = reason;
        control.enabled = data.enabled;
        Preferences.toolTipLevel = data.level;
        hover(false);
        const text = !data.enabled ? reason : data.alias === "empty" ? "" : data.alias === "caller" ? "Caller slider value" : "3.25";
        expect(data.level === "Off" || text === "" ? [] : [text], data.tag);
    }
    function test_value_field_data() {
        return Matrix.cases.value_field;
    }
    function test_value_field(data) {
        make("ValueField", 'uid: "cell.length_a"; fieldValue: "okay"; admits: function(t) { return t.startsWith("ok"); }; admitsRule: ' + JSON.stringify(rule));
        Preferences.toolTipLevel = data.level;
        if (["refusal", "refusal-and-rule", "disabled-refusal"].indexOf(data.state) >= 0)
            control.refusal = refusal;
        if (["typed-rule", "refusal-and-rule"].indexOf(data.state) >= 0) {
            control.forceActiveFocus();
            verify(SettingsProof.type(control, "bad"), "ADR-0076: the broken typed-input rule is reached by actual editor text events");
            compare(control.typedAdmitted, false, "ADR-0076: the typed witness actually violates its supplied input rule");
        }
        if (["disabled", "disabled-refusal"].indexOf(data.state) >= 0) {
            control.disabledReason = reason;
            control.enabled = false;
        }
        if (data.state === "clean-focused" || data.state === "focus-only")
            control.forceActiveFocus();
        if (data.state !== "focus-only")
            hover(data.state === "clean-focused" || ["typed-rule", "refusal-and-rule"].indexOf(data.state) >= 0);
        const text = ["refusal", "refusal-and-rule", "disabled-refusal"].indexOf(data.state) >= 0 ? refusal : data.state === "typed-rule" ? rule : data.state === "disabled" ? reason : "a: _cell.length_a";
        expect(data.level === "Off" || data.state === "focus-only" ? [] : [text], data.tag);
    }
    function test_value_field_clearance_data() {
        return Matrix.cases.value_field_clearance;
    }
    function test_value_field_clearance(data) {
        make("ValueField", 'uid: "cell.length_a"; fieldValue: "okay"; admits: function(t) { return t.startsWith("ok"); }; admitsRule: ' + JSON.stringify(rule));
        Preferences.toolTipLevel = data.level;
        if (data.state === "typed-rule") {
            control.forceActiveFocus();
            verify(SettingsProof.type(control, "bad"), "ADR-0076: warning clearance starts with an actual refused typed draft");
            compare(control.typedAdmitted, false, "ADR-0076: the typed draft violates the independent caller rule");
        } else
            control.refusal = refusal;
        if (data.mode === "disabled-hover") {
            control.disabledReason = reason;
            control.enabled = false;
        }
        const focused = data.mode === "focus-only" || data.mode === "focus-and-hover";
        if (focused)
            control.forceActiveFocus();
        if (data.mode !== "focus-only")
            hover(focused);
        expect(data.level === "Off" ? [] : [data.state === "typed-rule" ? rule : refusal], "warned " + data.tag);
        if (data.state === "typed-rule") {
            verify(SettingsProof.type(control, "okay"), "ADR-0076: correcting the typed draft retains the current focus and hover");
            compare(control.typedAdmitted, true, "ADR-0076: the corrected draft clears the typed-input warning");
        } else
            control.refusal = "";
        wait(0);
        expect(data.level === "Off" || data.mode === "focus-only" ? [] : [data.mode === "disabled-hover" ? reason : "a: _cell.length_a"], "cleared " + data.tag);
    }
    function selector() {
        ownsProject = true;
        verify(Session.createProject("Tooltip selector witness", ""), "ADR-0076: selector options belong to an actual project");
        verify(Session.project.createExperiment(), "ADR-0076: selector options are the actual supported experiment model");
        make("SelectorField", 'uid: "experiment_type.sample_form"; options: Session.project.currentExperiment.sampleFormOptions; token: "powder"');
    }
    function test_selector_warning_data() {
        return Matrix.cases.selector_warning;
    }
    function test_selector_warning(data) {
        selector();
        Preferences.toolTipLevel = data.level;
        if (data.state !== "option-help" && data.state !== "clear-token")
            control.helpText = help;
        if (["disabled", "disabled-clear-token"].indexOf(data.state) >= 0) {
            control.disabledReason = reason;
            control.writable = false;
        }
        if (["refusal", "open-refusal", "clear-token", "clear-token-caller", "disabled-clear-token"].indexOf(data.state) >= 0)
            control.refusal = refusal;
        hover(false);
        const initial = data.state === "disabled" ? reason : ["refusal", "open-refusal", "clear-token", "clear-token-caller", "disabled-clear-token"].indexOf(data.state) >= 0 ? refusal : data.state === "option-help" ? "_experiment_type.sample_form powder" : help;
        expect(data.level === "Off" ? [] : [initial], data.tag + " initial");
        if (data.state === "open-refusal") {
            control.popup.open();
            verify(SettingsProof.stepAnimationClock(1000), "ADR-0076: the refused selector's actual list finishes opening");
            compare(control.popup.visible, true, "ADR-0076: refused-selector visibility is checked while its list is open");
            settleAnimations();
            compare(JSON.stringify(shown()), "[]", "ADR-0076: opening a selector list suppresses warnings as well as ordinary help");
        }
        if (["clear-token", "clear-token-caller", "disabled-clear-token"].indexOf(data.state) >= 0) {
            control.token = "single crystal";
            compare(control.refusal, "", "ADR-0076: an actual token change clears the selector's refusal");
            expect(data.level === "Off" ? [] : [data.state === "disabled-clear-token" ? reason : data.state === "clear-token-caller" ? help : "_experiment_type.sample_form single crystal"], "cleared token without pointer exit");
        }
    }
    function test_project_name_data() {
        return Matrix.cases.project_name;
    }
    function test_project_name(data) {
        ownsProject = true;
        verify(Session.createProject("Tooltip name witness", ""), "ADR-0076: project-name warnings use a real project");
        make("DescriptionTab", 'project: Session.project');
        control.width = 720;
        control.height = 550;
        const page = control;
        control = findChild(page, "project.name");
        verify(control !== null && waitForPolish(control), "ADR-0076: the project-name witness reaches the actual metadata field");
        if (data.level !== undefined)
            Preferences.toolTipLevel = data.level;
        control.refusal = refusal;
        if (data.mode !== "hover")
            control.forceActiveFocus();
        if (data.mode !== "focus-only")
            hover(data.mode === "focus-and-hover");
        expect(data.level === "Off" ? [] : [refusal], "project name " + data.mode);
        control.forceActiveFocus();
        verify(SettingsProof.type(control, "tooltip_renamed"), "ADR-0076: a successful rename uses actual editor key events");
        verify(SettingsProof.key(control, Qt.Key_Return), "ADR-0076: the production accepted handler submits the rename");
        compare(Session.project.name, "tooltip_renamed", "ADR-0076: the public model accepts the new project name");
        compare(control.refusal, "", "ADR-0076: a successful rename clears the name refusal without leaving the state");
        settleAnimations();
        compare(JSON.stringify(shown()), "[]", "ADR-0076: a clean project name has no ordinary tooltip");
        control = page;
    }
    function test_standard_footer_icons_data() {
        return Matrix.cases.standard_footer_icons;
    }
    function test_standard_footer_icons() {
        make("E.DialogButtonBox");
        const all = [DialogButtonBox.Ok, DialogButtonBox.Open, DialogButtonBox.Save, DialogButtonBox.Cancel, DialogButtonBox.Close, DialogButtonBox.Discard, DialogButtonBox.Apply, DialogButtonBox.Reset, DialogButtonBox.RestoreDefaults, DialogButtonBox.Help, DialogButtonBox.SaveAll, DialogButtonBox.Yes, DialogButtonBox.YesToAll, DialogButtonBox.No, DialogButtonBox.NoToAll, DialogButtonBox.Abort, DialogButtonBox.Retry, DialogButtonBox.Ignore];
        control.standardButtons = all.reduce((flags, button) => flags | button, 0);
        verify(waitForPolish(control), "ADR-0077: the standard footer instantiates every supported standard button");
        for (const standard of all) {
            const button = control.standardButton(standard);
            verify(button !== null && typeof button.fontIcon === "string" && button.fontIcon !== "", "ADR-0077: every actual standard footer button has an icon, including roles beyond the examples");
        }
        const expected = [[DialogButtonBox.Ok, "check"], [DialogButtonBox.Yes, "check"], [DialogButtonBox.Apply, "check"], [DialogButtonBox.Cancel, "times"], [DialogButtonBox.No, "times"], [DialogButtonBox.Discard, "trash"], [DialogButtonBox.Reset, "undo"], [DialogButtonBox.Help, "question-circle"]];
        for (const role of expected) {
            const button = control.standardButton(role[0]);
            verify(button !== null, "ADR-0077: the standard footer creates the actual button for every documented role");
            compare(button.fontIcon, role[1], "ADR-0077: actual generated standard buttons carry the documented role icon");
        }
    }
}
