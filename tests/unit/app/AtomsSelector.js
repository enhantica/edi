.pragma library
.import "UiInteraction.js" as Ui

function checkEntries(test, combo, expected) {
    test.verify(combo !== null && typeof combo.textAt === "function",
                "The Structure toolbar exposes an Atoms selector");
    test.compare(Array.from({length: combo.count}, (_, row) => combo.textAt(row)), expected,
                 "The Atoms selector offers exactly the views for this structure");
}

function checkSelected(test, combo, label) {
    const shortLabels = {
        "Asymmetric unit (crystal)": "Crystal AU",
        "Asymmetric unit (magnetic)": "Magnetic AU",
        "Magnetic atoms": "Magnetic"
    };
    test.compare(combo.currentText, label, "The selected Atoms option retains its full name");
    test.compare(combo.displayText, shortLabels[label] || label,
                 "The closed Atoms selector displays its short name");
}

function select(test, probe, window, combo, label) {
    if (combo.currentText === label) {
        checkSelected(test, combo, label);
        return;
    }
    const index = Array.from({length: combo.count}, (_, row) => combo.textAt(row)).indexOf(label);
    test.verify(index >= 0, "The requested Atoms view is offered: " + label);
    Ui.click(test, probe, window, "structure.toolbar.atoms", true);
    test.tryCompare(combo.popup, "opened", true, 2000, "Pointer input opens the Atoms selector for " + label);
    const list = combo.popup.contentItem;
    test.tryVerify(() => list.itemAtIndex(index) && Ui.exposed(list.itemAtIndex(index)), 2000,
                   "The requested Atoms view is visible in the popup");
    const entry = list.itemAtIndex(index);
    test.compare(entry.text, label, "The visible Atoms choice carries the requested caption");
    test.mouseClick(entry, entry.width / 2, entry.height / 2);
    test.tryCompare(combo, "currentText", label, 2000, "Pointer input selects the requested Atoms view");
    test.tryCompare(combo.popup, "visible", false, 2000, "The Atoms popup leaves the input overlay after selection");
    checkSelected(test, combo, label);
}
