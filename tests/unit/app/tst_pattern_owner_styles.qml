import QtQuick
import QtQuick.Window
import QtTest
import QtGraphs
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render
import "UiInteraction.js" as Ui
import "ApprovedPalette.js" as Approved
import "../../fixtures/pattern_styles/input.js" as Input

Rectangle {
    id: surface
    width: 1200
    height: 850
    color: "white"
    Component {
        id: chartFactory
        PatternChart {
            width: 1100
            height: 760
            settingsPage: "pattern"
            shown: true
        }
    }
    Component {
        id: appFactory
        Main {
            width: Math.min(1400, SettingsProof.screen().width)
            height: Math.min(1000, SettingsProof.screen().height - 80)
            visible: true
        }
    }
    TestCase {
        id: test
        name: "PatternOwnerStyles"
        when: windowShown
        property var chart
        property var app
        readonly property var tokens: ["band", "line", "points", "linePoints"]
        readonly property var labels: ["band", "line", "points", "line + points"]
        FontMetrics {
            id: metrics
        }
        function cleanup() {
            if (chart)
                chart.destroy();
            chart = null;
            if (app) {
                app.close();
                app.destroy();
            }
            app = null;
            Session.closeProject();
        }
        function open(balanced = false) {
            Preferences.resetToDefaults();
            Preferences.patternYScale = "linear";
            const root = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/loop_parameter_ids/line-segment"));
            Input.prepare(SettingsProof, root, balanced);
            verify(Session.openProject(root), "The style actor opens its independent zero-scale, six-count-background input: " + Session.lastError);
            tryCompare(Session.project, "calculating", false, 8000, "The real style fixture calculation finishes before observing its chart");
            const rows = Probe.rows(Session.project.currentExperiment.pattern);
            verify(rows.length === 3 && rows.every(row => Math.abs(row.intensityCalc - 6) < 1e-10), "The independent zero-structure-scale invariant gives exactly six calculated counts at each measured point");
            return root;
        }
        function standalone() {
            chart = chartFactory.createObject(surface, {
                experiment: Session.project.currentExperiment,
                axisProject: Session.project
            });
            verify(chart !== null && waitForPolish(chart) && waitForRendering(chart), "The actor renders the actual production Pattern chart");
            return chart;
        }
        function selector(root) {
            const controls = Render.descendants(root).filter(item => item.objectName === "chart.toolbar.measuredStyle");
            compare(controls.length, 1, "The measured-data style is one actual combobox");
            const item = controls[0];
            verify(item.visible && item.enabled && item.count === 4, "The actual measured-data combobox offers all four choices");
            compare(Array.from({
                length: item.count
            }, (_, i) => item.textAt(i)).join(","), labels.join(","), "The measured-style items are band, line, points, line + points in that order");
            return item;
        }
        function click(item) {
            if (app) {
                tryVerify(() => !Ui.moving(app.contentItem), 2000, "Style input waits for the actual application transition to finish");
                verify(waitForPolish(app), "Style input follows a completed application layout");
                app.update();
                verify(waitForRendering(app.contentItem), "The actual style target has a completed application frame");
            }
            const at = Ui.clickPoint(item);
            verify(at !== null && item.enabled, "A style interaction reaches an exposed enabled production control");
            mouseClick(item, at.x, at.y);
            surface.Window.window.update();
        }
        function select(root, token) {
            const target = selector(root), index = tokens.indexOf(token);
            click(target);
            keyClick(Qt.Key_Home);
            for (let i = 0; i < index; ++i)
                keyClick(Qt.Key_Down);
            keyClick(Qt.Key_Return);
            tryCompare(target, "currentIndex", index, 1000, "Actual combobox input selects the requested measured-data style");
            compare(target.displayText, "meas: " + labels[index], "The closed measured-style box uses the neighbouring selectors' short prefix form");
            verify(waitForRendering(root), "The selected measured style reaches a completed actual chart frame");
        }
        function series(root, name) {
            const item = Render.series(root).find(item => item.objectName === "chart.series." + name);
            verify(item !== undefined, "The style witness reaches its actual " + name + " drawing series");
            return item;
        }
        function points(item) {
            return Array.from({
                length: item.count
            }, (_, index) => item.at(index));
        }
        function edges(root, name, expected) {
            const values = points(series(root, name));
            compare(values.length, 3, "A measured or residual band edge contains exactly the three independent samples");
            for (let i = 0; i < 3; ++i) {
                fuzzyCompare(values[i].x, [40, 52, 64][i], 1e-10, "Every uncertainty edge retains the independently declared measured x coordinate");
                fuzzyCompare(values[i].y, expected[i], 1e-10, "Every edge equals its independent measured or residual value plus or minus the declared s.u.");
            }
        }
        function rgb(hex) {
            return Qt.rgba(parseInt(hex.slice(1, 3), 16) / 255, parseInt(hex.slice(3, 5), 16) / 255, parseInt(hex.slice(5, 7), 16) / 255, 1);
        }
        function pixel(root, pane, x, y, dx = 0, dy = 0) {
            const view = findChild(root, "chart.view." + pane);
            verify(view !== null, "The pixel witness reaches its actual chart pane");
            const at = view.mapToItem(root, view.plotArea.x + (x - view.axisX.min) / (view.axisX.max - view.axisX.min) * view.plotArea.width, view.plotArea.y + (view.axisY.max - y) / (view.axisY.max - view.axisY.min) * view.plotArea.height);
            return grabImage(root).pixel(Math.round(at.x) + dx, Math.round(at.y) + dy);
        }
        function isInk(value, expected, bg) {
            let lower = 0, upper = 1;
            for (const c of ["r", "g", "b"]) {
                const span = expected[c] - bg[c];
                if (Math.abs(span) < 1e-12) {
                    if (Math.abs(value[c] - bg[c]) > 1 / 255)
                        return false;
                    continue;
                }
                const a = (value[c] - bg[c] - 1 / 255) / span, b = (value[c] - bg[c] + 1 / 255) / span;
                lower = Math.max(lower, Math.min(a, b));
                upper = Math.min(upper, Math.max(a, b));
            }
            return lower > 0 && lower <= upper && upper <= 1;
        }
        function nearInk(root, pane, x, y, colour, dx = 0, dy = 0) {
            let result = false;
            for (let offset = -1; offset <= 1; ++offset)
                for (let column = -1; column <= 1; ++column)
                    result = result || isInk(pixel(root, pane, x, y, dx + column, dy + offset), colour, root.colors.chartBackground);
            return result;
        }
        function test_default_and_group_order() {
            open();
            standalone();
            const group = selector(chart);
            compare(group.currentIndex, 0, "A fresh profile defaults to the uncertainty band style");
            metrics.font = group.font;
            const longest = Math.ceil(Math.max(...labels.concat(labels.map(text => "meas: " + text)).map(text => metrics.advanceWidth(text))));
            const label = group.contentItemLabel;
            verify(label !== undefined, "The actual combobox exposes its rendered text padding and arrow clearance");
            const clearance = label.leftPadding + label.rightPadding + group.leftPadding + group.rightPadding;
            verify(Math.abs(group.width - longest - clearance) <= 1, "The measured-style combobox fits its own longest item with normal padding and arrow clearance" + "; selector=" + group.objectName + " readWidth=" + group.width + " expected=" + (longest + clearance) + " maximumTextWidth=" + longest + " clearanceSum=" + clearance + " paddings=" + JSON.stringify({
                labelLeft: label.leftPadding,
                labelRight: label.rightPadding,
                controlLeft: group.leftPadding,
                controlRight: group.rightPadding
            }));
            const axes = [findChild(chart, "chart.toolbar.xaxis"), findChild(chart, "chart.toolbar.yscale")], legend = findChild(chart, "chart.toolbar.legend");
            verify(axes.every(item => item !== null) && legend !== null, "Group placement is measured against the actual axis selectors and legend button");
            const left = group.mapToItem(chart, 0, 0).x, right = group.mapToItem(chart, group.width, 0).x;
            verify(axes.every(item => item.mapToItem(chart, item.width, 0).x <= left) && right <= legend.mapToItem(chart, 0, 0).x, "The measured-data group lies between the left axis selectors and Show legend");
        }
        function test_each_mode_marks_data() {
            const rows = [];
            for (const token of tokens)
                for (const dark of [false, true])
                    rows.push({
                        tag: token + (dark ? "-dark" : "-light"),
                        token,
                        dark
                    });
            return rows;
        }
        function test_each_mode_marks(data) {
            open(data.token === "band");
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            standalone();
            select(chart, data.token);
            const measured = rgb(Approved.colours(SettingsProof, "earth", "measured", 1, data.dark)[0]);
            const line = series(chart, "meas"), layer = findChild(chart, "chart.measured");
            verify(layer !== null, "The measured marker/error-bar layer is independently observable");
            const hasLine = data.token === "line" || data.token === "linePoints", hasPoints = data.token === "points" || data.token === "linePoints";
            compare(nearInk(chart, "main", 46, data.token === "band" ? 7.5 : 26.5, measured), hasLine || data.token === "band", "The line joins independent samples exactly when the selected style draws a line or band");
            compare(layer.visible && layer.count > 0, hasPoints, "Markers and uncertainty bars are present exactly for Points and Line-and-points");
            if (data.token !== "band")
                tryVerify(() => nearInk(chart, "main", 52, 31.5, measured) === hasPoints, 1500, "The independent middle sample has error-bar ink between its centre and lower s.u. edge only in the two marker styles; the band interior is checked separately");
            if (hasPoints) {
                verify(nearInk(chart, "main", 40, 18, measured) && nearInk(chart, "main", 40, 22, measured), "The actual marker styles draw both independent error-bar ends");
            }
            if (data.token === "band") {
                edges(chart, "meas.band.top", [7, 10, 10]);
                edges(chart, "meas.band.bottom", [3, 4, 2]);
                edges(chart, "resid.band.top", [1, 4, 4]);
                edges(chart, "resid.band.bottom", [-3, -2, -4]);
                for (const [name, pane, y] of [["meas.band", "main", 7.5], ["resid.band", "residual", .75]]) {
                    const area = series(chart, name);
                    verify(area.visible && area.color.a > 0 && area.color.a < 1, "Measured and residual uncertainty bands have actual semi-transparent fills" + "; series=" + name + " expected=visible and 0<alpha<1 readVisible=" + area.visible + " readColour=" + area.color + " readAlpha=" + area.color.a);
                    const view = findChild(chart, "chart.view." + pane);
                    verify(view.axisX.min < 46 && 46 < view.axisX.max && view.axisY.min < y && y < view.axisY.max, "The independent band interior sample lies inside its actual pane");
                    const value = pixel(chart, pane, 46, y), colour = area.color, bg = chart.colors.chartBackground;
                    verify(["r", "g", "b"].every(c => Math.abs(value[c] - (colour[c] * colour.a + bg[c] * (1 - colour.a))) <= 2 / 255), "Rendered band interior uses the independent declared area with a semi-transparent colour over the plot background" + "; series=" + name + " pane=" + pane + " dataPoint=" + JSON.stringify([46, y]) + " declaredAlpha=" + colour.a + " read=" + value + " readAlpha=" + value.a + " colour=" + colour + " background=" + bg + " expectedRGB=" + JSON.stringify(["r", "g", "b"].map(c => colour[c] * colour.a + bg[c] * (1 - colour.a))) + " inferredCoverageRGB=" + JSON.stringify(["r", "g", "b"].map(c => colour[c] === bg[c] ? null : (value[c] - bg[c]) / (colour[c] - bg[c]))));
                }
                verify(!line.visible || points(line).every(point => !isFinite(point.x)), "Band style removes the ordinary central measured line");
            } else {
                verify(hasLine ? line.visible && points(line).length === 3 : !line.visible || points(line).every(point => !isFinite(point.x)), "The selected style draws or removes the full measured joining line");
                verify(["meas.band", "resid.band"].every(name => {
                    const area = series(chart, name);
                    return !area.visible || [area.upperSeries, area.lowerSeries].every(edge => points(edge).every(point => !isFinite(point.x) || !isFinite(point.y)));
                }), "Non-band styles remove all drawable points from both measured and residual band fills");
            }
        }
        function showPage(name) {
            Ui.click(test, Probe, app, "appBar.tab." + name);
            let page;
            tryVerify(() => {
                page = Render.descendants(app.contentItem).find(item => item.pageName === name && item.current);
                return page !== undefined;
            }, 2000, "Actual app input opens the requested Pattern page");
            tryVerify(() => !Ui.moving(app.contentItem), 2000, "Page navigation finishes before selecting its Pattern tab");
            verify(waitForPolish(app), "The actual application completes Pattern-page layout");
            app.update();
            verify(waitForRendering(app.contentItem), "The actual page has a completed frame before Pattern-tab input");
            const tab = Array.from(page.mainTabs).find(item => item.text === "Pattern");
            verify(tab !== undefined && tab.enabled, "Every pattern owner has its actual enabled Pattern tab");
            if (!tab.checked)
                click(tab);
            tryVerify(() => !Ui.moving(app.contentItem), 2000, "The actual Pattern tab finishes moving before a style observation");
            const result = Render.descendants(page).filter(item => item.objectName === "chart" && item.shown && item.visible && item.report === null);
            compare(result.length, 1, "The current page supplies exactly one shown Pattern chart");
            app.update();
            verify(waitForRendering(result[0]), "The current Pattern chart has a real completed frame");
            return result[0];
        }
        function test_choice_shared_and_remembered_data() {
            const rows = [];
            for (const origin of ["structure", "experiment", "analysis"])
                for (const token of tokens)
                    rows.push({
                        tag: origin + "-" + token,
                        origin,
                        token
                    });
            return rows;
        }
        function test_choice_shared_and_remembered(data) {
            open();
            app = appFactory.createObject(null);
            verify(app !== null && app.visible, "The style-sharing actor opens the real application window");
            app.requestActivate();
            tryCompare(app, "active", true, 2000, "Style sharing uses real input in the active application window");
            select(showPage(data.origin), data.token);
            for (const page of ["structure", "experiment", "analysis"]) {
                const target = showPage(page);
                compare(selector(target).currentIndex, tokens.indexOf(data.token), "A measured-data choice from every origin is shared by every Pattern page");
            }
            const fresh = SettingsProof.restart('import QtQuick; import edi.app; QtObject { property string selected:Preferences.patternMeasuredStyle }');
            verify(!fresh.error, "A fresh production settings engine reads the saved measured-data choice");
            compare(fresh.selected, data.token, "Every actual measured-data style choice survives a fresh settings engine; all actual page selectors were checked above");
        }
        function test_background_and_legend_dashed_data() {
            const cases = [];
            for (const page of ["structure", "experiment", "analysis", "report"])
                for (const dark of [false, true])
                    cases.push({
                        tag: page + (dark ? "-dark" : "-light"),
                        page,
                        dark
                    });
            return cases;
        }
        function test_background_and_legend_dashed(data) {
            open();
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            let target;
            if (data.page === "report") {
                Session.project.report.active = true;
                tryVerify(() => Session.project.report.model.experiments && Session.project.report.model.experiments.length > 0, 3000, "The real report model contains its independently specified experiment");
                chart = chartFactory.createObject(surface, {
                    report: Session.project.report,
                    reportExperiment: Session.project.report.model.experiments[0].id
                });
                chart.colors.light = true;
                target = chart;
            } else {
                app = appFactory.createObject(null);
                verify(app !== null, "The dashed-background actor opens the real application");
                app.requestActivate();
                tryCompare(app, "active", true, 2000, "Background styling is observed through actual active pages");
                target = showPage(data.page);
                const legend = findChild(target, "chart.toolbar.legend");
                verify(legend !== null, "Every interactive Pattern page has its real legend control");
                if (!legend.checked)
                    click(legend);
            }
            verify(target !== null && waitForRendering(target), "Each background drawing has a completed actual frame");
            const background = series(target, "bkg");
            compare(background.strokeStyle, LineSeries.StrokeStyle.DashLine, "Every background series uses a real dashed stroke");
            verify(background.dashPattern.length >= 2 && background.dashPattern.every(value => value > 0), "The actual background dash pattern contains positive ink and gap lengths");
            const expected = Approved.reference(SettingsProof).schemes[0].palette[data.dark && data.page !== "report" ? "dark" : "light"].background;
            compare(String(background.color).toLowerCase(), expected.toLowerCase(), "Dashing preserves the independently approved background role colour");
            const legend = findChild(target, "chart.legend");
            if (data.page === "report" && legend !== null) {
                legend.visible = true;
                verify(waitForRendering(target), "The optional report legend sample is rendered for its style observation");
            }
            verify(legend !== null && legend.visible, "Each drawn background has its actual visible legend sample");
            const rows = Render.descendants(legend).filter(item => item.segments !== undefined && item.label !== undefined && /background|bkg/i.test(item.label));
            compare(rows.length, 1, "Exactly one actual background legend entry is available");
            const segment = rows[0].segments.find(item => item.mark !== undefined);
            verify(segment !== undefined && segment.mark === "dash", "The background legend sample is explicitly dashed like its actual series");
            const shapes = Render.descendants(rows[0]).filter(item => item.visible && item.color !== undefined && item.width > 1 && item.height <= 2 && String(item.color) === String(background.color));
            verify(shapes.length >= 2, "The background legend draws separated dash ink rather than only carrying a dash label");
            const capture = target.Window.window.contentItem;
            const rowImage = grabImage(capture);
            const bounds = shapes.map(item => ({
                        x: item.mapToItem(capture, 0, 0).x,
                        y: item.mapToItem(capture, 0, 0).y,
                        width: item.width,
                        height: item.height
                    })).sort((a, b) => a.x - b.x);
            const first = bounds[0], last = bounds[bounds.length - 1], sampleY = Math.floor(first.y + first.height / 2);
            const blank = rowImage.pixel(Math.round((first.x + first.width + last.x) / 2), sampleY);
            let painted = 0, gaps = 0;
            for (let x = Math.ceil(first.x); x < Math.floor(last.x + last.width); ++x) {
                const p = rowImage.pixel(x, sampleY);
                if ([-1, 0, 1].some(dy => isInk(rowImage.pixel(x, sampleY + dy), background.color, rowImage.pixel(Math.round((first.x + first.width + last.x) / 2), sampleY + dy))))
                    ++painted;
                else if (["r", "g", "b"].every(c => Math.abs(p[c] - blank[c]) <= 1 / 255))
                    ++gaps;
            }
            verify(painted > 0 && gaps > 0, "The actual background legend sample contains both antialiased dash ink and a visible gap: " + JSON.stringify({
                bounds,
                painted,
                gaps,
                blank,
                image: [rowImage.width, rowImage.height],
                sampleY,
                colour: background.color
            }));
            if (data.page !== "report") {
                const toggle = findChild(target, "chart.toolbar.structureCurves");
                verify(toggle !== null && toggle.enabled, "The same chart can display its structure outlines");
                if (!toggle.checked)
                    click(toggle);
                const outlines = Render.series(target).filter(item => String(item.objectName).startsWith("chart.series.structure.") && item.strokeStyle !== undefined);
                verify(outlines.length > 0, "The solid-outline witness reaches actual structure drawing series");
                verify(outlines.every(item => item.strokeStyle === LineSeries.StrokeStyle.SolidLine), "Structure fill outlines remain solid when the background becomes dashed");
            }
            const model = Session.project.report;
            model.active = true;
            tryVerify(() => model.model.pattern_styles !== undefined, 2000, "The report publishes its actual chart style table");
            const styles = model.model.pattern_styles;
            verify(styles.some(row => row.key === "bkg" && row.mark.split("+").includes("dash")), "The report background style carries the same dashed contract");
            verify(styles.filter(row => String(row.key).startsWith("structure.")).every(row => !row.mark.split("+").includes("dash")), "Report structure fill outlines preserve solid style tokens");
        }
    }
}
