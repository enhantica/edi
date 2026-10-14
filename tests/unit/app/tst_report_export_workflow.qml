// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import QtQuick.Controls
import EasyApplication.Gui.Style as EaStyle
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
        property var webGroup
        property var reference: JSON.parse(SettingsProof.repoText("tests/fixtures/report_storage/reference.json"))
        function cleanup() {
            if (webGroup)
                webGroup.destroy();
            webGroup = null;
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
            const value = webGroup || findChild(page, "group.reportExport");
            verify(value !== null, "The Report page exposes its actual Export group");
            if (value.collapsed)
                mouseClick(value.titleArea, value.titleArea.width / 2, value.titleArea.height / 2);
            tryCompare(value, "collapsed", false, 1000, "The Export group is open before pointer input");
            return value;
        }
        function box(text) {
            const names = {
                "HTML": "report.writesHtml",
                "PDF": "report.writesPdf",
                "CIF": "report.writesCif",
                "Embed the chart libraries": "report.embedLibraries"
            };
            const value = findChild(group(), names[text] || "");
            verify(value !== null && typeof value.checked === "boolean", "Export exposes its actual format or library checkbox " + (names[text] || text));
            return value;
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
        function pathField(format) {
            const fields = Render.descendants(group()).filter(item => item.readOnly === true && item.placeholderText !== undefined && item.text !== undefined);
            compare(fields.length, 3, "Export has one actual read-only path control per HTML, PDF and CIF row; actual controls=" + fields.length);
            const checkbox = box(format.toUpperCase());
            const targetY = checkbox.mapToItem(group(), 0, checkbox.height / 2).y;
            fields.sort((a, b) => Math.abs(a.mapToItem(group(), 0, a.height / 2).y - targetY) - Math.abs(b.mapToItem(group(), 0, b.height / 2).y - targetY));
            const field = fields[0], point = field.mapToItem(group(), 0, field.height / 2);
            verify(Math.abs(point.y - targetY) <= Math.max(field.height, checkbox.height) / 2, "Each report path is on its own format's checkbox row: " + format + " actual y=" + point.y + " checkbox y=" + targetY);
            const indicator = checkbox.indicator;
            const labels = Render.descendants(checkbox).filter(item => item.text === format.toUpperCase() && item.paintedWidth !== undefined);
            const inkRight = Math.max(indicator ? indicator.mapToItem(group(), indicator.width, 0).x : 0, ...labels.map(label => label.mapToItem(group(), label.paintedWidth, 0).x));
            verify(point.x >= inkRight - 1, "Each report path follows the visible checkbox indicator and format label; logical checkbox width may extend farther: " + format + " actual field x=" + point.x + " indicator/label right=" + inkRight + " checkbox width=" + checkbox.width + " enabled=" + checkbox.enabled + " opacity=" + field.opacity);
            return field;
        }
        function pathIsRed(format) {
            return String(pathField(format).color) === String(EaStyle.Colors.red);
        }
        function effectiveOpacity(item) {
            let value = 1;
            while (item && item !== page) {
                value *= item.opacity;
                item = item.parent;
            }
            return value;
        }
        function test_export_path_rows_show_the_saved_file_state_data() {
            return ["not-saved", "current", "out-of-date", "missing", "unticked"].map(state => ({tag: state, state: state}));
        }
        function test_export_path_rows_show_the_saved_file_state(data) {
            prepare(undefined, "tests/fixtures/report_options/pairs");
            Session.project.report.setIncluded("charts", false);
            const html = pathField("html"), pdf = pathField("pdf"), cif = pathField("cif");
            for (const field of [html, pdf, cif]) {
                compare(String(field.text), "", "Before the first explicit Save report each format path is empty");
                verify(/not saved yet/i.test(field.placeholderText), "Before the first report save the path control says not saved yet; actual=" + field.placeholderText);
                const colour = field.placeholderTextColor;
                verify(colour !== undefined && Math.max(colour.r, colour.g, colour.b) - Math.min(colour.r, colour.g, colour.b) < 0.03, "The never-saved placeholder is neutral grey; actual=" + colour);
            }
            if (data.state === "not-saved")
                return;
            setChecked(box("PDF"), true);
            saveReport();
            tryVerify(() => ["html", "pdf"].every(format => SettingsProof.fileFacts(location, reportName(format)).bytes > 100), 15000, "The state gate writes and observes actual HTML and PDF outputs");
            for (const format of ["html", "pdf"]) {
                const field = pathField(format);
                compare(String(field.text), reportName(format), "A saved format shows its exact relative reports/project-name path: " + format);
                compare(String(field.color), String(EaStyle.Colors.themeForeground), "A current report path uses the normal text colour: " + format + " actual=" + field.color);
                const row = Session.project.report.savedReports.find(value => value.format === format);
                verify(row !== undefined && row.saved.length > 0 && String(field.ToolTip.text).includes(row.saved), "The path tooltip shows that actual saved-file record's time: " + format + " actual=" + field.ToolTip.text);
                const before = String(field.text);
                field.forceActiveFocus();
                keyClick(Qt.Key_End);
                keyClick(Qt.Key_X);
                compare(String(field.text), before, "Actual keyboard input cannot edit the read-only report path: " + format);
            }
            const checkedOpacity = effectiveOpacity(html), checkedColour = String(html.color);
            if (data.state === "out-of-date") {
                Session.project.title = "Independently changed after saving both reports";
                tryVerify(() => ["html", "pdf"].every(pathIsRed), 2000, "Changing project content makes both actual saved report paths red before project Save");
                verify(Session.save(), "The edited content saves without regenerating its reports");
            } else if (data.state === "missing") {
                verify(SettingsProof.remove(location, reportName("html")), "The missing-output witness deletes the real saved HTML file");
            } else if (data.state === "unticked") {
                setChecked(box("HTML"), false);
                verify(effectiveOpacity(html) < checkedOpacity || String(html.color) !== checkedColour, "Unticking a saved format visibly dims its read-only path; checked opacity=" + checkedOpacity + " actual=" + effectiveOpacity(html) + " colour=" + html.color);
                verify(SettingsProof.fileFacts(location, reportName("html")).bytes > 100, "Unticking the format retains its actual saved output");
                return;
            } else {
                return;
            }
            page.destroy();
            page = null;
            Session.closeProject();
            verify(Session.openProject(location), "The stale or missing saved report is reopened from its real project folder");
            tryCompare(Session.project, "calculating", false, 15000, "Reopening settles before reading the saved report path state");
            page = pageFactory.createObject(parent, {width: 1300, height: 1000, current: true});
            verify(page !== null && waitForPolish(page), "The reopened Report page constructs its actual path rows");
            tryVerify(() => pathIsRed("html"), 2000, "The reopened stale or missing HTML report keeps its relative path and red state");
            compare(String(pathField("html").text), reportName("html"), "A missing or stale output retains the saved path rather than deleting its row");
            if (data.state === "missing")
                compare(String(pathField("pdf").color), String(EaStyle.Colors.themeForeground), "Removing HTML leaves the actual existing PDF current");
            saveReport();
            tryVerify(() => ["html", "pdf"].every(format => String(pathField(format).color) === String(EaStyle.Colors.themeForeground)), 15000, "Save report rewrites missing or stale files and returns both path rows to normal text");
        }
        function test_browser_path_rows_use_the_session_file_state_data() {
            return ["not-saved", "current", "out-of-date"].map(state => ({tag: state, state: state}));
        }
        function test_browser_path_rows_use_the_session_file_state(data) {
            prepare(undefined, "tests/fixtures/report_options/pairs");
            Session.project.report.setIncluded("charts", false);
            const desktop = findChild(page, "group.reportExport");
            verify(desktop !== null, "The browser capability seam starts with the actual app's Report group and model");
            desktop.visible = false;
            webGroup = SettingsProof.webExport(page, Session.project.report, findChild(page, "report.preview"));
            verify(webGroup !== null && SettingsProof.webAvailable, "The browser UI gate compiles the real resource with only its WebFiles.available capability operand set true");
            verify(waitForPolish(webGroup), "The actual Export resource lays out under the browser capability seam");
            const html = pathField("html");
            compare(String(html.text), "", "A fresh browser session reads no saved path before an actual report save");
            verify(/not saved yet/i.test(html.placeholderText), "The fresh browser session displays the grey not-saved placeholder");
            if (data.state === "not-saved")
                return;
            webGroup.saveReport();
            tryVerify(() => SettingsProof.fileFacts(location, reportName("html")).bytes > 100, 15000, "The web UI capability gate still runs the real report writer and observes its session file");
            compare(String(html.text), reportName("html").split('/').pop(), "The browser field shows the report file name rather than a desktop-relative path");
            compare(String(html.color), String(EaStyle.Colors.themeForeground), "The amended web saving rule shows a current session file in normal text");
            const row = Session.project.report.savedReports.find(value => value.format === "html");
            verify(row !== undefined && /downloaded at/i.test(html.ToolTip.text) && String(html.ToolTip.text).includes(row.saved), "The browser path tooltip names the actual download time; actual=" + html.ToolTip.text);
            if (data.state === "out-of-date") {
                Session.project.title = "Changed in the browser after its actual report save";
                tryVerify(() => pathIsRed("html"), 2000, "The amended web rule colours a stale in-browser file red like the desktop");
                verify(SettingsProof.fileFacts(location, reportName("html")).bytes > 100, "A stale browser report remains in the session folder");
            }
        }
        function evolutionWitness(included) {
            prepare(undefined, "tests/fixtures/report_evolution/project");
            const reference = JSON.parse(SettingsProof.repoText("tests/fixtures/report_evolution/reference.json"));
            const model = Session.project.evolution.parameters;
            const order = [], titles = [];
            compare(model.count, reference.names.length, "The scan's actual Evolution tab lists all six independently declared free parameters");
            for (let i = 0; i < model.count; ++i) {
                order.push(model.text(i, "name"));
                Session.project.evolution.currentParameter = i;
                titles.push(Session.project.evolution.yTitle);
            }
            compare(JSON.stringify(order), JSON.stringify(reference.names), "The prior Evolution tab's parameter order matches the independent scan ledger");
            for (const group of ["charts", "correlations", "reflections", "data"])
                Session.project.report.setIncluded(group, false);
            Session.project.report.setIncluded("evolution", included);
            const preview = findChild(page, "report.preview");
            verify(preview !== null && waitForPolish(preview), "The report evolution gate reaches the actual native preview");
            return {
                reference: reference,
                order: order,
                titles: titles,
                preview: preview
            };
        }
        function test_preview_shows_every_evolution_chart_in_order_data() {
            return [
                {
                    tag: "wide",
                    included: true,
                    narrow: false
                },
                {
                    tag: "narrow",
                    included: true,
                    narrow: true
                },
                {
                    tag: "excluded",
                    included: false,
                    narrow: false
                }
            ];
        }
        function test_preview_shows_every_evolution_chart_in_order(data) {
            const witness = evolutionWitness(data.included);
            if (data.narrow) {
                page.width = 650;
                verify(waitForPolish(page), "The narrow preview lays out its actual text column before checking one chart per row");
            }
            const preview = witness.preview;
            const allCharts = Render.descendants(preview).filter(item => item.objectName === "report.evolution");
            const charts = allCharts.filter(item => item.visible);
            const failures = [];
            if (charts.length !== (data.included ? witness.order.length : 0))
                failures.push("recursive report.evolution items=" + allCharts.length + "; visible charts=" + charts.length + "; expected=" + (data.included ? witness.order.length : 0) + "; records=" + JSON.stringify(allCharts.map(item => ({visible: item.visible, width: item.width, height: item.height, series: item.reportSeries || item.reportShown}))));
            for (let i = 0; i < charts.length; ++i) {
                const chart = charts[i];
                const series = chart.reportSeries || chart.reportShown;
                if (!series || series.name !== witness.order[i])
                    failures.push("chart " + i + " actual reportSeries parameter=" + JSON.stringify(series));
                const points = chart.reportPoints;
                const expected = witness.reference.points[i];
                if (!points || !expected || points.length !== expected.length || expected.some((row, index) => ["x", "y", "su"].some(key => Math.abs(points[index][key] - row[key]) > 1e-9)))
                    failures.push("chart " + i + " numeric points and uncertainties=" + JSON.stringify(points));
                const yTitle = findChild(chart, "report.evolution.title") || findChild(chart, "evolution.title.y"), xTitle = findChild(chart, "evolution.title.x");
                if (!yTitle || yTitle.text !== witness.titles[i] || !xTitle || xTitle.text !== Session.project.evolution.xTitle)
                    failures.push("chart " + i + " native title/units=" + (yTitle ? yTitle.text : null) + "; x=" + (xTitle ? xTitle.text : null));
                const at = chart.mapToItem(preview.contentItem, 0, 0);
                if (i > 0) {
                    const previous = charts[i - 1].mapToItem(preview.contentItem, 0, 0);
                    if (data.narrow && !(at.y >= previous.y + charts[i - 1].height - 1))
                        failures.push("narrow chart " + i + " is not on the next whole row");
                    if (!data.narrow && i % 2 === 1 && (Math.abs(at.y - previous.y) > 1 || at.x < previous.x + charts[i - 1].width - 1 || Math.abs(chart.width - charts[i - 1].width) > 1))
                        failures.push("wide chart pair " + i + " does not share a row with equal half-column widths");
                    if (!data.narrow && i % 2 === 0 && at.y <= previous.y)
                        failures.push("wide chart " + i + " does not start the next row");
                }
            }
            compare(failures.length, 0, "The scan preview shows every free parameter's evolution in tab order, retains titles, axes, points and s.u. bars, uses two charts per wide row or one per narrow row, and leaves Evolution out only when excluded; actual " + failures.join("; "));
        }
        function test_browser_observer_reaches_independent_plot_geometry() {
            const reference = JSON.parse(SettingsProof.repoText("tests/fixtures/report_evolution/reference.json"));
            const observed = SettingsProof.htmlEvolutionFacts(Probe.repoUrl("tests/fixtures/report_evolution/browser-positive.html"));
            verify(!observed.error, "The browser observer reaches the independent six-box HTML control: " + observed.error);
            for (const view of ["wide", "narrow"]) {
                const facts = observed[view];
                compare(facts.plots.length, 6, "The actual browser observer sees all six independently declared plot boxes");
                compare(facts.selectors, 0, "The independent hand document contains no parameter selector");
                const columns = view === "wide" ? 2 : 1;
                const expectedWidth = (facts.viewport - 16 - (columns - 1) * 10) / columns;
                for (let i = 0; i < 6; ++i) {
                    const plot = facts.plots[i];
                    compare(plot.traces[0].name, reference.names[i], "The browser observer retains each independent named plot in actual DOM order");
                    fuzzyCompare(plot.box[0], 8 + (i % columns) * (expectedWidth + 10), 0.1, "The browser observer measures the independently declared column x coordinate");
                    fuzzyCompare(plot.box[1], 8 + Math.floor(i / columns) * 170, 0.1, "The browser observer measures the independently declared row y coordinate");
                    fuzzyCompare(plot.box[2], expectedWidth, 0.1, "The browser observer measures actual CSS half widths and the narrow single width");
                    compare(plot.box[3], 160, "The browser observer measures the independent chart height");
                    verify(plot.svgCount > 0, "The browser observer reaches each actual independent vector drawing element");
                }
            }
        }
        function test_saved_html_draws_all_evolution_charts_without_a_selector_data() {
            return [
                {
                    tag: "included",
                    included: true
                },
                {
                    tag: "excluded",
                    included: false
                }
            ];
        }
        function test_saved_html_draws_all_evolution_charts_without_a_selector(data) {
            const witness = evolutionWitness(data.included);
            setChecked(box("Embed the chart libraries"), true);
            saveReport();
            tryVerify(() => SettingsProof.fileFacts(location, reportName("html")).bytes > 100, 15000, "The evolution HTML gate reaches the actual saved offline app report");
            const observed = SettingsProof.htmlEvolutionFacts(SettingsProof.childUrl(location, reportName("html")));
            verify(!observed.error, "An actual browser loads both wide and narrow copies of the saved HTML: " + observed.error);
            const failures = [];
            for (const view of ["wide", "narrow"]) {
                const facts = observed[view];
                verify(facts !== undefined && typeof facts.plots.length === "number", "The browser proves the " + view + " saved report's actual DOM and Plotly plot inventory");
                if (facts.selectors !== 0)
                    failures.push(view + " parameter selectors=" + facts.selectors);
                const plots = facts.plots, names = [];
                for (const plot of plots)
                    for (const trace of plot.traces)
                        names.push(trace.name);
                if (JSON.stringify(names) !== JSON.stringify(data.included ? witness.order : []))
                    failures.push(view + " actual browser Plotly trace order=" + JSON.stringify(names) + "; DOM figures=" + JSON.stringify(facts.figures) + "; runtime diagnostics=" + JSON.stringify(facts.errors));
                for (let i = 0; i < plots.length; ++i) {
                    const plot = plots[i], trace = plot.traces[0], expected = witness.reference.points[i];
                    if (plot.traces.length !== 1 || !expected || expected.some((point, index) => ["x", "y"].some(key => Math.abs(trace[key][index] - point[key]) > 1e-9) || Math.abs((trace.error_y.array || [])[index] - point.su) > 1e-9) || !trace.error_y.visible)
                        failures.push(view + " chart " + i + " numeric coordinates/s.u. bars=" + JSON.stringify(plot.traces));
                    if (!plot.xTitle || !plot.xTitle.includes("K") || !plot.yTitle)
                        failures.push(view + " chart " + i + " axis name/temperature units=" + JSON.stringify([plot.xTitle, plot.yTitle]));
                    const box = plot.box;
                    if (box[2] <= 0 || box[3] <= 0 || plot.svgCount <= 0)
                        failures.push(view + " chart " + i + " has no nonempty actual vector/canvas drawing");
                    if (box[0] < -1 || box[0] + box[2] > facts.viewport + 1)
                        failures.push(view + " chart " + i + " leaves the actual text viewport " + JSON.stringify(box));
                    if (i > 0) {
                        const previous = plots[i - 1].box;
                        if (view === "narrow" && box[1] < previous[1] + previous[3] - 1)
                            failures.push("narrow chart " + i + " does not occupy its own row");
                        if (view === "wide" && i % 2 === 1 && (Math.abs(box[1] - previous[1]) > 1 || box[0] < previous[0] + previous[2] - 1 || Math.abs(box[2] - previous[2]) > 1))
                            failures.push("wide chart pair " + i + " does not occupy equal half columns");
                        if (view === "wide" && i % 2 === 0 && box[1] <= previous[1])
                            failures.push("wide chart " + i + " does not start the next row");
                    }
                }
            }
            compare(failures.length, 0, "The real saved HTML shows every included scan parameter in Evolution tab order with named axes and uncertainty bars, no parameter selector, two equal wide columns or one narrow column, and no excluded charts; actual " + failures.join("; "));
        }
        function test_pdf_keeps_all_evolution_charts_whole_data() {
            return [
                {
                    tag: "included",
                    included: true
                },
                {
                    tag: "excluded",
                    included: false
                }
            ];
        }
        function test_pdf_keeps_all_evolution_charts_whole(data) {
            const witness = evolutionWitness(data.included);
            setChecked(box("PDF"), true);
            saveReport();
            tryVerify(() => SettingsProof.fileFacts(location, reportName("pdf")).bytes > 100, 15000, "The scan evolution gate reaches a real saved app PDF");
            const facts = SettingsProof.pdfFacts(SettingsProof.childUrl(location, reportName("pdf")));
            verify(!facts.error && facts.pages.length > 0, "The actual evolution PDF is independently readable and nonempty: " + facts.error);
            const draws = [];
            for (let p = 0; p < facts.pages.length; ++p)
                for (const image of facts.pages[p].image_draws)
                    draws.push({
                        page: p,
                        box: facts.pages[p].box,
                        image: image
                    });
            const failures = [], mm = 72 / 25.4;
            if (draws.length !== (data.included ? witness.order.length : 0))
                failures.push("drawn evolution images=" + draws.length + "; expected=" + (data.included ? witness.order.length : 0));
            for (let i = 0; i < draws.length; ++i) {
                const draw = draws[i], image = draw.image, b = image.bounds, clip = image.clip;
                if (b[0] < 25 * mm - 1 || b[2] > 185 * mm + 1 || b[1] < 25 * mm - 1 || b[3] > draw.box[3] - 25 * mm + 1 || b[0] < clip[0] - 0.1 || b[1] < clip[1] - 0.1 || b[2] > clip[2] + 0.1 || b[3] > clip[3] + 0.1)
                    failures.push("chart " + i + " is cut across a page/body clip: " + JSON.stringify(draw));
                if (image.edge_width > 80 * mm + 1)
                    failures.push("chart " + i + " exceeds its half of the 160 mm column");
                const pixel = Math.max(image.edge_width / image.pixels[0], image.edge_height / image.pixels[1]);
                if (Math.abs(image.edge_width - image.edge_height * image.pixels[0] / image.pixels[1]) > 2 * pixel)
                    failures.push("chart " + i + " lost its actual raster aspect");
                if (i % 2 === 1) {
                    const previous = draws[i - 1];
                    if (draw.page !== previous.page || Math.abs(b[1] - previous.image.bounds[1]) > 1 || b[0] < previous.image.bounds[2] - 1)
                        failures.push("chart pair " + i + " is not kept whole together in two half-width columns");
                }
            }
            compare(failures.length, 0, "The saved scan PDF contains every included evolution chart, two per row, each whole within its page, preserving aspect, and no evolution images when excluded; actual " + failures.join("; "));
        }
        function test_export_rows_default_formats_and_disabled_actions() {
            prepare();
            const html = box("HTML"), pdf = box("PDF"), cif = box("CIF"), embed = box("Embed the chart libraries");
            compare(html.checked, true, "I34 absent formats select HTML");
            compare(pdf.checked, false, "I34 absent formats leave PDF unticked");
            compare(cif.checked, false, "I34 absent formats leave CIF unticked");
            compare(cif.enabled, false, "I38 CIF is disabled until its writer task");
            verify(String(cif.ToolTip.text).includes("CIF"), "I38 the disabled CIF box explains its pending writer");
            // Before: two checkbox columns. After: one path row per format and its own Embed row.
            const h = html.mapToItem(group(), 0, 0), p = pdf.mapToItem(group(), 0, 0), c = cif.mapToItem(group(), 0, 0), e = embed.mapToItem(group(), 0, 0);
            verify(p.y > h.y && c.y > p.y, "Each export format has its own HTML, PDF, CIF row in that order");
            verify(e.y > h.y && e.y < p.y, "Embed has its own unindented row immediately below HTML");
            fuzzyCompare(e.x, h.x, 1, "The HTML Embed row is not indented relative to the format checkboxes");
            verify(embed.width >= group().contentItem.width - 1 && embed.text.includes("HTML"), "Embed occupies a full-width row explicitly naming HTML");
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
            tryVerify(() => ["pdf", "html"].every(format => String(pathField(format).text) === reportName(format)), 2000, "I35 the new folder's Export fields reach both copied report paths");
            verify(["pdf", "html"].every(format => String(pathField(format).color) === String(EaStyle.Colors.themeForeground)), "I35 both copied report paths remain normal after Save as changes only the path and metadata time");
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
            tryVerify(() => pathIsRed("html"), 2000, "I37 the Export path turns red before project Save");
            verify(Session.save(), "I37 the changed project is persisted without regenerating reports");
            const original = location;
            Session.closeProject();
            verify(Session.openProject(original), "I37 the saved changed project reopens");
            tryVerify(() => pathIsRed("html"), 2000, "I37 the out-of-date mark survives reopening");
            saveReport();
            tryVerify(() => String(pathField("html").color) === String(EaStyle.Colors.themeForeground), 2000, "I37 Save report replaces the stale digest and clears its mark");
            verify(SettingsProof.remove(location, reportName("html")), "I37 the witness removes the actual saved output");
            Session.closeProject();
            verify(Session.openProject(original), "I37 the project with a missing saved output reopens");
            tryVerify(() => pathIsRed("html"), 2000, "I37 reopening keeps a missing file path and colours it red");
        }
    }
}
