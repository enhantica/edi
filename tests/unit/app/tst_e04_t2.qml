import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui
import "E04Review.js" as Review

TestCase {
    id: test
    name: "E04T2OwnerReview"
    when: windowShown
    property var appWindow
    property var oracle
    // Independent gui-components Colors.qml light/dark token pairs; aliases collapse.
    readonly property var textPairs: [
        ["#333333", "#eeeeee"], ["#aaaaaa", "#888888"], ["#bbbbbb", "#666666"],
        ["#222222", "#eeeeee"], ["#444444", "#cccccc"], ["#777777", "#888888"],
        ["#999999", "#666666"], ["#00a3e3", "#4ec1ef"], ["#8ad6ed", "#4d9dbd"],
        ["#ff5722", "#ffab91"], ["#39abdf", "#81d4fa"], ["#7aaa42", "#c5e1a5"],
        ["#666666", "#222222"], ["#ff9800", "#ffcc80"],
        //  idea 12: gui-components v0.9.1 models and chartForegroundsExtra.
        ["#009688", "#80cbc4"], ["#e91e63", "#f48fb1"],
        ["#4caf50", "#a5d6a7"], ["#03a9f4", "#81d4fa"], ["#795548", "#bcaaa4"]
    ]
    readonly property var fonts: ["PT Sans", "PT Mono", "Noto Sans", "Noto Sans Mono", "Baloo 2", "Font Awesome 5 Free"]
    Component { id: application; Main {} }
    Component { id: textWitness; Text { text: "theme witness"; color: Style.Colors.themeForeground } }
    Component { id: plainFields; Column { TextField { text: "1" } } }
    Component { id: tableWitness; ListView {
        width: 200; height: 100; model: ["witness"]
        header: Text { text: "label" }
        delegate: Text { required property string modelData; text: modelData }
    } }
    Component { id: paneWitness; Flickable {
        width: 160; height: 80; contentWidth: 160; contentHeight: 400; clip: true
    } }
    Component { id: groupWitness; Item {
        width: 140; height: 48; objectName: "group.peak"
        property string title: "Peak"
        property bool collapsible: true
        property bool collapsed: true
        property alias titleArea: header
        property alias contentItem: body
        Item { id: header; width: 140; height: 24; visible: parent.title !== "" }
        Item { id: body; y: 24; width: 140; height: 24 }
    } }

    function init() {
        failOnWarning(/.*/);
        oracle = JSON.parse(Probe.readFile("tests/fixtures/e04_t2/loops.json"));
        appWindow = application.createObject(null);
        verify(appWindow !== null, ": acceptance runs the real application window");
        verify(waitForRendering(appWindow.contentItem), ": application renders before inspection");
    }
    function cleanup() {
        Session.closeProject();
        verify(waitForRendering(appWindow.contentItem), ": pending layouts settle before destruction");
        Style.Colors.theme = Style.Colors.LightTheme;
        appWindow.destroy();
    }
    function click(name) {
        const item = Ui.control(Probe, appWindow, name);
        if (item && item.checked === true) return;
        Ui.click(test, Probe, appWindow, name);
    }
    function open(path) {
        Session.closeProject();
        Session.openProject(Probe.repoUrl(path || "tests/fixtures/e04_t1/editable-project"));
        verify(Session.hasProject, ": frozen project opens: " + Session.lastError);
        //  ideas 24/25 replace the automatic banner with the central dialog.
        verify(findChild(appWindow, "warning.banner") === null,
               " idea 24: project loading never creates the retired warning toast");
        const messages = findChild(appWindow, "warnings");
        verify(messages !== null && !messages.opened,
               " idea 24: loading leaves the Messages dialog closed until requested");
    }
    function pane(page, tier) {
        click("appBar.tab." + page);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1,
                  2000, ": workflow page reaches the main viewport before sidebar input");
        const tab = Ui.control(Probe, appWindow, "sideBar.tab." + tier);
        if (tab && !tab.checked) {
            click("sideBar.tab." + tier);
            verify(waitForRendering(appWindow.contentItem), ": sidebar transition starts rendering");
            tryVerify(() => !Ui.moving(Ui.page(appWindow)), 2000,
                      ": sidebar transition settles before category discovery");
        }
        verify(waitForPolish(appWindow, 2000), ": sidebar content layout is polished");
        tryVerify(() => Review.descendants(Ui.page(appWindow)).filter(item =>
            item.visible && item.interactive === false && item.count === 3 && item.currentItem)
            .every(view => Math.abs(view.currentItem.mapToItem(view, 0, 0).x) < 0.1),
            2000, ": selected sidebar pane reaches its final viewport position");
    }
    function group(name) {
        const found = Review.findGroup(Ui.page(appWindow), "group." + name);
        verify(found !== null, ": .edi category has a rendered group: " + name);
        Ui.scrollIntoView(Ui.target(found));
        Ui.expandGroup(test, Probe, appWindow, "group." + name);
        compare(Ui.control(Probe, appWindow, "group." + name), found,
                ": discovery and real expansion inspect the same active-pane group");
        return found;
    }
    function test_cutoff_in_extras_peak() {
        open(); pane("experiment", "basic");
        const basic = group("peak");
        verify(Review.find(basic, "peak.cutoff_fwhm") === null,
               "note 5: Basic peak does not display cutoff_fwhm");
        pane("experiment", "extras");
        const extra = group("peak");
        const cutoff = Review.find(extra, "peak.cutoff_fwhm");
        verify(cutoff !== null && !cutoff.readOnly, "note 5: Extras peak exposes editable cutoff_fwhm");
    }
    function test_analysis_groups_fixed_and_untitled_data() {
        return [{tag: "parameters", group: "parameters"}, {tag: "fitting", group: "fitting"}];
    }
    function test_analysis_groups_fixed_and_untitled(data) {
        open(); pane("analysis", "basic");
        const box = Review.findGroup(Ui.page(appWindow), "group." + data.group);
        verify(box !== null, "note 8: Analysis retains the requested group content");
        compare(box.title, "", "note 8: original Analysis groups have no title");
        compare(box.collapsible, false, "note 8: original Analysis groups cannot fold");
        compare(box.collapsed, false, "note 8: Analysis content stays expanded");
    }
    function test_slider_limit_boxes() {
        open(); pane("analysis", "basic");
        const box = group("parameters");
        const rows = Probe.rows(Session.project.parameters);
        const parameter = rows.find(row => row.path === "structure.cell.length_a").parameter;
        ["lengthA", "lengthB", "lengthC"].forEach(name => {
            const cell = Session.project.currentStructure.cell[name];
            box.selected = cell;
            const control = Review.find(box, "parameters.slider");
            tryVerify(() => Math.abs(control.from - (cell.value - .05)) < 1e-10 && Math.abs(control.to - (cell.value + .05)) < 1e-10,
                      2000, "all three lattice constants use the declared half width of 0.05 A");
        });
        const angle = Session.project.currentStructure.cell.angleAlpha;
        box.selected = angle;
        const angleSlider = Review.find(box, "parameters.slider");
        tryVerify(() => Math.abs(angleSlider.from - angle.value / 2) < 1e-10 && Math.abs(angleSlider.to - angle.value * 1.5) < 1e-10,
                  2000, "cell angles retain their prior half-magnitude slider range");
        box.selected = parameter;
        const slider = Review.find(box, "parameters.slider");
        verify(slider !== null, "note 9: selected parameter has its real slider");
        const fields = Review.descendants(slider.parent).filter(item =>
            item !== slider && item.visible && typeof item.text === "string" && typeof item.getText === "function");
        compare(fields.length, 2, "note 9: slider has left and right native text boxes");
        const ordered = fields.sort((a,b) => a.x - b.x);
        verify(ordered[0].x < slider.x && ordered[1].x >= slider.x + slider.width,
               "note 9: limit boxes flank the slider");
        [1.2866603586797143, 2.718281828459045].forEach(value => {
            parameter.value = value;
            tryVerify(() => Math.abs(slider.from - (value - .05)) < 1e-10 && Math.abs(slider.to - (value + .05)) < 1e-10,
                      2000, "lattice slider endpoints follow the current value plus or minus 0.05 A");
            compare(Number(ordered[0].text), Number(slider.from.toPrecision(3)),
                    "notes 9/14: left box displays the minimum at reference precision");
            compare(Number(ordered[1].text), Number(slider.to.toPrecision(3)),
                    "notes 9/14: right box displays the maximum at reference precision");
            compare(parameter.value, value, "note 14: rounded slider labels preserve the selected stored value");
        });
    }
    function test_effective_tolerance_and_no_calculator() {
        open(); pane("analysis", "extras");
        verify(!Ui.groupNames(Ui.page(appWindow)).includes("calculator"),
               "note 11: fixture analysis.edi has fitting_mode/minimizer/joint_fit, no calculator category");
        const box = group("minimizer");
        const field = Review.find(box, "minimizer.chiSquareTolerance");
        verify(field !== null && field.text.trim() !== "", "note 10: tolerance displays the effective default");
        // Producer include/crysta/fit.hpp kDefaultChiSquareTolerance; no value in this fixture.
        compare(Number(field.text), 1e-6, "note 10: absent override uses independent crysta default 1e-6");
    }
    function test_explicit_tolerance_override() {
        open("docs/user/cli/pd-neut-tof_si-sepd_start-2/project");
        pane("analysis", "extras");
        const field = Review.find(group("minimizer"), "minimizer.chiSquareTolerance");
        verify(field !== null, "note 10: explicit project tolerance has a rendered field");
        // This committed analysis.edi declares 1e-4: it is an override, not the producer default.
        compare(Number(field.text), 1e-4, "note 10: declared project override replaces the producer default");
        Session.project.analysis.chiSquareTolerance = 0.0025;
        tryCompare(field, "text", "0.0025", 2000, "note 10: explicit nondefault tolerance is displayed");
    }
    function test_round_display_preserve_storage() {
        open(); pane("structure", "basic");
        const box = group("cell");
        const field = Review.find(box, "cell.length_a");
        verify(field !== null, "note 14: production parameter field is exposed");
        const value = 1.2866603586797143;
        field.item.value = value;
        tryCompare(field, "text", "1.29", 2000, "note 14: default display uses the reference three significant digits");
        verify(field.text.length < String(value).length, "note 14: display rounds the long fractional value");
        compare(field.item.value, value, "note 14: displaying a rounded value preserves stored precision");
        field.forceActiveFocus();
        keyClick(Qt.Key_Tab);
        compare(field.item.value, value, "note 14: leaving an unedited rounded field preserves stored precision");
    }
    function test_plain_value_rounding_preserves_storage() {
        open(); pane("analysis", "extras");
        const box = group("minimizer");
        const field = Review.find(box, "minimizer.chiSquareTolerance");
        const value = 0.0025646436261;
        Session.project.analysis.chiSquareTolerance = value;
        tryCompare(field, "text", "0.00256", 2000,
                   "note 14: plain numeric field uses the reference three significant digits");
        compare(Session.project.analysis.chiSquareTolerance, value,
                "note 14: plain-field display does not round the stored value");
        field.forceActiveFocus(); keyClick(Qt.Key_Tab);
        compare(Session.project.analysis.chiSquareTolerance, value,
                "note 14: leaving an unedited plain field preserves full precision");
    }
    function test_loop_tables_data() {
        // Parsed file data, never Session.*.categories. Include every project/block loop.
        return JSON.parse(Probe.readFile("tests/fixtures/e04_t2/loops.json")).loops;
    }
    function test_loop_tables(data) {
        open(data.project);
        if (["structure", "experiment"].includes(data.page)) {
            const model = Session.project[data.page === "structure" ? "structures" : "experiments"];
            const index = Probe.rows(model).findIndex(row => row.name === data.block);
            verify(index >= 0, "gate 3: fixture block is selectable by its file identity");
            Session.project[data.page === "structure" ? "currentStructureIndex" : "currentExperimentIndex"] = index;
        }
        let box = null;
        for (const tier of ["basic", "extras"]) {
            pane(data.page, tier);
            if (Ui.groupNames(Ui.page(appWindow)).includes(data.category)) {
                box = group(data.category); break;
            }
        }
        verify(box !== null, "gate 3: each fixture loop category appears in Basic or Extras: " + data.category);
        compare(Review.tableProblem(box, data.rows), "", "gate 3: loop renders as a populated table: " + data.tag);
    }
    function test_theme_system_seam() {
        verify(Probe.writable(AppState, "platformColorScheme"), "note 1: app exposes its platform appearance seam");
        Style.Colors.theme = Style.Colors.SystemTheme;
        AppState.platformColorScheme = Qt.ColorScheme.Dark;
        tryCompare(Style.Colors, "isDarkPalette", true, 2000, "note 1: system follows injected dark appearance");
        AppState.platformColorScheme = Qt.ColorScheme.Light;
        tryCompare(Style.Colors, "isDarkPalette", false, 2000, "note 1: system follows live light appearance");
        Style.Colors.theme = Style.Colors.DarkTheme;
        compare(Style.Colors.isDarkPalette, true, "note 1: explicit dark overrides light system appearance");
        Style.Colors.theme = Style.Colors.LightTheme;
    }
    function test_every_text_theme_and_font_data() {
        let rows = [];
        ["project", "structure", "experiment", "analysis", "report"].forEach(page =>
            (page === "project" || page === "report" ? ["basic", "text"] : ["basic", "extras", "text"]).forEach(tier => rows.push({tag: page + "-" + tier, page: page, tier: tier})));
        return rows;
    }
    function fixedAtomColor(item) {
        // Independent EasyDiffractionBeta v0.9.9 easyDiffractionApp/Logic/Tables.py.
        // Only the four elements declared by editable-project/structures/lbco.edi.
        const elements = {"La": "#70d4ff", "Ba": "#00c900", "Co": "#f090a0", "O": "#ff0d0d"};
        const color = String(item.color).toLowerCase();
        if (item.font.family === "Font Awesome 5 Free" && item.text === "atom")
            return Object.values(elements).includes(color) ? color : "";
        return elements[item.text] === color ? color : "";
    }
    function allowedLight(item) {
        if (fixedAtomColor(item) !== "") return true;
        return (item.text === "\uf00c" && item.font.family === "Font Awesome 5 Free" && String(item.color) === "#ffffff") ||
            textPairs.some(pair => String(item.color) === pair[0]);
    }
    function allowedPair(item, light) {
        if (fixedAtomColor(item) !== "") return fixedAtomColor(item) === light;
        // Upstream CheckIndicator.qml: the check glyph is white in both palettes.
        return (item.text === "\uf00c" && item.font.family === "Font Awesome 5 Free" &&
                String(item.color) === "#ffffff" && light === "#ffffff") ||
            Review.themeProblem(light, item.color, textPairs) === "";
    }
    function textScene() {
        return Review.textItems(Ui.windowRoot(appWindow)).map(item => {
            const point = item.mapToItem(appWindow.contentItem, 0, 0);
            return {item: item, key: JSON.stringify([item.text, item.font.family, item.font.pixelSize,
                item.font.bold, item.font.styleName, Math.round(point.x), Math.round(point.y)])};
        }).sort((a,b) => a.key.localeCompare(b.key));
    }
    function sceneMatches(light, dark) {
        //  IconLine recreates its delegates when palette segments change.
        // Pair fresh renderers by unchanged text/font/position, retaining every
        // renderer and exact token checks; never dereference deleted QObjects.
        const current = textScene();
        return current.length === light.length && current.every((entry, index) =>
            entry.key === light[index].key && (dark ? allowedPair(entry.item, light[index].color) :
                String(entry.item.color) === light[index].color));
    }
    function test_every_text_theme_and_font(data) {
        open(); pane(data.page, data.tier);
        // Expand all groups so hidden default-collapsed text cannot evade the sweep.
        Review.descendants(Ui.page(appWindow)).forEach(item => {
            if (item.visible && item.objectName.startsWith("group.") && item.collapsed !== undefined)
                item.collapsed = false;
        });
        Style.Colors.theme = Style.Colors.LightTheme;
        tryCompare(Style.Colors, "themeForeground", "#333333", 2000, "note 2: light palette reaches independent token");
        const items = Review.textItems(Ui.windowRoot(appWindow));
        verify(items.length > 0, "notes 2/17: the text sweep cannot be empty");
        // Theme animations are bounded by convergence, never a blind delay.
        tryVerify(() => items.every(allowedLight),
                  4000, "note 2: every rendered text colour is a light-theme token: " + items.filter(item => !allowedLight(item)).map(item => item.text.slice(0,30) + "=" + item.color).join(";"));
        const light = textScene().map(entry => ({key: entry.key, color: String(entry.item.color)}));
        items.forEach(item => verify(fonts.includes(item.font.family),
            "note 17: every native text renderer uses a bundled family: " + item.font.family));
        Style.Colors.theme = Style.Colors.DarkTheme;
        tryVerify(() => sceneMatches(light, true),
                  2000, "note 2: every native text renderer, including status bar, follows its dark token");
        if (Probe.writable(AppState, "platformColorScheme")) {
            Style.Colors.theme = Style.Colors.SystemTheme;
            AppState.platformColorScheme = Qt.ColorScheme.Light;
            tryVerify(() => sceneMatches(light, false),
                      3000, "note 1: every text item follows system light through the app seam");
            AppState.platformColorScheme = Qt.ColorScheme.Dark;
            tryVerify(() => sceneMatches(light, true),
                      3000, "note 1: every text item follows a live system dark transition");
        } else {
            fail("note 1: theme text sweep requires the app platform seam");
        }
        Style.Colors.theme = Style.Colors.LightTheme;
    }
    function test_full_width_append() {
        open(); pane("structure", "extras");
        const scattering = group("scattering_length");
        const append = Review.find(scattering, "scatteringLengths.append");
        verify(append !== null, "note 3: scattering-length append exists");
        fuzzyCompare(append.width, Style.Sizes.sideBarContentWidth, 1,
                     "note 3: append spans the full content width as in the original QML");
    }
    function test_full_width_cw_instrument() {
        open(); pane("experiment", "basic");
        const instrument = group("instrument");
        const fields = Review.descendants(instrument).filter(item =>
            item.visible && item.objectName.startsWith("instrument.") && typeof item.text === "string");
        verify(fields.length >= 2, "note 4: CW instrument exposes every available parameter field");
        const right = Math.max.apply(null, fields.map(item => item.mapToItem(instrument, item.width, 0).x));
        const left = Math.min.apply(null, fields.map(item => item.mapToItem(instrument, 0, 0).x));
        fuzzyCompare(right - left, Style.Sizes.sideBarContentWidth, 1,
                     "note 4: CW instrument fields fill the row for both two- and four-field dictionaries");
        compare(fields.length, Probe.rows(Session.project.currentExperiment.instrument).length,
                "note 4: all available CW parameters receive a field, including later  additions");
    }
    function test_text_tabs_selector_and_alignment_data() {
        return ["project", "structure", "experiment", "analysis", "report"].map(page => ({tag: page, page: page}));
    }
    function test_text_tabs_selector_and_alignment(data) {
        open(); pane(data.page, "text");
        const view = Ui.control(Probe, appWindow, "text.view");
        verify(view !== null, "note 12: each Text tab renders its block text");
        const selector = Ui.control(Probe, appWindow, "sideBar.blocks");
        if (!["structure", "experiment"].includes(data.page)) {
            verify(selector === null,
                   " idea 9: singleton Project, Analysis and Report blocks need no selector");
            return;
        }
        verify(selector !== null, " idea 9: Structure and Experiment share their selector across tabs");
        verify(selector.count >= 1 && selector.currentIndex >= 0 && selector.currentText.trim() !== "",
               "note 12: block selector displays a selected block");
        const top = view.mapToItem(selector, 0, 0);
        verify(top.y >= selector.height, "note 12: aligned text begins below the block selector");
        verify(top.x >= 0 && top.x <= Style.Sizes.fontPixelSize * 2,
               "note 12: text inset aligns with the selector's content column");
    }
    function test_atom_color_exception_does_not_admit_ordinary_text() {
        const ordinary = createTemporaryObject(textWitness, appWindow.contentItem,
                                              {text: "ordinary theme text", color: "#70d4ff"});
        verify(!allowedLight(ordinary), "idea 12: a fixed atom colour cannot bypass theme checks for ordinary text");
    }
    function test_bundled_fonts_data() { return test_every_text_theme_and_font_data(); }
    function test_bundled_fonts(data) {
        open(); pane(data.page, data.tier);
        const items = Review.textItems(Ui.windowRoot(appWindow));
        verify(items.length > 0, "note 17: bundled-font sweep observes native text");
        items.forEach(item => verify(fonts.includes(item.font.family),
            "note 17: each text font is bundled: " + item.font.family));
    }
    function test_observer_escapes() {
        const viewport = createTemporaryObject(paneWitness, appWindow.contentItem);
        const inactive = createTemporaryObject(groupWitness, viewport.contentItem, {x: -200});
        const active = createTemporaryObject(groupWitness, viewport.contentItem, {y: 240});
        compare(Review.findGroup(viewport, "group.peak"), active,
                "observer selection: a visible offscreen duplicate cannot replace the active below-fold group");
        compare(Ui.find(viewport, "group.peak"), null,
                "observer selection: discovery does not pretend a below-fold header is exposed for input");
        Ui.scrollIntoView(Ui.target(active));
        verify(viewport.contentY > 0,
               "observer selection: the active below-fold group scrolls its enclosing viewport");
        compare(Ui.find(viewport, "group.peak"), active,
                "observer selection: the discovered group becomes the actual exposed input target");
        active.x = 200; inactive.x = 0;
        compare(Review.findGroup(viewport, "group.peak"), inactive,
                "observer selection: switching the horizontal pane changes the selected duplicate");
        inactive.visible = false;
        compare(Review.findGroup(viewport, "group.peak"), null,
                "observer selection: an absent active group cannot fall back to an offscreen duplicate");
        active.x = 0; active.title = ""; active.collapsible = false; active.collapsed = false;
        compare(Review.findGroup(viewport, "group.peak"), active,
                "note 8: untitled fixed-open groups are discovered through active-pane content");
        const fields = createTemporaryObject(plainFields, appWindow.contentItem);
        const table = createTemporaryObject(tableWitness, appWindow.contentItem);
        verify(waitForRendering(appWindow.contentItem), "gate escapes: native controls render");
        compare(Review.tableProblem(table, 1), "", "gate escapes: a real populated table is admitted");
        verify(Review.tableProblem(fields, 1) !== "", "gate escapes: loop replaced by fields is rejected");
        Style.Colors.theme = Style.Colors.LightTheme;
        const witness = createTemporaryObject(textWitness, appWindow.contentItem);
        const light = String(witness.color);
        Style.Colors.theme = Style.Colors.DarkTheme;
        compare(Review.themeProblem(light, witness.color, textPairs), "", "gate escapes: bound native text pair is admitted");
        witness.color = light;
        verify(Review.themeProblem(light, witness.color, textPairs) !== "",
               "gate escapes: a native text item with hard-coded colour is rejected by the same observer");
    }
}
