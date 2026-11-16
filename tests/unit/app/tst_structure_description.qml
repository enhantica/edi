import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

Item {
    id: surface
    width: 1200
    height: 900
    readonly property url fullReference: Qt.resolvedUrl("../../fixtures/legacy_structure_project/project")
    readonly property url uiReference: Qt.resolvedUrl("../../fixtures/legacy_structure_project/compact-project")
    function projectChanges(reference, output) {
        const before = SettingsProof.projectBytes(reference), after = SettingsProof.projectBytes(output);
        if (before.error || after.error || Object.keys(before).length === 0)
            return ["unreadable project"];
        const expected = Object.keys(before), actual = Object.keys(after);
        return actual.filter(name => !expected.includes(name)).map(name => "added " + name).concat(expected.filter(name => !actual.includes(name)).map(name => "removed " + name)).concat(expected.filter(name => actual.includes(name) && before[name] !== after[name]).map(name => "changed " + name));
    }
    TestCase {
        id: test
        name: "StructureDescription"
        when: windowShown
        visible: true
        width: 1200
        height: 900
        property var page
        property url scratch
        Component {
            id: pageFactory
            StructurePage {
                current: true
                visible: true
            }
        }
        TextMetrics {
            id: nameInk
        }

        function init() {
            scratch = SettingsProof.copyProject(surface.uiReference);
            verify(Session.openProject(scratch), "Structure description opens the pre-feature saved nonmagnetic cobalt project");
            tryCompare(Session.project, "calculating", false, 15000, "The nonmagnetic input finishes calculating before UI input");
            page = pageFactory.createObject(test, {
                width: test.width,
                height: test.height
            });
            verify(page !== null, "Structure description uses the production Structure page");
            tryVerify(() => page.structure !== null && findChild(page, "structures.list") !== null, 1000, "The production Structure page binds the actual saved project");
            click("sideBar.tab.basic");
        }
        function cleanup() {
            Session.closeProject();
            if (page)
                page.destroy();
            page = null;
        }
        function click(name) {
            const item = typeof name === "string" ? findChild(page, name) : name;
            verify(item !== null, "The production Structure page exposes the requested real control");
            const target = Ui.target(item);
            Ui.scrollIntoView(target);
            tryVerify(() => item.enabled && Ui.clickPoint(target) !== null, 1000, "The production Structure control is enabled and exposed before real input");
            verify(waitForPolish(page), "The actual Structure page finishes layout before input");
            const point = Ui.clickPoint(target);
            mouseClick(target, point.x, point.y);
            verify(waitForRendering(page), "The production Structure page renders the real input");
        }
        function expand(name) {
            const group = findChild(page, name);
            verify(group !== null, "The production Structure page exposes the requested group");
            if (group.collapsed)
                click(group);
            else
                Ui.scrollIntoView(Ui.target(group));
            tryCompare(group, "collapsed", false, 1000, "The actual Structure group opens through its real header");
            tryVerify(() => Math.abs(group.height - group.implicitHeight) < 1, 2000, "The real Structure group reaches its expanded geometry before input");
            verify(waitForPolish(group), "The actual Structure group's layout finishes before observation");
            return group;
        }
        function groups() {
            return Render.descendants(page).filter(item => item.visible && typeof item.categoryId === "string" && typeof item.collapsed === "boolean");
        }
        function moments() {
            const found = groups().filter(item => item.categoryId === "atom_site_moment");
            compare(found.length, 1, "Moments remains present for a structure without magnetic sites");
            expand("group.atom_site_moment");
            Ui.scrollIntoView(found[0]);
            verify(waitForPolish(found[0]), "The real moments group completes layout");
            return found[0];
        }
        function magneticGroups() {
            return groups().filter(item => ["space_group_magn", "parent_propagation_vector", "magnetic_form_factor"].includes(item.categoryId));
        }
        function choose(combo, label) {
            verify(combo !== null && combo.enabled, "The magnetic choice is reachable through its real control");
            const index = Array.from({
                length: combo.count
            }, (_, i) => combo.textAt(i)).indexOf(label);
            verify(index >= 0, "The magnetic control offers the independently specified ion or none");
            Ui.scrollIntoView(combo);
            tryVerify(() => combo.enabled && Ui.clickPoint(combo) !== null, 1000, "The magnetic control has an exposed pointer target after its group opens");
            const point = Ui.clickPoint(combo);
            mouseClick(combo, point.x, point.y);
            tryCompare(combo.popup, "opened", true, 1000, "Pointer input opens the actual magnetic selector");
            const list = combo.popup.contentItem;
            list.positionViewAtIndex(index, ListView.Contain);
            tryVerify(() => list.itemAtIndex(index) && Ui.exposed(list.itemAtIndex(index)), 1000, "The requested magnetic choice is visible in the real popup");
            const entry = list.itemAtIndex(index);
            mouseClick(entry, entry.width / 2, entry.height / 2);
            tryCompare(combo.popup, "visible", false, 1000, "Selecting an ion dismisses the real popup");
        }
        function checkTypeColumn(interact = false) {
            expand("group.structures");
            const table = findChild(page, "structures.list");
            verify(table !== null && table.count > 0, "The actual Structures table has model rows to inspect");
            const headers = Render.cells(table.headerItem).filter(item => item.visible && item.width > 0);
            const name = headers.findIndex(item => item.text === "Name");
            const type = headers.findIndex(item => item.text === "Type");
            verify(name >= 0 && type === name + 1, "The read-only Type column immediately follows Name");
            for (let row = 0; row < table.count; ++row) {
                table.positionViewAtIndex(row, ListView.Contain);
                table.forceLayout();
                tryVerify(() => table.itemAtIndex(row) !== null, 1000, "Each actual Structures row is materialized");
                const cell = Render.cells(table.itemAtIndex(row))[type];
                verify(cell !== undefined && cell.visible, "Each structure has a visible Type cell");
                compare(cell.text, "Atom-based", "Every current structure is described as Atom-based");
                verify(!cell.enabled, "A structure's Type is shown disabled because it cannot be edited");
                const nameCell = findChild(table.itemAtIndex(row), "structures.name." + row);
                verify(nameCell !== null, "Each Type follows its actual structure-name cell");
                tryVerify(() => {
                    nameInk.font = headers[name].font;
                    nameInk.text = headers[name].text;
                    let widestEnd = headers[name].mapToItem(table, headers[name].leftPadding + nameInk.advanceWidth, 0).x;
                    for (let other = 0; other < table.count; ++other) {
                        const otherRow = table.itemAtIndex(other);
                        const otherName = otherRow ? findChild(otherRow, "structures.name." + other) : null;
                        if (!otherName)
                            return false;
                        nameInk.font = otherName.font;
                        nameInk.text = String(otherName.value);
                        widestEnd = Math.max(widestEnd, otherName.mapToItem(table, otherName.leftPadding + nameInk.advanceWidth, 0).x);
                    }
                    const typeStart = cell.mapToItem(table, cell.leftPadding, 0).x;
                    return typeStart >= widestEnd && typeStart - widestEnd <= 2 * nameCell.font.pixelSize;
                }, 2000, "Type follows the widest Name entry and leaves spare width after Type");
                verify(Render.descendants(cell).every(item => typeof item.currentIndex !== "number" && (typeof item.selectAll !== "function" || item.readOnly === true)), "The Type cell has no editable field or description selector");
                if (interact) {
                    Ui.scrollIntoView(cell);
                    const point = Ui.clickPoint(cell);
                    verify(point !== null, "The actual Type cell has a visible pointer target");
                    const priorName = String(nameCell.value);
                    mouseDoubleClickSequence(cell, point.x, point.y);
                    verify(SettingsProof.key(cell, Qt.Key_M), "The Type cell's actual window receives an edit key");
                    verify(SettingsProof.key(cell, Qt.Key_Return), "The Type cell's actual window receives Return");
                    compare(cell.text, "Atom-based", "Pointer and keyboard input cannot edit a structure's Type");
                    compare(String(nameCell.value), priorName, "Input over the disabled Type cell also preserves the structure name");
                    compare(Probe.visiblePopups(page).length, 0, "Interacting with the disabled Type cell opens no model-choice popup");
                }
            }
            const selectors = Render.descendants(page).filter(item => item.visible && typeof item.textAt === "function" && Array.from({
                    length: item.count
                }, (_, i) => item.textAt(i)).some(text => ["Atom sites", "Symmetry modes", "Atom-based", "Mode-based"].includes(text)));
            compare(selectors.length, 0, "Structure description is shown only in the read-only column");
            return table;
        }
        function test_type_column_is_disabled_after_name() {
            checkTypeColumn(true);
            verify(Session.save(), "The project read by the new Type and moments controls saves through the public operation");
            tryCompare(Session.project, "saving", false, 10000, "The unchanged UI project save finishes before byte comparison");
            const changes = surface.projectChanges(surface.uiReference, scratch);
            verify(changes.length === 0, "Reading the new controls preserves the old saved project outside its two clock fields: " + changes.join(", "));
        }
        function test_create_structure_is_atom_based() {
            expand("group.structures");
            const table = findChild(page, "structures.list"), count = table.count;
            verify(count > 0, "The real Create action starts from the existing saved structure");
            click("structures.create");
            tryCompare(table, "count", count + 1, 3000, "Create structure adds one structure through its real button");
            checkTypeColumn();
            moments();
        }
        function test_moments_appear_and_disappear_via_atom_site_input() {
            compare(magneticGroups().length, 0, "A structure without moments hides the magnetic groups");
            let group = moments();
            let table = findChild(group, "atomSiteMoments.list");
            verify(table !== null && table.count > 0, "Moments lists the actual nonmagnetic atom sites");
            for (let row = 0; row < table.count; ++row) {
                const ion = findChild(table.itemAtIndex(row), "atomSiteMoment.ion." + row);
                verify(ion !== null, "Every nonmagnetic site retains its magnetic choice");
                compare(ion.currentText, "none", "Every site starts explicitly at none");
                const component = findChild(table.itemAtIndex(row), "atomSiteMoment.mx." + row);
                verify(component !== null && !component.enabled, "A site without a moment has a greyed moment component");
            }
            choose(findChild(table.itemAtIndex(0), "atomSiteMoment.ion.0"), "Co2+");
            tryVerify(() => magneticGroups().length > 0, 3000, "An atom-site magnetic choice reveals the magnetic groups");
            table = findChild(moments(), "atomSiteMoments.list");
            const siteCount = table.count;
            for (let row = 0; row < siteCount; ++row) {
                group = moments();
                table = findChild(group, "atomSiteMoments.list");
                const choice = findChild(table.itemAtIndex(row), "atomSiteMoment.ion." + row);
                verify(choice !== null, "Every site remains reachable while removing its moment");
                if (choice.currentText !== "none") {
                    choose(choice, "none");
                    tryVerify(() => {
                        const currentTable = findChild(page, "atomSiteMoments.list");
                        const fresh = currentTable && findChild(currentTable.itemAtIndex(row), "atomSiteMoment.ion." + row);
                        return fresh && fresh.currentText === "none";
                    }, 3000, "Removing a site's moment is reflected in its real selector");
                }
            }
            tryCompare(Session.project, "calculating", false, 15000, "Removing the last moment finishes its calculation");
            tryVerify(() => magneticGroups().length === 0, 3000, "Removing every moment hides the magnetic groups again");
            moments();
        }
        function test_magnetic_structure_bytes_survive_save_and_reload() {
            const table = findChild(moments(), "atomSiteMoments.list");
            verify(table !== null && table.count > 0, "Magnetic persistence starts from an actual atom site");
            choose(findChild(table.itemAtIndex(0), "atomSiteMoment.ion.0"), "Co2+");
            tryVerify(() => magneticGroups().length > 0, 3000, "The magnetic persistence witness has a moment created by real input");
            checkTypeColumn();
            tryCompare(Session.project, "calculating", false, 15000, "The new moment finishes calculating before saving");
            verify(Session.save(), "The public Save operation writes the magnetic structure created by real input");
            tryCompare(Session.project, "modified", false, 10000, "The magnetic save finishes before observing the saved bytes");
            const before = SettingsProof.fileObservation(scratch, "structures/cosio.edi");
            verify(before.exists && !before.error && /_atom_site_moment\./.test(before.text), "The saved structure actually contains its atom-site moment records");
            page.destroy();
            page = null;
            verify(waitForRendering(test), "The Structure page finishes teardown before the persistence round trip");
            Session.closeProject();
            verify(Session.openProject(scratch), "The saved magnetic structure reopens through the real loader");
            tryCompare(Session.project, "calculating", false, 15000, "The reopened magnetic structure finishes calculating");
            verify(Session.save(), "The reopened magnetic structure saves through the real session");
            verify(SettingsProof.fileObservation(scratch, "structures/cosio.edi").base64 === before.base64, "The complete saved magnetic structure is byte-identical after reload and save");
        }
    }
    TestCase {
        id: legacy
        name: "LegacyStructurePersistence"
        when: windowShown
        property url scratch
        function init() {
            scratch = SettingsProof.copyProject(surface.fullReference);
            verify(Session.openProject(scratch), "The legacy regression pin opens through the actual project loader");
            tryCompare(Session.project, "calculating", false, 15000, "The legacy saved project's calculation finishes");
        }
        function cleanup() {
            Session.closeProject();
        }
        function test_legacy_saved_project_regression_pin_retains_bytes() {
            const before = SettingsProof.fileObservation(surface.fullReference, "structures/cosio.edi");
            const projectBefore = SettingsProof.projectBytes(surface.fullReference);
            verify(!projectBefore.error, "The legacy-project witness reads every original project member");
            verify(before.exists && !before.error, "The byte-identity witness reads the original committed structure");
            verify(Session.save(), "The unchanged legacy project saves through the actual session");
            verify(SettingsProof.fileObservation(scratch, "structures/cosio.edi").base64 === before.base64, "Opening and saving a legacy structure preserves every byte");
            Session.closeProject();
            verify(Session.openProject(scratch), "The saved legacy project reopens through the actual loader");
            tryCompare(Session.project, "calculating", false, 15000, "The reopened legacy project finishes calculating");
            verify(Session.save(), "The reopened legacy project saves a second time");
            verify(SettingsProof.fileObservation(scratch, "structures/cosio.edi").base64 === before.base64, "Save and reload retain the complete original structure bytes");
            const saved = SettingsProof.projectBytes(scratch);
            verify(!saved.error, "The saved legacy-project witness reads every project member");
            const beforeNames = Object.keys(projectBefore), savedNames = Object.keys(saved);
            const added = savedNames.filter(name => !beforeNames.includes(name));
            const removed = beforeNames.filter(name => !savedNames.includes(name));
            const changed = beforeNames.filter(name => savedNames.includes(name) && saved[name] !== projectBefore[name]);
            verify(added.length === 0 && removed.length === 0 && changed.length === 0, "Legacy save/reload preserves every member byte outside its two clock values; added [" + added.join(", ") + "]; removed [" + removed.join(", ") + "]; changed [" + changed.join(", ") + "]");
        }
    }
}
