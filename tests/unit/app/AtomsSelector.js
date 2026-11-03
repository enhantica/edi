.pragma library
.import "UiInteraction.js" as Ui

function checkEntries(test, combo, expected) {
    test.verify(combo !== null && typeof combo.textAt === "function",
                "The Structure toolbar exposes an Atoms selector");
    test.compare(Array.from({length: combo.count}, (_, row) => combo.textAt(row)), expected,
                 "The Atoms selector offers exactly the views for this structure");
}

function select(test, window, combo, label) {
    if (combo.currentText === label)
        return;
    const index = Array.from({length: combo.count}, (_, row) => combo.textAt(row)).indexOf(label);
    test.verify(index >= 0, "The requested Atoms view is offered: " + label);
    test.tryVerify(() => Ui.exposed(combo) && !Ui.moving(window.contentItem), 2000,
                   "The Atoms selector is reachable after the toolbar settles");
    test.mouseClick(combo, combo.width / 2, combo.height / 2);
    test.tryCompare(combo.popup, "opened", true, 2000, "Pointer input opens the Atoms selector");
    const list = combo.popup.contentItem;
    test.tryVerify(() => list.itemAtIndex(index) && Ui.exposed(list.itemAtIndex(index)), 2000,
                   "The requested Atoms view is visible in the popup");
    const entry = list.itemAtIndex(index);
    test.compare(entry.text, label, "The visible Atoms choice carries the requested caption");
    test.mouseClick(entry, entry.width / 2, entry.height / 2);
    test.tryCompare(combo, "currentText", label, 2000, "Pointer input selects the requested Atoms view");
    test.tryCompare(combo.popup, "opened", false, 2000, "The Atoms selector closes after selection");
}
