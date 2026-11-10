// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import "ApprovedPalette.js" as Approved
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import ReportBoundaryAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render

Rectangle {
    width: 1300
    height: 1000
    Component {
        id: pageFactory
        ReportPage {}
    }
    Component {
        id: previewFactory
        ReportPreview {}
    }
    TestCase {
        name: "ReportContextBoundary"
        when: windowShown
        property var reference: Approved.reference(SettingsProof)
        property var page
        property var frozen
        property var browserExport
        property var savedScheme
        property int savedTheme
        function init() {
            try {
                savedScheme = Approved.getScheme(Preferences);
            } catch (error) {
                savedScheme = null;
            }
            savedTheme = Style.Colors.theme;
        }
        function cleanup() {
            if (browserExport)
                browserExport.destroy();
            browserExport = null;
            if (page)
                page.destroy();
            if (frozen) {
                frozen.report = null;
                frozen.destroy();
            }
            page = null;
            frozen = null;
            Session.closeProject();
            if (savedScheme)
                Approved.setScheme(Preferences, savedScheme);
            else
                Preferences.resetToDefaults();
            Style.Colors.theme = savedTheme;
        }
        function normalized(document) {
            const copy = JSON.parse(JSON.stringify(document));
            copy.generated = "";
            return copy;
        }
        function same(left, right) {
            function order(value) {
                if (Array.isArray(value))
                    return value.map(order);
                if (value !== null && typeof value === "object") {
                    const out = {};
                    for (const key of Object.keys(value).sort())
                        out[key] = order(value[key]);
                    return out;
                }
                return value;
            }
            return JSON.stringify(order(left)) === JSON.stringify(order(right));
        }
        function test_all_report_surfaces_use_identical_stored_inputs_data() {
            const cases = [];
            for (const browser of [false, true])
                for (const scheme of reference.schemes.map(row => row.id))
                    for (const shown of [0, 1])
                        cases.push({
                            tag: (browser ? "browser-" : "desktop-") + scheme + "-bank" + shown,
                            browser,
                            scheme,
                            shown
                        });
            return cases;
        }
        function test_all_report_surfaces_use_identical_stored_inputs(data) {
            const location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/report_context/joint"));
            verify(Session.openProject(location), "The context witness loads two independently distinct saved banks: " + Session.lastError);
            tryCompare(Session.project, "calculating", false, 15000, "The actual joint-bank projection settles");
            Approved.setScheme(Preferences, data.scheme);
            Session.project.currentExperimentIndex = data.shown;
            tryVerify(() => !Session.project.calculating && Probe.datasetReady(Session.project), 5000, "The selected bank finishes its real pattern projection");
            page = pageFactory.createObject(parent, {
                width: 1300,
                height: 1000,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The real report page consumes the app's actual context");
            Session.project.report.writesPdf = true;
            verify(Session.save(), "The same report settings are persisted for app, Python and CLI");
            tryCompare(Session.project, "calculating", false, 15000, "Saving adopts the actual persisted parameter values before report identity checks");
            const preview = findChild(page, "report.preview");
            if (data.browser) {
                const resource = SettingsProof.webExport(page, Session.project.report, preview);
                browserExport = resource;
                verify(resource !== null, "The browser Export resource receives the same actual report model");
                resource.saveReport();
            } else
                Session.project.report.saveReport("PT Sans");
            const name = Session.project.name + ".html";
            tryVerify(() => SettingsProof.fileFacts(location, "reports/" + name).bytes > 100 && Session.project.report.savedReports.length === 2, 15000, "The app really publishes HTML and PDF and their tracking rows");
            const app = normalized(SettingsProof.htmlModel(SettingsProof.childUrl(location, "reports/" + name)));
            const facts = BoundaryProof.surfaceFacts(location, data.scheme, Session.project.currentExperiment.name);
            verify(!facts.error, "The actual Python and CLI observers complete in the pinned binding context: " + facts.error);
            const expected = normalized(facts.python_model), failures = [];
            const canonical = normalized(facts.canonical_model);
            canonical.contents = canonical.contents.filter(item => item.included);
            if (!same(normalized(facts.python_display), canonical))
                failures.push("The implicit notebook display differs from its documented default inputs");
            if (BoundaryProof.reportDigest(Session.project.report) !== BoundaryProof.jsonDigest(facts.python_model_json))
                failures.push("Explicit report inputs produce different app and Python digests");
            expected.contents = expected.contents.filter(item => item.included);
            for (const route of ["python_html", "python_save_html", "python_save", "cli_output", "cli_save"])
                if (!same(normalized(facts[route]), expected))
                    failures.push(route + " differs from the Python model");
            if (!same(app, expected))
                failures.push("App report differs from Python/CLI at scheme=" + data.scheme + ", shown=" + data.shown);
            if (!facts.python_check.every(row => row[1] === "current") || facts.cli_check.code !== 0)
                failures.push("The same app-saved rows are stale through Python/CLI check: " + JSON.stringify(facts.python_check) + "; " + JSON.stringify(facts.cli_check));
            compare(failures.length, 0, "The app, display, Python model/writers/check and CLI writers/check reproduce one report from identical stored settings and explicit scheme/bank inputs for every Preferences scheme and shown bank, including browser Export; actual " + failures.join("; "));
        }
        function test_native_evolution_and_pdf_read_only_the_supplied_report_styles_data() {
            return [
                {
                    tag: "light",
                    theme: Style.Colors.LightTheme
                },
                {
                    tag: "dark",
                    theme: Style.Colors.DarkTheme
                }
            ];
        }
        function test_native_evolution_and_pdf_read_only_the_supplied_report_styles(data) {
            const location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/report_context/long-scan"));
            verify(SettingsProof.write(location, "reports/report.edi", "_edi.schema_version 3\n_report.excluded \"charts reflections data correlations\"\n"), "The fixed-style witness renders evolution alone, leaving the unrelated 3D and pattern producers to their own gates");
            const report = BoundaryProof.privateReport(location);
            verify(report !== null, "A separately owned report remains alive when the Session project changes");
            compare(BoundaryProof.colourObserverControl(), 5, "The figure-colour observer reaches five exact independent coloured pixels and excludes one white pixel");
            const original = normalized(BoundaryProof.fullModel(report));
            const style = original.pattern_styles.find(row => row.key === "meas.0");
            verify(style !== undefined && original.evolution.length === 6, "The supplied report contains its own measured style and all six independent series");
            Style.Colors.theme = data.theme;
            frozen = previewFactory.createObject(parent, {
                width: 1000,
                height: 900,
                report
            });
            verify(frozen !== null && waitForPolish(frozen), "The actual native preview renders the separately owned report");
            const failures = [];
            for (const input of ["tests/fixtures/report_options/pairs", "tests/fixtures/report_context/long-scan"]) {
                verify(Session.openProject(Probe.repoUrl(input)), "The live Session changes independently of the fixed report renderer");
                tryCompare(Session.project, "calculating", false, 15000, "The unrelated project finishes opening");
                for (const scheme of reference.schemes.map(row => row.id)) {
                    Approved.setScheme(Preferences, scheme);
                    const charts = Render.descendants(frozen).filter(item => item.objectName === "report.evolution");
                    compare(charts.length, 6, "The native observer reaches every actual report evolution chart");
                    const expected = String(style.light).toLowerCase();
                    for (const chart of charts) {
                        const layer = findChild(chart, "evolution.points");
                        verify(layer !== null, "The style gate observes the actual MeasuredLayer drawing the supplied report");
                        if (String(layer.color).toLowerCase() !== expected)
                            failures.push(input + "/" + scheme + " actual=" + layer.color + "; model=" + expected);
                    }
                    if (!same(normalized(BoundaryProof.fullModel(report)), original))
                        failures.push("Global UI choices changed the separately owned report model");
                }
            }
            let figures = null;
            frozen.grabFigures(value => figures = value);
            tryVerify(() => figures !== null, 15000, "The actual light PDF copies finish grabbing their report figures");
            const pixels = BoundaryProof.figureColours(figures, style.light);
            const keys = Object.keys(pixels).filter(key => key.startsWith("evolution-"));
            compare(keys.length, 6, "The PDF observer reaches all six actual evolution image copies");
            if (!keys.every(key => pixels[key] > 0))
                failures.push("A light PDF evolution copy lacks the supplied model's light series colour: " + JSON.stringify(pixels));
            compare(failures.length, 0, "Every native and light PDF evolution renderer reads the fixed model's styles while the open project's count and every Preferences scheme change; actual " + failures.slice(0, 4).join("; ") + "; total=" + failures.length);
        }
    }
}
