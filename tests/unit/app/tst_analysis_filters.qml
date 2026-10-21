import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import PatternPolishAcceptance 1.0
import EasyApplication.Gui.Style as Style
import "UiInteraction.js" as Ui
import "E04Review.js" as View
import "RenderedTable.js" as Render

TestCase {
    id: test
    name: "AnalysisFilters"
    when: windowShown
    property var appWindow
    property var expected
    Component {
        id: application
        Main {}
    }
    function init() {
        Session.closeProject();
        expected = JSON.parse(Probe.readFile("tests/fixtures/analysis_filters/expected.json"));
        appWindow = application.createObject(null);
        verify(appWindow !== null, "Analysis acceptance must host the production application");
        appWindow.width = 1300;
        appWindow.height = 1000;
        verify(waitForRendering(appWindow.contentItem), "Analysis acceptance must render before interaction");
    }
    function cleanup() {
        Session.closeProject();
        if (appWindow)
            appWindow.destroy();
        appWindow = null;
        Probe.releaseScratchProjects();
    }
    function open(path) {
        verify(Session.openProject(SettingsProof.copyProject(Probe.repoUrl(path))), "The independently authored filter project must load: " + Session.lastError);
        Ui.click(test, Probe, appWindow, "appBar.tab.analysis");
        tryVerify(() => Math.abs(Ui.page(appWindow).mapToItem(appWindow.contentItem, 0, 0).x) < 1, 3000, "Analysis must enter the actual viewport before checking its controls");
        Ui.click(test, Probe, appWindow, "sideBar.tab.basic");
        verify(waitForPolish(appWindow.contentItem), "Analysis must finish its real layout before checking controls");
    }
    function all(root, name) {
        return View.descendants(root).filter(item => item.objectName === name);
    }
    function control(name) {
        const found = Ui.find(Ui.page(appWindow), name, true);
        verify(found !== null, "Analysis must expose the actual " + name + " control");
        return found;
    }
    function title(entry) {
        return typeof entry === "string" ? entry : entry.title;
    }
    function options(picker) {
        const result = [];
        for (let i = 0; i < picker.count; ++i)
            result.push(title(picker.model[i]));
        return result;
    }
    function caption(text) {
        return String(text).replace(/\s*\(\d+\)$/, "");
    }
    function count(text) {
        const match = String(text).match(/\((\d+)\)$/);
        verify(match !== null, "Every selector entry must show its parameter count: " + text);
        return Number(match[1]);
    }
    function iconSegments(entry) {
        const result = [];
        for (const item of View.descendants(entry)) {
            if (item.segments === undefined)
                continue;
            for (let i = 0; i < item.segments.length; ++i)
                result.push(item.segments[i]);
        }
        return result;
    }
    function choose(picker, index, heading) {
        Ui.scrollIntoView(picker);
        const hit = Ui.clickPoint(picker);
        verify(hit !== null, "Every selector must expose a real pointer target");
        mouseClick(picker, hit.x, hit.y);
        tryVerify(() => picker.popup.visible, 500, "A selector click must open its actual menu");
        const list = picker.popup.contentItem;
        list.positionViewAtIndex(index, ListView.Contain);
        verify(waitForPolish(list), "The selected menu delegate must finish layout");
        const entry = list.itemAtIndex(index);
        verify(entry !== null, "Every offered filter must have an actual menu delegate");
        if (typeof heading === "boolean") {
            const segments = iconSegments(entry);
            verify(segments.some(segment => segment.text && !!segment.bold === heading), "Category group headings must be bold and ordinary categories must use normal text");
        }
        const point = Ui.clickPoint(entry);
        verify(point !== null, "Every filter option must be reachable through the menu viewport");
        mouseClick(entry, point.x, point.y);
        tryVerify(() => !picker.popup.visible, 500, "Selecting a filter must close the actual popup before the next input");
        compare(picker.currentIndex, index, "Pointer selection must update the actual filter selector");
    }
    function select(picker, text, heading) {
        const index = options(picker).findIndex(value => caption(value) === text);
        verify(index >= 0, "The selector must offer its required subset: " + text);
        choose(picker, index, heading);
    }
    function typeName(query) {
        const field = control("parameters.nameFilter");
        Ui.scrollIntoView(field);
        const hit = Ui.clickPoint(field);
        verify(hit !== null, "The name filter must accept actual user input");
        mouseClick(field, hit.x, hit.y);
        appWindow.requestActivate();
        field.forceActiveFocus();
        tryCompare(field, "activeFocus", true, 1000, "The actual name field must receive keyboard focus");
        if (query.length) {
            verify(SettingsProof.type(field, query), "Name filtering must receive real keyboard text");
        } else {
            field.selectAll();
            verify(SettingsProof.key(field, Qt.Key_Backspace), "Clearing the name must send a real editing key");
            compare(field.text, "", "The real name editor must become empty after clearing");
        }
    }
    function identity(row) {
        return [row.kind, row.block, row.category, row.label, row.name].join("/");
    }
    function actualRows() {
        return Probe.rows(control("parameters.list").sourceModel).map(row => {
            const p = row.parameter;
            const uid = String(p.uid).split(".");
            return {
                kind: String(p.blockKind),
                block: String(p.blockName),
                category: uid[0],
                name: uid[1],
                label: String(p.rowLabel),
                free: p.free
            };
        });
    }
    function sameRows(rows, reason) {
        compare(actualRows().map(identity).sort(), rows.map(identity).sort(), reason);
    }
    function groups(rows) {
        const result = [
            {
                title: "All categories",
                rows: rows,
                heading: false
            }
        ];
        function add(text, subset, heading) {
            if (subset.length)
                result.push({
                    title: text,
                    rows: subset,
                    heading: !!heading
                });
        }
        ["structure", "experiment"].forEach(kind => {
            const source = rows.filter(r => r.kind === kind);
            add(kind === "structure" ? "Structure" : "Experiment", source, true);
            const cell = source.filter(r => r.category === "cell");
            add("Unit cell", cell);
            const atoms = source.filter(r => r.category === "atom_site");
            add("Atom sites", atoms);
            add("Atomic coordinates", atoms.filter(r => r.name.startsWith("fract_")));
            add("Atomic occupancies", atoms.filter(r => r.name === "occupancy"));
            add("Atomic displacement", atoms.filter(r => r.name === "adp_iso"));
            const peak = source.filter(r => r.category === "peak");
            add("Peak profile", peak);
            // Only a proper subset gets a second category choice.
            if (peak.some(r => !r.name.startsWith("broad_")))
                add("Peak broadening", peak.filter(r => r.name.startsWith("broad_")));
            add("Instrument", source.filter(r => r.category === "instrument"));
            add("Linked structures", source.filter(r => r.category === "linked_structure"));
            add("Background", source.filter(r => r.category === "background"));
        });
        return result;
    }
    function checkCounts(block, category, variability, wanted, selectedRows) {
        options(variability).forEach((entry, choice) => compare(count(entry), selectedRows.filter(r => choice === 0 || r.free === (choice === 1)).length, "Every parameter count must remain scoped to its upper selections"));
        options(category).forEach(entry => compare(count(entry), wanted.find(group => group.title === caption(entry)).rows.length, "Downstream filters must not change category membership counts"));
        options(block).forEach(entry => compare(count(entry), expected.filter(r => caption(entry) === "All datablocks" || r.block === caption(entry)).length, "Downstream filters must not change datablock parameter counts"));
    }
    function test_file_oracle() {
        open("tests/fixtures/analysis_filters/project");
        const actual = Probe.rows(Session.project.parameters);
        const rows = actual.map(row => {
            const p = row.parameter, uid = String(p.uid).split(".");
            return {
                kind: String(p.blockKind),
                block: String(p.blockName),
                category: uid[0],
                name: uid[1],
                label: String(p.rowLabel),
                free: p.free
            };
        });
        compare(rows.map(identity).sort(), expected.map(identity).sort(), "The independent saved-file oracle must account for every actual parameter identity");
        compare(options(control("parameters.category")).map(caption).sort(), groups(expected).map(g => g.title).sort(), "Independent file categories must account for the existing category presentation");
        compare(rows.filter(r => r.free).map(identity).sort(), expected.filter(r => r.free).map(identity).sort(), "Parenthesised saved values independently define the free parameter subset");
    }
    function test_layout_and_icons() {
        open("tests/fixtures/analysis_filters/project");
        appWindow.update();
        verify(waitForRendering(appWindow.contentItem), "The filter look witness must wait for a completed frame");
        const capture = PatternProof.capture(appWindow, "analysis-filter-layout");
        verify(capture.openGL && capture.saved, "The filter layout must retain an actual OpenGL capture");
        const block = control("parameters.datablock"), category = control("parameters.category");
        const variability = control("parameters.variability"), name = control("parameters.nameFilter");
        const clear = control("parameters.clearFilters");
        const pos = item => item.mapToItem(appWindow.contentItem, 0, 0);
        compare(pos(block).y, pos(category).y, "Datablocks and categories must share the first filter line");
        compare(pos(block).y, pos(variability).y, "All three selectors must share the first filter line");
        compare(block.width, category.width, "The first line must give selectors equal widths");
        compare(block.width, variability.width, "The parameter selector must share the same width");
        verify(pos(block).x < pos(category).x && pos(category).x < pos(variability).x, "The first line must order datablocks, categories and parameters");
        verify(pos(name).y > pos(block).y && pos(name).y === pos(clear).y, "The name field and clear button must share a separate second line");
        compare(clear.width, clear.height, "Clear all filters must be a square button");
        verify(name.width > 3 * clear.width && pos(name).x < pos(clear).x, "Filter by name must occupy most of the second line, before the eraser");
        compare(name.placeholderText, "Filter by name", "The name field must carry the stated prompt");
        compare(clear.fontIcon, "eraser", "The reset button must use the eraser icon");
        compare(clear.ToolTip.text, "Clear all filters", "The reset button must explain that it clears every filter");
        compare(options(block).map(caption), ["All datablocks", "amber", "violet", "east", "west"], "Datablocks must list every structure then every experiment");
        const palette = [];
        for (let i = 1; i < block.count; ++i) {
            mouseClick(block, block.width / 2, block.height / 2);
            const list = block.popup.contentItem;
            list.positionViewAtIndex(i, ListView.Contain);
            verify(waitForPolish(list), "Datablock icons must finish actual menu layout");
            const entry = list.itemAtIndex(i);
            verify(entry !== null, "Each datablock must have a real menu delegate");
            const segments = iconSegments(entry);
            const icon = segments.find(segment => segment.icon === (i < 3 ? "layer-group" : "microscope"));
            verify(icon !== undefined && String(icon.color) !== String(Style.Colors.themeForegroundMinor), "Every datablock entry must show its usual coloured structure or experiment icon");
            palette.push(String(icon.color));
            block.popup.close();
        }
        verify(palette[0] !== palette[1] && palette[2] !== palette[3], "Distinct datablocks of each kind must retain their distinct palette colours");
    }
    function test_combinations_data() {
        return ["All datablocks", "amber", "violet", "east", "west"].map(block => ({
                    tag: block,
                    block: block
                }));
    }
    function test_combinations(data) {
        open("tests/fixtures/analysis_filters/project");
        const block = control("parameters.datablock"), category = control("parameters.category"), variability = control("parameters.variability");
        options(block).forEach(value => compare(count(value), expected.filter(r => caption(value) === "All datablocks" || r.block === caption(value)).length, "Every datablock count must count parameters independently from the saved files"));
        select(block, data.block);
        const subset = expected.filter(r => data.block === "All datablocks" || r.block === data.block);
        const wanted = groups(subset);
        compare(options(category).map(caption).sort(), wanted.map(g => g.title).sort(), "Category choices must be exactly those present in the selected datablock subset");
        options(category).forEach(value => {
            const entry = wanted.find(g => g.title === caption(value));
            compare(count(value), entry.rows.length, "Every category menu entry must count parameters in the selected datablocks");
        });
        wanted.forEach(g => {
            select(category, g.title, g.heading);
            compare(count(category.currentText), g.rows.length, "Every category count must be its independent parameter membership");
            const choices = options(variability);
            compare(choices.map(caption), ["All parameters", "Free parameters", "Fixed parameters"], "The parameter filter must retain all, free and fixed choices");
            choices.forEach((value, index) => {
                const rows = g.rows.filter(r => index === 0 || r.free === (index === 1));
                compare(count(value), rows.length, "Parameter menu counts must respect both upstream selectors");
                choose(variability, index);
                checkCounts(block, category, variability, wanted, g.rows);
                sameRows(rows, "Every datablock/category/variability combination must show exactly its independent parameter identities");
                ["COEF", "amber", "east", "absent_parameter"].forEach(query => {
                    typeName(query);
                    const matching = rows.filter(r => query === "COEF" ? r.category === "background" : r.block === query || r.label === query);
                    sameRows(matching, "Case-insensitive name search must return every matching row and only that upstream subset");
                    checkCounts(block, category, variability, wanted, g.rows);
                    typeName("");
                    sameRows(rows, "Clearing the name must restore exactly the upstream-selected subset");
                });
            });
        });
    }
    function test_clear_and_invalid_selection() {
        open("tests/fixtures/analysis_filters/project");
        const block = control("parameters.datablock"), category = control("parameters.category"), variability = control("parameters.variability");
        select(block, "amber");
        select(category, "Atomic coordinates");
        choose(variability, 1);
        typeName("fract");
        const clear = control("parameters.clearFilters");
        mouseClick(clear, clear.width / 2, clear.height / 2);
        compare(block.currentIndex, 0, "The eraser must reset datablocks");
        compare(category.currentIndex, 0, "The eraser must reset categories");
        compare(variability.currentIndex, 0, "The eraser must reset parameter variability");
        compare(control("parameters.nameFilter").text, "", "The eraser must reset the name filter");
        sameRows(expected, "One eraser click must restore every independent parameter row");
        select(block, "amber");
        select(category, "Atomic coordinates");
        select(block, "east");
        compare(category.currentIndex, 0, "A category absent from the newly selected datablock must immediately return to All");
        sameRows(expected.filter(r => r.block === "east"), "Invalid category reset must restore the new datablock subset");
    }
    function scopedRows(state) {
        let rows = expected.filter(row => !state.block || row.block === state.block);
        if (state.category === "Peak asymmetry")
            rows = rows.filter(row => row.category === "peak" && /^(rise_alpha_|decay_beta_|asym_)/.test(row.name));
        else if (state.category)
            rows = rows.filter(row => row.category === (state.category === "Peak profile" ? "peak" : "background"));
        return rows;
    }
    function wantedRows(state) {
        return scopedRows(state).filter(row => (state.variability === 0 || row.free === (state.variability === 1)) && (!state.query || identity(row).toLowerCase().includes(state.query.toLowerCase())));
    }
    function closedPicker(picker, text, icons) {
        compare(picker.displayText, text, "The closed selector's display text names its applied selection with its independent count");
        compare(picker.currentText, text, "A selector's current menu entry and closed caption agree after every rebuild");
        const labels = Render.texts(picker.contentItem).filter(item => !item.isIcon);
        verify(labels.some(item => item.text === text), "The closed selector actually renders its selected title and count");
        if (icons) {
            const index = picker.currentIndex;
            mouseClick(picker, picker.width / 2, picker.height / 2);
            tryVerify(() => picker.popup.visible, 1000, "The applied selection opens its real menu for icon comparison");
            const list = picker.popup.contentItem;
            list.positionViewAtIndex(index, ListView.Contain);
            verify(waitForPolish(list), "The selected open entry finishes layout before comparing icons");
            const entry = list.itemAtIndex(index);
            verify(entry !== null, "The applied selection has a materialized open menu entry");
            const menuIcons = Render.texts(entry).filter(item => item.isIcon).map(item => [item.text, String(item.color)].join("|"));
            const shownIcons = Render.texts(picker.contentItem).filter(item => item.isIcon).map(item => [item.text, String(item.color)].join("|"));
            compare(shownIcons, menuIcons, "Each closed selector renders the same icon and colour as its selected open entry");
            if (picker.objectName !== "parameters.variability" && !text.startsWith("All "))
                verify(shownIcons.length > 0, "A selected datablock or category renders its prescribed icon while closed");
            picker.popup.close();
            tryVerify(() => !picker.popup.visible, 1000, "The selector menu closes without changing its applied selection");
        }
    }
    function checkRebuild(state, aspect) {
        verify(waitForPolish(appWindow.contentItem), "Filter rebuilds finish layout before observing closed captions and rows");
        const block = control("parameters.datablock"), category = control("parameters.category"), variability = control("parameters.variability");
        const source = control("parameters.list").sourceModel;
        if (aspect === "rows") {
            const rows = wantedRows(state);
            sameRows(rows, "After every rebuilding action the shown rows equal the independently counted selected subset");
            compare(actualRows().filter(row => row.free).map(identity).sort(), rows.filter(row => row.free).map(identity).sort(), "The applied subset retains each independently tracked free flag after editing and restoration");
            compare(source.datablockFilter, state.block ? "experiment:" + state.block : "", "The applied datablock changes only on an explicit choice or invalidation");
            compare(source.categoryFilter, state.category === "Peak asymmetry" ? "@peakAsymmetry" : state.category === "Peak profile" ? "peak" : state.category === "Background" ? "background" : "", "The applied category survives rebuilds independently of a combo-box index reset");
            compare(Number(source.variability), state.variability, "Free and fixed edits never replace the user's variability selection");
            compare(source.nameFilter, state.query, "Rebuilding another filter preserves the independently entered name query");
            return;
        }
        const upper = scopedRows(state);
        const variabilityRows = upper.filter(row => state.variability === 0 || row.free === (state.variability === 1));
        closedPicker(block, (state.block || "All datablocks") + " (" + expected.filter(row => !state.block || row.block === state.block).length + ")", aspect === "icons");
        closedPicker(category, (state.category || "All categories") + " (" + upper.length + ")", aspect === "icons");
        closedPicker(variability, ["All parameters", "Free parameters", "Fixed parameters"][state.variability] + " (" + variabilityRows.length + ")", aspect === "icons");
    }
    function ncaf() {
        expected = JSON.parse(Probe.readFile("tests/fixtures/analysis_filters/ncaf.json"));
        open("tests/fixtures/fit_tables/five");
    }
    function test_ncaf_oracle() {
        ncaf();
        compare(expected.length, 269, "The saved I 21 3 project has its independently counted parameter population");
        compare(expected.filter(row => row.block === "wish_2_9").length, 44, "The reported wish bank has its independently counted complete parameter population");
        compare(expected.filter(row => row.category === "peak" && /^(rise_alpha_|decay_beta_)/.test(row.name)).length, 20, "The five banks each contribute four independent TOF asymmetry parameters");
        sameRows(expected, "The source-file and Wyckoff construction accounts for every real NCAF parameter identity");
        compare(actualRows().filter(row => row.free).map(identity).sort(), expected.filter(row => row.free).map(identity).sort(), "Saved value parentheses independently account for every NCAF free parameter");
    }
    function test_closed_filter_icons_data() {
        return ["datablock", "category"].map(selector => ({
                    tag: selector,
                    selector: selector
                }));
    }
    function test_closed_filter_icons(data) {
        ncaf();
        select(control("parameters.datablock"), "wish_2_9");
        select(control("parameters.category"), "Peak asymmetry");
        const picker = control("parameters." + data.selector);
        const icons = Render.texts(picker.contentItem).filter(item => item.isIcon);
        verify(icons.length > 0, "A selected datablock or category renders its icon on the closed selector before any further rebuild");
        verify(icons.every(item => item.width > 0 && item.height > 0 && Ui.exposed(item)), "Closed selector icons have actual visible glyph geometry");
    }
    function test_rebuild_consistency_data() {
        const cases = [];
        for (const action of ["datablock", "category", "free-to-fixed", "fixed-to-free", "name", "fit", "undo", "load"])
            for (const aspect of ["rows", "closed", "icons"])
                cases.push({
                    tag: action + "-" + aspect,
                    action: action,
                    aspect: aspect
                });
        return cases;
    }
    function editFirstFree(state, value) {
        const rows = wantedRows(state);
        verify(rows.length > 0, "The free-column edit reaches a real independently predicted parameter");
        const view = control("parameters.list");
        view.positionViewAtIndex(0, ListView.Contain);
        verify(waitForPolish(view), "The edited parameter's real free checkbox finishes layout");
        const item = control("parameters.free.0");
        compare(item.checked, !value, "The free-column actor changes a genuinely different state");
        const actual = actualRows()[0];
        mouseClick(item, item.width / 2, item.height / 2);
        expected.find(row => identity(row) === identity(actual)).free = value;
    }
    function test_rebuild_consistency(data) {
        let state = {
            block: "wish_2_9",
            category: "Peak asymmetry",
            variability: 0,
            query: ""
        };
        if (data.action === "fit") {
            open("tests/fixtures/analysis_filters/project");
            for (const row of expected)
                row.free = row.category === "background" && row.label === "c0";
            for (const row of Probe.rows(Session.project.parameters)) {
                const parameter = row.parameter;
                parameter.free = parameter.category === "background" && parameter.rowLabel === "c0";
            }
            state = {
                block: "east",
                category: "Background",
                variability: 1,
                query: ""
            };
        } else {
            ncaf();
        }
        const block = control("parameters.datablock"), category = control("parameters.category"), variability = control("parameters.variability");
        select(block, state.block);
        select(category, state.category);
        choose(variability, state.variability);
        if (data.action === "datablock") {
            select(block, "All datablocks");
            state.block = "";
        } else if (data.action === "category") {
            choose(variability, 1);
            state.variability = 1;
            select(category, "All categories");
            state.category = "";
            checkRebuild(state, data.aspect);
            choose(variability, 0);
            state.variability = 0;
        } else if (data.action === "free-to-fixed" || data.action === "fixed-to-free") {
            const makeFree = data.action === "fixed-to-free";
            state.category = makeFree ? "Peak profile" : "Peak asymmetry";
            select(category, state.category);
            state.variability = makeFree ? 2 : 1;
            choose(variability, state.variability);
            state.query = makeFree ? "gamma_0" : "alp";
            typeName(state.query);
            const changes = wantedRows(state).length;
            verify(changes > 0, "The independent input provides a nonempty filtered free-column edit witness");
            for (let i = 0; i < changes; ++i) {
                editFirstFree(state, makeFree);
                checkRebuild(state, data.aspect);
            }
        } else if (data.action === "name") {
            choose(variability, 1);
            state.variability = 1;
            state.query = "alp";
            typeName(state.query);
            checkRebuild(state, data.aspect);
            typeName("");
            state.query = "";
        } else if (data.action === "undo") {
            const parameter = Probe.rows(Session.project.parameters).map(row => row.parameter).find(item => item.blockName === state.block && item.uid === "peak.rise_alpha_0");
            verify(parameter !== undefined, "Undo reaches the independently named bank's alpha parameter");
            verify(Session.project.setParametersFree([parameter], !parameter.free), "The pre-undo free change creates a real restoration record");
            const undo = control("appBar.button.undo");
            verify(undo.enabled, "A real filter-rebuilding edit enables the app's Undo control");
            Ui.click(test, Probe, appWindow, "appBar.button.undo");
        } else if (data.action === "fit") {
            verify(control("fitting.start").enabled, "The independently reduced free subset enables a real fit");
            Ui.click(test, Probe, appWindow, "fitting.start");
            tryVerify(() => !Session.project.fit.running && Session.project.fit.iterations !== "" && Session.project.fit.canUndo, 15000, "A real fit completion rebuilds the parameter projection and provides undo");
            const dialog = findChild(appWindow, "fit.results");
            verify(dialog !== null, "The fitting rebuild witness has its real result dialog");
            tryCompare(dialog, "opened", true, 2000, "The fitting rebuild witness waits for its completed result dialog to open");
            mouseClick(dialog.standardButton(Dialog.Ok));
        } else if (data.action === "load") {
            open("tests/fixtures/fit_tables/five");
        }
        checkRebuild(state, data.aspect);
    }
    function test_empty_slider_data() {
        return ["disabled", "empty", "restored"].map(aspect => ({
                    tag: aspect,
                    aspect: aspect
                }));
    }
    function test_empty_slider(data) {
        ncaf();
        select(control("parameters.datablock"), "wish_2_9");
        select(control("parameters.category"), "Peak asymmetry");
        choose(control("parameters.variability"), 1);
        typeName("alp");
        const slider = control("parameters.slider"), lower = control("parameters.slider.from"), upper = control("parameters.slider.to");
        verify(slider.enabled && lower.enabled && upper.enabled, "A genuinely current free parameter first enables the slider and both bounds");
        const before = Probe.rows(Session.project.parameters).map(row => row.parameter.value);
        typeName("");
        typeName("absent_parameter");
        compare(actualRows().length, 0, "The independently absent name leaves no current parameter in the filtered table");
        if (data.aspect === "disabled") {
            verify(!slider.enabled && !lower.enabled && !upper.enabled, "No current parameter disables the slider and both bound fields");
            mouseDrag(slider, slider.width / 2, slider.height / 2, slider.width / 4, 0);
            compare(Probe.rows(Session.project.parameters).map(row => row.parameter.value), before, "Input on an empty disabled slider cannot change the previous or any hidden parameter");
        } else if (data.aspect === "empty") {
            compare(lower.text, "", "No current parameter leaves the lower bound empty");
            compare(upper.text, "", "No current parameter leaves the upper bound empty");
            compare(slider.toolTipText, "", "No current parameter leaves no stale slider value text");
            verify(!slider.handle.visible || slider.handle.opacity === 0, "No current parameter leaves no positioned value thumb in the empty slider");
        } else {
            typeName("");
            typeName("beta");
            verify(slider.enabled && lower.enabled && upper.enabled, "A newly current parameter restores the slider and both bound controls");
            const group = control("group.parameters"), selected = group.selected;
            verify(selected !== null && String(selected.uid).includes("beta"), "The restored slider belongs to a newly current parameter with a different identity");
            compare(slider.value, selected.value, "The restored slider displays the current parameter's value rather than the previous one");
            verify(lower.text !== "" && upper.text !== "" && slider.from < selected.value && slider.to > selected.value, "The restored current parameter regains nonempty bounds around its value");
        }
    }
    function test_mode_controls_data() {
        return [
            {
                tag: "joint",
                path: "tests/fixtures/analysis_filters/project",
                mode: "joint",
                scan: false
            },
            {
                tag: "single",
                path: "tests/fixtures/e04_t1/editable-project",
                mode: "single",
                scan: false
            },
            {
                tag: "sequential",
                path: "tests/fixtures/correlations/scan-sequential",
                mode: "sequential",
                scan: true
            },
            {
                tag: "independent",
                path: "tests/fixtures/correlations/scan-independent",
                mode: "independent",
                scan: true
            }
        ];
    }
    function checkMode(scan) {
        const evolution = all(Ui.page(appWindow), "mainArea.analysis.tab.evolution");
        compare(evolution.some(item => Ui.exposed(item)), scan, "Evolution must be visible only in sequential and independent modes");
        const follow = all(Ui.page(appWindow), "fitting.follow");
        compare(follow.some(item => Ui.exposed(item)), scan, "Follow must be visible only in sequential and independent modes");
        if (!scan) {
            const start = control("fitting.start");
            compare(Math.round(start.width), Math.round(Style.Sizes.sideBarContentWidth), "Start fitting must span the full sidebar content width for single and joint fits");
        }
    }
    function test_mode_controls(data) {
        open(data.path);
        compare(Session.project.analysis.fittingMode, data.mode, "The mode fixture must load its declared fitting mode");
        checkMode(data.scan);
        if (data.scan) {
            for (const mode of ["single", "independent", "single", "sequential"]) {
                Session.project.analysis.fittingMode = mode;
                compare(Session.project.analysis.fittingMode, mode, "A mode switch must reach the real production setter");
                verify(waitForPolish(appWindow.contentItem), "Mode-dependent visibility must update within the next layout pass");
                checkMode(mode !== "single");
            }
        }
    }
}
