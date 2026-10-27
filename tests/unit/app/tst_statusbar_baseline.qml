// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import "ExampleProjects.js" as Examples
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import edi.app
import "E04Review.js" as View

Item {
    TextMetrics {
        id: digitInk
        text: "0"
    }
    TextMetrics {
        id: arrowInk
        text: "→"
    }
    width: 1400
    height: 180
    Component {
        id: barComponent
        StatusBar {
            width: 1300
            height: 40
            y: 60
        }
    }
    TestCase {
        name: "StatusBarBaseline"
        when: windowShown
        property int savedPage
        property int savedTheme

        function init() {
            failOnWarning(/.*/);
            savedPage = EaGlobals.Vars.appBarCurrentIndex;
            savedTheme = EaStyle.Colors.theme;
            Session.closeProject();
            EaGlobals.Vars.appBarCurrentIndex = 4;
        }
        function cleanup() {
            Session.closeProject();
            EaGlobals.Vars.appBarCurrentIndex = savedPage;
            EaStyle.Colors.theme = savedTheme;
        }
        function test_fitted_numbers_share_rendered_baseline_and_arrow_ink() {
            verify(Examples.bundled(this, Session, "pd-neut-cwl_lbco-hrpt"), "The independent bundled baseline fixture opens through the real Session: " + Session.lastError);
            const fit = Session.project.fit;
            tryCompare(Session.project, "calculating", false, 10000, "The actual baseline project finishes its initial calculation");
            verify(fit.available, "The baseline fixture can execute its real fit");
            fit.start();
            tryVerify(() => !fit.running && fit.outcome !== "", 20000, "A real fit publishes its result before baseline checks");
            verify(fit.outcome !== "failed", "The baseline witness completes a real fit: " + fit.status);
            const values = fit.goodnessOfFit.split(" → ");
            compare(values.length, 2, "The fixture supplies actual before and after values");
            verify(values.every(value => value.trim() !== "" && Number.isFinite(Number(value))), "Both before and after fields contain finite fit metrics");
            const bar = createTemporaryObject(barComponent, parent);
            verify(bar !== null, "The physical baseline witness creates the actual production status bar");
            let runs = [];
            tryVerify(() => {
                const value = View.descendants(bar).find(item => item.objectName === "statusBar.fit.value" && item.text === values.join("→"));
                runs = value ? View.textItems(value).sort((a, b) => a.x - b.x) : [];
                return runs.length > 0 && runs.map(item => item.text).join("") === values.join("→");
            }, 2000, "The real per-digit renderer displays every before/after character with its separating arrow");
            const arrows = runs.filter(item => item.text === "→");
            compare(arrows.length, 1, "The actual before/after renderer draws exactly one separating arrow");
            const arrow = arrows[0], at = runs.indexOf(arrow);
            const before = runs.slice(0, at), after = runs.slice(at + 1);
            compare(before.map(item => item.text).join(""), values[0], "The actual before-value glyphs preserve the metric supplied by the fit model");
            compare(after.map(item => item.text).join(""), values[1], "The actual after-value glyphs preserve the metric supplied by the fit model");
            compare(arrow.font.family, EaStyle.Fonts.encodeSansRegular.name, "The separating arrow uses the bundled font that supplies its glyph");
            compare(arrow.font.bold, false, "The separating arrow keeps the regular text weight");
            const digits = before.concat(after).filter(item => /^[0-9]$/.test(item.text));
            verify(digits.length > 1, "The physical baseline witness observes digits on both sides of the arrow");
            digitInk.font = digits[0].font;
            arrowInk.font = arrow.font;
            for (const theme of [EaStyle.Colors.Themes.LightTheme, EaStyle.Colors.Themes.DarkTheme]) {
                EaStyle.Colors.theme = theme;
                for (const width of [900, 1300]) {
                    bar.width = width;
                    verify(waitForPolish(bar), "The status-bar value glyphs finish layout after resizing");
                    verify(waitForRendering(bar), "The status-bar value glyphs reach a frame after resizing");
                    const firstBaseline = digits[0].mapToItem(bar, 0, digits[0].baselineOffset).y;
                    for (const run of before.concat(after)) {
                        const baseline = run.mapToItem(bar, 0, run.baselineOffset).y;
                        fuzzyCompare(baseline, firstBaseline, .25, "Every rendered before/after glyph shares the same physical text baseline");
                        compare(run.font.family, digits[0].font.family, "Both numbers use the same UI typeface");
                        compare(run.font.pixelSize, digits[0].font.pixelSize, "Both numbers use the same UI text size");
                        compare(run.color, EaStyle.Colors.themeForeground, "All metric glyphs follow the theme's ordinary foreground ink");
                    }
                    for (const digit of digits)
                        compare(digit.width, digits[0].width, "Every metric digit has the same fixed-width cell");
                    compare(arrow.color, digits[0].color, "The separating arrow shares the metric's theme ink");
                    const digitCentre = firstBaseline + digitInk.tightBoundingRect.y + digitInk.tightBoundingRect.height / 2;
                    const arrowCentre = arrow.mapToItem(bar, 0, arrow.baselineOffset + arrowInk.tightBoundingRect.y + arrowInk.tightBoundingRect.height / 2).y;
                    fuzzyCompare(arrowCentre, digitCentre, .25, "The arrow's drawn ink is vertically centred on the digit ink");
                    const beforeRight = before[before.length - 1].mapToItem(bar, before[before.length - 1].width, 0).x;
                    const arrowLeft = arrow.mapToItem(bar, 0, 0).x;
                    const arrowRight = arrow.mapToItem(bar, arrow.width, 0).x;
                    const afterLeft = after[0].mapToItem(bar, 0, 0).x;
                    verify(beforeRight <= arrowLeft + .25 && arrowRight <= afterLeft + .25, "The actual separating arrow stays between non-overlapping before and after values");
                    const last = after[after.length - 1];
                    verify(last.mapToItem(bar, last.width, 0).x <= bar.width, "The final metric glyph stays inside the status bar");
                }
            }
        }
    }
}
