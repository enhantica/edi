// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import "ApprovedPalette.js" as Approved
import QtQuick.Window
import QtTest
import "ExampleProjects.js" as Examples
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
        property var paletteReference: Approved.reference(SettingsProof)
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
            verify(Examples.fixture(Session, "pd-neut-cwl_cosio-d20_scan-3f"), "The committed three-file scan opens without fitting");
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
                for (const scheme of paletteReference.schemes.map(row => row.id))
                    for (const count of [3, 100])
                        rows.push({
                            tag: scheme + "-" + count + (dark ? "-dark" : "-light"),
                            dark: dark,
                            scheme: scheme,
                            count: count
                        });
            return rows;
        }
        function test_palette_functions_follow_data_for_few_and_many_patterns(data) {
            verify(Session.createProject("palette_witness", "Independent empty experiments"), "The palette gate creates a real project without calculated data");
            for (let i = 0; i < data.count; ++i)
                verify(Session.project.createExperiment(), "The palette gate gives each requested place a real experiment identity");
            for (let i = 0; i < 5; ++i)
                verify(Session.project.createStructure(), "The icon witness creates each actual structure identity before checking its colour");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            verify(typeof Approved.getScheme(Preferences) === "string", "The single figure palette preference are available to every actual colour consumer");
            Approved.setScheme(Preferences, data.scheme);
            const expected = Approved.colours(SettingsProof, data.scheme, "measured", data.count, data.dark, {
                experiments: data.count,
                structures: 5
            });
            const colors = Array.from({
                length: data.count
            }, (_, i) => String(AppColors.experiment(i)).toLowerCase());
            compare(JSON.stringify(colors), JSON.stringify(expected), "Every app pattern place equals the approved categorical or independently computed shared-position Oklab shades");
            const structures = Approved.colours(SettingsProof, data.scheme, "structures", Session.project.structures.count, data.dark, {
                experiments: data.count,
                structures: 5
            });
            compare(structures.length, 5, "All five real structure icons reach their independent categorical reference");
            for (let i = 0; i < structures.length; ++i)
                compare(String(AppColors.structure(i)).toLowerCase(), structures[i], "Structure icons consume their own independent count-aware group");
        }

        function test_scan_summary_uses_ui_font_size_and_equal_digit_slots() {
            verify(Examples.fixture(Session, "pd-neut-cwl_cosio-d20_scan-3f"), "A real three-file scan supplies the status-bar summary");
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
