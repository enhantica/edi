.pragma library
.import "UiInteraction.js" as Ui

function open(test, factory, window, preferences, existing) {
    const dialog = existing || factory.createObject(window.contentItem);
    test.verify(dialog !== null, "ADR-0076: delay edits use the actual Preferences dialog");
    dialog.enter = null;
    dialog.exit = null;
    preferences.dialogTab = "interface";
    preferences.dialogShown = true;
    test.tryCompare(dialog, "opened", true, 2000, "ADR-0076: Preferences is open before the user's delay edit");
    test.verify(test.waitForPolish(dialog.contentItem), "ADR-0076: the selected Preferences editor completes layout before input");
    test.verify(test.waitForRendering(dialog.contentItem), "ADR-0076: the open Preferences editor renders before native input");
    return dialog;
}

function edit(test, dialog, probe, proof, mode, expected) {
    const controls = probe.objectsWithProperty(dialog, "objectName").filter(item => item.objectName === "preferences.toolTipDelay");
    test.compare(controls.length, 1, "ADR-0076: the real Preferences exposes one delay editor");
    const spin = controls[0];
    test.verify(spin.visible && spin.enabled && test.waitForPolish(spin), "ADR-0076: the actual delay input is visible, enabled and laid out");
    test.tryVerify(() => {
        for (let item = spin; item; item = item.parent) {
            if (item.moving === true) return false;
            if (String(item).startsWith("SwipeView") && item.currentItem &&
                Math.abs(item.currentItem.mapToItem(item, 0, 0).x - item.leftPadding) > 1) return false;
        }
        return Ui.clickPoint(spin.contentItem) !== null;
    }, 2000, "ADR-0076: the actual delay editor settles inside its selected Preferences viewport before input");
    if (mode === "plus" || mode === "minus") {
        const target = mode === "plus" ? spin.up.indicator : spin.down.indicator;
        test.verify(target.visible && target.enabled && target.width > 0 && target.height > 0, "ADR-0076: the real delay indicator receives the pointer action");
        test.mouseClick(target, target.width / 2, target.height / 2);
    } else {
        const editor = spin.contentItem;
        const point = Ui.clickPoint(editor);
        test.verify(point !== null, "ADR-0076: the actual delay editor has an exposed pointer target");
        test.mouseClick(editor, point.x, point.y);
        test.tryCompare(editor, "activeFocus", true, 1000, "ADR-0076: real pointer input focuses the delay editor before typing");
        test.verify(proof.type(editor, String(expected)), "ADR-0076: native keyboard input edits the actual delay text field");
        test.keyClick(mode === "typed-enter" ? Qt.Key_Return : Qt.Key_Tab);
    }
    test.compare(spin.value, expected, "ADR-0076: the delay editor displays the actual committed user input");
    return spin;
}
