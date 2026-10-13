// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import edi.app
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render

Item {
    id: surface
    width: 1100
    height: 900
    Component {
        id: chartFactory
        CorrelationChart {}
    }
    Component {
        id: buttonReference
        ChartToolButton {}
    }
    TestCase {
        name: "CorrelationOptions"
        when: windowShown
        property var chart
        property int savedTheme
        function initTestCase() {
            surface.Window.window.width = surface.width;
            surface.Window.window.height = surface.height;
            savedTheme = Style.Colors.theme;
        }
        function cleanup() {
            if (chart)
                chart.destroy();
            chart = null;
            Session.closeProject();
            Style.Colors.theme = savedTheme;
        }
        function test_options_data() {
            return [
                {
                    tag: "light",
                    dark: false
                },
                {
                    tag: "dark",
                    dark: true
                }
            ];
        }
        function renderFrame() {
            surface.Window.window.update();
            verify(waitForRendering(surface), "The actual chart window completes a requested rendered frame");
        }
        function buttons() {
            const box = findChild(chart, "correlations.toolbar.parameters");
            verify(box !== null, "The Parameters box supplies the real toolbar position reference");
            const result = box.parent.children.filter(item => typeof item.checked === "boolean" && typeof item.clicked === "function");
            compare(result.length, 2, "The Correlations toolbar exposes both actual toggle buttons");
            result.sort((a, b) => a.x - b.x);
            verify(result[0].x >= box.x + box.width && result[1].x >= result[0].x + result[0].width, "The label and matrix toggles sit after Parameters in the specified order");
            const reference = createTemporaryObject(buttonReference, surface, {
                x: 0,
                y: 0
            });
            verify(reference !== null, "The existing pattern toolbar button supplies its production style");
            renderFrame();
            for (const button of result) {
                verify(button.visible && button.opacity === 1, "Both correlation toggles are visibly drawn");
                compare(button.width, reference.width, "Correlation toggles share the pattern toolbar button width");
                compare(button.height, reference.height, "Correlation toggles share the pattern toolbar button height");
                compare(button.color, reference.color, "Correlation toggles share the pattern toolbar button background");
                compare(button.border.color, reference.border.color, "Correlation toggles share the pattern toolbar button border");
                compare(button.border.width, reference.border.width, "Correlation toggles share the pattern toolbar border thickness");
                const frame = grabImage(surface);
                const at = button.mapToItem(surface, 3, 3);
                const referenceAt = reference.mapToItem(surface, 3, 3);
                compare(frame.pixel(Math.floor(at.x), Math.floor(at.y)), frame.pixel(Math.floor(referenceAt.x), Math.floor(referenceAt.y)), "The drawn toggle background matches the existing pattern toolbar button");
            }
            return result;
        }
        function axisLabels() {
            return Render.descendants(chart).filter(item => typeof item.text === "string" && chart.labels.includes(item.text) && item.visible && item.width > 0 && item.height > 0);
        }
        function test_options(data) {
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/correlations/polynomial-3")), "Independent polynomial observations supply a nontrivial correlation matrix");
            tryVerify(() => !Session.project.calculating, 3000, "The input dataset finishes calculation before fitting");
            Session.project.fit.start();
            tryCompare(Session.project.fit, "running", false, 5000, "The independently supplied small polynomial fit completes");
            chart = chartFactory.createObject(surface, {
                project: Session.project,
                width: 1000,
                height: 800,
                x: 20,
                y: 20
            });
            verify(chart !== null, "Options are inspected in the real drawn correlation chart");
            renderFrame();
            compare(chart.count, 3, "The input exercises three parameters and both matrix triangles");
            const toggles = buttons();
            compare(toggles[0].checked, false, "Axis tick labels are hidden by default");
            compare(toggles[1].checked, false, "Only the lower triangle is shown by default");
            compare(axisLabels().length, 0, "Hidden tick labels produce no visible parameter labels along either axis");
            const cells = findChild(chart, "correlations.cells");
            verify(cells !== null, "The actual matrix delegates expose their displayed coefficients");
            const lower = cells.itemAt(3), upper = cells.itemAt(1), diagonal = cells.itemAt(0);
            verify(lower !== null && upper !== null && diagonal !== null, "Both triangles and the diagonal have actual cell delegates");
            function coloured(cell) {
                return cell.visible && cell.opacity > 0 && cell.color.a > 0;
            }
            verify(coloured(lower), "The default view displays a real lower-triangle coefficient");
            verify(!coloured(upper) && !coloured(diagonal), "Lower-triangle mode leaves the upper triangle and diagonal blank");
            const pointer = findChild(chart, "correlations.pointer");
            mouseMove(pointer, lower.x + lower.width / 2, lower.y + lower.height / 2);
            const tip = findChild(chart, "correlations.toolTip");
            tryVerify(() => tip.visible && tip.text.includes(chart.labels[0]) && tip.text.includes(chart.labels[1]), 1500, "The cell popup names both parameters while axis labels are hidden");
            mouseClick(toggles[0], toggles[0].width / 2, toggles[0].height / 2);
            compare(toggles[0].checked, true, "A real click enables the axis-label toggle");
            renderFrame();
            compare(axisLabels().length, 6, "Enabling labels draws all three names on both axes when space allows");
            mouseClick(toggles[1], toggles[1].width / 2, toggles[1].height / 2);
            compare(toggles[1].checked, true, "A real click enables the full-matrix toggle");
            renderFrame();
            verify(coloured(upper), "Full-matrix mode displays the upper triangle");
            compare(upper.color, lower.color, "Symmetric correlation pairs have equal colours in full-matrix mode");
            mouseMove(pointer, upper.x + upper.width / 2, upper.y + upper.height / 2);
            tryVerify(() => tip.visible && tip.text.includes(chart.labels[0]) && tip.text.includes(chart.labels[1]), 1500, "The full-matrix upper cell popup also names both parameters");
            mouseClick(toggles[0], toggles[0].width / 2, toggles[0].height / 2);
            compare(axisLabels().length, 0, "The labels toggle is reversible independently of the matrix toggle");
            verify(coloured(upper), "Hiding labels preserves full-matrix mode");
            mouseClick(toggles[1], toggles[1].width / 2, toggles[1].height / 2);
            verify(!coloured(upper) && !coloured(diagonal) && coloured(lower), "The matrix toggle returns to the lower triangle without changing its coefficient");
        }
    }
}
