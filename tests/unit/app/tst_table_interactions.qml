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
            const directory = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/table_display"));
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
            const overlay = control.Overlay.overlay;
            verify(overlay !== null, "The supported parameter menu has its real window overlay");
            control.readOnly = true;
            click(control, Qt.RightButton);
            tryVerify(() => Ui.text(overlay).includes("cell.length_a"), 2000, "Read-only inspection retains the supported parameter menu");
            const readOnlyWords = Ui.text(overlay).split(/\s+/).filter(word => word.length > 0);
            verify(readOnlyWords.includes("s.u.") && readOnlyWords.includes("units") && readOnlyWords.includes("Å"), "Read-only inspection retains uncertainty and units");
            verify(!Ui.exposed(control.fitCheckBox), "Read-only inspection cannot expose an editable free toggle");
            compare(parameter.free, true, "Read-only inspection cannot change the parameter's free flag");
            mouseClick(surface, surface.width - 10, surface.height - 10);
            tryVerify(() => !Ui.text(overlay).includes("cell.length_a"), 2000, "The read-only parameter menu closes through ordinary input");
            control.readOnly = false;
            click(control, Qt.RightButton);
            tryVerify(() => Ui.text(overlay).includes("cell.length_a"), 2000, "A real right click opens the parameter's own menu");
            const words = Ui.text(overlay).split(/\s+/).filter(word => word.length > 0);
            verify(words.includes("s.u."), "The uncertainty heading uses s.u.");
            verify(words.includes("free"), "The fit toggle heading uses free");
            verify(words.includes("units") && words.includes("Å"), "The popup displays the parameter units");
            verify(!words.includes("error") && !words.includes("vary"), "The supported menu retains the app's scientific headings");
            verify(Ui.exposed(control.fitCheckBox), "An applicable free parameter exposes its real menu toggle");
            compare(control.fitCheckBox.checked, true, "The real free flag is initially checked");
            click(control.fitCheckBox);
            compare(control.fitCheckBox.checked, false, "A real menu click clears the toggle");
            compare(parameter.free, false, "The actual supported menu commits to the original typed parameter");
            mouseClick(surface, surface.width - 10, surface.height - 10);
            tryVerify(() => !Ui.text(overlay).includes("cell.length_a"), 2000, "Clicking outside closes the original parameter menu");

        }
    }
}
