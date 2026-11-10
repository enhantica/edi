import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiOnlineHttpFixture 1.0
import ReportAcceptance 1.0
import OnboardingAcceptance 1.0
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui
import "TutorialGeometry.js" as Geometry

OnlineLoadCase {
    name: "VisibleWebControls"
    loadGroupsOnly: true
    Component { id: calloutFactory; TutorialPanel {} }
    function routes() {
        return [
            {tag: "structure", page: AppState.Page.Structure, group: "structures", action: "web", kind: "structure"},
            {tag: "data", page: AppState.Page.Experiment, group: "experiments", action: "dataWeb", kind: "data"}
        ];
    }
    function populated(data) {
        resetProject();
        Preferences.toolTipLevel = "All";
        Preferences.toolTipDelay = 0;
        const search = Session.onlineSearch;
        const selector = openOnline(data);
        if (data.kind === "structure")
            selectSource(selector, "EasyDiffraction Database", Qt.Key_Down);
        searchFor("");
        tryCompare(search, "busy", false, 3000, "The independently supplied long row finishes loading");
        tryCompare(search.results, "count", 1, 3000, "The real table receives exactly one long collection row");
        const table = onlineControl("results");
        verify(waitForPolish(table), "The result columns lay out before overflow is measured");
        return table;
    }
    function test_every_overflowing_web_cell_elides_and_keeps_its_tooltip_data() { return routes(); }
    function test_every_overflowing_web_cell_elides_and_keeps_its_tooltip(data) {
        const table = populated(data), problems = [];
        const cells = Render.descendants(table).filter(item => typeof item.fullText === "string" && item.fullText.trim() !== "" && item.font && item.visible && item.width > 0);
        verify(cells.length >= 8, "The actual results expose headers and row cells for the overflow census");
        let overflow = 0;
        for (const cell of cells) {
            const metrics = Qt.createQmlObject('import QtQuick; TextMetrics {}', app.contentItem);
            metrics.font = cell.font;
            metrics.text = cell.fullText;
            const available = cell.width - cell.leftPadding - cell.rightPadding;
            if (metrics.advanceWidth > available + 1) {
                ++overflow;
                if (cell.elide !== Text.ElideRight || !cell.truncated)
                    problems.push({text: cell.fullText, problem: "overflow is not elided"});
                if (!cell.shortened) {
                    problems.push({text: cell.fullText, problem: "overflow has no full-text tooltip trigger"});
                    metrics.destroy();
                    continue;
                }
                mouseMove(cell, Math.max(1, cell.width / 2), cell.height / 2, 0);
                tryVerify(() => {
                    settle();
                    return Probe.objectsWithProperty(cell, "requested").some(tip => tip.visible && String(tip.text).includes(cell.fullText.trim()));
                }, 2000, "An overflowing cell exposes its full text through the real tooltip");
            }
            metrics.destroy();
        }
        verify(overflow >= 2, "The nontrivial row exercises at least two overflowing columns");
        console.info("VISIBLE_WEB_RESULT " + JSON.stringify({id: "elision-" + data.kind, errors: problems, overflow: overflow}));
        verify(problems.length === 0, "Every overflowing web-load header or cell ends with an ellipsis within its own column");
    }
    function test_row_callout_does_not_cover_its_target_data() { return routes(); }
    function test_row_callout_does_not_cover_its_target(data) {
        populated(data);
        const row = onlineControl("row.0"), panel = calloutFactory.createObject(app.contentItem);
        verify(panel !== null, "The overlap witness uses the production tutorial callout");
        try {
            panel.tutorial = {id: "visible-row", title: "Load", completion: [], steps: [
                {title: "Choose the row", text: "Click the matching result row to load it.", target: "onlineLoad.row.0", files: false, page: data.group === "structures" ? "structure" : "experiment"}
            ]};
            panel.open();
            tryVerify(() => {
                settle();
                return panel.opened && panel.anchored && panel.opacity > 0.99;
            }, 3000, "The real tutorial callout is placed beside the visible result row");
            const target = Geometry.rect(row, app.contentItem), box = Geometry.rect(panel.background, app.contentItem);
            const overlap = Geometry.overlap(box, target);
            console.info("VISIBLE_WEB_RESULT " + JSON.stringify({id: "placement-" + data.kind, errors: overlap ? ["callout covers target row"] : []}));
            compare(overlap, 0, "The callout leaves the entire target row visible and clickable");
            panel.x = target.x;
            panel.y = target.y;
            verify(Geometry.overlap(Geometry.rect(panel.background, app.contentItem), target) > 0, "An explicitly overlapping placement is detected by the same geometry observer");
        } finally {
            panel.close();
            panel.destroy();
        }
    }
}
