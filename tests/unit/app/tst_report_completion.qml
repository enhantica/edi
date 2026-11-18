import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import ReportBoundaryAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

Item {
    id: surface
    width: 1300
    height: 1000
    TestCase {
        id: test
        name: "ReportCompletion"
        when: windowShown
        property var page
        property var root
        readonly property var reference: JSON.parse(SettingsProof.repoText("tests/fixtures/report_completion/reference.json"))
        Component {
            id: pageFactory
            ReportPage {
                current: true
            }
        }
        function cleanup() {
            if (page)
                page.destroy();
            page = null;
            verify(waitForRendering(surface), "The real Report preview retires before the project closes");
            Session.closeProject();
        }
        function click(item) {
            verify(item !== null && item.visible && item.enabled, "The report action uses its actual visible enabled control");
            Ui.scrollIntoView(Ui.target(item));
            verify(waitForPolish(page), "The Report control settles after real viewport scrolling");
            tryVerify(() => Ui.clickPoint(Ui.target(item)) !== null, 1000, "The actual Report control is exposed after its real layout transition");
            const point = Ui.clickPoint(Ui.target(item));
            mouseClick(Ui.target(item), point.x, point.y);
            verify(waitForRendering(page), "The clicked Report control renders its real response");
        }
        function expand(name) {
            const group = findChild(page, name);
            verify(group !== null && group.visible, "The actual Report page exposes its contents or export group");
            if (group.collapsed)
                click(group);
            tryVerify(() => !group.collapsed, 1500, "The report group reaches its expanded layout before input");
            tryVerify(() => !group.folding, 1500, "Sidebar input waits for the real group to finish folding");
            return group;
        }
        function prepare(kind = "buttons") {
            Preferences.resetToDefaults();
            root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/legacy_structure_project/compact-project"));
            verify(SettingsProof.write(root, "structures/cosio.edi", SettingsProof.repoText("tests/fixtures/report_completion/report-structure.edi")), "The report witness supplies an independently declared three-site cubic structure");
            verify(SettingsProof.write(root, "experiments/d20.edi", SettingsProof.repoText("tests/fixtures/report_completion/long-table.edi")), "The report witness supplies every independently declared measured row");
            verify(SettingsProof.write(root, "analysis/analysis.edi", "_edi.schema_version 3\n_fitting_mode.type single\n"), "The report input contains no aliases belonging to the legacy structure");
            if (kind === "table") {
                verify(SettingsProof.remove(root, "structures/cosio.edi"), "The table-only witness omits unrelated 3D structure categories");
                verify(SettingsProof.write(root, "experiments/d20.edi", SettingsProof.repoText("tests/fixtures/report_completion/table-only.edi")), "The table-only input retains every declared measured row without unrelated structure links");
            }
            const excluded = kind === "table" ? "charts data" : kind === "html" ? "" : "data";
            verify(SettingsProof.write(root, "reports/report.edi", '_edi.schema_version 3\n_report.html true\n_report.pdf false\n_report.html_offline true\n_report.excluded "' + excluded + '"\n'), "The input explicitly declares only the report content required by this witness");
            verify(Session.openProject(root), "The real loader opens the independent report witness");
            tryCompare(Session.project, "calculating", false, 10000, "The independent report calculation completes before report input");
            page = pageFactory.createObject(surface, {
                width: 1300,
                height: 1000
            });
            verify(page !== null && waitForPolish(page) && waitForRendering(page), "The real Report page draws its preview");
            if (kind !== "table")
                return;
            expand("group.reportContents");
            const data = findChild(page, "report.contents.data");
            verify(data !== null && data.enabled, "The actual Report Contents exposes the measured-data table choice");
            if (!data.checked)
                click(data);
            tryVerify(() => findChild(page, "report.contents.data") !== null && findChild(page, "report.contents.data").checked, 1000, "Actual Contents input includes the full measured table after its real delegate refresh");
        }
        function preview() {
            return findChild(page, "report.preview");
        }
        function test_every_declared_table_row_reaches_the_real_viewport() {
            prepare("table");
            let table;
            tryVerify(() => {
                table = Render.descendants(preview()).find(item => item.rows !== undefined && item.rows !== null && item.rows.length === reference.rows.length && item.columns !== undefined);
                return table !== undefined;
            }, 2000, "The native Report preview retains every declared data row beyond the long-table boundary");
            const first = table.rows[0], last = table.rows[reference.rows.length - 1];
            for (const [row, source] of [[first, reference.rows[0]], [last, reference.rows[reference.rows.length - 1]]])
                for (const value of source)
                    verify(Array.from(row).some(cell => Number(String(cell)) === value), "The real Report table preserves the independently declared first and final row values");
            Ui.scrollIntoView(table);
            const list = Render.descendants(table).find(item => typeof item.positionViewAtIndex === "function" && item.count === reference.rows.length);
            verify(list !== undefined, "The full Report table has a real viewport for every input row");
            list.positionViewAtIndex(reference.rows.length - 1, ListView.End);
            verify(waitForPolish(list) && waitForRendering(list), "The actual full Report table draws its final row");
            const finalValue = reference.rows[reference.rows.length - 1][1];
            verify(Render.descendants(list).some(item => item.visible && Ui.rendered(item) && Number(item.text) === finalValue), "The final independent measured intensity is rendered in the actual Report table viewport");
        }
        function test_save_report_to_self_contained_html() {
            prepare("html");
            expand("group.reportExport");
            for (const [name, checked] of [["report.writesHtml", true], ["report.writesPdf", false], ["report.embedLibraries", true]]) {
                const box = findChild(page, name);
                verify(box !== null && box.enabled, "The real export offers HTML and offline chart libraries");
                if (box.checked !== checked)
                    click(box);
                tryCompare(box, "checked", checked, 1000, "Actual Report export input chooses self-contained HTML");
            }
            click(findChild(page, "report.save"));
            const file = "reports/" + Session.project.name + ".html";
            tryVerify(() => SettingsProof.fileFacts(root, file).bytes > 100, 3000, "The actual Save report writes its self-contained HTML file");
            const observed = SettingsProof.fileObservation(root, file);
            verify(typeof observed.text === "string" && observed.text.includes("<html"), "The report gate reads the actual saved HTML bytes");
            const chunks = Math.ceil(observed.base64.length / 16384);
            for (let index = 0; index < chunks; ++index)
                console.log("COMPLETE_REPORT_HTML " + JSON.stringify({
                    index,
                    chunks,
                    base64: observed.base64.slice(index * 16384, (index + 1) * 16384)
                }));
        }
        function test_supported_preview_buttons_reach_real_chart_actions_data() {
            return [
                {
                    tag: "pattern",
                    structure: false
                },
                {
                    tag: "structure",
                    structure: true
                }
            ];
        }
        function test_supported_preview_buttons_reach_real_chart_actions(data) {
            prepare();
            const figure = Render.descendants(preview()).find(item => data.structure ? item.objectName === "structure.view" && item.report !== null : item.objectName === "chart" && item.report !== null);
            verify(figure !== undefined, "The actual Report preview creates its structure or pattern figure");
            Ui.scrollIntoView(figure);
            verify(waitForPolish(figure) && waitForRendering(figure), "The report figure reaches its visible viewport");
            const prefix = data.structure ? "structure.toolbar." : "chart.toolbar.";
            verify(findChild(figure, prefix + "save") === null, "Report figures leave Save image to the main view rather than duplicating a camera control");
            if (data.structure)
                for (const role of ["labels", "bonds", "cell", "axes"])
                    verify(!findChild(figure, prefix + role).visible, "Report structure figures keep report-owned features outside the interactive camera controls");
            for (const role of data.structure ? ["projection", "a", "b", "c", "reset"] : ["pan", "zoom", "reset", "legend"]) {
                const control = findChild(figure, prefix + role);
                verify(control !== null && control.visible && control.enabled && Ui.rendered(control), "The Report preview exposes the supported app chart buttons as actual visible controls");
                if (role === "reset")
                    continue;
                const old = control.checked, projection = data.structure ? figure.projection : "";
                click(control);
                if (role === "projection")
                    tryVerify(() => figure.projection !== projection, 1000, "The actual Report projection button changes the rendered structure camera projection");
                if (["legend", "pan", "zoom"].includes(role) && typeof old === "boolean")
                    tryCompare(control, "checked", !old, 1000, "The supported Report chart button changes its actual mode or visibility state");
            }
            click(findChild(figure, prefix + "reset"));
        }
    }
}
