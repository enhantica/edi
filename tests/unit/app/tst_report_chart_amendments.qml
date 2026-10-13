// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Window
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render
import EasyApplication.Gui.Globals as Globals

Item {
    id: surface
    width: 1200
    height: 900
    Component {
        id: evolutionFactory
        EvolutionChart {
            width: 1000
            height: 600
        }
    }
    Component {
        id: emptyFactory
        EmptyStateLabel {
            text: "No structures defined"
        }
    }
    Component {
        id: statusFactory
        StatusBar {
            width: 1150
            height: 40
        }
    }
    TestCase {
        name: "ReportChartAmendments"
        when: windowShown
        property int savedPage
        property int savedTheme
        function initTestCase() {
            savedTheme = Style.Colors.theme;
            savedPage = Globals.Vars.appBarCurrentIndex;
            surface.Window.window.width = surface.width;
            surface.Window.window.height = surface.height;
        }
        function cleanup() {
            Session.closeProject();
            Style.Colors.theme = savedTheme;
            Globals.Vars.appBarCurrentIndex = savedPage;
        }
        function test_unfitted_evolution_has_every_free_parameter_and_no_axes() {
            verify(Session.openExample("pd-neut-cwl_cosio-d20_scan-3f"), "The committed three-file scan opens without fitting");
            compare(Session.project.evolution.parameters.count, 39, "The unfitted cosio evolution selector lists all 39 free parameters");
            compare(Session.project.evolution.count, 0, "No evolution point is fabricated before a dataset is fitted");
            const chart = createTemporaryObject(evolutionFactory, surface, {
                project: Session.project
            });
            const reference = createTemporaryObject(emptyFactory, surface);
            verify(chart !== null && reference !== null && waitForPolish(chart), "The real Evolution chart lays out its unfitted state");
            const message = Render.texts(chart).find(item => item.text === "No fitted results yet");
            verify(message !== undefined, "An unfitted Evolution chart shows the declared empty-state message");
            compare(message.font.family, reference.font.family, "Evolution uses the standard empty-state font");
            compare(message.font.pixelSize, reference.font.pixelSize, "Evolution uses the standard empty-state size");
            compare(message.color, reference.color, "Evolution uses the standard empty-state colour");
            const view = findChild(chart, "evolution.view");
            verify(view !== null && !view.visible, "Evolution draws no axes until a fitted point exists");
        }
        function test_palette_functions_follow_data_for_few_and_many_patterns_data() {
            const rows = [];
            for (const dark of [false, true])
                for (const safe of [false, true])
                    for (const count of [3, 100])
                        rows.push({
                            tag: (safe ? "safe" : "default") + "-" + count + (dark ? "-dark" : "-light"),
                            dark: dark,
                            safe: safe,
                            count: count
                        });
            return rows;
        }
        function test_palette_functions_follow_data_for_few_and_many_patterns(data) {
            verify(Session.createProject("palette_witness", "Independent empty experiments"), "The palette gate creates a real project without calculated data");
            for (let i = 0; i < data.count; ++i)
                verify(Session.project.createExperiment(), "The palette gate gives each requested place a real experiment identity");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            verify(typeof Preferences.colourScheme === "string", "The scheme preference is available to every actual colour consumer");
            Preferences.colourScheme = data.safe ? "colourBlindSafe" : "default";
            const rows = SettingsProof.palette(data.safe);
            verify(rows.pattern && rows.pattern.length >= 10 && rows.structure && rows.structure.length > 0, "The independent colour inputs are the shipped palette data rows");
            const theme = data.dark ? "dark" : "light";
            const colors = Array.from({
                length: data.count
            }, (_, i) => String(AppColors.experiment(i)).toLowerCase());
            const roles = ["#f44336", "#607d8b", "#8bc34a", "#8c8c8c"];
            verify(colors.every(color => !roles.includes(color)), "Few and many patterns cannot collide with calculated, background, residual or excluded colours");
            if (data.count === 3) {
                compare(JSON.stringify(colors), JSON.stringify(rows.pattern.slice(0, 3).map(row => row[theme].toLowerCase())), "Few patterns use their distinct palette rows in order");
                compare(new Set(colors).size, 3, "Three patterns retain distinct colours in each scheme and theme");
            } else {
                compare(colors[0], rows.pattern[rows.pattern.length - 2][theme].toLowerCase(), "The 100-pattern gradient starts at its first declared endpoint");
                compare(colors[99], rows.pattern[rows.pattern.length - 1][theme].toLowerCase(), "The 100-pattern gradient finishes at its last declared endpoint");
                verify(colors[50] !== colors[0] && colors[50] !== colors[99], "An interior pattern receives an interior gradient colour rather than an endpoint or repeated short palette");
            }
            for (let i = 0; i < rows.structure.length; ++i)
                compare(String(AppColors.structure(i)).toLowerCase(), rows.structure[i][theme].toLowerCase(), "Structure icons read their own palette rows through the shared core function");
            if (!data.safe && data.count === 3)
                compare(colors[0], data.dark ? "#81d4fa" : "#03a9f4", "Default keeps the existing first measured-series colour in each theme");
        }
        function test_scan_summary_uses_ui_font_size_and_equal_digit_slots() {
            verify(Session.openExample("pd-neut-cwl_cosio-d20_scan-3f"), "A real three-file scan supplies the status-bar summary");
            Globals.Vars.appBarCurrentIndex = 4;
            verify(SettingsProof.publishScanSummary(Session.project), "Hand-declared scan counts reach the actual FitViewModel summary consumer");
            const bar = createTemporaryObject(statusFactory, surface);
            verify(bar !== null && waitForPolish(bar), "The real status bar lays out the completed scan summary");
            // Before: a combined valuePart. After the owner's icon/key/value items,
            // observe the actual counter's DigitText and each of its rendered cells.
            const text = Render.descendants(bar).find(item => item.objectName === "statusBar.fit.value" && item.text === "160");
            verify(text !== undefined && text.visible, "The font gate reaches the drawn scan counter in its actual status item");
            compare(text.font.family, Style.Fonts.fontFamily, "The scan summary uses the application's regular UI font");
            compare(text.font.pixelSize, Style.Sizes.fontPixelSize, "The scan summary has the same font size as the status bar's left items");
            const digits = Render.texts(text).filter(item => /^[0-9]$/.test(item.text));
            verify(digits.length > 1, "The actual summary reaches multiple rendered digit slots");
            for (const digit of digits)
                compare(digit.width, digits[0].width, "Every scan counter digit occupies the same logical width to prevent jitter");
        }
    }
}
