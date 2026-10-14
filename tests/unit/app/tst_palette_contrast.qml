// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render

Rectangle {
    width: 1400
    height: 1000
    Component {
        id: reportFactory
        ReportPage {}
    }
    Component {
        id: preferencesFactory
        AppPreferencesDialog {}
    }
    TestCase {
        name: "PublishedPaletteContrast"
        when: windowShown
        property int oldTheme
        property string oldScheme
        property var page
        property var reference: JSON.parse(SettingsProof.repoText("tests/fixtures/palette_sources/reference.json"))
        function initTestCase() {
            oldTheme = Style.Colors.theme;
            oldScheme = Preferences.colourScheme;
        }
        function cleanup() {
            if (page)
                page.destroy();
            page = null;
            Session.closeProject();
            Style.Colors.theme = oldTheme;
            Preferences.colourScheme = oldScheme;
        }
        // W3C WCAG 2.2, relative luminance: the sRGB transfer function, then
        // the fixed 0.2126/0.7152/0.0722 weights. No product colour arithmetic.
        function luminance(colour) {
            if (colour === undefined || colour === null)
                return NaN;
            let channels;
            const css = /^rgba?\(([^)]+)\)$/.exec(String(colour));
            if (css)
                channels = css[1].split(",").slice(0, 3).map(value => Number(value.trim()) / 255);
            else if (colour.r !== undefined)
                channels = [colour.r, colour.g, colour.b];
            else {
                let hex = String(colour).replace("#", "");
                if (hex.length === 3)
                    hex = hex.split("").map(value => value + value).join("");
                channels = [0, 2, 4].map(index => parseInt(hex.slice(index, index + 2), 16) / 255);
            }
            const linear = channels.map(value => value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4));
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
        }
        function contrast(a, b) {
            const x = luminance(a), y = luminance(b);
            return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
        }
        function oklab(colour) {
            const hex = String(colour).replace("#", "");
            const rgb = [0, 2, 4].map(index => parseInt(hex.slice(index, index + 2), 16) / 255).map(value => value <= 0.04045 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4));
            const lms = [[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566], [0.0883024619, 0.2817188376, 0.6299787005]].map(row => Math.cbrt(row.reduce((sum, value, index) => sum + value * rgb[index], 0)));
            return [[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099], [0.0259040371, 0.7827717662, -0.8086757660]].map(row => row.reduce((sum, value, index) => sum + value * lms[index], 0));
        }
        function oklabDistance(first, second) {
            const a = oklab(first), b = oklab(second);
            return Math.sqrt(a.reduce((sum, value, index) => sum + Math.pow(value - b[index], 2), 0));
        }
        function test_independent_wcag_formula_controls() {
            fuzzyCompare(oklabDistance("#000000", "#ffffff"), 1, 1e-7, "The independent Oklab observer reaches the unit neutral black/white distance");
            compare(contrast("#000000", "#ffffff"), 21, "The independent WCAG observer reaches the published black/white 21:1 endpoint");
            compare(contrast("#333333", "#333333"), 1, "Equal encoded colours have exactly unit contrast");
            verify(contrast("#949494", "#ffffff") > 3 && contrast("#959595", "#ffffff") < 3, "Adjacent independent RGB grey values straddle the strict 3:1 boundary");
            fuzzyCompare(luminance("#0a0a0a"), 0.003035269835488375, 1e-12, "Encoded sRGB 10 uses the W3C lower linear branch");
            fuzzyCompare(luminance("#0b0b0b"), 0.003346535763899161, 1e-12, "Encoded sRGB 11 uses the W3C power branch");
        }
        function test_preferences_lists_all_five_published_schemes() {
            const dialog = createTemporaryObject(preferencesFactory, parent);
            verify(dialog !== null, "The five-scheme gate creates the actual Preferences dialog");
            const box = findChild(dialog, "preferences.colourScheme");
            verify(box !== null, "Appearance exposes its actual preferences.colourScheme selector");
            const actual = Array.from({
                length: box.count
            }, (_, index) => box.textAt(index));
            compare(JSON.stringify(actual), JSON.stringify(reference.schemes.map(scheme => scheme.label)), "Preferences lists the five published schemes in the owner's order; actual=" + JSON.stringify(actual));
            for (let index = 0; index < reference.schemes.length; ++index) {
                box.currentIndex = index;
                box.activated(index);
                compare(Preferences.colourScheme, reference.schemes[index].id, "Selecting each actual published scheme stores its corresponding token: " + actual[index]);
            }
        }
        function test_every_palette_colour_meets_three_to_one_data() {
            const rows = [];
            for (const scheme of reference.schemes)
                for (const dark of [false, true])
                    rows.push({
                        tag: scheme.id + (dark ? "-dark" : "-light"),
                        scheme: scheme.id,
                        dark: dark
                    });
            return rows;
        }
        function test_every_palette_colour_meets_three_to_one(data) {
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            const background = Style.Colors.chartBackground;
            const table = SettingsProof.paletteForScheme(data.scheme);
            verify(table.pattern !== undefined && table.structure !== undefined, "Each of the five schemes has both actual colour roles before contrast evaluation: " + data.scheme);
            const failures = [], theme = data.dark ? "dark" : "light";
            function check(colour, point, pattern) {
                const ratio = contrast(colour, background);
                const separation = oklabDistance(colour, data.dark ? "#ef9a9a" : "#f44336");
                if (pattern && (!isFinite(separation) || separation < 0.10))
                    failures.push(point + " colour=" + colour + " calculated Oklab distance=" + separation);
                if (!isFinite(ratio) || ratio < 3)
                    failures.push(point + " colour=" + colour + " background=" + background + " WCAG ratio=" + ratio);
            }
            for (const role of ["pattern", "structure", ...(table.gradient ? ["gradient"] : [])])
                for (const row of table[role])
                    check(row[theme], "stored " + role + " index=" + row.index, role !== "structure");
            // Both actual APIs, every short palette place, the transition past ten,
            // and dense gradient sampling. Endpoints alone cannot prove a gradient.
            for (const count of [1, 2, 10, 11, 30, 31, 162, 1001])
                for (let place = 0; place < count; ++place)
                    check(ApplicationInfo.patternColour(data.scheme, place, count, data.dark), "pattern API place=" + place + " count=" + count, true);
            for (let place = 0; place < table.structure.length * 2; ++place)
                check(ApplicationInfo.structureColour(data.scheme, place, data.dark), "structure API place=" + place);
            compare(failures.length, 0, "Every stored pattern/structure colour and actual discrete/gradient API sample has at least 3:1 contrast, and every pattern colour stays at least 0.10 Oklab from calculated against the actual theme chart background; scheme=" + data.scheme + " theme=" + theme + " failures=" + failures.slice(0, 30).join("; ") + "; total=" + failures.length);
        }
        function test_pdf_colour_observer_reaches_an_independent_qt_image() {
            const witness = SettingsProof.pdfWitness();
            verify(!witness.error && witness.url !== undefined, "The palette observer consumes the independent Qt-written PDF image");
            const facts = SettingsProof.pdfImageColours(witness.url, ["#0000ff", "#00ff00"]);
            verify(!facts.error && facts.images > 0, "The PDF colour observer decodes an actual independent image stream: " + facts.error);
            verify(facts.counts["#0000ff"] > 0 && facts.counts["#00ff00"] === 0, "The PDF colour observer finds the independently blue image and rejects absent green; actual=" + JSON.stringify(facts));
        }
        function test_report_preview_html_and_pdf_use_light_palettes_data() {
            return reference.schemes.map(scheme => ({
                        tag: scheme.id,
                        scheme: scheme.id
                    }));
        }
        function test_report_preview_html_and_pdf_use_light_palettes(data) {
            Style.Colors.theme = Style.Colors.DarkTheme;
            Preferences.colourScheme = data.scheme;
            const table = SettingsProof.paletteForScheme(data.scheme);
            verify(table.pattern !== undefined, "The report colour gate reaches the selected published palette: " + data.scheme);
            const folder = SettingsProof.copyProject(Qt.resolvedUrl("../../../docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project"));
            verify(Session.openProject(folder), "The light-report colour gate opens the real lbco project in the dark app theme");
            tryCompare(Session.project, "calculating", false, 15000, "The report colour input finishes its actual pattern and reflection calculation");
            page = reportFactory.createObject(parent, {
                width: 1400,
                height: 1000,
                current: true
            });
            verify(page !== null && waitForPolish(page), "The actual Report page creates its real pattern chart");
            const preview = findChild(page, "report.preview");
            function colourSeries(name) {
                const items = Render.descendants(preview);
                for (const item of items) {
                    if (item.objectName === name)
                        return item;
                    if (item.seriesList !== undefined)
                        for (let index = 0; index < item.seriesList.length; ++index)
                            if (item.seriesList[index].objectName === name)
                                return item.seriesList[index];
                }
                return findChild(preview, name);
            }
            tryVerify(() => colourSeries("chart.series.meas") !== null && colourSeries("chart.series.bragg.0") !== null, 5000, "The native report gate reads actual GraphsView seriesList consumers after lazy figure loading; actual chart items=" + JSON.stringify(Render.descendants(preview).filter(item => String(item.objectName).startsWith("chart.")).map(item => item.objectName)));
            const measured = colourSeries("chart.series.meas"), bragg = colourSeries("chart.series.bragg.0");
            const lightMeasured = String(ApplicationInfo.patternColour(data.scheme, 0, 1, false)), lightStructure = String(ApplicationInfo.structureColour(data.scheme, 0, false));
            const failures = [];
            if (String(measured.color) !== lightMeasured || String(bragg.color) !== lightStructure)
                failures.push("preview measured=" + measured.color + " Bragg=" + bragg.color + "; light expected=" + lightMeasured + "/" + lightStructure);
            const exportGroup = findChild(page, "group.reportExport");
            verify(exportGroup !== null, "The palette gate reaches the actual Export writer action");
            Session.project.report.embedLibraries = true;
            Session.project.report.writesPdf = true;
            exportGroup.saveReport();
            const base = "reports/" + Session.project.name;
            tryVerify(() => SettingsProof.fileFacts(folder, base + ".html").bytes > 100 && SettingsProof.fileFacts(folder, base + ".pdf").bytes > 100, 15000, "The palette gate consumes actual saved HTML and PDF reports");
            const html = SettingsProof.htmlEvolutionFacts(SettingsProof.childUrl(folder, base + ".html"));
            verify(!html.error, "The actual saved HTML renderer loads in an independent browser: " + html.error);
            for (const view of ["wide", "narrow"]) {
                const patterns = html[view].patterns;
                if (!patterns || patterns.length !== 1) {
                    failures.push(view + " actual HTML patterns=" + JSON.stringify(patterns));
                    continue;
                }
                const traces = patterns[0].traces;
                const meas = traces.find(trace => /measured/i.test(String(trace.name).replace(/<[^>]+>/g, "")));
                const ticks = traces.find(trace => /Bragg peaks/i.test(String(trace.name).replace(/<[^>]+>/g, "")));
                if (!meas || String(meas.line.color).toLowerCase() !== lightMeasured || !ticks || String(ticks.line.color).toLowerCase() !== lightStructure)
                    failures.push(view + " actual drawn HTML colours=" + JSON.stringify(traces.map(trace => ({
                                name: trace.name,
                                colour: trace.line ? trace.line.color : null
                            }))));
                if (contrast(patterns[0].background, "#ffffff") !== 1)
                    failures.push(view + " actual HTML plot background=" + patterns[0].background);
            }
            const pixels = SettingsProof.pdfImageColours(SettingsProof.childUrl(folder, base + ".pdf"), [lightMeasured, lightStructure]);
            verify(!pixels.error && pixels.images > 0, "The saved-PDF palette gate decodes actual figure images: " + pixels.error);
            if (!(pixels.counts[lightMeasured] >= 5 && pixels.counts[lightStructure] >= 5))
                failures.push("actual saved PDF light-colour pixels=" + JSON.stringify(pixels));
            compare(failures.length, 0, "Report preview, actual rendered HTML and actual saved PDF use the selected scheme's light pattern and structure colours while the app is dark; scheme=" + data.scheme + " actual=" + failures.join("; "));
        }
    }
}
