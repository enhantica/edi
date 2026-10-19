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
    // Independent rows exercise the first shared native delegate, not a copied handler.
    ListModel {
        id: inputRows557
        ListElement { label: "alpha" }
        ListElement { label: "beta" }
        ListElement { label: "gamma" }
        ListElement { label: "delta" }
        ListElement { label: "epsilon" }
        ListElement { label: "zeta" }
        ListElement { label: "eta" }
        ListElement { label: "theta" }
    }
    Component {
        id: inputTable557
        DataTable {
            width: 700
            maxRowCountShow: 3
            sourceModel: inputRows557
            multiSelection: true
            columnWidths: [220, 120, -1]
            header: EaComponents.ListViewHeader {
                TextCell { value: "Text"; readOnly: true }
                TextCell { value: "Action"; readOnly: true }
                TextCell { value: ""; readOnly: true }
            }
            delegate: EaComponents.ListViewDelegate {
                required property int index
                required property string label
                EaComponents.ListViewTextInput {
                    objectName: "rowInput557.text." + index
                    text: label
                }
                EaComponents.TableViewButton {
                    objectName: "rowInput557.button." + index
                    text: "Action"
                    focusPolicy: Qt.StrongFocus
                }
                TextCell { value: label; readOnly: true }
            }
        }
    }
    TestCase {
        name: "TableInteractions"
        when: windowShown
        property var savedRecentPaths
        property string savedRecentLast
        SignalSpy { id: pressed557; signalName: "pressed" }
        SignalSpy { id: released557; signalName: "released" }
        SignalSpy { id: clicked557; signalName: "clicked" }
        SignalSpy { id: edited557; signalName: "textEdited" }
        function init() {
            failOnWarning(/.*/);
            savedRecentPaths = Array.from(RecentProjects.settings.recent);
            savedRecentLast = RecentProjects.settings.last;
            Session.closeProject();
            RecentProjects.settings.recent = [];
            RecentProjects.settings.last = "";
        }
        function cleanup() {
            Session.closeProject();
            RecentProjects.settings.recent = savedRecentPaths;
            RecentProjects.settings.last = savedRecentLast;
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
        function test_shared_row_preserves_native_children_and_background_input() {
            const table = createTemporaryObject(inputTable557, surface);
            verify(table !== null && waitForPolish(table), "ROW557: the actual shared row table completes layout");
            table.forceLayout();
            tryVerify(() => table.itemAtIndex(2) !== null, 2000, "ROW557: three original visible rows are instantiated");
            const row0 = table.itemAtIndex(0), row1 = table.itemAtIndex(1), row2 = table.itemAtIndex(2);
            // Only this fixture's live column gap is a row-background receiver.
            function backgroundPoint559(row) {
                const text = Ui.find(row, "rowInput557.text." + row.index);
                const button = Ui.find(row, "rowInput557.button." + row.index);
                verify(text !== null && button !== null && Ui.exposed(text) && Ui.exposed(button),
                    "ROW559: original children surrounding the background gap are exposed");
                const left = text.mapToItem(row, text.width, 0).x;
                const right = button.mapToItem(row, 0, 0).x;
                verify(right > left, "ROW559: live interactive cell bounds leave a genuine gap");
                const point = {x:(left + right) / 2, y:row.height / 2};
                const at = row.mapToItem(table, point.x, point.y);
                verify(at.x > 0 && at.x < table.width && at.y > 0 && at.y < table.height,
                    "ROW559: background point lies inside the original table viewport");
                for (let item = row; item; item = item.parent) {
                    if (!item.clip) continue;
                    const local = item.mapFromItem(row, point.x, point.y);
                    verify(local.x > 0 && local.x < item.width && local.y > 0 && local.y < item.height,
                        "ROW559: every live ancestor clip exposes the chosen original background point");
                }
                const bar = table.ScrollBar.vertical, header = table.headerItem;
                verify(bar !== null && bar.visible && bar.enabled && bar.interactive && header !== null,
                    "ROW559: original interactive scrollbar and header remain present and unchanged");
                for (const item of [text, button, bar, header]) {
                    const local = item.mapFromItem(row, point.x, point.y);
                    verify(local.x < 0 || local.x >= item.width || local.y < 0 || local.y >= item.height,
                        "ROW559: original gap excludes each cell, full scrollbar and header regardless of faded ink");
                }
                const frames = table.children.filter(item => item.visible && item.border !== undefined
                    && item.width === table.width && item.height === table.height);
                compare(frames.length, 1, "ROW559: the actual original table frame is uniquely observed");
                const frame = frames[0], inside = frame.mapFromItem(row, point.x, point.y), width = frame.border.width;
                verify(inside.x > width && inside.y > width && inside.x < frame.width - width && inside.y < frame.height - width,
                    "ROW559: background point excludes the actual native frame pen");
                return point;
            }
            const action = Ui.find(row0, "rowInput557.button.0");
            const editor = Ui.find(row0, "rowInput557.text.0");
            verify(action !== null && editor !== null && Ui.exposed(action) && Ui.exposed(editor),
                "ROW557: original nested button and text receiver are both exposed");
            const p0 = backgroundPoint559(row0);
            mouseClick(row0, p0.x, p0.y, Qt.LeftButton, Qt.NoModifier, table.pressDelay + 1);
            verify(table.isSelected(0) && !table.isSelected(1) && !table.isSelected(2),
                "ROW557: actual row background selects exactly its own row");
            try {
                pressed557.target = action; released557.target = action; clicked557.target = action; edited557.target = editor;
                pressed557.clear(); released557.clear(); clicked557.clear(); edited557.clear();
                verify(pressed557.valid && released557.valid && clicked557.valid && edited557.valid,
                    "ROW557: passive spies bind the four original native signals");
                click(action);
                compare(pressed557.count, 1, "ROW557: original nested button receives one native press");
                compare(released557.count, 1, "ROW557: original nested button receives one native release");
                compare(clicked557.count, 1, "ROW557: original nested button receives one native click");
                verify(action.activeFocus, "ROW557: row background does not steal the button's declared click focus");
                click(editor);
                verify(editor.activeFocus && row0.editing, "ROW557: native text click retains its original keyboard owner");
                const original = editor.text;
                keyClick("Z");
                compare(edited557.count, 1, "ROW557: one real key reaches the original text receiver once");
                compare(editor.text.split("Z").join(""), original, "ROW557: typed text preserves every original character");
                compare(editor.text.length, original.length + 1, "ROW557: exactly one independent character is inserted");
                const p1 = backgroundPoint559(row1);
                mouseClick(row1, p1.x, p1.y, Qt.LeftButton, Qt.NoModifier, table.pressDelay + 1);
                verify(!editor.activeFocus && !row0.editing && table.isSelected(1)
                    && !table.isSelected(0) && !table.isSelected(2),
                    "ROW557: genuine other-row background ends editing and replaces selection");
                const controlPoint = backgroundPoint559(row0);
                mouseClick(row0, controlPoint.x, controlPoint.y, Qt.LeftButton, Qt.ControlModifier, table.pressDelay + 1);
                verify(table.isSelected(0) && table.isSelected(1) && !table.isSelected(2),
                    "ROW557: genuine Control background input adds the independently chosen row");
                const shiftPoint = backgroundPoint559(row2);
                mouseClick(row2, shiftPoint.x, shiftPoint.y, Qt.LeftButton, Qt.ShiftModifier, table.pressDelay + 1);
                verify(table.isSelected(0) && table.isSelected(1) && table.isSelected(2),
                    "ROW557: genuine Shift background input retains the exact contiguous range");
                compare(clicked557.count, 1, "ROW557: row background and modifiers never replay the child action");
                const before = table.contentY;
                const wheelGap = backgroundPoint559(row1);
                const wheelPoint = row1.mapToItem(table, wheelGap.x, wheelGap.y);
                mouseWheel(table, wheelPoint.x, wheelPoint.y, 0, -120);
                tryVerify(() => table.contentY > before, 2000, "ROW557: original native wheel still scrolls the shared row table");
                verify(table.isSelected(0) && table.isSelected(1) && table.isSelected(2),
                    "ROW557: native scrolling preserves the selected model rows after delegate recycling");
            } finally {
                pressed557.target = null; released557.target = null; clicked557.target = null; edited557.target = null;
            }
        }
        function test_recent_open_missing_and_remove_use_real_input() {
            verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), Session.lastError);
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
