// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtTest
import EasyApplication.Gui.Globals as EaGlobals
import EasyApplication.Gui.Style as EaStyle
import edi.app
import "UiInteraction.js" as Ui

Item {
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
            verify(Session.openExample("pd-neut-cwl_lbco-hrpt_start-2"), Session.lastError);
            const fit = Session.project.fit;
            tryCompare(Session.project, "calculating", false, 10000);
            verify(fit.available);
            fit.start();
            tryVerify(() => !fit.running && fit.outcome !== "", 20000, "A real fit publishes its result before baseline checks");
            verify(fit.outcome !== "failed", fit.status);
            const values = fit.goodnessOfFit.split(" → ");
            compare(values.length, 2, "The fixture supplies actual before and after values");
            verify(values.every(value => value.trim() !== "" && Number.isFinite(Number(value))));
            const bar = createTemporaryObject(barComponent, parent);
            verify(bar !== null);
            let first = null;
            let second = null;
            let arrow = null;
            tryVerify(() => {
                first = Ui.find(bar, "statusBar.fit.valuePart.0");
                second = Ui.find(bar, "statusBar.fit.valuePart.1");
                arrow = Ui.find(bar, "statusBar.fit.changeArrow");
                return first !== null && second !== null && arrow !== null;
            });
            verify(first.text.endsWith(values[0]) && first.text.includes("χ²"));
            compare(second.text, values[1]);
            compare(arrow.text, "→");
            compare(arrow.font.family, EaStyle.Fonts.encodeSansRegular.name);
            compare(arrow.font.bold, false);
            compare(first.font.family, second.font.family);
            compare(first.font.pixelSize, second.font.pixelSize);
            for (const theme of [EaStyle.Colors.Themes.LightTheme, EaStyle.Colors.Themes.DarkTheme]) {
                EaStyle.Colors.theme = theme;
                for (const width of [900, 1300]) {
                    bar.width = width;
                    verify(waitForPolish(bar));
                    verify(waitForRendering(bar));
                    const firstBaseline = first.mapToItem(bar, 0, first.baselineOffset).y;
                    const secondBaseline = second.mapToItem(bar, 0, second.baselineOffset).y;
                    verify(Math.abs(firstBaseline - secondBaseline) < 0.25, "Rendered before/after number baselines coincide");
                    compare(arrow.color, first.color);
                    compare(second.color, first.color);
                    compare(first.color, EaStyle.Colors.themeForeground);
                    const firstRight = first.mapToItem(bar, first.width, 0).x;
                    const arrowLeft = arrow.mapToItem(bar, 0, 0).x;
                    const arrowRight = arrow.mapToItem(bar, arrow.width, 0).x;
                    const secondLeft = second.mapToItem(bar, 0, 0).x;
                    verify(firstRight < arrowLeft && arrowRight < secondLeft, "The separate arrow stays between the two values");
                    verify(second.mapToItem(bar, second.width, 0).x <= bar.width, "The final value stays within the status bar");
                }
            }
        }
    }
}
