// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import EasyApplication.Gui.Components as EaComponents
import EasyApplication.Gui.Elements as EaElements
import EasyApplication.Gui.Style as EaStyle
import edi.app
import TableIdTests 1.0
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
        EaComponents.TableViewParameter {
            width: 240
            height: 48
        }
    }
    Component {
        id: fieldComponent
        EaElements.ParamTextField {
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
        property string savedRecentPaths
        function init() {
            failOnWarning(/.*/);
            savedRecentPaths = RecentProjects.settings.paths;
            Session.closeProject();
            RecentProjects.settings.paths = "[]";
        }
        function cleanup() {
            Session.closeProject();
            RecentProjects.settings.paths = savedRecentPaths;
            RecentProjects.refresh();
        }
        function click(control, button) {
            verify(control !== null && Ui.exposed(control));
            const point = Ui.clickPoint(control);
            let delay = 0;
            for (let item = control.parent; item; item = item.parent) {
                if (typeof item.pressDelay === "number")
                    delay = Math.max(delay, item.pressDelay + 1);
            }
            mouseClick(control, point.x, point.y, button ?? Qt.LeftButton, Qt.NoModifier, delay);
        }
        function expanded(group) {
            verify(waitForPolish(group));
            tryVerify(() => Math.abs(group.height - (group.titleArea.height + group.spacing + group.contentHeight + group.bottomPadding)) < 0.01);
        }
        function test_recent_open_missing_and_remove_use_real_input() {
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), Session.lastError);
            verify(Session.saveAs(files.directory()), Session.lastError);
            const found = Session.projectLocation;
            const missing = found + "/missing-project";
            Session.closeProject();
            RecentProjects.settings.paths = JSON.stringify([missing, found]);
            RecentProjects.refresh();
            const group = createTemporaryObject(recentComponent, surface);
            verify(group !== null);
            expanded(group);
            const table = Ui.find(group, "recentProjects.list");
            tryCompare(table, "count", 2);
            compare(Ui.find(group, "recentProjects.status.0").text, "Missing");
            compare(Ui.find(group, "recentProjects.status.1").text, "Found");
            click(Ui.find(group, "recentProjects.path.0"));
            compare(Session.hasProject, false, "A missing row cannot open a project");
            compare(RecentProjects.rows.count, 2);
            click(Ui.find(group, "recentProjects.path.1"));
            tryCompare(Session, "hasProject", true);
            compare(Session.projectLocation, found, "Opening the second row uses its directory");
            Session.closeProject();
            RecentProjects.settings.paths = JSON.stringify([missing, found]);
            RecentProjects.refresh();
            tryCompare(table, "count", 2);
            click(Ui.find(group, "recentProjects.remove.1"));
            tryCompare(table, "count", 1);
            compare(Session.hasProject, false, "The delete cell must not trigger the row's open action");
            compare(RecentProjects.rows.get(0).path, missing);
            verify(Session.projectDirectoryExists(found), "Removing history does not delete the saved project");
            click(Ui.find(group, "recentProjects.remove.0"));
            tryCompare(table, "count", 0);
        }
        function test_measured_table_hide_detach_and_reattach() {
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), Session.lastError);
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
                tryVerify(() => Math.abs(popup.height - expected) < 0.1, "The first opening must not retain a larger default height");
                verify(popup.width >= picker.width && popup.width <= surface.width);
                tryVerify(() => Math.abs(list.contentY - list.originY) < 0.1, "All categories remains visible even with a later current selection");
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
            const parameter = {
                value: 3.9,
                error: 0.02,
                enabled: true,
                fittable: true,
                fit: true,
                category: "cell",
                name: "length_a",
                units: "Å"
            };
            const control = createTemporaryObject(data.component, surface, {
                x: 100,
                y: 100,
                parameter: parameter
            });
            verify(control !== null);
            verify(waitForPolish(control));
            click(control, Qt.RightButton);
            const overlay = control.Overlay.overlay;
            verify(overlay !== null);
            tryVerify(() => Ui.text(overlay).includes("cell.length_a"));
            const words = Ui.text(overlay).split(/\s+/).filter(word => word.length > 0);
            verify(words.includes("s.u."), "The uncertainty heading uses s.u.");
            verify(words.includes("free"), "The fit toggle heading uses free");
            verify(words.includes("units") && words.includes("Å"), "The popup displays the parameter units");
            verify(!words.includes("error") && !words.includes("vary"));
            verify(Ui.exposed(control.fitCheckBox));
            compare(control.fitCheckBox.checked, true);
            click(control.fitCheckBox);
            compare(control.fitCheckBox.checked, false);
            mouseClick(surface, surface.width - 10, surface.height - 10);
            tryVerify(() => !Ui.text(overlay).includes("cell.length_a"));
        }
    }
}
