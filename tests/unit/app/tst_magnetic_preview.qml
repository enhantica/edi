import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render
import "E04Review.js" as Review

TestCase {
    id: test
    name: "MagneticPreview"
    when: windowShown
    property var appWindow
    property var scratch
    property var repeatFitPreferences: null
    Component { id: application; Main {} }
    Component { id: preferences; AppPreferencesDialog {} }
    Component { id: fitPublication; SignalSpy { signalName: "finished" } }
    Component { id: analysisParameters; ParametersGroup { width: 760; y: 60; z: 1000; tableViewportHeight: 500 } }
    Component { id: pattern; PatternChart { width: 1200; height: 800 } }
    function init() {
        scratch = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/magnetic_pnma/app-project"));
        verify(Session.openProject(scratch), "The magnetic preview opens the independent cobalt input");
        appWindow = application.createObject(null, { width: 1400, height: 1000, visible: true });
        verify(appWindow !== null, "Magnetic display checks use the production application window");
        tryVerify(() => appWindow.pagesBuilt > 0 && appWindow.pagesBuilt === appWindow.pagesWanted, 10000, "The magnetic project builds its real pages");
        tryCompare(Session.project, "calculating", false, 15000, "The initial magnetic calculation finishes");
    }
    function cleanup() {
        Session.closeProject();
        if (repeatFitPreferences !== null) {
            Preferences.engineThreads = repeatFitPreferences.threads;
            Preferences.showFitResults = repeatFitPreferences.showResults;
            repeatFitPreferences = null;
        }
        appWindow.destroy();
    }
    function click(name) { Ui.click(test, Probe, appWindow, name); }
    function groups(page, tier) {
        click("appBar.tab." + page);
        click("sideBar.tab." + tier);
        verify(waitForPolish(appWindow.contentItem), "Magnetic page groups finish layout");
        return Render.descendants(Ui.page(appWindow)).filter(item => typeof item.title === "string" && typeof item.collapsed === "boolean" && (item.shown === true || (item.categoryId === undefined && item.visible)));
    }
    function group(id, page, tier) {
        const found = groups(page || "structure", tier || "basic").filter(item => item.categoryId === id);
        compare(found.length, 1, "Each magnetic category has one displayed group: " + id);
        found[0].collapsed = false;
        Ui.scrollIntoView(found[0]);
        verify(waitForPolish(found[0]), "The opened magnetic category completes layout");
        return found[0];
    }
    function test_extra_groups_are_single_ordered_and_human_readable() {
        const shown = groups("structure", "extras");
        const appearances = shown.filter(item => /^Appearance/.test(item.title));
        compare(appearances.length, 1, "The two preview Appearance groups are merged into one");
        verify(!shown.some(item => item.categoryId === "parent_space_group"), "The crystal parent has no duplicate Extra group");
        verify(!shown.some(item => item.categoryId === "magnetic_form_factor"), "The ion selector belongs to moment rows, not a separate group");
        const ids = shown.map(item => item.categoryId);
        for (const id of ["space_group_symop_magn_operation", "space_group_symop_magn_centering", "expanded_atom_site_moment"])
            verify(ids.includes(id), "Extra retains the signed operators and moments in the cell: " + id);
        const magnetic = shown.filter(item => /magn|moment/.test(item.categoryId));
        verify(magnetic.length > 0, "Extra exposes actual magnetic groups");
        const crystal = shown.filter(item => ["cell", "atom_site", "atom_site_aniso", "space_group_symop"].includes(item.categoryId));
        verify(crystal.every(c => magnetic.every(m => shown.indexOf(c) < shown.indexOf(m))), "Extra magnetic groups follow the existing crystal groups");
        const labels = Render.descendants(Ui.page(appWindow)).filter(item => typeof item.label === "string").map(item => item.label);
        verify(!labels.some(label => /number_BNS|name_BNS|name_UNI/.test(label)), "GUI labels use readable BNS and UNI titles instead of CIF item names");
    }
    function test_main_order_all_sites_ids_ions_and_symmetry_form() {
        const shown = groups("structure", "basic");
        const ids = shown.map(item => item.categoryId);
        const firstMagnetic = ids.findIndex(id => id === "space_group_magn");
        verify(firstMagnetic >= 0, "Main exposes the magnetic space group");
        for (const id of ["space_group", "cell", "atom_site", "atom_site_aniso"])
            verify(ids.indexOf(id) >= 0 && ids.indexOf(id) < firstMagnetic, "Magnetic Main groups follow each crystal group: " + id);
        const moments = group("atom_site_moment");
        const table = Render.descendants(moments).find(item => item.sourceModel !== undefined && typeof item.itemAtIndex === "function");
        verify(table !== undefined, "Moments uses the shared row table");
        compare(table.count, 6, "Moments lists all six atom sites, including sites without a moment");
        verify(/\(6\)/.test(moments.title), "The moments header reports its actual row count");
        const headers = Render.cells(table.headerItem).filter(item => item.visible && item.width > 1);
        verify(headers.some(item => String(item.text).toLowerCase() === "id"), "The first identity column is id, as in Atomic displacement");
        verify(!headers.some(item => String(item.text).toLowerCase() === "label"), "The preview label heading is replaced by id");
        verify(!headers.some(item => /[μµ]B|Bohr/.test(String(item.text))), "Moment units follow shared field tooltips rather than custom column headings");
        const forms = Render.descendants(moments).filter(item => /symmform|symmetry.?form/i.test(item.objectName || ""));
        verify(forms.length > 0, "The derived symmetry form is displayed");
        verify(forms.every(item => !("readOnly" in item) || item.readOnly || !item.enabled), "Symmetry form is read-only in every displayed editor");
        const displacement = group("atom_site_aniso");
        verify(/\(6\)/.test(displacement.title), "Atomic displacement reports all six site rows instead of zero");
    }
    function test_symmetry_form_column_has_room_and_a_gap_after_mz() {
        const moments = group("atom_site_moment");
        const form = findChild(moments, "atomSiteMoment.symmform.0");
        const mx = findChild(moments, "atomSiteMoment.mx.0");
        const my = findChild(moments, "atomSiteMoment.my.0");
        const mz = findChild(moments, "atomSiteMoment.mz.0");
        verify(form && mx && my && mz, "The first cobalt row lays out the symmetry form beside its three components");
        verify(form.readOnly, "The wider symmetry form remains read-only");
        const em = form.font.pixelSize;
        verify(form.width - form.implicitWidth >= em / 2, "The symmetry form has spare width beyond its full expression");
        const gap = (left, right) => right.mapToItem(moments, right.leftPadding, 0).x
            - left.mapToItem(moments, left.width - left.rightPadding, 0).x;
        verify(gap(mz, form) >= gap(mx, my) + em / 4, "The symmetry form has a distinct gap beyond normal component spacing");
    }
    function test_magnetic_column_shows_none_and_aligns_each_choice() {
        const moments = group("atom_site_moment");
        const table = findChild(moments, "atomSiteMoments.list");
        verify(table !== null, "The moments group exposes its rendered table");
        const headers = Render.cells(table.headerItem);
        verify(headers.some(cell => cell.visible && String(cell.text).toLowerCase() === "magnetic"), "The moment choice column is headed magnetic");
        const boxes = [];
        for (let i = 0; i < table.count; ++i) {
            const box = findChild(table.itemAtIndex(i), "atomSiteMoment.ion." + i);
            verify(box && box.visible && box.width > 0, "Each site has a laid-out magnetic combo box");
            boxes.push(box);
        }
        compare(boxes.length, 6, "Every cobalt, silicon and oxygen site has its own choice");
        compare(boxes.map(box => box.currentText), ["Co2+", "Co2+", "none", "none", "none", "none"], "Nonmagnetic sites display none and the cobalt sites display their ion");
        const left = box => box.mapToItem(moments, 0, 0).x;
        for (const box of boxes) {
            verify(Math.abs(left(box) - left(boxes[0])) <= 1, "Magnetic combo boxes share the same left edge");
            verify(Math.abs(box.width - boxes[0].width) <= 1, "Magnetic combo boxes share the same right edge");
        }
        const co = boxes[0];
        const none = Array.from({length: co.count}, (_, i) => i).find(i => co.textAt(i) === "none");
        verify(none !== undefined, "A magnetic site offers none as an explicit choice");
        co.currentIndex = none;
        co.activated(none);
        tryVerify(() => {
            const box = findChild(table.itemAtIndex(0), "atomSiteMoment.ion.0");
            return box && box.currentText === "none";
        }, 3000, "Choosing none removes the cobalt moment from that site");
        const cleared = findChild(table.itemAtIndex(0), "atomSiteMoment.mx.0");
        verify(cleared && cleared.item === null, "Choosing none removes the site's moment parameter as well as its ion");
    }
    function test_moment_colour_preferences_offer_three_schemes() {
        const dialog = preferences.createObject(appWindow.contentItem);
        verify(dialog !== null, "The moment colour check uses the production Preferences dialog");
        dialog.open();
        tryCompare(dialog, "visible", true, 1000, "Preferences opens before checking colour schemes");
        const appearanceTab = findChild(dialog.contentItem, "preferences.tab.appearance");
        verify(appearanceTab !== null, "Preferences provides the Appearance tab");
        mouseClick(appearanceTab);
        verify(waitForPolish(dialog.contentItem), "The Appearance preferences complete layout");
        const items = Render.descendants(dialog.contentItem);
        verify(items.some(item => item.visible && /^Moment colours:?$/.test(item.text || "")), "Appearance labels the selector Moment colours");
        const boxes = items.filter(item => item.visible && typeof item.textAt === "function" && item.count > 0 && item.textAt(0) === "Atom");
        compare(boxes.length, 1, "There is one moment colour selector in Preferences");
        const box = boxes[0];
        compare(Array.from({length: box.count}, (_, i) => box.textAt(i)), ["Atom", "Greyed atom", "Single"], "The moment colour selector offers the three approved schemes");
        compare(box.currentText, "Greyed atom", "Greyed atom is the default in a fresh preference store");
        box.activated(0);
        tryCompare(box, "currentText", "Atom", 1000, "Selecting Atom updates the moment colour preference");
        box.activated(2);
        tryCompare(box, "currentText", "Single", 1000, "Selecting Single updates the moment colour preference");
        dialog.close();
        click("appBar.tab.structure");
        const view = Review.find(Ui.page(appWindow), "structure.view");
        verify(view !== null, "The Single palette is available to the production structure viewer");
        const controller = view.controller;
        const wasDark = controller.dark;
        controller.dark = false;
        const light = controller.styleColor("moment");
        controller.dark = true;
        const dark = controller.styleColor("moment");
        controller.dark = wasDark;
        verify(light.a > 0 && dark.a > 0, "Single supplies a visible moment colour in both palettes");
        verify(light.r === light.g && light.g === light.b && dark.r === dark.g && dark.g === dark.b, "Single retains neutral grey in both palettes");
        verify(dark.r > light.r, "Single uses a lighter grey in the dark palette");
        box.activated(1);
        tryCompare(box, "currentText", "Greyed atom", 1000, "The selector can restore the default scheme");
        dialog.destroy();
    }
    function test_magnetic_selector_and_scale_use_one_editing_surface() {
        const dialog = preferences.createObject(appWindow.contentItem);
        verify(dialog !== null, "The magnetic preference check uses the production dialog");
        dialog.open();
        tryCompare(dialog, "visible", true, 1000, "Preferences opens before checking duplicate controls");
        const appearanceTab = findChild(dialog.contentItem, "preferences.tab.appearance");
        verify(appearanceTab !== null, "The production Appearance preference tab is present");
        mouseClick(appearanceTab);
        verify(waitForPolish(dialog.contentItem), "Preference controls complete their layout");
        const preferenceItems = Render.descendants(dialog.contentItem);
        verify(!preferenceItems.some(item => /moment.*(?:scale|length)|(?:scale|length).*moment/i.test(String(item.text || item.label || item.objectName || ""))), "The moment length preference is removed when project Appearance owns the field");
        dialog.close();
        dialog.destroy();
        const magnetic = group("space_group_magn");
        const selectors = Render.descendants(magnetic).filter(item => typeof item.textAt === "function" && item.editable === true);
        compare(selectors.length, 1, "The magnetic name fields share one searchable selector");
        const appearances = groups("structure", "extras").filter(item => /^Appearance/.test(item.title));
        compare(appearances.length, 1, "Magnetic scale is edited in the single Appearance group");
        appearances[0].collapsed = false;
        const fields = Render.descendants(appearances[0]).filter(item => typeof item.label === "string");
        const atom = fields.find(item => item.label === "Atom scale");
        const moment = fields.find(item => item.label === "Moment scale");
        verify(atom !== undefined && moment !== undefined, "Appearance places Moment scale alongside Atom scale");
        compare(Session.project.structureViewOptions.momentScale, .75, "Default moment length is 1.5 times the preview length");
        Session.project.structureViewOptions.momentScale = 1.125;
        verify(Session.save(), "The selected appearance scale saves through the real project");
        Session.closeProject();
        verify(Session.openProject(scratch), "The saved magnetic appearance reopens");
        compare(Session.project.structureViewOptions.momentScale, 1.125, "Moment scale survives project save and reload");
    }
    function test_visibility_keeps_camera_and_independent_moments() {
        click("appBar.tab.structure");
        const view = Review.find(Ui.page(appWindow), "structure.view");
        verify(view !== null, "The magnetic case reaches the real structure view");
        tryVerify(() => view.current, 10000, "The magnetic scene is current before visibility edits");
        const controller = view.controller;
        controller.viewAnimationDuration = 0;
        const state = () => JSON.stringify({position: controller.cameraPosition, rotation: controller.cameraRotation, projection: controller.cameraProjection, zoom: controller.magnification});
        const before = state();
        const options = Session.project.structureViewOptions;
        for (const change of [["atoms", "none"], ["bonds", false], ["showMoments", false], ["showMoments", true], ["cell", false]]) {
            options[change[0]] = change[1];
            verify(waitForRendering(view), "A visibility edit reaches a rendered frame");
            compare(state(), before, "Showing or hiding structure features preserves camera position, projection and zoom");
        }
        verify(options.showMoments && controller.hasMoments, "Moments remain enabled and present with atoms hidden");
    }
    function test_analysis_contains_only_independent_magnetic_components() {
        click("appBar.tab.analysis");
        const rows = Probe.rows(Session.project.parameters).filter(row => row.category === "atom_site_moment");
        compare(rows.length, 6, "Analysis exposes the six components of the two magnetic sites");
        compare(rows.filter(row => row.fittable).length, 4, "Analysis allows exactly four symmetry-independent cobalt components");
        const filters = Probe.objectsWithProperty(Ui.page(appWindow), "categoryGroups");
        verify(filters.some(filter => filter.categoryGroups.some(row => row.key === "atom_site_moment" && /Magnetic moments/.test(row.title))), "The Analysis category uses the readable Magnetic moments title");
    }
    function test_nuclear_and_magnetic_tick_rows_cover_the_independent_reflections() {
        const chart = pattern.createObject(appWindow.contentItem, {experiment: Session.project.currentExperiment});
        verify(chart !== null && waitForPolish(chart), "The magnetic chart reaches the actual shared controller");
        tryVerify(() => Probe.objectsWithProperty(chart, "braggLabels").length === 1, 5000, "The pattern uses one presentation controller");
        const controller = Probe.objectsWithProperty(chart, "braggLabels")[0];
        tryCompare(controller, "braggRows", 2, 5000, "A magnetic phase has separate nuclear and magnetic tick rows");
        const expected = JSON.parse(SettingsProof.text(Probe.repoUrl("tests/fixtures/magnetic_pnma"), "magnetic-ticks.json"));
        const series = Render.series(chart).filter(item => String(item.objectName).startsWith("chart.series.bragg.") && item.at !== undefined && item.count > 0);
        const magneticRows = series.filter(row => {
            const points = Array.from({length: row.count}, (_, i) => row.at(i).x);
            return expected.every(angle => points.some(x => Math.abs(x - angle) < .0001));
        });
        compare(magneticRows.length, 1, "One tick series contains every independent magnetic reflection, including nuclear-forbidden peaks");
        const magnetic = magneticRows[0];
        const nuclear = series.find(row => row !== magnetic);
        verify(nuclear !== undefined, "The nuclear tick series is present beside the magnetic series");
        verify(String(magnetic.color) !== String(nuclear.color), "The two tick series retain their distinct fill colours");
        const rendered = Render.descendants(chart).filter(item => item.objectName === "chart.bragg.label" && item.visible);
        const labelFor = row => rendered.find(item => Math.abs(item.modelData.centre - row.at(0).y) < .5);
        const magneticLabel = labelFor(magnetic);
        const nuclearLabel = labelFor(nuclear);
        verify(magneticLabel && nuclearLabel, "Each tick series has a visible label at its own row");
        compare(magneticLabel.segments.find(part => part.text !== undefined)?.text, "cosio", "The magnetic tick row shows the phase name without a magnetic suffix");
        compare(nuclearLabel.segments.find(part => part.text !== undefined)?.text, "cosio", "The nuclear tick row shows the same phase name");
        const magnet = magneticLabel.segments.find(part => part.icon !== undefined);
        const structure = nuclearLabel.segments.find(part => part.icon !== undefined);
        compare(magnet?.icon, "magnet", "A magnet icon identifies the magnetic row");
        compare(structure?.icon, "layer-group", "A structure icon identifies the nuclear row");
        compare(String(magnet.color), String(structure.color), "The magnet uses the same phase colour as its nuclear structure icon");
        chart.destroy();
    }
    function test_phase_contributions_draw_two_independent_curves_and_fills() {
        Preferences.structureCurves = true;
        Preferences.patternLegendShown = true;
        const chart = pattern.createObject(appWindow.contentItem, {experiment: Session.project.currentExperiment});
        verify(chart && waitForPolish(chart), "The contribution check uses the production chart");
        const areas = () => Render.series(chart).filter(series => /^chart\.series\.structure\.\d+$/.test(series.objectName));
        tryVerify(() => areas().length === 2 && areas().every(area => area.upperSeries.count > 0 && area.lowerSeries.count > 0), 5000, "One magnetic phase draws two populated contribution fills");
        const [first, second] = areas();
        for (const area of [first, second]) {
            verify(area.outline.count > 0 && area.outline.color.a > 0 && area.color.a > 0, "Each contribution draws a populated visible outline and a visible fill");
            verify(area.upperSeries.count === area.outline.count, "Each contribution fill follows its own curve");
        }
        verify(String(first.outline.color) !== String(second.outline.color), "Nuclear and magnetic contributions use different shades");
        const legend = findChild(chart, "chart.legend");
        verify(legend && legend.visible, "The real chart legend exposes the two phase controls");
        const rows = Render.descendants(legend).filter(item => item.objectName === "chart.legend.entry" && item.visible && !item.bragg && item.segments.some(part => part.text === "cosio"));
        compare(rows.length, 2, "The legend presents two independent controls for the same phase");
        const ticks = Render.series(chart).filter(series => String(series.objectName).startsWith("chart.series.bragg.") && series.count > 0);
        const tickLabels = Render.descendants(chart).filter(item => item.objectName === "chart.bragg.label" && item.visible);
        for (const glyph of ["layer-group", "magnet"]) {
            const label = tickLabels.find(item => item.segments.some(part => part.icon === glyph));
            const entry = rows.find(item => item.segments.some(part => part.icon === glyph));
            verify(label && entry, "The contribution and its tick row share the approved icon: " + glyph);
            const tick = ticks.find(series => Math.abs(series.at(0).y - label.modelData.centre) < .5);
            verify(tick, "Each contribution icon identifies an actual populated tick series");
            verify(areas().some(area => String(area.outline.color) === String(tick.color)), "Each contribution curve matches its tick shade");
        }
        const magnetic = rows.find(item => item.segments.some(part => part.icon === "magnet"));
        legend.toggled(magnetic.key);
        tryVerify(() => areas().filter(area => area.outline.color.a > 0 && area.color.a > 0).length === 1, 2000, "The magnetic legend control hides one curve and fill independently");
        legend.toggled(magnetic.key);
        tryVerify(() => areas().every(area => area.outline.color.a > 0 && area.color.a > 0), 2000, "The magnetic legend control restores its curve and fill");
        chart.destroy();
    }
    function openMagneticFitExample() {
        const project = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-neut-cwl_cosio-d20_2k/project"));
        verify(Session.openProject(project), "The gate opens a disposable copy of the documented 2.3 K fit");
        tryCompare(Session.project, "calculating", false, 15000, "The example's initial measured pattern finishes");
    }
    function checkAnalysisRows(table, block, category, variability, transition) {
        const model = table.sourceModel;
        function count(text) {
            const match = /\((\d+)\)\s*$/.exec(text);
            verify(match !== null, "The active selector publishes its concrete row count");
            return Number(match[1]);
        }
        const scope = [transition, block.displayText, category.displayText, variability.displayText].join(" / ");
        const promised = count(variability.displayText);
        compare(count(category.displayText), promised, "The selected category and parameter counts agree: " + scope);
        if (model.categoryFilter === "")
            compare(count(block.displayText), promised, "The datablock count agrees when all its categories are selected: " + scope);
        tryCompare(table, "count", promised, 1000, "The visible table model lists the promised number of parameters: " + scope);
        const paths = Probe.rows(model).map(row => String(row.path));
        compare(paths.length, promised, "The filter model preserves every promised row: " + scope);
        compare(new Set(paths).size, promised, "The active filters never repeat a parameter identity: " + scope);
        for (let row = 0; row < promised; ++row) {
            table.positionViewAtIndex(row, ListView.Contain);
            table.forceLayout();
            tryVerify(() => Ui.rendered(table.itemAtIndex(row)), 500, "Every promised parameter row becomes visible after scrolling: " + scope + " row " + (row + 1));
            compare(String(table.itemAtIndex(row).path), paths[row], "The rendered row is the actual matching parameter: " + scope);
        }
    }
    function test_analysis_filter_counts_match_every_rendered_row() {
        openMagneticFitExample();
        const controls = analysisParameters.createObject(appWindow.contentItem, {project: Session.project});
        verify(controls && waitForPolish(controls), "The census uses the rendered production Analysis Parameters group");
        const table = Review.find(controls, "parameters.list");
        const block = Review.find(controls, "parameters.datablock");
        const category = Review.find(controls, "parameters.category");
        const variability = Review.find(controls, "parameters.variability");
        verify(table && block && category && variability, "Analysis exposes the real table and all three selectors");
        const model = table.sourceModel;
        model.clearFilters();
        function select(blockIndex, categoryIndex, parameterIndex) {
            block.activated(blockIndex);
            category.activated(categoryIndex);
            variability.activated(parameterIndex);
        }
        const moments = model.categories.indexOf("atom_site_moment");
        verify(moments > 0, "The cobalt fit exposes its magnetic moment category");
        const expected = ["Co1.crystalaxis_x", "Co1.crystalaxis_y", "Co1.crystalaxis_z", "Co2.crystalaxis_y"];
        for (const categoryFirst of [true, false]) {
            model.clearFilters();
            if (categoryFirst) {
                category.activated(moments);
                variability.activated(ParameterFilterModel.Free);
            } else {
                variability.activated(ParameterFilterModel.Free);
                category.activated(moments);
            }
            tryCompare(table, "count", 4, 1000, "Magnetic moments (4) with Free parameters (4) lists four rows in either selection order");
            table.positionViewAtBeginning();
            table.forceLayout();
            verify(waitForPolish(table), "The four-row cobalt repro completes its Analysis layout");
            for (let i = 0; i < 4; ++i)
                verify(Ui.rendered(table.itemAtIndex(i)), "The four cobalt components are visible together without scrolling");
            checkAnalysisRows(table, block, category, variability, "Static census");
            const components = Probe.rows(model).map(row => String(row.rowLabel) + "." + String(row.name)).sort();
            compare(components, expected, "The four rows identify the independent cobalt components");
        }
        const blocks = Array.from(model.datablocks);
        verify(blocks.length >= 3, "The census covers the all, structure and experiment datablock choices");
        for (let b = 0; b < blocks.length; ++b) {
            select(b, 0, ParameterFilterModel.All);
            const categories = Array.from(model.categories);
            for (let c = 0; c < categories.length; ++c) {
                for (let v = 0; v < variability.count; ++v) {
                    select(b, c, v);
                    compare(model.datablockFilter, blocks[b], "The datablock selection survives the other filter changes");
                    compare(model.categoryFilter, categories[c], "The category selection survives the parameter filter changes");
                    checkAnalysisRows(table, block, category, variability, "Static census");
                }
            }
        }
        controls.destroy();
    }
    function test_analysis_filter_counts_survive_repeated_fit_publications_and_tabs() {
        openMagneticFitExample();
        repeatFitPreferences = {threads: Preferences.engineThreads, showResults: Preferences.showFitResults};
        Preferences.engineThreads = 1;
        Preferences.showFitResults = false;
        const fit = Session.project.fit;
        const publication = fitPublication.createObject(appWindow, {target: fit});
        verify(publication && publication.valid, "The repeat witness observes real fit publications");
        function analysisPage() {
            AppState.open(AppState.Page.Analysis);
            tryVerify(() => {
                const page = Ui.page(appWindow);
                return page && page.item && typeof page.item.showMainTab === "function"
                    && Ui.find(page.item, "parameters.list", true)
                    && Math.abs(page.mapToItem(appWindow.contentItem, 0, 0).x) < 1;
            }, 5000, "The real Analysis page returns to the viewport with its Parameters table");
            return Ui.page(appWindow).item;
        }
        function view() {
            const page = Ui.page(appWindow);
            const table = Ui.find(page, "parameters.list", true);
            const block = Ui.find(page, "parameters.datablock", true);
            const category = Ui.find(page, "parameters.category", true);
            const variability = Ui.find(page, "parameters.variability", true);
            verify(table && block && category && variability, "The current Analysis page has the real table and selectors");
            return {table, block, category, variability, model: table.sourceModel};
        }
        function check(transition) {
            const current = view();
            checkAnalysisRows(current.table, current.block, current.category, current.variability, transition);
        }
        function change(kind, key, transition) {
            const current = view();
            const model = current.model;
            const index = kind === "block" ? model.datablocks.indexOf(key)
                : kind === "category" ? model.categories.indexOf(key) : key;
            verify(index >= 0 && index < current[kind].count, "The selected filter option is offered: " + transition);
            current[kind].activated(index);
            const selected = kind === "block" ? model.datablockFilter
                : kind === "category" ? model.categoryFilter : model.variability;
            compare(selected, key, "The production selector applies the requested filter: " + transition);
            check(transition);
        }
        analysisPage();
        const blocks = Array.from(view().model.datablocks);
        const structure = blocks.find(key => key.startsWith("structure:"));
        const experiment = blocks.find(key => key.startsWith("experiment:"));
        verify(structure && experiment, "The repeat witness covers both structure and experiment datablocks");
        change("category", "atom_site_moment", "Initial magnetic category");
        change("variability", ParameterFilterModel.Free, "Initial free moments");
        for (let round = 0; round < 3; ++round) {
            if (round > 0) {
                const moment = Probe.rows(Session.project.parameters).find(row =>
                    row.category === "atom_site_moment" && row.free);
                verify(moment !== undefined, "A subsequent fit can start from a fresh magnetic parameter edit");
                const start = moment.parameter.value + .02;
                moment.parameter.value = start;
                compare(moment.parameter.value, start, "The edited moment reaches the live project before the next fit");
                tryCompare(Session.project, "calculating", false, 15000, "The edited example finishes recalculating");
            }
            const before = publication.count;
            verify(fit.available, "Each repeat round admits a real fit");
            fit.start();
            verify(fit.running, "The fit starts before the page switch");
            AppState.open(AppState.Page.Experiment);
            tryVerify(() => publication.count > before && !fit.running, 25000,
                      "A new fit result is published while Analysis is offscreen");
            verify(Probe.rows(fit.results.agreement).some(row => row.place >= 0),
                   "The new publication contains real measured agreement values");
            const page = analysisPage();
            check("Round " + (round + 1) + " after publication and returning to Analysis");
            page.showMainTab(1);
            tryCompare(page, "mainTabIndex", 1, 1000, "The repeat reaches the Correlations tab");
            check("Round " + (round + 1) + " after Correlations");
            page.showMainTab(0);
            tryCompare(page, "mainTabIndex", 0, 1000, "The repeat returns to the Pattern tab");
            check("Round " + (round + 1) + " after Pattern");
            change("block", structure, "Structure datablock");
            change("category", round % 2 === 0 ? "cell" : "atom_site_moment", "Structure category");
            change("variability", ParameterFilterModel.Free, "Free structure parameters");
            change("category", round % 2 === 0 ? "atom_site_moment" : "cell", "Second structure category");
            change("variability", ParameterFilterModel.All, "All structure parameters");
            change("block", experiment, "Experiment datablock");
            change("category", "instrument", "Instrument category");
            change("variability", ParameterFilterModel.Fixed, "Fixed instrument parameters");
            change("block", "", "All datablocks");
        }
        compare(publication.count, 3, "The filter and tab sequence spans three fresh fit publications");
        publication.destroy();
    }
    function test_fit_from_zero_moments_reaches_reference_and_logs_start() {
        const path = Probe.repoUrl("docs/user/cli/pd-neut-cwl_cosio-d20_2k");
        Preferences.engineThreads = 1;
        const reference = JSON.parse(SettingsProof.text(path, "expected.json")).quantities;
        function fit(zero) {
            openMagneticFitExample();
            const moments = () => Probe.rows(Session.project.parameters).filter(row => row.category === "atom_site_moment" && row.free);
            compare(moments().length, 4, "The 2.3 K fit uses the four free moment components");
            if (zero)
                for (const row of moments())
                    row.parameter.value = 0;
            verify(moments().every(row => (row.parameter.value === 0) === zero), "The fit receives the requested nonzero or all-zero start");
            verify(OnboardingProbe.startHostLog().length > 0, "The test observes the actual fit log");
            const model = Session.project.fit;
            verify(model.available, "The real project admits a fit with the requested moment start");
            model.start();
            tryVerify(() => !model.running && model.outcome !== "", 55000, "The actual minimizer publishes its completed result");
            const log = OnboardingProbe.finishHostLog();
            const notice = log.split("\n").filter(line => /moment/i.test(line) && /start|seed|initial/i.test(line) && /\b1(?:\.0+)?\s*(?:[µμ]B|mu[_ ]?B|Bohr magneton)/i.test(line));
            if (zero)
                verify(notice.length > 0, "The fit log names the one-magneton start for all-zero free moments");
            else
                compare(notice.length, 0, "The fit does not replace the nonzero user start");
            const rows = Probe.rows(model.results.agreement);
            const result = rows.find(row => row.place >= 0);
            verify(result !== undefined, "The completed 2.3 K fit publishes its measured dataset agreement");
            const rwp = Number(result.values[1]) / 100;
            const limit = reference.rwp.value * reference.rwp.tol_rel;
            verify(Math.abs(rwp - reference.rwp.value) <= limit, "The fit reaches the independent fixed-model FullProf Rwp interval");
            const components = moments();
            for (const key of Object.keys(reference).filter(key => key.startsWith("param."))) {
                const row = components.find(row => "param." + row.rowLabel + "." + row.name + ".value" === key);
                verify(row !== undefined, "The completed fit exposes the independently referenced moment: " + key);
                verify(Math.abs(Math.abs(row.parameter.value) - Math.abs(reference[key].value)) <= reference[key].tol_abs, "The fitted component magnitude meets the independent FullProf interval: " + key);
            }
            return rwp;
        }
        const baseline = fit(false);
        const fromZero = fit(true);
        verify(Math.abs(fromZero - baseline) <= reference.rwp.value * reference.rwp.tol_rel, "Zero and nonzero starts reach the same reference minimum within its stated Rwp tolerance");
    }
    function test_k_editor_refuses_without_changing_the_saved_model() {
        const propagation = group("parent_propagation_vector");
        const editors = Render.descendants(propagation).filter(item => typeof item.text === "string" && "readOnly" in item && !item.readOnly && item.enabled);
        verify(editors.length > 0, "Propagation rows expose the validated editable k input");
        verify(Session.save(), "The valid propagation model saves before the refused edit");
        const before = SettingsProof.text(scratch, "structures/cosio.edi");
        const editor = editors[editors.length - 1];
        const old = editor.text;
        editor.forceActiveFocus();
        keyClick(Qt.Key_A, Qt.ControlModifier);
        editor.text = "1/3,0,0";
        keyClick(Qt.Key_Return);
        tryCompare(editor, "text", old, 2000, "The primitive third-order k is refused and the editor restores the old row");
        verify(Session.save(), "A refused k edit leaves a saveable consistent model");
        compare(SettingsProof.text(scratch, "structures/cosio.edi"), before, "A refused GUI propagation edit writes no change to the model");
    }
    function test_catalogue_count_and_selector_operator_replacement() {
        const magnetic = group("space_group_magn");
        const selectors = Render.descendants(magnetic).filter(item => typeof item.textAt === "function" && item.editable === true);
        compare(selectors.length, 1, "The vendored groups reach one searchable magnetic selector");
        const selector = selectors[0];
        compare(selector.count, 1651, "The selector contains every independently counted BNS group");
        function choice(number) {
            for (let i = 0; i < selector.count; ++i)
                if (selector.textAt(i).includes(number)) return i;
            return -1;
        }
        const grey = choice("62.442");
        verify(grey >= 0, "The independent grey Pnma identity is searchable by BNS number");
        selector.currentIndex = grey;
        selector.activated(grey);
        tryCompare(Session.project, "calculating", false, 15000, "The accepted group selection recalculates through the core");
        const moments = Probe.rows(Session.project.parameters).filter(row => row.category === "atom_site_moment");
        verify(moments.length >= 6 && moments.every(row => Number(row.value) === 0), "Selecting grey Pnma replaces signed operators and fixes every moment at zero");
        verify(Session.save(), "The selected grey group saves through the native writer");
        const before = SettingsProof.text(scratch, "structures/cosio.edi");
        verify(before.includes("62.442") && /x,y,z,-1/.test(before.replace(/\s+/g, "")), "The saved BNS identity and negative-time identity agree after selection");
        const incompatible = choice("1.3");
        verify(incompatible >= 0, "The type-IV control is present in the same catalogue");
        selector.currentIndex = incompatible;
        selector.activated(incompatible);
        verify(Session.save(), "A refused incompatible selector choice leaves a saveable prior model");
        compare(SettingsProof.text(scratch, "structures/cosio.edi"), before, "The selector cannot replace operators with a group incompatible with the current propagation");
        verify(Probe.rows(Session.loadWarnings).some(row => /propagation|translation|lattice|magnetic/i.test(row.message)), "A refused magnetic selection gives its acceptance-rule reason");
    }
    function test_primitive_propagation_add_refuses_without_losing_rows() {
        const vectors = group("parent_propagation_vector");
        const objects = Render.descendants(vectors);
        const table = objects.find(item => item.sourceModel !== undefined && typeof item.itemAtIndex === "function");
        verify(table !== undefined && table.count === 1, "Primitive cobalt starts with its one zero propagation row");
        const add = objects.find(item => typeof item.clicked === "function" && item.text === "Add vector");
        verify(add !== undefined, "The primitive model exposes the same Add vector boundary");
        verify(Session.save(), "The primitive model saves before the refused addition");
        const before = SettingsProof.text(scratch, "structures/cosio.edi");
        mouseClick(add);
        compare(table.count, 1, "A primitive cell cannot add another distinct commensurate propagation vector");
        verify(Session.save(), "A refused addition preserves a saveable magnetic model");
        compare(SettingsProof.text(scratch, "structures/cosio.edi"), before, "A refused new vector preserves every prior row and operator");
        verify(Probe.rows(Session.loadWarnings).some(row => /duplicate|propagation|translation|commensurate/i.test(row.message)), "The refused addition states the same acceptance-rule reason as an edit");
    }
    function test_propagation_rows_add_remove_and_refuse_duplicates_data() {
        return [{tag: "fraction-first", first: "1/2", duplicate: "0.5"},
                {tag: "decimal-first", first: "0.5", duplicate: "1/2"}];
    }
    function test_propagation_rows_add_remove_and_refuse_duplicates(data) {
        const location = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/magnetic_pnma/propagation-project"));
        const original = SettingsProof.text(location, "structures/cosio.edi");
        verify(SettingsProof.write(location, "structures/cosio.edi", original.replace("1/2,0,0", data.first + ",0,0")), "The duplicate control independently chooses its exact starting spelling");
        verify(Session.openProject(location), "The period-22 edit control opens with one valid half-order row");
        const vectors = group("parent_propagation_vector");
        const objects = () => Render.descendants(vectors);
        const table = objects().find(item => item.sourceModel !== undefined && typeof item.itemAtIndex === "function");
        verify(table !== undefined && table.count === 1, "The propagation control starts with exactly one row");
        const removes = () => objects().filter(item => typeof item.clicked === "function" && /remove|delete/i.test((item.objectName || "") + " " + (item.toolTip || "")));
        verify(removes().length === 1 && !removes()[0].enabled, "The final propagation row cannot be removed");
        verify(!objects().some(item => /enable|active/i.test(item.objectName || "") && "checked" in item), "Propagation rows have no enable toggle");
        const add = objects().find(item => typeof item.clicked === "function" && item.text === "Add vector");
        verify(add !== undefined && add.width > vectors.width * .6, "A wide Add vector button sits below the propagation table");
        mouseClick(add);
        tryCompare(table, "count", 2, 2000, "Add vector creates a second compatible distinct row");
        verify(Session.save(), "The two accepted propagation rows save");
        const before = SettingsProof.text(location, "structures/cosio.edi");
        const editors = objects().filter(item => typeof item.text === "string" && "readOnly" in item && !item.readOnly && item.enabled);
        verify(editors.length >= 2, "Both propagation rows have real editable k fields");
        const editor = editors[editors.length - 1];
        const old = editor.text;
        for (const value of [data.duplicate + ",0,0", "1/3,0,0"]) {
            editor.forceActiveFocus();
            editor.text = value;
            keyClick(Qt.Key_Return);
            tryCompare(editor, "text", old, 2000, "An exact duplicate or incompatible k restores the previous row");
            verify(Session.save(), "A refused propagation edit keeps a valid saveable row set");
            compare(SettingsProof.text(location, "structures/cosio.edi"), before, "Duplicate and incompatible edits preserve every prior propagation row");
            verify(Probe.rows(Session.loadWarnings).some(row => /duplicate|propagation|translation|commensurate/i.test(row.message)), "Each refused row edit explains the acceptance-rule failure");
        }
        verify(removes().length === 2 && removes().every(item => item.enabled), "Every row can be removed while another remains");
        mouseClick(removes()[1]);
        tryCompare(table, "count", 1, 2000, "Removing a propagation row leaves its peer intact");
        verify(removes().length === 1 && !removes()[0].enabled, "Removal disables again at the last remaining row");
    }
    function test_named_magcif_import_uses_the_app_loader_data() {
        return [{tag: "isodistort", file: "isodistort.mcif"}, {tag: "fullprof", file: "cosio1.mcif"}];
    }
    function test_named_magcif_import_uses_the_app_loader(data) {
        const before = Probe.rows(Session.project.structures).length;
        verify(Session.project.loadStructure(Probe.repoUrl("tests/fixtures/magnetic_pnma/cosio/" + data.file)), "The app imports each independently supplied magnetic CIF");
        compare(Probe.rows(Session.project.structures).length, before + 1, "MagCIF import adds one structure through the core loader");
        if (data.tag === "isodistort")
            verify(Probe.rows(Session.loadWarnings).some(row => /mode/i.test(row.message) && /not.*fit|later|component/i.test(row.message)), "Import explains that retained mode definitions are not yet fittable amplitudes");
        verify(Probe.rows(Session.project.currentStructure.categories).some(row => row.categoryId === "atom_site_moment"), "The imported magnetic category reaches the actual app model");
    }
}
