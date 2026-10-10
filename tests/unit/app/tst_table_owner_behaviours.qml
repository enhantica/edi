// SPDX-License-Identifier: BSD-3-Clause
import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import EasyApplication.Gui.Style as Style
import EasyApplication.Gui.Elements as Elements
import EasyApplication.Gui.Globals as Globals
import "UiInteraction.js" as Ui
import "E04Review.js" as Review
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "TableOwnerBehaviours"
    when: windowShown
    property bool savedTooltips
    property var appWindow
    Component {
        id: application
        Main {}
    }
    Component {
        id: toolbar
        ChartToolbar {}
    }
    Component {
        id: standalone
        ParameterField {
            width: 220
            label: ""
        }
    }
    Component {
        id: selectorComponent
        BlockSelector {
            width: 800
        }
    }
    ListModel {
        id: selectorRows
        dynamicRoles: true
    }
    TextMetrics {
        id: ink
    }
    function init() {
        failOnWarning(/.*/);
        Session.closeProject();
        savedTooltips = Globals.Vars.showToolTips;
        Globals.Vars.showToolTips = true;
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Owner-note gates run the production application");
        verify(waitForRendering(appWindow.contentItem), "The owner-note application renders before interaction");
        Ui.click(test, Probe, appWindow, "appBar.tab.home");
    }
    function cleanup() {
        Globals.Vars.showAppAboutDialog = false;
        Session.closeProject();
        appWindow.destroy();
        Globals.Vars.showToolTips = savedTooltips;
    }
    function open() {
        verify(Session.openExample("pd-neut-cwl_cosio-d20_start-1"), "The independently named scientific example opens");
    }
    function pane(page, tier) {
        Ui.click(test, Probe, appWindow, "appBar.tab." + page);
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 2000, "The selected page reaches the real viewport");
        const tab = Ui.control(Probe, appWindow, "sideBar.tab." + tier);
        if (tab && !tab.checked)
            Ui.click(test, Probe, appWindow, "sideBar.tab." + tier);
        verify(waitForPolish(appWindow), "The selected sidebar completes actual layout");
    }
    function named(root, name) {
        const found = Review.find(root, name);
        verify(found !== null, "The owner-named visible consumer exists: " + name);
        return found;
    }
    function expand(name) {
        const group = Review.findGroup(Ui.page(appWindow), "group." + name);
        verify(group !== null, "The requested production sidebar group exists");
        Ui.scrollIntoView(Ui.target(group));
        Ui.expandGroup(test, Probe, appWindow, "group." + name);
        return group;
    }
    function actualText(root) {
        return Render.texts(root).filter(item => Ui.inPane(Ui.target(item)));
    }
    function test_plain_profile_hyphens_in_choice_labels() {
        open();
        pane("experiment", "basic");
        const peak = expand("peak");
        const field = named(peak, "peak.type");
        const labels = Probe.rows(Session.project.currentExperiment.peakTypeOptions).map(row => row.label);
        verify(labels.length > 1 && labels.some(label => label.includes("-")), "The profile choices include nontrivial hyphenated names");
        verify(labels.every(label => !/[–—]/.test(label)), "All profile labels use plain hyphens");
        const box = Render.descendants(field).find(item => item.popup && typeof item.currentText === "string");
        verify(box !== undefined, "The actual profile choice control is discoverable");
        mouseClick(box, box.width / 2, box.height / 2);
        tryCompare(box.popup, "visible", true, 2000, "A real click opens the profile choices");
        const text = actualText(box.popup.contentItem).map(item => item.text).join(" ");
        verify(!/[–—]/.test(text) && text.includes("-"), "The actual displayed profile options retain plain hyphens");
        box.popup.close();
    }
    function test_real_category_activation_changes_visible_parameter_rows() {
        open();
        pane("analysis", "basic");
        const table = named(Ui.page(appWindow), "parameters.list");
        const picker = named(Ui.page(appWindow), "parameters.category");
        const total = table.count;
        const index = picker.model.findIndex(group => group.key === "@coordinates");
        verify(index > 0, "The independent olivine input exposes a coordinates subset");
        mouseClick(picker, picker.width / 2, picker.height / 2);
        tryCompare(picker.popup, "visible", true, 2000, "The real category picker opens through input");
        keyClick(Qt.Key_Home);
        for (let i = 0; i < index; ++i)
            keyClick(Qt.Key_Down);
        keyClick(Qt.Key_Return);
        tryVerify(() => table.count > 0 && table.count < total, 2000, "Activating the real category choice narrows the visible table");
        const rows = Probe.rows(table.model);
        verify(rows.every(row => /\.atom_site\.[^.]+\.fract_[xyz]$/.test(row.path)), "The visible rows contain only the independently declared coordinate family");
        table.forceLayout();
        verify(table.itemAtIndex(0) !== null, "The filtered family has a real visible parameter delegate");
        mouseClick(picker, picker.width / 2, picker.height / 2);
        keyClick(Qt.Key_Home);
        keyClick(Qt.Key_Return);
        tryCompare(table, "count", total, 2000, "Choosing All through the same picker restores every visible parameter row");
    }
    function test_analysis_alignment_units_and_available_height() {
        open();
        pane("analysis", "basic");
        const table = named(Ui.page(appWindow), "parameters.list");
        const alignments = [Text.AlignHCenter, Text.AlignLeft, Text.AlignRight, Text.AlignLeft, Text.AlignRight, Text.AlignHCenter, Text.AlignHCenter, Text.AlignHCenter];
        // Alignment reference: Beta Fittables header/delegate, independent of edi's new QML.
        const header = Render.cells(table.headerItem);
        compare(header.length, alignments.length, "Analysis retains all Beta scientific columns");
        for (let i = 0; i < header.length; ++i)
            compare(header[i].horizontalAlignment, alignments[i], "Analysis header follows the Beta alignment reference");
        compare(header[3].text, "", "Analysis keeps the units column untitled");
        const rows = Probe.rows(table.model);
        verify(rows.some(row => row.units === "Å"), "The independent crystallographic fixture exercises nonempty units");
        for (let i = 0; i < rows.length; ++i) {
            table.positionViewAtIndex(i, ListView.Center);
            table.forceLayout();
            verify(waitForPolish(table), "Each analysis unit row completes actual layout");
            const delegate = table.itemAtIndex(i);
            verify(delegate !== null, "Each unit witness is inspected in its real delegate");
            const body = Render.cells(delegate);
            for (let j = 0; j < body.length; ++j)
                compare(body[j].horizontalAlignment, alignments[j], "The rendered analysis row follows the Beta alignment reference");
            ink.font = body[3].font;
            ink.text = rows[i].units;
            verify(body[3].width >= Math.ceil(ink.advanceWidth), "Every actual units cell fits its independently supplied unit text");
        }
        const heights = [];
        for (const height of [760, 1060]) {
            appWindow.height = height;
            verify(waitForPolish(appWindow), "A changed real window height relays out the Analysis sidebar");
            table.contentY = 0;
            table.forceLayout();
            const fitting = named(Ui.page(appWindow), "group.fitting");
            const group = named(Ui.page(appWindow), "group.parameters");
            const sidebar = group.parent;
            const bottom = fitting.mapToItem(sidebar, 0, fitting.height).y;
            verify(Math.abs(sidebar.height - bottom) <= Style.Sizes.tableRowHeight + Style.Sizes.fontPixelSize * 2, "The Analysis controls fill the actual available sidebar height to within one row");
            const first = table.itemAtIndex(0);
            verify(first !== null, "The Analysis table has a rendered first row");
            const rowCount = (table.height - table.headerItem.height) / first.height;
            const nextIndex = Math.floor(rowCount);
            const next = table.itemAtIndex(nextIndex);
            verify(next !== null, "The real Analysis viewport instantiates its scrolling cue row");
            const fraction = (table.height - next.mapToItem(table, 0, 0).y) / next.height;
            verify(Math.abs(fraction - 0.5) < 0.06, "The actual Analysis sidebar shows half the next row at either available height");
            heights.push(table.height);
        }
        verify(heights[1] > heights[0], "The Analysis table uses extra available window height");
    }
    function test_last_sidebar_border_is_actually_absent_on_every_page() {
        open();
        for (const page of ["project", "structure", "experiment", "analysis"])
            for (const tier of ["basic", "extras"]) {
                pane(page, tier);
                const groups = Review.descendants(Ui.page(appWindow)).filter(item => item.visible && item.objectName.startsWith("group.") && Ui.inPane(Ui.target(item)) && item.background);
                verify(groups.length > 0, "Each sidebar consumer has actual group backgrounds");
                const last = groups[groups.length - 1];
                compare(Render.borderLines(last.background).length, 0, "The last visible sidebar group has no rendered bottom separator");
                for (const group of groups.slice(0, -1).filter(item => item.collapsible))
                    verify(Render.borderLines(group.background).length > 0, "Preceding sidebar categories retain their actual separating line");
                if (page === "structure" && tier === "extras")
                    compare(last.objectName, "group.appearance", "The Structure Extras Appearance group is the borderless last consumer");
            }
    }
    function test_input_gaps_match_the_actual_chart_button_group() {
        open();
        const chart = createTemporaryObject(toolbar, appWindow.contentItem, {
            x: 0,
            y: 0
        });
        verify(chart !== null && waitForPolish(chart), "The production chart-button group completes layout");
        const a = named(chart, "chart.toolbar.legend"), b = named(chart, "chart.toolbar.hover");
        const expected = b.x - a.x - a.width;
        verify(expected >= 0, "The real chart buttons expose their within-group gap");
        const cases = [["project", "basic", "examples", ["examples.search", "examples.property", "examples.value"]], ["experiment", "extras", "data", ["range.minimum", "range.maximum", "range.step", "range.points"]], ["analysis", "basic", "parameters", ["parameters.nameFilter", "parameters.category", "parameters.variability"]]];
        for (const data of cases) {
            pane(data[0], data[1]);
            const group = data[2] === "parameters" ? named(Ui.page(appWindow), "group.parameters") : expand(data[2]);
            const inputs = data[3].map(name => named(group, name));
            for (let i = 1; i < inputs.length; ++i) {
                const gap = inputs[i].mapToItem(group, 0, 0).x - inputs[i - 1].mapToItem(group, inputs[i - 1].width, 0).x;
                verify(Math.abs(gap - expected) < 0.6, "Actual horizontal input gaps match the gap within the chart-button group");
            }
        }
    }
    function test_peak_parameter_grid_gaps_match_actual_chart_buttons() {
        open();
        const chart = createTemporaryObject(toolbar, appWindow.contentItem, {
            x: 0,
            y: 0
        });
        verify(chart !== null && waitForPolish(chart), "The real chart group supplies its actual within-group gap");
        const a = named(chart, "chart.toolbar.legend"), b = named(chart, "chart.toolbar.hover");
        const expected = b.x - a.x - a.width;
        pane("experiment", "basic");
        const group = expand("peak");
        const fields = Render.descendants(group).filter(item => item.visible && item.item && typeof item.commit === "function" && item.width > 0);
        let exercised = false;
        const grids = [...new Set(fields.map(item => item.parent))];
        for (const grid of grids) {
            const members = fields.filter(item => item.parent === grid).sort((a, b) => a.y - b.y || a.x - b.x);
            for (let i = 1; i < members.length; ++i) {
                const left = members[i - 1], right = members[i];
                if (Math.abs(left.y - right.y) > 0.6)
                    continue;
                verify(Math.abs(right.x - left.x - left.width - expected) < 0.6, "Every actual adjacent Peak field pair uses the chart-button group gap");
                exercised = true;
            }
        }
        verify(exercised, "The independently named profile exercises at least one real adjacent parameter-field pair");
    }
    function test_free_colour_and_weight_follow_state_in_cell_and_standalone_field() {
        open();
        pane("analysis", "basic");
        const table = named(Ui.page(appWindow), "parameters.list");
        const rows = Probe.rows(table.model);
        const index = rows.findIndex(row => row.parameter && row.parameter.fittable && row.parameter.refinable && !row.parameter.outsideRange);
        verify(index >= 0, "The independent fixture supplies a freely selectable in-range parameter");
        table.positionViewAtIndex(index, ListView.Center);
        table.forceLayout();
        const cell = named(table, "parameters.value." + index);
        const field = createTemporaryObject(standalone, appWindow.contentItem, {
            item: rows[index].parameter,
            x: 10,
            y: 10
        });
        verify(field !== null, "The same real ParameterItem reaches its standalone consumer");
        for (const free of [true, false, true]) {
            rows[index].parameter.free = free;
            verify(waitForPolish(appWindow), "Changing parameter freedom updates both actual consumers");
            for (const input of [cell, field]) {
                compare(input.font.bold, free, "Both consumers change weight with parameter freedom");
                compare(input.color, free ? Style.Colors.chartForegroundsExtra[1] : Style.Colors.themeForeground, "Both consumers change residual green with parameter freedom");
            }
        }
    }
    function test_chart_buttons_have_pointer_cursor_under_real_hover() {
        const chart = createTemporaryObject(toolbar, appWindow.contentItem, {
            x: 10,
            y: 10
        });
        verify(chart !== null && waitForPolish(chart), "The actual chart toolbar completes layout");
        for (const name of ["legend", "hover", "pan", "zoom", "reset"]) {
            const button = named(chart, "chart.toolbar." + name);
            mouseMove(button, button.width / 2, button.height / 2);
            tryVerify(() => Probe.cursorShape(button) === Qt.PointingHandCursor, 2000, "Every real chart-button hover exposes the pointing-hand cursor");
            mouseMove(appWindow.contentItem, appWindow.width - 2, appWindow.height - 2);
            tryVerify(() => Probe.cursorShape(button) !== Qt.PointingHandCursor, 2000, "Leaving the real chart button clears its pointing-hand cursor");
        }
    }
    function markerAfterName(root) {
        const text = actualText(root);
        const marker = text.find(item => item.text === "template");
        const label = text.find(item => item.text.includes("pattern.dat"));
        verify(marker !== undefined && label !== undefined, "The actual selector line displays the supplied filename and template marker");
        const markerX = marker.mapToItem(root, 0, 0).x, end = label.mapToItem(root, label.contentWidth, 0).x;
        verify(markerX >= end && markerX - end <= label.font.pixelSize, "The actual selector marker immediately follows the filename");
        compare(marker.color, Style.Colors.themeAccent, "The selector template marker retains its accent colour");
    }
    function test_template_order_in_selector_current_line_and_popup() {
        selectorRows.clear();
        selectorRows.append({
            label: "bank · pattern.dat",
            isTemplate: true,
            fitOutcome: ""
        });
        const selector = createTemporaryObject(selectorComponent, appWindow.contentItem, {
            x: 10,
            y: 10,
            blocks: selectorRows,
            blocksTextRole: "label",
            blockKind: "experiment",
            templateRole: "isTemplate",
            currentTemplate: true,
            outcomeRole: "fitOutcome"
        });
        verify(selector !== null && waitForPolish(selector), "The real block selector consumes independent template metadata");
        markerAfterName(selector);
        const box = Render.descendants(selector).find(item => item.popup && typeof item.currentText === "string" && item !== selector);
        verify(box !== undefined, "The actual selector choice control exists");
        mouseClick(box, box.width / 2, box.height / 2);
        tryCompare(selector.popup, "visible", true, 2000, "A real click opens the template selector popup");
        markerAfterName(selector.popup.contentItem);
        selector.popup.close();
    }
    function test_example_description_has_visible_identity_facets_and_detail() {
        pane("project", "basic");
        const group = expand("examples");
        const search = named(group, "examples.search");
        search.forceActiveFocus();
        for (const character of "cosio-d20_start-1")
            keyClick(character.charCodeAt(0));
        const table = named(group, "examples.list");
        tryCompare(table, "count", 1, 2000, "The actual search isolates the independently named olivine example");
        const row = table.itemAtIndex(0);
        verify(row !== null, "The example description is inspected in its rendered row");
        const text = actualText(row);
        const identity = text.find(item => item.text.includes("Co₂SiO₄") && item.text.includes("D20 @ ILL"));
        const detail = text.find(item => item.text.includes("Starting model 1"));
        verify(identity !== undefined && detail !== undefined, "The example shows the independent sample, facility and starting-model identities");
        verify(identity.font.bold && !detail.font.bold, "The visible example identity is distinguished from its secondary detail");
        const facets = text.filter(item => ["Fitting", "Single", "powder", "pd", "neut", "cwl", "Bragg"].includes(item.text));
        verify(facets.length > 0, "The example's scientific and workflow facets have their own visible line");
        const identityY = identity.mapToItem(row, 0, 0).y, detailY = detail.mapToItem(row, 0, 0).y;
        verify(facets.some(item => item.mapToItem(row, 0, 0).y > identityY && item.mapToItem(row, 0, 0).y < detailY), "The actual example description separates identity, facets and detail vertically");
        for (const item of [identity, detail])
            verify(item.mapToItem(row, 0, item.height).y <= row.height, "The new example description stays within its actual row");
    }
    function aboutDialog() {
        Ui.click(test, Probe, appWindow, "home.about");
        let dialog = null;
        tryVerify(() => {
            dialog = Probe.visibleDialogs(appWindow).find(item => item.title === "About");
            return dialog !== undefined;
        }, 2000, "The actual Home action opens About");
        return dialog;
    }
    function singleAbout(dialog) {
        const dialogs = Probe.visibleDialogs(appWindow);
        compare(dialogs.length, 1, "About navigation retains exactly one visible dialog");
        compare(dialogs[0], dialog, "Licence and notices remain in the original About window");
    }
    function textInDialog(dialog, name) {
        const item = Review.find(dialog.contentItem, name);
        verify(item !== null && Ui.rendered(item), "The selected About view has its actual visible text consumer: " + name);
        return item;
    }
    function formatted(text) {
        return [TextEdit.RichText, TextEdit.MarkdownText].includes(text.textFormat);
    }
    function normalized(text) {
        return text.replace(/\s+/g, " ").trim();
    }
    function test_about_navigation_licences_and_structured_notices() {
        const dialog = aboutDialog();
        singleAbout(dialog);
        const original = dialog;
        const copyright = textInDialog(dialog, "about.copyright");
        verify(copyright.text.includes("EasyScience") && !/all rights? reserved/i.test(copyright.text), "About names EasyScience contributors without the withdrawn reservation sentence");
        const components = Probe.visibleControl(appWindow, "about.components");
        verify(components === null || !Ui.rendered(components), "The component table is absent from the initially displayed About view");
        const licenceTab = textInDialog(dialog, "about.tab.licence");
        mouseClick(licenceTab, licenceTab.width / 2, licenceTab.height / 2);
        verify(waitForPolish(appWindow), "The Licence view completes actual navigation layout");
        singleAbout(original);
        const summary = textInDialog(dialog, "about.licence.summary");
        verify(summary.text.length < 650 && /GNU General Public License/.test(summary.text) && /BSD/.test(summary.text), "About provides a short user-facing licence summary for both distribution terms");
        verify(!/ADR-\d|app\/|DISTRIBUTION-LICENSE|source repo/i.test(summary.text), "The short licence summary has no developer file or decision references");
        verify(formatted(summary), "The user licence summary renders as formatted text");
        for (const data of [["gpl", "COPYING"], ["bsd", "LICENSE"]]) {
            const link = textInDialog(dialog, "about.licence." + data[0]);
            mouseClick(link, link.width / 2, link.height / 2);
            verify(waitForPolish(appWindow), "A real licence request lays out the inline full text");
            singleAbout(original);
            const full = textInDialog(dialog, "about.licence.text");
            verify(formatted(full), "The requested full licence uses consistent formatted text rendering");
            compare(normalized(full.getText(0, full.length)), normalized(Probe.readFile(data[1])), "The complete independent bundled licence text remains reachable inside About");
            verify(full.font.pixelSize <= Style.Sizes.fontPixelSize * 1.25, "Licence body text uses the app text size instead of oversized headings");
            verify(full.readOnly, "The complete licence remains a read-only text view");
        }
        const noticesTab = textInDialog(dialog, "about.tab.thirdParty");
        mouseClick(noticesTab, noticesTab.width / 2, noticesTab.height / 2);
        verify(waitForPolish(appWindow), "A real Third-party software click reveals the components table");
        singleAbout(original);
        const table = textInDialog(dialog, "about.components");
        const expected = JSON.parse(Probe.readFile("tests/fixtures/table_display/notices.json")).rows;
        const rows = Probe.rows(table.model);
        compare(rows.length, expected.length, "The structured notices table retains every independently frozen shipped component");
        const header = Render.cells(table.headerItem);
        compare(header.map(item => item.text), ["Component", "Version", "Licence", "Used for"], "The structured table uses consistent component, version, licence and purpose columns");
        ink.font = header[2].font;
        const needed = Math.max(...expected.map(row => {
            ink.text = row.licence;
            return ink.advanceWidth;
        }));
        verify(header[2].width >= Math.ceil(needed) && header[2].width <= Math.ceil(needed) + ink.font.pixelSize + 2, "The actual licence column is sized independently from the longest supplied expression");
        for (let i = 0; i < rows.length; ++i) {
            for (const key of ["component", "version", "licence", "use"])
                compare(rows[i][key], expected[i][key], "The actual structured notice row retains its independent component attribution");
            table.positionViewAtIndex(i, ListView.Center);
            table.forceLayout();
            verify(waitForPolish(table), "Each shipped component row completes real table layout");
            const delegate = table.itemAtIndex(i);
            verify(delegate !== null, "Every notice licence is inspected in its real rendered row");
            const cells = Render.cells(delegate);
            ink.font = cells[2].font;
            ink.text = expected[i].licence;
            verify(cells[2].width >= Math.ceil(ink.advanceWidth), "The actual licence column fits each complete independently supplied licence expression");
        }
        const eigen = expected.findIndex(row => row.component === "Eigen");
        verify(eigen >= 0, "The frozen notice input contains an independent MPL component witness");
        table.positionViewAtIndex(eigen, ListView.Center);
        table.forceLayout();
        const row = table.itemAtIndex(eigen);
        mouseClick(row, row.width / 2, row.height / 2);
        const text = textInDialog(dialog, "about.components.licence");
        tryVerify(() => text.getText(0, text.length).includes("Mozilla Public License"), 2000, "Selecting a real component shows its own licence text below the table");
        verify(formatted(text), "Selected third-party licence text uses consistent formatted rendering");
        verify(text.mapToItem(dialog.contentItem, 0, 0).y >= table.mapToItem(dialog.contentItem, 0, table.height).y, "The selected component licence is rendered below the structured table");
        singleAbout(original);
        for (const item of actualText(dialog.contentItem).filter(item => item.objectName.startsWith("about.tab.")))
            verify(item.font.pixelSize <= Style.Sizes.fontPixelSize * 1.25, "About headings retain the app-sized typography");
    }
}
