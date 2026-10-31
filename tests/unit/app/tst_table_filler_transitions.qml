// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import EasyApplication.Gui.Style as EaStyle
import EasyApplication.Gui.Components as EaComponents
import edi.app
import EdiAcceptance 1.0
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui

Item {
    id: surface
    width: 1200
    height: 1100
    ListModel { id: supplied; dynamicRoles: true }
    TextMetrics { id: ink }
    Component {
        id: textTable
        DataTable {
            columns: [numberColumnWidth, -1, -1, AppSizes.iconColumnWidth]
            header: EaComponents.ListViewHeader {
                EaComponents.ListViewLabel { horizontalAlignment: Text.AlignHCenter }
                EaComponents.ListViewLabel { text: "ID" }
                EaComponents.ListViewLabel { text: "Description" }
                EaComponents.ListViewLabel { horizontalAlignment: Text.AlignHCenter }
            }
            delegate: TableRow {
                id: textRow
                required property string label
                required property string note
                EaComponents.ListViewLabel {
                    horizontalAlignment: Text.AlignHCenter
                    text: textRow.index + 1
                }
                EaComponents.ListViewLabel { text: textRow.label }
                EaComponents.ListViewLabel { text: textRow.note }
                IconCell { icon: "check"; horizontalAlignment: Text.AlignHCenter }
            }
        }
    }
    Component { id: numberTable; BackgroundGroup {} }
    Component { id: heldTable; ExperimentsGroup { collapsed: false } }
    SignalSpy { id: leftChanges; signalName: "fillerWidthChanged" }
    SignalSpy { id: rightChanges; signalName: "fillerWidthChanged" }
    TestCase {
        id: test
        name: "TableFillerTransitions"
        when: windowShown
        function init() {
            failOnWarning(/.*/);
            Session.closeProject();
            supplied.clear();
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/table_display")),
                "Filler history uses the genuine independent project and typed ParameterItem");
        }
        function cleanup() {
            leftChanges.target = null;
            rightChanges.target = null;
            Session.closeProject();
        }
        function parameter() {
            const row = Probe.rows(Session.project.parameters).find(item =>
                item.parameter && item.parameter.name === "intensity");
            verify(row !== undefined, "The independent fixture owns a real intensity parameter");
            return row.parameter;
        }
        function make(data, width) {
            const root = createTemporaryObject(data.component, surface, {width});
            verify(root !== null, "The declared actual table component is constructed");
            if (data.tag === "held-text")
                root.project = Session.project;
            else if (data.tag === "number")
                root.experiment = Session.project.currentExperiment;
            const table = data.tag === "text" ? root : Ui.find(root, data.table);
            verify(table !== null, "The actual production DataTable owner is present");
            table.sourceModel = supplied;
            table.maxRowCountShow = 4;
            table.width = width;
            table.forceLayout();
            settle(table);
            compare(table.count, 1, "Both histories consume the same authored real model row");
            return {root, table};
        }
        function settle(table) {
            tryVerify(() => table.columnFitLife !== null && table.columnFitLife.alive
                && !table.columnFitLife.queued && !table.refitting
                && !isPolishScheduled(surface.Window.window), 2000,
                "The original geometry clock admits only the actual settled queued owner");
        }
        function resize(owner, width) {
            owner.root.width = width;
            owner.table.width = width;
            owner.table.forceLayout();
            settle(owner.table);
        }
        function capture(data, owner) {
            const table = owner.table, row = table.itemAtIndex(0);
            verify(row !== null, "The public model has a genuine instantiated delegate");
            const body = Render.cells(row), head = Render.cells(table.headerItem);
            compare(body.length, data.count, "The actual body retains every declared column");
            compare(head.length, data.count, "The actual header retains every declared column");
            const captureCell = cell => ({x: cell.mapToItem(table, 0, 0).x,
                width: cell.width, left: cell.leftPadding, right: cell.rightPadding,
                alignment: cell.horizontalAlignment});
            for (const cell of [head[data.filler], body[data.filler]]) {
                for (const item of Render.texts(cell)) {
                    ink.font = item.font;
                    ink.text = Probe.plainText(item.text);
                    const advance = ink.advanceWidth;
                    const left = typeof item.leftPadding === "number" ? item.leftPadding : 0;
                    const right = typeof item.rightPadding === "number" ? item.rightPadding : 0;
                    verify(item.width - left - right + 0.6 >= advance,
                        "The final filler preserves the complete actual unrounded header/body ink");
                }
            }
            return {body: body.map(captureCell), head: head.map(captureCell),
                headerPadding: head[data.filler].rightPadding,
                filler: table.fillerWidth, width: table.width};
        }
        function sameGeometry(first, second) {
            compare(first.width, second.width, "The final external viewport input is identical");
            for (const owner of ["body", "head"])
                for (let column = 0; column < first[owner].length; ++column) {
                    for (const field of ["x", "width", "left", "right"])
                        if (first[owner][column][field] !== undefined)
                            fuzzyCompare(first[owner][column][field], second[owner][column][field], 0.6,
                                "Equal current inputs have history-independent " + owner + " " + field);
                    compare(first[owner][column].alignment, second[owner][column].alignment,
                        "A prior filler state cannot change the current source-owned alignment");
                }
        }
        function test_prior_applied_padding_cannot_change_current_layout_data() {
            return [
                {tag: "text", component: textTable, count: 4, filler: 2},
                {tag: "held-text", component: heldTable, table: "experiments.list", count: 7, filler: 4},
                {tag: "number", component: numberTable, table: "background.list", count: 5, filler: 3}
            ];
        }
        function test_prior_applied_padding_cannot_change_current_layout(data) {
            const p = parameter(), before = [p.value, p.uncertainty, p.free];
            supplied.append({label: "r0", note: "Independent final content", id: "r0",
                name: "bank", experiment: Session.project.currentExperiment,
                fitOutcome: "", file: "pattern.dat", extracted: [], isTemplate: false,
                position: 12, intensity: p});
            const left = make(data, 930), right = make(data, 610);
            const first = capture(data, left), second = capture(data, right);
            console.log("TABLE_FILLER_HISTORY " + JSON.stringify({kind: data.tag,
                stage: "prior-applied", first, second}));
            verify(first.headerPadding !== second.headerPadding,
                "The adversary actually starts from distinct previously APPLIED header padding");
            verify(first.filler !== second.filler,
                "Distinct prior widths genuinely exercise different published filler states");
            leftChanges.target = left.table;
            rightChanges.target = right.table;
            verify(leftChanges.valid && rightChanges.valid,
                "The real existing filler notifications identify the exercised owners");
            leftChanges.clear();
            rightChanges.clear();
            resize(left, 800);
            resize(right, 800);
            verify(leftChanges.count > 0 && rightChanges.count > 0,
                "Both real owners publish a changed filler after their distinct prior states");
            const current = capture(data, left), peer = capture(data, right);
            console.log("TABLE_FILLER_HISTORY " + JSON.stringify({kind: data.tag,
                stage: "same-final-input", current, peer,
                actualFillerSignals: [leftChanges.count, rightChanges.count]}));
            sameGeometry(current, peer);
            // Exchange the applied histories and return to the same final input.
            resize(left, 610);
            resize(right, 930);
            const reverseLeft = capture(data, left), reverseRight = capture(data, right);
            verify(reverseLeft.headerPadding !== reverseRight.headerPadding,
                "The reverse transition is armed by distinct actual applied padding again");
            resize(left, 800);
            resize(right, 800);
            sameGeometry(current, capture(data, left));
            sameGeometry(current, capture(data, right));
            compare([p.value, p.uncertainty, p.free], before,
                "Geometry never modifies the genuine numeric parameter or its free/SU state");
            compare(supplied.count, 1, "No synthetic fit changes the input population");
            compare(supplied.get(0).note, "Independent final content",
                "History tests retain the original authored text rather than shrinking it to fit");
        }
    }
}
