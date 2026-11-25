// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import "ExampleProjects.js" as Examples
import EasyApplication.Gui.Components as EaComponents
import EasyApplication.Gui.Style as EaStyle
import edi.app
import TableIdTests 1.0
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui

Item {
    id: surface
    width: 1000
    height: 900
    TableIdFiles {
        id: files
    }
    Component {
        id: recentComponent
        RecentProjectsGroup {
            width: 900
            collapsed: false
        }
    }
    Component {
        id: rangeComponent
        MeasuredRangeGroup {
            width: 900
        }
    }
    Component {
        id: cellComponent
        ParameterCell {
            width: 240
            height: 48
        }
    }
    Component {
        id: fieldComponent
        ParameterField {
            label: ""
            width: 240
            height: 48
        }
    }
    Component {
        id: pickerComponent
        SearchableComboBox {
            x: 100
            y: 100
            width: 160
            inTable: true
        }
    }
    Component { id: parametersGroup; ParametersGroup { tableViewportHeight: 160 } }
    Component { id: atomSitesGroup; AtomSitesGroup {} }
    Component { id: adpGroup; AtomSiteAdpGroup {} }
    TestCase {
        name: "TableInteractions"
        when: windowShown
        property var savedRecentPaths
        function init() {
            failOnWarning(/.*/);
            savedRecentPaths = RecentProjects.settings.recent.slice();
            Session.closeProject();
            RecentProjects.settings.recent = [];
        }
        function cleanup() {
            Session.closeProject();
            RecentProjects.settings.recent = savedRecentPaths;
            RecentProjects.refresh();
        }
        function click(control, button) {
            verify(control !== null && Ui.exposed(control), "The supplied input target is exposed: " + (control ? control.objectName : "null"));
            const point = Ui.clickPoint(control);
            let delay = 0;
            for (let item = control.parent; item; item = item.parent) {
                if (typeof item.pressDelay === "number")
                    delay = Math.max(delay, item.pressDelay + 1);
            }
            mouseClick(control, point.x, point.y, button ?? Qt.LeftButton, Qt.NoModifier, delay);
        }
        function clickNamed(root, name) {
            let control = null;
            tryVerify(() => {
                control = Ui.find(root, name);
                return control !== null && Ui.exposed(control);
            }, 2000, "The rebuilt recent-row input is exposed: " + name);
            click(control);
        }
        function expanded(group) {
            verify(waitForPolish(group));
            tryVerify(() => Math.abs(group.height - (group.titleArea.height + group.spacing + group.contentHeight + group.bottomPadding)) < 0.01);
        }
        function test_recent_open_missing_and_remove_use_real_input() {
            verify(Examples.bundled(this, Session, "pd-neut-cwl_cosio-d20"), Session.lastError);
            verify(Session.saveAs(files.directory()), Session.lastError);
            const found = Session.projectLocation;
            const missing = found + "/missing-project";
            Session.closeProject();
            RecentProjects.settings.recent = [missing, found];
            RecentProjects.refresh();
            const group = createTemporaryObject(recentComponent, surface);
            verify(group !== null);
            expanded(group);
            const table = Ui.find(group, "recentProjects.list");
            tryCompare(table, "count", 2);
            const missingCell = Ui.find(group, "recentProjects.status.0");
            const foundCell = Ui.find(group, "recentProjects.status.1");
            compare(foundCell.icon, "check-circle", "Found uses the fit-family check icon");
            compare(foundCell.iconColor, String(EaStyle.Colors.green), "Found is green");
            compare(foundCell.toolTip, "Found", "The availability word is the icon tooltip");
            verify(["exclamation-circle", "exclamation-triangle"].includes(missingCell.icon), "Missing uses a warning icon");
            verify([String(EaStyle.Colors.red), String(EaStyle.Colors.orange)].includes(missingCell.iconColor), "Missing is red or amber");
            compare(missingCell.toolTip, "Missing", "Missing remains named in the icon tooltip");
            verify(!Ui.text(foundCell).includes("Found") && !Ui.text(missingCell).includes("Missing"), "Availability words are tooltips rather than visible column text");
            clickNamed(group, "recentProjects.path.0");
            compare(Session.hasProject, false, "A missing row cannot open a project");
            compare(RecentProjects.rows.count, 2);
            clickNamed(group, "recentProjects.path.1");
            tryCompare(Session, "hasProject", true);
            compare(Session.projectLocation, found, "Opening the second row uses its directory");
            Session.closeProject();
            RecentProjects.settings.recent = [missing, found];
            RecentProjects.refresh();
            tryCompare(table, "count", 2);
            clickNamed(group, "recentProjects.remove.1");
            tryCompare(table, "count", 1);
            compare(Session.hasProject, false, "The delete cell must not trigger the row's open action");
            compare(RecentProjects.rows.get(0).path, missing);
            verify(Session.projectDirectoryExists(found), "Removing history does not delete the saved project");
            clickNamed(group, "recentProjects.remove.0");
            tryCompare(table, "count", 0);
        }
        function test_measured_table_hide_detach_and_reattach() {
            verify(Examples.bundled(this, Session, "pd-neut-cwl_cosio-d20"), Session.lastError);
            const group = createTemporaryObject(rangeComponent, surface, {
                experiment: Session.project.currentExperiment
            });
            verify(group !== null);
            verify(waitForPolish(group));
            const table = Ui.find(group, "data.list");
            verify(table !== null);
            tryVerify(() => table.count > 0);
            group.visible = false;
            tryCompare(table, "model", null);
            tryCompare(table, "count", 0);
            group.visible = true;
            tryVerify(() => table.count > 0);
            group.experiment = null;
            tryCompare(table, "model", null);
            tryCompare(table, "count", 0);
            group.experiment = Session.project.currentExperiment;
            tryVerify(() => table.count > 0);
            Session.closeProject();
            tryCompare(group, "experiment", null);
            tryCompare(table, "count", 0);
        }
        function test_parameter_number_opens_full_popup_data() {
            return [
                {tag: "parameters", group: parametersGroup, table: "parameters.list",
                 prefix: "parameters.value.", value: 4.0267, uid: "cell.length_a", fileName: "structure.cell.length_a"},
                {tag: "atom-sites", group: atomSitesGroup, table: "atomSites.list",
                 prefix: "atomSite.occupancy.", value: 0.987654, fileName: "structure.atom_site.Li1.occupancy"},
                {tag: "atomic-displacement", group: adpGroup, table: "atomSiteAdps.list",
                 prefix: "atomSiteAdp.iso.", value: 1.234567, fileName: "structure.atom_site.Li1.adp_iso"}
            ];
        }
        function test_parameter_number_opens_full_popup(data) {
            const directory = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/table_display"));
            const file = "structures/structure.edi";
            const original = SettingsProof.text(directory, file);
            const token = "Li1 a Li Biso 0 0 0 1 1.2";
            verify(original.includes(token), "The authored popup values address the same independent atom");
            verify(SettingsProof.write(directory, file,
                    original.replace(token, "Li1 a Li Biso 0 0 0 0.987654 1.234567")),
                   "The loader receives nontrivial occupancy and displacement digits");
            verify(Session.openProject(directory), "The actual tables open the authored parameter project");
            const owner = data.tag === "parameters" ? {project: Session.project}
                                                    : {structure: Session.project.currentStructure};
            const width = data.tag === "atom-sites" ? 960 : 640;
            const group = createTemporaryObject(data.group, surface, Object.assign({width}, owner));
            verify(group !== null, "The production table group instantiates for the popup witness");
            verify(waitForPolish(group), "The production group lays out its number columns before input");
            const table = Ui.find(group, data.table, true);
            verify(table !== null && table.count > 0, "The selected production table contains number cells");
            let index = 0;
            if (data.tag === "parameters") {
                table.sourceModel.categoryFilter = "cell";
                index = Probe.rows(table.model).findIndex(row => row.parameter.uid === data.uid);
                verify(index >= 0, "The Analysis table includes the independently named lattice parameter");
            }
            table.positionViewAtIndex(index, ListView.Contain);
            table.forceLayout();
            let cell = null;
            tryVerify(() => {
                const row = table.itemAtIndex(index);
                if (row)
                    cell = findChild(row, data.prefix + index);
                return cell !== null && cell.item;
            }, 2000, "The requested number is a rendered delegate of the actual table and parameter");
            compare(cell.item.value, data.value, "The clicked parameter has the complete independently authored numeric value");
            surface.forceActiveFocus();
            verify(!cell.activeFocus, "The number cell starts without keyboard focus before the click");
            const popup = Ui.parameterPopup(this, cell);
            const mouseFocusedCell = cell.activeFocus || cell.manualEditing;
            const editor = Ui.parameterValue(this, cell, popup);
            const docs = findChild(popup.contentItem, cell.objectName + ".popup.docs");
            verify(docs !== null && docs.enabled && Ui.exposed(docs),
                   "The full parameter popup exposes its enabled documentation link");
            compare(docs.text, data.fileName, "The popup link names the complete independently authored .edi parameter");
            const words = Ui.text(popup.contentItem).split(/\s+/);
            verify(words.includes("Min") && words.includes("Max"), "The popup contains both parameter bounds");
            const free = findChild(popup.contentItem, cell.objectName + ".popup.free");
            verify(free !== null && Ui.exposed(free), "An applicable parameter exposes its actual Free checkbox");
            Ui.focusParameter(this, editor);
            tryCompare(editor, "text", cell.item.fileEditValue, 2000, "The opened editor exposes the complete native value spelling");
            compare(Ui.numericText(editor.text), data.value, "The popup restores every independently supplied value digit");
            verify(editor.contentWidth <= editor.width - editor.leftPadding - editor.rightPadding + 1,
                   "The dedicated Value input visibly fits the complete editable number");
            const valuePreserved = cell.item.value === data.value;
            verify(SettingsProof.key(editor, Qt.Key_Escape), "Escape reaches the actual popup editing window");
            // Let the overlay's ordinary exit transition finish before classifying Escape.
            wait(250);
            const faults = [];
            if (mouseFocusedCell) faults.push("the number cell took in-place focus from the mouse");
            if (popup.opened) {
                faults.push("Escape left the parameter popup open");
                popup.close();
            }
            if (!valuePreserved || cell.item.value !== data.value) faults.push("inspection changed the authored value");
            compare(faults, [], "The pointer route and Escape preserve the full popup contract");
        }

        function test_parameter_menus_data() {
            return [
                {
                    tag: "table-cell",
                    component: cellComponent
                },
                {
                    tag: "parameter-field",
                    component: fieldComponent
                }
            ];
        }
        function test_first_popup_matches_entries_and_exposes_first_option_data() {
            return [
                {
                    tag: "one-entry",
                    names: ["cosio"]
                },
                {
                    tag: "selected-last",
                    names: ["All categories", "Atomic coordinates", "Atomic displacement"]
                }
            ];
        }
        function test_first_popup_matches_entries_and_exposes_first_option(data) {
            const picker = createTemporaryObject(pickerComponent, surface, {
                model: data.names,
                currentIndex: data.names.length - 1
            });
            verify(picker !== null);
            verify(waitForPolish(picker));
            let firstHeight = 0;
            for (let opening = 0; opening < 2; ++opening) {
                click(picker);
                tryCompare(picker.popup, "opened", true);
                const popup = picker.popup;
                const list = popup.contentItem;
                const expected = data.names.length * EaStyle.Sizes.comboBoxHeight + popup.topPadding + popup.bottomPadding;
                tryVerify(() => Math.abs(popup.height - expected) < 0.1, 2000, "The first opening must not retain a larger default height");
                verify(popup.width >= picker.width && popup.width <= surface.width);
                tryVerify(() => Math.abs(list.contentY - list.originY) < 0.1, 2000, "All categories remains visible even with a later current selection");
                verify(Ui.exposed(list.itemAtIndex(0)), "The first option is inside the opened popup");
                if (opening === 0)
                    firstHeight = popup.height;
                else
                    compare(popup.height, firstHeight, "First and second opening have the same content height");
                popup.close();
                tryCompare(popup, "visible", false);
            }
        }
        function test_parameter_menus(data) {
            const directory = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/table_display"));
            const file = "structures/structure.edi";
            const original = SettingsProof.text(directory, file);
            verify(original.includes("_cell.length_a 4.026700"), "The menu input addresses the declared physical lattice parameter");
            verify(SettingsProof.write(directory, file, original.replace("_cell.length_a 4.026700", "_cell.length_a 4.026700(2000)")), "The real loader receives an authored positive uncertainty and free flag");
            verify(Session.openProject(directory), "The supported menu opens a real project: " + Session.lastError);
            const parameter = Probe.rows(Session.project.parameters).map(row => row.parameter).find(item => item.category === "cell" && item.name === "length_a");
            verify(parameter !== undefined && parameter.refinable && parameter.fittable, "The menu input is a genuine applicable typed ParameterItem");
            verify(parameter.hasUncertainty && parameter.uncertainty > 0 && parameter.free, "The actual parameter supplies uncertainty and a free flag");
            compare(parameter.displayUnits, "Å", "The native dictionary supplies lattice units");
            const control = createTemporaryObject(data.component, surface, {
                x: 100,
                y: 100,
                item: parameter
            });
            verify(control !== null && control.item === parameter, "The app-owned cell or field retains the genuine typed item");
            verify(waitForPolish(control), "The supported menu consumer finishes layout before real input");
            compare(control.canFit, parameter.fittable || parameter.free, "The menu follows the native fittability or existing free flag");
            verify(control.Overlay.overlay !== null, "The supported parameter popup has its real window overlay");
            function inspect(popup) {
                const docs = Ui.parameterPopupItem(test, control, popup, "docs");
                verify(docs && docs.enabled && Ui.exposed(docs), "The popup exposes its live documentation link");
                compare(docs.text, "structure.cell.length_a", "The popup names the same saved lattice parameter");
                const editor = Ui.parameterValue(test, control, popup);
                compare(editor.parameter.units, "Å", "The shared Value input retains the actual lattice unit");
                const su = Ui.parameterPopupItem(test, control, popup, "su");
                verify(su && Ui.exposed(su) && !su.enabled, "The popup displays s.u. in its dedicated disabled input");
                compare(su.text, parameter.fileSu, "The s.u. input preserves the independently supplied uncertainty");
                const words = Ui.text(popup.contentItem).split(/\s+/);
                verify(words.includes("Å"), "The lattice unit is visibly rendered inside its Value field");
                for (const title of ["Value", "s.u.", "Min", "Max"])
                    verify(words.includes(title), "The shared parameter popup exposes its scientific heading " + title);
                verify(!words.includes("units") && !words.includes("error") && !words.includes("vary"),
                       "Value includes its unit and the shared popup uses the declared scientific headings");
                return Ui.parameterPopupItem(test, control, popup, "free");
            }
            control.readOnly = true;
            const inspection = Ui.parameterPopup(this, control);
            const hiddenFree = inspect(inspection);
            verify(hiddenFree && !Ui.exposed(hiddenFree), "Read-only inspection cannot expose an editable Free toggle");
            compare(parameter.free, true, "Read-only inspection cannot change the parameter's Free flag");
            mouseClick(surface, surface.width - 10, surface.height - 10);
            tryCompare(inspection, "opened", false, 2000, "Ordinary outside input closes the read-only popup");

            control.readOnly = false;
            const popup = Ui.parameterPopup(this, control, data.tag === "table-cell" ? Qt.RightButton : Qt.LeftButton);
            const fit = inspect(popup);
            verify(Ui.text(popup.contentItem).split(/\s+/).includes("Free"), "The applicable toggle has its Free heading");
            verify(fit && Ui.exposed(fit) && fit.enabled, "An applicable free parameter exposes its editable popup toggle");
            compare(fit.checked, true, "The real Free flag is initially checked");
            click(fit);
            compare(fit.checked, false, "A real popup click clears the Free toggle");
            compare(parameter.free, false, "The popup commits to the original typed parameter");
            mouseClick(surface, surface.width - 10, surface.height - 10);
            tryCompare(popup, "opened", false, 2000, "Clicking outside closes the original parameter popup");

        }
    }
}
