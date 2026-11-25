// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import TooltipAcceptance 1.0
import "UiInteraction.js" as Ui

TestCase {
    id: test
    name: "FieldTyping"
    when: windowShown

    property var appWindow
    property int previousDelay
    property string previousLevel

    Component {
        id: application
        Main {
            width: 1400
            height: 1000
        }
    }
    SignalSpy {
        id: edits
        signalName: "edited"
    }
    SignalSpy {
        id: values
        signalName: "valueChanged"
    }

    function init() {
        previousLevel = Preferences.toolTipLevel;
        previousDelay = Preferences.toolTipDelay;
        Preferences.toolTipLevel = "All";
        Preferences.toolTipDelay = 100;
        appWindow = application.createObject(null);
        verify(appWindow !== null, "The field typing witness uses the ordinary application window");
        appWindow.requestActivate();
        tryCompare(appWindow, "active", true, 2000, "Real key events belong to the active application window");
        const scratch = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/e04_t1/editable-project"));
        verify(Session.openProject(scratch), "The native app opens an independent scratch project: " + Session.lastError);
    }

    function cleanup() {
        edits.target = null;
        values.target = null;
        Session.closeProject();
        if (appWindow)
            appWindow.destroy();
        appWindow = null;
        Preferences.toolTipLevel = previousLevel;
        Preferences.toolTipDelay = previousDelay;
    }

    function test_replaces_or_cancels_the_selected_value_data() {
        const controls = [
            {
                tag: "wavelength",
                page: "experiment",
                group: "instrument",
                control: "instrument.setup_wavelength",
                parameter: "hrpt.instrument.setup_wavelength",
                original: 1.494
            },
            {
                tag: "cell-length",
                page: "structure",
                group: "cell",
                control: "cell.length_a",
                parameter: "lbco.cell.length_a",
                original: 3.88
            },
            {
                tag: "atom-displacement",
                page: "structure",
                group: "atom_site_aniso",
                control: "atomSiteAdp.iso.0",
                parameter: "lbco.atom_site.La.adp_iso",
                original: 0.5
            },
            {
                tag: "analysis-value",
                page: "analysis",
                group: "parameters",
                table: "parameters.list",
                parameter: "lbco.cell.length_a",
                original: 3.88
            }
        ];
        const cases = [];
        for (const control of controls)
            for (const waitForAnimation of [false, true])
                cases.push(Object.assign({}, control, {
                    tag: control.tag + (waitForAnimation ? "-after-wait" : "-immediate"),
                    waitForAnimation
                }));
        return cases;
    }

    function findControl(data) {
        Ui.click(test, Probe, appWindow, "appBar.tab." + data.page);
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        Ui.expandGroup(test, Probe, appWindow, "group." + data.group);
        let name = data.control;
        if (data.table) {
            const table = Ui.find(Ui.page(appWindow), data.table, true);
            verify(table !== null, "Analysis exposes its actual parameter table");
            const index = Probe.rows(table.sourceModel).findIndex(row => row.parameter.fullName === data.parameter);
            verify(index >= 0, "The Analysis value belongs to the independently named parameter");
            table.positionViewAtIndex(index, ListView.Contain);
            table.forceLayout();
            name = "parameters.value." + index;
        }
        let control = null;
        tryVerify(() => {
            control = Ui.find(Ui.page(appWindow), name, true);
            return control !== null && control.enabled && control.item !== null;
        }, 2000, "The actual input or delegate is available: " + name);
        Ui.scrollIntoView(control);
        compare(control.item.fullName, data.parameter, "The clicked input belongs to the intended saved parameter");
        compare(control.item.value, data.original, "The loaded project has the independent starting value");
        return control;
    }

    function ownedVisibleTooltips(control) {
        return SettingsProof.tooltipObjects(control).filter(tip => TooltipClock.isTooltip(tip) && tip.visible && SettingsProof.tooltipOwnedBy(tip, control));
    }

    function openValue(control, click) {
        if (click) {
            const point = Ui.clickPoint(control);
            verify(point !== null, "The current value exposes a real mouse hit point");
            let pressDelay = 0;
            for (let parent = control.parent; parent; parent = parent.parent)
                if (typeof parent.pressDelay === "number")
                    pressDelay = Math.max(pressDelay, parent.pressDelay + 1);
            mouseClick(control, point.x, point.y, Qt.LeftButton, Qt.NoModifier, pressDelay);
        }
        let popup = null;
        tryVerify(() => {
            popup = findChild(control, Ui.parameterPopupName(control));
            return popup !== null && popup.visible;
        }, 2000, "Ordinary input makes this value's popup visible");
        return {
            popup,
            editor: Ui.parameterValue(test, control, popup)
        };
    }

    function typeDigits(text) {
        // SettingsProof.type selects all before sending its input. Send each ordinary key ourselves.
        for (const character of text)
            keyClick(character === "." ? Qt.Key_Period : Qt.Key_0 + Number(character), Qt.NoModifier, 0);
    }

    function verifySelected(input, token) {
        verify(input.editor.activeFocus, "The opened value editor already owns keyboard focus");
        compare(input.editor.text, token, "The popup offers the complete current edit token");
        compare(input.editor.selectedText, token, "The first click selects every digit of the current value");
    }

    function dismiss(input) {
        keyClick(Qt.Key_Escape, Qt.NoModifier, 0);
        tryCompare(input.popup, "visible", false, 2000, "Escape closes this popup");
    }

    function test_replaces_or_cancels_the_selected_value(data) {
        const control = findControl(data);
        const item = control.item;
        edits.target = Session.project;
        values.target = item;
        edits.clear();
        values.clear();
        verify(!Session.project.canUndo, "The independently opened project starts without an Undo entry");

        verify(waitForPolish(appWindow), "The selected value's viewport settles before real hover");
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "The selected control reaches a rendered frame before hover");
        verify(TooltipClock.movePointer(appWindow.contentItem, 10, appWindow.height / 2), "Hover begins away from the target value");
        tryVerify(() => {
            if (!control.hovered) {
                const target = Ui.clickPoint(control);
                if (target !== null)
                    TooltipClock.movePointer(control, target.x, target.y);
            }
            return ownedVisibleTooltips(control).some(tip => tip.opened && tip.text !== "");
        }, 3000, "Before clicking, real hover opens a tooltip owned by the original value");

        let input = openValue(control, true);
        if (data.waitForAnimation) {
            tryCompare(input.popup, "opened", true, 2000, "The delayed input starts after the popup animation");
            wait(350);
        }
        verifySelected(input, item.fileEditValue);
        typeDigits("1.54822");
        compare(input.editor.text, "1.54822", "Ordinary digits replace the previous value in full");
        tryCompare(input.popup, "opened", true, 2000, "The popup opens fully without disturbing the draft typed during entry");
        verify(!ownedVisibleTooltips(control).some(tip => tip.opened), "Opening the value popup dismisses the original fully open tooltip");
        tryVerify(() => input.popup.opened && ownedVisibleTooltips(control).length === 0, 1500, "The tooltip fades out completely while the value popup stays open");
        compare(input.editor.text, "1.54822", "Finishing the popup animation preserves the first draft");
        compare(item.value, data.original, "Typing a draft does not edit the model before Return");
        compare(edits.count, 0, "The first draft opens no project edit");
        keyClick(Qt.Key_Return, Qt.NoModifier, 0);
        tryCompare(item, "value", 1.54822, 2000, "Return commits only the replacement number");
        if (input.popup.visible)
            dismiss(input);
        compare(values.count, 1, "Return and popup focus loss deliver one value change");
        compare(edits.count, 1, "Return and popup focus loss publish exactly one project edit");

        input = openValue(control, true);
        tryCompare(input.popup, "opened", true, 2000, "The reopened popup settles before a second pointer click");
        verifySelected(input, item.fileEditValue);
        const start = input.editor.positionToRectangle(0);
        mouseClick(input.editor, start.x, start.y + start.height / 2);
        compare(input.editor.selectedText, "", "A click inside the already opened editor clears its opening selection");
        compare(input.editor.cursorPosition, 0, "The second pointer click puts the caret at the chosen character");
        keyClick(Qt.Key_A, Qt.ControlModifier, 0);
        compare(input.editor.selectedText, input.editor.text, "Ctrl+A still selects the whole value after placing the caret");
        typeDigits("1.64822");
        compare(input.editor.text, "1.64822", "The escape witness has a valid replacement draft");
        dismiss(input);
        compare(item.value, 1.54822, "Escape discards the new draft and keeps the previously committed value");
        compare(edits.count, 1, "Escape adds no project edit");

        const previous = control.nextItemInFocusChain(false);
        verify(previous !== null && previous !== control, "The value has a real predecessor in the app's focus chain");
        previous.forceActiveFocus();
        verify(previous.activeFocus, "Tab starts on the preceding control");
        keyClick(Qt.Key_Tab, Qt.NoModifier, 0);
        tryCompare(control, "activeFocus", true, 2000, "Tab reaches the original value without a mouse click");
        if (control.opensPopup === true) {
            compare(control.selectedText, control.text, "Tab to a standalone field selects its whole value");
        } else {
            keyClick(Qt.Key_Return, Qt.NoModifier, 0);
            input = openValue(control, false);
            verifySelected(input, item.fileEditValue);
            tryCompare(input.popup, "opened", true, 2000, "The keyboard-opened popup settles before Escape");
            dismiss(input);
        }
        compare(values.count, 1, "Caret movement, Tab and cancelled edits leave the first value change alone");
        compare(edits.count, 1, "Keyboard inspection adds no duplicate edit");
        Ui.click(test, Probe, appWindow, "appBar.button.undo");
        tryCompare(item, "value", data.original, 2000, "One ordinary Undo restores the independent original value");
        compare(Session.project.canUndo, false, "Exactly one Undo entry was recorded for Return");
    }
}
