// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import "RenderedTable.js" as Render

Rectangle {
    width: 1200
    height: 800
    TestCase {
        id: test
        name: "ReportContentsLifecycle"
        when: windowShown
        property var page
        Component {
            id: reportFactory
            ReportPage {}
        }
        function init() {
            Session.closeProject();
            // The offscreen runner has no GLES context. Exempt only these exact Qt
            // bootstrap diagnostics; every QML/product warning still fails.
            failOnWarning(/^(?!QRhiGles2: Failed to create (temporary )?context$).*/);
            page = reportFactory.createObject(parent, {
                width: 1200,
                height: 800,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The actual Report page opens without a console warning");
        }
        function cleanup() {
            Session.closeProject();
            if (page)
                page.destroy();
            page = null;
        }
        function open(path) {
            verify(Session.openProject(Probe.repoUrl(path)), "The warning witness opens a committed valid project through the real Session: " + Session.lastError);
            tryCompare(Session.project, "calculating", false, 15000, "The warning witness finishes loading before the next project transition");
            verify(waitForPolish(page) && waitForRendering(page), "The real Report page consumes and renders the new project's model");
            const contents = findChild(page, "group.reportContents");
            verify(contents !== null, "The actual Report sidebar contains its Contents group");
            contents.collapsed = false;
            verify(waitForPolish(contents), "The live Contents delegates are laid out before replacing their model");
            tryVerify(() => Render.descendants(contents).some(item => String(item.objectName).startsWith("report.contents.")), 2000, "The warning witness actually creates Contents delegates rather than testing an empty repeater");
        }
        function test_report_project_lifecycle_has_no_console_warning_data() {
            return [
                {
                    tag: "open",
                    transition: "open"
                },
                {
                    tag: "smaller",
                    transition: "smaller"
                },
                {
                    tag: "close",
                    transition: "close"
                }
            ];
        }
        function test_report_project_lifecycle_has_no_console_warning(data) {
            open("docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project");
            const structures = Probe.rows(Session.project.structures).length;
            const experiments = Probe.rows(Session.project.experiments).length;
            verify(structures > 1 && experiments > 1, "The rich lifecycle witness starts with multiple structures and experiments");
            if (data.transition === "smaller") {
                open("tests/fixtures/loop_parameter_ids/line-segment");
                verify(Probe.rows(Session.project.structures).length < structures, "Replacing the project really shrinks its structure population");
                verify(Probe.rows(Session.project.experiments).length < experiments, "Replacing the project really shrinks its experiment population");
                compare(page.project, Session.project, "The Report page follows the replacement project rather than retaining stale delegates");
            } else if (data.transition === "close") {
                Session.closeProject();
                tryCompare(page, "project", null, 2000, "Closing clears the actual Report page's project binding without a console warning");
                verify(waitForPolish(page) && waitForRendering(page), "Closing flushes the Report page's delegate teardown and frame");
            }
        }
    }
}
