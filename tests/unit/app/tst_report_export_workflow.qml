// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import QtQuick.Controls
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "RenderedTable.js" as Render

Rectangle {
    width: 1300
    height: 1000
    Component {
        id: pageFactory
        ReportPage {}
    }
    TestCase {
        name: "ReportExportWorkflow"
        when: windowShown
        property var page
        property var location
        property var reference: JSON.parse(SettingsProof.repoText("tests/fixtures/report_storage/reference.json"))
        function cleanup() {
            Session.closeProject();
            if (page)
                page.destroy();
            page = null;
        }
        function prepare(text, input) {
            location = SettingsProof.copyProject(Probe.repoUrl(input || "docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project"));
            if (text !== undefined)
                verify(SettingsProof.write(location, "reports/report.edi", text), "The export witness independently declares the new report file before loading");
            verify(Session.openProject(location), "The export gate opens the actual lbco project through Session: " + Session.lastError);
            tryCompare(Session.project, "calculating", false, 15000, "The export input finishes loading before report operations");
            page = pageFactory.createObject(parent, {
                width: 1300,
                height: 1000,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The real Report page lays out its export controls");
        }
        function group() {
            const value = findChild(page, "group.reportExport");
            verify(value !== null, "The Report page exposes its actual Export group");
            if (value.collapsed)
                mouseClick(value.titleArea, value.titleArea.width / 2, value.titleArea.height / 2);
            tryCompare(value, "collapsed", false, 1000, "The Export group is open before pointer input");
            return value;
        }
        function box(text) {
            const values = Render.descendants(group()).filter(item => item.text === text && typeof item.checked === "boolean");
            compare(values.length, 1, "Export has exactly one format or library checkbox labelled " + text);
            return values[0];
        }
        function setChecked(value, checked) {
            if (value.checked === checked)
                return;
            const parentGroup = group();
            tryVerify(() => value.visible && value.enabled && value.mapToItem(parentGroup, 0, 0).y + value.height <= parentGroup.height, 2000, "The checkbox clears the expanded Export clip before pointer input");
            mouseClick(value, value.width / 2, value.height / 2);
            tryCompare(value, "checked", checked, 1000, "Actual pointer input changes the export checkbox");
        }
        function button() {
            const buttons = Render.descendants(group()).filter(item => item.text === "Save report" && typeof item.clicked === "function");
            compare(buttons.length, 1, "I36 Export has one Save report action for all ticked formats");
            return buttons[0];
        }
        function saveReport() {
            const action = button();
            verify(action.enabled, "I38 the Save report action is enabled with a ticked format");
            tryVerify(() => action.mapToItem(group(), 0, 0).y + action.height <= group().height, 2000, "Save report clears the expanded clip before its real click");
            mouseClick(action, action.width / 2, action.height / 2);
        }
        function reportName(extension) {
            return "reports/" + Session.project.name + "." + extension;
        }
        function test_export_rows_default_formats_and_disabled_actions() {
            prepare();
            const html = box("HTML"), pdf = box("PDF"), cif = box("CIF"), embed = box("Embed the chart libraries");
            compare(html.checked, true, "I34 absent formats select HTML");
            compare(pdf.checked, false, "I34 absent formats leave PDF unticked");
            compare(cif.checked, false, "I34 absent formats leave CIF unticked");
            compare(cif.enabled, false, "I38 CIF is disabled until its writer task");
            verify(String(cif.ToolTip.text).includes("CIF"), "I38 the disabled CIF box explains its pending writer");
            compare(html.parent, embed.parent, "I38 HTML and Embed occupy one checkbox row");
            compare(pdf.parent, cif.parent, "I38 PDF and CIF occupy the next checkbox row");
            verify(html.mapToItem(group(), 0, 0).y < pdf.mapToItem(group(), 0, 0).y, "I38 the HTML row precedes the PDF row");
            setChecked(embed, true);
            setChecked(html, false);
            compare(embed.enabled, false, "I38 unticking HTML disables Embed");
            compare(embed.checked, true, "I38 disabling Embed preserves its stored choice");
            compare(button().enabled, false, "I38 no ticked format disables Save report");
            setChecked(pdf, true);
            compare(button().enabled, true, "I38 a PDF selection enables the same Save report action");
        }
        function test_project_save_writes_settings_only_and_preserves_unchanged_bytes_and_time() {
            prepare();
            setChecked(box("Embed the chart libraries"), true);
            verify(Session.save(), "I35 project Save writes the changed report setting");
            verify(/_report\.html_offline\s+true/.test(SettingsProof.text(location, "reports/report.edi")), "I34 Embed is written in reports/report.edi");
            compare(SettingsProof.fileFacts(location, reportName("html")).bytes, undefined, "I35 project Save creates no HTML report");
            compare(SettingsProof.fileFacts(location, reportName("pdf")).bytes, undefined, "I35 project Save creates no PDF report");
            const before = SettingsProof.fileFacts(location, "reports/report.edi");
            verify(Session.save(), "I35 unchanged project Save succeeds");
            compare(JSON.stringify(SettingsProof.fileFacts(location, "reports/report.edi")), JSON.stringify(before), "I35 unchanged settings retain exact bytes, size and modification time after publish");
        }
        function test_report_text_tab_reads_the_report_owned_file_and_legacy_boxes_use_defaults() {
            const legacy = reference.legacy.join("\n") + "\n";
            prepare("_edi.schema_version 3\n_report.html true\n_report.pdf false\n_report.html_offline false\n_report.excluded \"\"\n");
            verify(SettingsProof.write(location, "project.edi", SettingsProof.text(location, "project.edi") + legacy), "I34 the legacy witness contains all seven retired lines");
            Session.closeProject();
            verify(Session.openProject(location), "I34 legacy lines remain valid syntax rather than refused known-category items");
            compare(box("HTML").checked, true, "I34 the new file's HTML wins over legacy false");
            compare(box("PDF").checked, false, "I34 the new file's PDF wins over legacy true");
            compare(box("Embed the chart libraries").checked, false, "I34 the new file's online choice wins over legacy Embed");
            const tab = findChild(page, "sideBar.tab.text");
            verify(tab !== null && tab.enabled, "I34 the real Report page offers its Text tab");
            mouseClick(tab, tab.width / 2, tab.height / 2);
            tryVerify(() => findChild(page, "text.view") !== null, 1000, "I34 the actual Text editor is loaded");
            const editor = findChild(page, "text.view");
            verify(editor.text.includes('_report.excluded ""') && !editor.text.includes('_report.tex true'), "I34 Report Text shows the report-owned file rather than the legacy project record");
        }
        function test_pdf_observer_is_qualified_against_independent_multipage_text_and_image() {
            const witness = SettingsProof.pdfWitness();
            verify(!witness.error, "The independent PDF observer parses a separately written Qt witness: " + witness.error);
            compare(witness.pages.length, 2, "The independent PDF witness reaches both pages");
            verify(witness.text.includes("Short name lbco_hrpt_s2") && witness.text.includes("Second page"), "The PDF observer extracts Unicode text from both witness pages");
            verify(Object.values(reference.correlation_rgb).every(colour => witness.colours.includes(colour)), "The independent PDF observer extracts all three hand-declared correlation colour operators");
            verify(witness.images > 0, "The PDF observer identifies a real witness image object");
            for (const p of witness.pages)
                compare(JSON.stringify(p.box), JSON.stringify(reference.pdf.media_box), "The qualified PDF observer measures Qt's actual A4 MediaBox");
            const fragments = witness.pages[0].lines.filter(row => row.text.includes("Short"));
            verify(fragments.length > 0 && Math.abs(fragments[0].size - reference.pdf.body_pt) < 0.1, "The qualified PDF observer resolves font size through PDF transforms");
        }
        function test_app_save_report_writes_a4_pdf_with_extractable_text_figures_and_page_numbers() {
            prepare();
            setChecked(box("PDF"), true);
            saveReport();
            tryVerify(() => SettingsProof.fileFacts(location, reportName("pdf")).bytes > 100, 15000, "I36 the app writes an actual PDF in the project's reports folder");
            const facts = SettingsProof.pdfFacts(SettingsProof.childUrl(location, reportName("pdf")));
            verify(!facts.error, "I41 the actual app PDF is independently readable: " + facts.error);
            verify(facts.pages.length > 0 && facts.images > 0, "I41 the PDF contains A4 pages and image figures");
            verify(facts.text.includes("Short name") && facts.text.includes("lbco_hrpt_s2"), "I41 the PDF summary is extractable text rather than a screenshot");
            const margin = reference.pdf.margin_mm * 72 / 25.4;
            for (let i = 0; i < facts.pages.length; ++i) {
                const p = facts.pages[i];
                compare(JSON.stringify(p.box), JSON.stringify(reference.pdf.media_box), "I41 every actual PDF page has Qt's rounded 595 by 842 point A4 box");
                const footer = p.lines.filter(row => row.text === String(i + 1) && row.y > 770);
                verify(footer.length > 0 && Math.abs(footer[0].x - 595 / 2) < 12, "I41 every page has its sequential number centred below the body");
                const body = p.fragments.filter(row => row.text.trim() !== "" && row.y < 770);
                verify(body.every(row => row.x >= margin - 1 && row.x <= 595 - margin + 1), "I41 body text lies inside the independently derived 25 mm side margins");
            }
            verify(facts.pages.some(p => p.fragments.some(row => row.text.trim() !== "" && Math.abs(row.size - reference.pdf.body_pt) < 0.1)), "I41 the body uses the reference's 10.04 point font");
        }
        function test_pdf_correlation_table_uses_the_signed_reference_colours() {
            prepare(undefined, "tests/fixtures/report_storage/signed");
            setChecked(box("PDF"), true);
            saveReport();
            tryVerify(() => SettingsProof.fileFacts(location, reportName("pdf")).bytes > 100, 15000, "I40 the signed PSD fixture reaches an actual PDF report");
            const facts = SettingsProof.pdfFacts(SettingsProof.childUrl(location, reportName("pdf")));
            verify(!facts.error, "I40 the signed correlation PDF is independently readable: " + facts.error);
            verify(Object.values(reference.correlation_rgb).every(colour => facts.colours.includes(colour)), "I40 coefficients minus one, zero and one use the independent red, white and blue in the PDF table");
        }
        function test_saved_pdf_figures_fit_the_text_column_whole_data() {
            return [
                {
                    tag: "ordinary",
                    longDescription: false
                },
                {
                    tag: "page-break",
                    longDescription: true
                }
            ];
        }
        function test_saved_pdf_figures_fit_the_text_column_whole(data) {
            prepare();
            if (data.longDescription)
                Session.project.description = Array.from({
                    length: 36
                }, (_, i) => "Independent pagination line " + (i + 1) + ": " + "a complete figure moves to the following page with its entire frame ".repeat(2)).join("\n");
            setChecked(box("PDF"), true);
            saveReport();
            tryVerify(() => SettingsProof.fileFacts(location, reportName("pdf")).bytes > 100, 15000, "The figure-bounds witness reaches the actual saved app PDF");
            const facts = SettingsProof.pdfFacts(SettingsProof.childUrl(location, reportName("pdf")));
            verify(!facts.error, "The saved PDF figure matrices and clip bounds are independently readable: " + facts.error);
            if (data.longDescription)
                verify(facts.text.includes("Independent pagination line 36"), "The saved long-description PDF actually reaches its final declared pagination line");
            const mm = 72 / 25.4, left = 25 * mm, right = left + 160 * mm;
            let figures = 0;
            const failures = [];
            for (let pageIndex = 0; pageIndex < facts.pages.length; ++pageIndex) {
                const page = facts.pages[pageIndex];
                verify(page.image_draws !== undefined && typeof page.image_draws.length === "number", "Each saved PDF page exposes its actual drawn image placements; actual=" + JSON.stringify(page));
                for (const image of page.image_draws) {
                    ++figures;
                    const b = image.bounds, clip = image.clip;
                    if (b[0] < left - 1 || b[2] > right + 1)
                        failures.push("160 mm column: page=" + pageIndex + " bounds=" + JSON.stringify(b));
                    if (b[1] < 25 * mm - 1 || b[3] > page.box[3] - 25 * mm + 1)
                        failures.push("whole page: page=" + pageIndex + " bounds=" + JSON.stringify(b));
                    if (b[0] < clip[0] - 0.1 || b[1] < clip[1] - 0.1 || b[2] > clip[2] + 0.1 || b[3] > clip[3] + 0.1)
                        failures.push("cropped: page=" + pageIndex + " bounds=" + JSON.stringify(b) + " clip=" + JSON.stringify(clip));
                    // Allow one-pixel quantisation on both raster extents.
                    const pixel = Math.max(image.edge_width / image.pixels[0], image.edge_height / image.pixels[1]);
                    if (Math.abs(image.edge_width - image.edge_height * image.pixels[0] / image.pixels[1]) > 2 * pixel)
                        failures.push("aspect: page=" + pageIndex + " scales=" + image.edge_width + "/" + image.edge_height + " pixels=" + JSON.stringify(image.pixels));
                    if (data.longDescription && pageIndex === 0)
                        failures.push("long-description figure did not move whole beyond the first page");
                }
            }
            verify(figures >= 2, "The bounds gate reaches both actual structure and pattern figures rather than an empty PDF");
            compare(failures.length, 0, "Every saved PDF figure with its frame fits the 160 mm column and page whole, keeps its aspect and is never clipped; actual failures: " + failures.join("; "));
        }
        function test_unticking_pdf_keeps_its_file_and_row_and_save_as_copies_both_reports() {
            prepare();
            const pdf = box("PDF");
            setChecked(pdf, true);
            saveReport();
            tryVerify(() => SettingsProof.fileFacts(location, reportName("pdf")).bytes > 100, 15000, "I36 the app first reaches a real PDF output");
            const pdfName = reportName("pdf"), htmlName = reportName("html");
            const oldPdf = SettingsProof.fileFacts(location, pdfName);
            setChecked(pdf, false);
            saveReport();
            compare(SettingsProof.fileFacts(location, pdfName).sha256, oldPdf.sha256, "I36 unticking PDF never deletes or rewrites its saved file");
            verify(SettingsProof.text(location, "reports/report.edi").includes(pdfName.split('/').pop()), "I36 the unticked PDF retains its saved-file row");
            const oldRecord = SettingsProof.text(location, "reports/report.edi");
            const oldHtml = SettingsProof.fileFacts(location, htmlName);
            const destination = SettingsProof.emptyDirectory();
            verify(String(destination) !== "", "I35 Save as uses a genuinely empty independent destination folder");
            verify(Session.saveAs(destination), "I35 the app Save as publishes a different project folder");
            compare(SettingsProof.text(destination, "reports/report.edi"), oldRecord, "I35 Save as copies report settings and both saved-file rows byte for byte");
            compare(SettingsProof.fileFacts(destination, pdfName).sha256, oldPdf.sha256, "I35 Save as copies the original PDF without generating it");
            compare(SettingsProof.fileFacts(destination, htmlName).sha256, oldHtml.sha256, "I35 Save as copies the original HTML without generating it");
            compare(SettingsProof.text(location, "reports/report.edi"), oldRecord, "I35 Save as leaves the source report record untouched");
            tryVerify(() => [pdfName, htmlName].every(name => Render.texts(group()).some(item => item.text.includes(name.split('/').pop()))), 2000, "I35 the new folder's Export list actually reaches both copied report rows");
            verify(!Render.texts(group()).some(item => /out of date|missing/i.test(item.text)), "I35 both copied reports remain current after Save as changes only the path and metadata time");
        }
        function checkHtmlGeometry(text) {
            const facts = SettingsProof.htmlFigureFacts(text);
            verify(!facts.error, "I40 the actual HTML shared-site and legend producers execute: " + facts.error);
            compare(JSON.stringify(facts.legend), JSON.stringify([
                {
                    color: "#ff0000",
                    text: "red"
                },
                {
                    color: "#0000ff",
                    text: "blue"
                }
            ]), "I40 legend entries use their own series colours and identities");
            verify(facts.positions.length > 0 && facts.positions.length === facts.normals.length && facts.positions.length === facts.colours.length, "I40 the HTML producer emits actual coloured sphere surface vertices");
            let red = 0, blue = 0;
            for (let at = 0; at < facts.positions.length; at += 3) {
                const x = facts.positions[at] - 1, y = facts.positions[at + 1] - 2, z = facts.positions[at + 2] - 3;
                fuzzyCompare(Math.sqrt(x * x + y * y + z * z), 2.7, 0.00001, "I40 every emitted shared-site vertex lies on the independent nontrivial-radius sphere");
                const colour = facts.colours.slice(at, at + 3);
                if (JSON.stringify(colour) === "[1,0,0]") {
                    verify(x >= -0.00001 && y >= -0.00001, "I40 the quarter red occupancy stays within its independent quarter-turn wedge");
                    red++;
                } else {
                    compare(JSON.stringify(colour), "[0,0,1]", "I40 the remaining vertices use blue and emit no zero-occupancy green wedge");
                    verify(x <= 0.00001 || y <= 0.00001 || Math.abs(z) >= 2.69999, "I40 the three-quarter blue occupancy stays outside the red quarter-turn interior");
                    blue++;
                }
            }
            verify(red > 0 && blue > red, "I40 both nonzero occupancies reach distinct coloured surface wedges");
        }
        function test_html_geometry_observer_reaches_the_actual_prior_producers() {
            checkHtmlGeometry(SettingsProof.repoText("data/report/report.js"));
        }
        function test_saved_html_carries_executable_split_spheres_and_series_coloured_legend() {
            prepare();
            saveReport();
            tryVerify(() => SettingsProof.fileFacts(location, reportName("html")).bytes > 100, 15000, "I40 the geometry gate consumes an actual saved HTML report");
            checkHtmlGeometry(SettingsProof.text(location, reportName("html")));
        }
        function test_unsaved_content_edits_mark_saved_reports_stale_then_reopen_keeps_the_mark() {
            prepare();
            saveReport();
            tryVerify(() => SettingsProof.fileFacts(location, reportName("html")).bytes > 100, 15000, "I37 staleness is exercised after a real report save");
            Session.project.title = "Changed unsaved report title";
            compare(Session.project.modified, true, "I37 the witness reaches an unsaved content change");
            tryVerify(() => Render.texts(group()).some(item => /out of date/i.test(item.text)), 2000, "I37 the Export list marks a report stale before project Save");
            verify(Session.save(), "I37 the changed project is persisted without regenerating reports");
            const original = location;
            Session.closeProject();
            verify(Session.openProject(original), "I37 the saved changed project reopens");
            tryVerify(() => Render.texts(group()).some(item => /out of date/i.test(item.text)), 2000, "I37 the out-of-date mark survives reopening");
            saveReport();
            tryVerify(() => !Render.texts(group()).some(item => /out of date/i.test(item.text)), 2000, "I37 Save report replaces the stale digest and clears its mark");
            verify(SettingsProof.remove(location, reportName("html")), "I37 the witness removes the actual saved output");
            Session.closeProject();
            verify(Session.openProject(original), "I37 the project with a missing saved output reopens");
            tryVerify(() => Render.texts(group()).some(item => /missing/i.test(item.text)), 2000, "I37 reopening marks a missing file rather than deleting its row");
        }
    }
}
