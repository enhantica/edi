// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import "RenderedTable.js" as Render

Item {
    id: surface

    height: 1000
    width: 1400

    Component {
        id: pageFactory

        AnalysisPage {
        }
    }
    TestCase {
        property var page

        function cleanup() {
            if (page)
                page.destroy();
            page = null;
            Session.closeProject();
        }
        function test_structure_fills_and_scan_tabs() {
            verify(Session.openExample("pd-neut-tof_ferrite-austenite-beer_joint"), "The Analysis actor uses the two-structure BEER project");
            tryCompare(Session.project, "calculating", false, 10000, "The real two-structure calculation completes");
            page = pageFactory.createObject(surface, {
                width: surface.width,
                height: surface.height,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The actual Analysis page lays out its chart and sidebar");
            const tabs = Render.texts(page).filter(item => /stack|map/i.test(item.text));
            verify(tabs.some(item => /stack/i.test(item.text)) && tabs.some(item => /map/i.test(item.text)), "Analysis offers both stacked patterns and the 2D intensity map beside its existing views");
            const settings = Render.descendants(page).find(item => item.objectName === "group.chartSettings");
            verify(settings !== undefined, "The chart's real sidebar settings are present");
            const toggle = Render.descendants(settings).find(item => typeof item.checked === "boolean" && /structure/i.test(String(item.text)));
            verify(toggle !== undefined && !toggle.checked, "Each structure's fill is off by default in the Analysis sidebar");
            mouseClick(toggle, toggle.width / 2, toggle.height / 2);
            tryCompare(toggle, "checked", true, 1000, "The structure-fill setting can be enabled through real input");
            verify(waitForRendering(page), "The enabled component curves complete a rendered frame");
            const fills = Render.descendants(page).filter(item => item.visible && item.opacity > 0 && item.upperSeries !== undefined && item.lowerSeries !== undefined);
            verify(fills.length === Session.project.structures.count, "The chart draws one area series for each linked structure");
            for (const fill of fills)
                verify(fill.lowerSeries !== null && fill.upperSeries !== null, "Every unstacked structure fill has its own curve over a background baseline");
        }

        name: "StructureScanViews"
        when: windowShown
    }
}
