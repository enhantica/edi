import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import OnboardingAcceptance 1.0
import PatternPolishAcceptance 1.0
import ReportAcceptance 1.0
import ProjectTextAcceptance 1.0
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
    ProjectTextProof { id: dictionaryProof }
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
    function test_sidebar_categories_follow_crysta_dictionary_order() {
        const ranks = dictionaryProof.categoryRanks();
        const differences = [];
        for (const page of ["structure", "experiment"]) {
            for (const tier of ["basic", "extras"]) {
                const context = page + " " + tier;
                const shownTier = tier === "basic" ? "Basic" : "Extras";
                const listed = groups(page, tier).filter(item => item.visible &&
                    item.shownTier === shownTier && item.objectName === "group." + item.categoryId);
                verify(listed.length >= 2, context + " renders multiple dictionary categories");
                const laidOut = listed.map(item => ({
                    id: item.categoryId, y: item.mapToItem(appWindow.contentItem, 0, 0).y
                })).sort((a, b) => a.y - b.y);
                const actual = laidOut.map(item => item.id);
                compare(new Set(actual).size, actual.length, context + " lists every category once: " + actual.join(", "));
                for (let i = 0; i < laidOut.length; ++i) {
                    verify(Number.isInteger(ranks[actual[i]]), context + " category is in crysta's dictionary: " + actual[i]);
                    if (i > 0)
                        verify(laidOut[i].y > laidOut[i - 1].y, context + " gives each category a distinct position");
                }
                if (page === "structure" && tier === "extras") {
                    for (const id of ["geom_bond", "space_group_symop_magn_operation",
                                      "space_group_symop_magn_centering", "expanded_atom_site_moment"])
                        verify(actual.includes(id), context + " reaches the category whose order matters: " + id);
                }
                const expected = actual.slice().sort((a, b) => ranks[a] - ranks[b]);
                if (actual.join(",") !== expected.join(","))
                    differences.push(context + " actual [" + actual.join(", ") + "] expected [" + expected.join(", ") + "]");
            }
        }
        compare(differences.length, 0, "All four sidebars use crysta's category order: " + differences.join("; "));
    }
    function test_extra_groups_are_single_ordered_and_human_readable() {
        Session.closeProject();
        scratch = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-neut-cwl_cosio-d20_2k/project"));
        verify(Session.openProject(scratch), "The published 2.3 K example opens for the Extra sidebar check");
        tryCompare(Session.project, "calculating", false, 15000, "The example's computed Extra groups finish calculating");
        const shown = groups("structure", "extras").filter(item => item.visible &&
            (item.shownTier === "Extras" && item.listed || /^Appearance/.test(item.title)));
        shown.sort((a, b) => a.mapToItem(appWindow.contentItem, 0, 0).y -
                             b.mapToItem(appWindow.contentItem, 0, 0).y);
        const titles = shown.map(item => item.title.replace(/\s*\(\d+\)$/, ""));
        compare(titles, ["Scattering lengths", "Symmetry operators", "Atoms in the cell",
                         "Bonds", "Magnetic operators", "Moments in the cell", "Appearance"],
                "The rendered 2.3 K Extra groups use the approved names and order");
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
    function test_monoclinic_moment_form_selector_edits_and_saves_crystal_axes() {
        Session.closeProject();
        const structureFile = "structures/cosio.edi";
        const fixture = Probe.readFile("tests/fixtures/magnetic_pnma/moment-forms-monoclinic.edi");
        verify(fixture.length > 0 && SettingsProof.write(scratch, structureFile, fixture),
               "The test replaces the disposable project structure with its monoclinic witness");
        verify(Session.openProject(scratch), "The monoclinic cobalt structure opens in the real app");
        tryCompare(Session.project, "calculating", false, 15000, "The monoclinic project settles before editing");
        const forms = ["Crystal axes", "Cartesian", "Spherical"];
        function controls() {
            const moments = group("atom_site_moment");
            const table = findChild(moments, "atomSiteMoments.list");
            verify(table !== null, "The magnetic moment group has its visible component table");
            const candidates = Render.descendants(moments).filter(item => item.visible &&
                typeof item.textAt === "function" &&
                Array.from({length: item.count}, (_, i) => item.textAt(i)).includes("Crystal axes"));
            compare(candidates.length, 1, "The Magnetic moments group has one form selector");
            const box = candidates[0];
            compare(Array.from({length: box.count}, (_, i) => box.textAt(i)), forms,
                    "The form selector offers crystal axes, Cartesian and spherical coordinates");
            verify(box.mapToItem(moments, 0, box.height).y <= table.mapToItem(moments, 0, 0).y + 1,
                   "The form selector sits above the Magnetic moments table");
            tryVerify(() => table.itemAtIndex(0) !== null, 3000,
                      "The cobalt witness renders its magnetic moment row");
            return {box, table};
        }
        function readToken(text) {
            const match = String(text).trim().match(/^([+-]?\d+(?:\.(\d+))?)(?:\((\d+)\))?(?:[eE]([+-]?\d+))?$/);
            verify(match !== null, "The displayed moment cell has a numeric value: " + text);
            const unit = Math.pow(10, Number(match[4] || 0) - (match[2] || "").length);
            return {value: Number(match[1]) * Math.pow(10, Number(match[4] || 0)),
                    su: match[3] === undefined ? null : Number(match[3]) * unit, unit};
        }
        function near(token, expected, reason) {
            verify(Math.abs(token.value - expected) <= token.unit / 2 + 1e-7,
                   reason + " expected " + expected + " observed " + token.value);
        }
        function inspect(form, components, magnitude, uncertainties) {
            const {box, table} = controls();
            const index = forms.indexOf(form);
            if (box.currentIndex !== index) {
                box.currentIndex = index;
                box.activated(index);
            }
            tryCompare(box, "currentText", form, 3000, "The selected coordinate form is displayed");
            verify(waitForPolish(table), "The selected coordinate form settles the moment layout");
            const headers = Render.cells(table.headerItem);
            const magnitudeIndex = headers.findIndex(cell => cell.visible && /^\|\s*M\s*\|$/.test(String(cell.text).trim()));
            verify(magnitudeIndex >= 0, "Every coordinate form shows the |M| column");
            const cells = Render.cells(table.itemAtIndex(0));
            const modulus = cells[magnitudeIndex];
            verify(modulus && modulus.visible && (modulus.readOnly === true || typeof modulus.selectAll !== "function"),
                   "The magnitude column reports a read-only value");
            near(readToken(modulus.text || modulus.value), magnitude, form + " reports the physical moment norm");
            const editors = cells.filter(cell => cell.visible && cell.enabled && cell.readOnly === false &&
                typeof cell.selectAll === "function" && /^[+-]?\d/.test(String(cell.text).trim()));
            compare(editors.length, 3, form + " presents three editable coordinates on the general site");
            for (let axis = 0; axis < 3; ++axis) {
                const token = readToken(editors[axis].text);
                near(token, components[axis], form + " displays component " + axis + " in its selected basis");
                if (uncertainties) {
                    verify(token.su !== null && Math.abs(token.su - uncertainties[axis]) <= token.unit / 2 + 1e-7,
                           form + " displays the independently propagated standard uncertainty of component " + axis);
                }
            }
            return editors;
        }
        const root3 = Math.sqrt(3);
        const crystal = [3 + 4 * root3, 4, 8 * root3];
        const degrees = 180 / Math.PI;
        const spherical = y => [Math.hypot(3, y, 12), Math.atan2(Math.hypot(3, y), 12) * degrees,
                                Math.atan2(y, 3) * degrees];
        // At Cartesian (3,4,12), differentiate r, theta and phi in the crystal basis
        // X=A-C/2, Y=B, Z=C*sqrt(3)/2, with independent crystal s.u. (0.1,0.2,0.3).
        const sphericalSu = [
            Math.hypot(0.3, 0.8, 0.3 * (-1.5 + 6 * root3)) / 13,
            degrees * Math.hypot(0.1 * 7.2, 0.2 * 9.6, 0.3 * (-3.6 - 2.5 * root3)) / 169,
            degrees * Math.hypot(0.1 * 4, 0.2 * 3, 0.3 * 2) / 25
        ];
        inspect("Crystal axes", crystal, 13, [0.1, 0.2, 0.3]);
        inspect("Spherical", spherical(4), 13, sphericalSu);
        const cartesian = inspect("Cartesian", [3, 4, 12], 13,
                                  [Math.hypot(0.1, 0.15), 0.2, 0.15 * root3]);
        const y = cartesian[1];
        Ui.scrollIntoView(y);
        verify(Ui.exposed(y), "The Cartesian Y editor is reachable by real input");
        mouseClick(y);
        y.selectAll();
        keyClick(Qt.Key_6);
        keyClick(Qt.Key_Return);
        tryVerify(() => /^6(?:\D|$)/.test(String(y.text)), 3000, "The Cartesian Y edit commits to the moment");
        const changed = spherical(6);
        inspect("Crystal axes", [crystal[0], 6, crystal[2]], changed[0]);
        inspect("Spherical", changed, changed[0]);
        verify(Session.save(), "The edited spherical view saves the project");
        const saved = SettingsProof.text(scratch, structureFile);
        for (const axis of ["x", "y", "z"])
            verify(saved.includes("_atom_site_moment.crystalaxis_" + axis), "The saved moment has its crystal-axis " + axis + " column");
        verify(!/_atom_site_moment[._](?:Cartn|spherical)_/i.test(saved),
               "The displayed coordinate form leaves alternate moment columns out of the saved structure");
        const momentLoop = saved.split(/^\s*loop_\s*$/m)
            .find(block => /^\s*_atom_site_moment\.label\s*$/m.test(block));
        verify(momentLoop !== undefined, "The saved structure contains the canonical moment loop");
        const tags = [];
        const rows = [];
        for (const line of momentLoop.trim().split(/\r?\n/)) {
            const field = line.trim();
            if (field.startsWith("_atom_site_moment."))
                tags.push(field);
            else if (field.startsWith("CoWitness "))
                rows.push(field.split(/\s+/));
        }
        compare(rows.length, 1, "The canonical moment loop saves one row for the edited site");
        for (const [i, axis] of ["x", "y", "z"].entries()) {
            const column = tags.indexOf("_atom_site_moment.crystalaxis_" + axis);
            verify(column >= 0, "The saved crystal-axis column identifies its numeric field");
            near(readToken(rows[0][column]), [crystal[0], 6, crystal[2]][i],
                 "The saved crystal-axis value preserves the cross-view edit");
        }
        Session.closeProject();
        verify(Session.openProject(scratch), "The saved monoclinic project reopens");
        tryCompare(controls().box, "currentText", "Spherical", 3000, "The form choice persists as a project view preference");
    }
    function test_symmetry_form_column_has_room_and_a_gap_after_mz() {
        const moments = group("atom_site_moment");
        const form = findChild(moments, "atomSiteMoment.symmform.0");
        const mx = findChild(moments, "atomSiteMoment.mx.0");
        const my = findChild(moments, "atomSiteMoment.my.0");
        const mz = findChild(moments, "atomSiteMoment.mz.0");
        verify(form && mx && my && mz, "The first cobalt row lays out the symmetry form beside its three components");
        verify(form.readOnly, "The wider symmetry form remains read-only");
        compare(form.horizontalAlignment, Text.AlignRight, "The symmetry form text is right-aligned");
        const em = form.font.pixelSize;
        verify(form.width - form.implicitWidth >= em / 2, "The symmetry form has spare width beyond its full expression");
        function extent(input) {
            const first = input.positionToRectangle(0);
            const last = input.positionToRectangle(input.text.length);
            return [input.mapToItem(moments, first.x, 0).x,
                    input.mapToItem(moments, last.x, 0).x];
        }
        const gap = (left, right) => extent(right)[0] - extent(left)[1];
        const normal = gap(mx, my);
        const separated = gap(mz, form);
        verify(separated >= normal + em / 4,
               "The rendered text has a distinct gap after Mz: " + separated + " px versus " + normal + " px");
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
        const options = Session.project.structureViewOptions;
        controller.viewAnimationDuration = 0;
        const xyz = v => [v.x, v.y, v.z];
        const quaternion = q => [q.scalar, q.x, q.y, q.z];
        const projection = matrix => [matrix.m11, matrix.m22, matrix.m13, matrix.m23];
        const differences = [];
        function state() {
            const camera = view.view3d ? view.view3d.camera : null;
            const result = {
                position: xyz(controller.cameraPosition),
                orientation: quaternion(controller.cameraRotation),
                zoom: controller.magnification,
                projection: controller.projection,
                effectiveZoom: controller.projection === "perspective"
                    ? projection(controller.cameraProjection) : [controller.orthographicMagnification]
            };
            if (camera) {
                result.drawnPosition = xyz(camera.scenePosition);
                result.drawnOrientation = quaternion(camera.sceneRotation);
                result.drawnZoom = controller.projection === "perspective"
                    ? projection(camera.projection) : [camera.horizontalMagnification, camera.verticalMagnification];
            }
            return result;
        }
        function toggle(control, property) {
            const before = state();
            const beforeValue = options[property];
            const revision = controller.revision;
            click("structure.toolbar." + control);
            tryVerify(() => options[property] !== beforeValue && controller.revision > revision, 5000,
                      control + " toolbar click publishes the changed visibility and scene");
            appWindow.update();
            verify(waitForRendering(view, 5000), control + " reaches a rendered frame with the new visibility");
            const after = state();
            for (const key of Object.keys(before)) {
                if (JSON.stringify(before[key]) !== JSON.stringify(after[key]))
                    differences.push(before.projection + " " + control + " " + beforeValue + " → " +
                                     options[property] + " " + key + " " + JSON.stringify(before[key]) +
                                     " → " + JSON.stringify(after[key]));
            }
        }
        for (let mode = 0; mode < 2; ++mode) {
            if (mode === 1) {
                const beforeProjection = controller.projection;
                click("structure.toolbar.projection");
                tryVerify(() => controller.projection !== beforeProjection, 5000,
                          "The second pass reaches the other projection");
            }
            const beforeZoom = controller.magnification;
            controller.zoomAt(view.width * 0.42, view.height * 0.58, 120);
            tryVerify(() => controller.magnification !== beforeZoom, 5000,
                      "The visibility pass starts from a user-adjusted zoom");
            appWindow.update();
            verify(waitForRendering(view, 5000), "The adjusted camera reaches a rendered frame");
            const baseline = state();
            verify(baseline.position.concat(baseline.orientation, baseline.effectiveZoom).every(Number.isFinite),
                   "The camera snapshot contains real position, orientation and effective zoom numbers");
            const startingAtoms = options.atoms;
            const visited = new Set();
            for (let transition = 0; transition < 3; ++transition) {
                toggle("atoms", "atoms");
                visited.add(options.atoms);
                if (options.atoms === startingAtoms)
                    break;
            }
            compare(options.atoms, startingAtoms, "The atom control completes its whole display cycle");
            verify(visited.has("none") && visited.size >= 2, "The atom cycle both hides and shows atoms");
            for (const [control, property] of [["bonds", "bonds"], ["labels", "showLabels"],
                                               ["moments", "showMoments"], ["cell", "cell"], ["axes", "axes"]]) {
                const original = options[property];
                toggle(control, property);
                toggle(control, property);
                compare(options[property], original, control + " is tested both hidden and shown");
            }
        }
        for (let transition = 0; options.atoms !== "none" && transition < 3; ++transition)
            toggle("atoms", "atoms");
        compare(options.atoms, "none", "The final scene has hidden atoms");
        if (!options.showMoments)
            toggle("moments", "showMoments");
        verify(options.showMoments && controller.hasMoments, "Moments remain enabled and present with atoms hidden");
        compare(differences.length, 0, "Every visibility change keeps the same camera before and after: " + differences.join("; "));
    }
    function test_analysis_contains_only_independent_magnetic_components() {
        click("appBar.tab.analysis");
        const rows = Probe.rows(Session.project.parameters).filter(row => row.category === "atom_site_moment");
        compare(rows.length, 6, "Analysis exposes the six components of the two magnetic sites");
        compare(rows.filter(row => row.fittable).length, 4, "Analysis allows exactly four symmetry-independent cobalt components");
        const filters = Probe.objectsWithProperty(Ui.page(appWindow), "categoryGroups");
        verify(filters.some(filter => filter.categoryGroups.some(row => row.key === "atom_site_moment" && /Magnetic moments/.test(row.title))), "The Analysis category uses the readable Magnetic moments title");
    }
    function tickRows(chart) {
        return PatternProof.series(chart, "chart.series.bragg.").filter(row =>
            row.points.some(point => Number.isFinite(point.y)));
    }
    function tickLabels(chart) {
        return Render.descendants(chart).filter(item =>
            item.objectName === "chart.bragg.label" && item.visible);
    }
    function tickRowFor(rows, label) {
        return rows.find(row => Math.abs(label.modelData.centre - row.points[0].y) < .5);
    }
    function test_nuclear_and_magnetic_tick_rows_cover_the_independent_reflections() {
        openMagneticFitExample();
        const chart = pattern.createObject(appWindow.contentItem, {experiment: Session.project.currentExperiment});
        verify(chart !== null && waitForPolish(chart), "The magnetic chart reaches the actual shared controller");
        const controller = Probe.objectsWithProperty(chart, "braggLabels")[0];
        verify(controller, "The pattern exposes its presentation controller");
        tryCompare(controller, "braggRows", 2, 5000, "A magnetic phase has separate nuclear and magnetic tick rows");
        appWindow.update();
        verify(waitForRendering(chart, 5000), "The chart renders after the tick rows are published");
        tryVerify(() => tickRows(chart).length === 2 && tickLabels(chart).length === 2,
                  5000, "Both tick series and their labels are populated");
        const rows = tickRows(chart);
        const labels = tickLabels(chart);
        const magneticLabel = labels.find(item => item.segments.some(part => part.icon === "magnet"));
        const nuclearLabel = labels.find(item => item.segments.some(part => part.icon === "layer-group"));
        verify(magneticLabel && nuclearLabel, "Each tick series has its own visible structure or magnet icon");
        const magnetic = tickRowFor(rows, magneticLabel);
        const nuclear = tickRowFor(rows, nuclearLabel);
        verify(magnetic && nuclear && magnetic !== nuclear, "Each label identifies a distinct populated tick row");
        verify(String(magnetic.color) !== String(nuclear.color), "The two tick series retain their distinct fill colours");

        const expected = JSON.parse(SettingsProof.text(Probe.repoUrl("tests/fixtures/magnetic_pnma"), "magnetic-ticks.json"));
        const left = controller.xMin;
        const right = controller.xMax;
        const columns = Math.floor(controller.plotWidth * controller.devicePixelRatio);
        verify(columns > 0 && right > left, "The rendered pattern has a nonempty pixel grid");
        const column = x => Math.min(columns - 1, Math.floor((x - left) / (right - left) * columns));
        const occupied = new Map();
        for (const [row, label] of [[magnetic, magneticLabel], [nuclear, nuclearLabel]]) {
            const ticks = [];
            for (const point of row.points) {
                if (Number.isFinite(point.x) && point.y < label.modelData.centre)
                    ticks.push(column(point.x));
            }
            occupied.set(row, new Set(ticks));
            compare(occupied.get(row).size, ticks.length, "A row draws at most one tick per pixel column");
        }
        const eligible = angle => left <= angle && angle <= right &&
            !expected.excluded.some(([lo, hi]) => lo <= angle && angle <= hi);
        const visible = expected.reflections.filter(({angle}) => eligible(angle));
        for (const hkl of ["1,0,0", "0,0,1"])
            verify(visible.some(peak => String(peak.hkl) === hkl), "The view includes the nuclear-forbidden control " + hkl);
        verify(new Set(visible.map(({angle}) => column(angle))).size < visible.length,
               "Independent reflections exercise at least one shared pixel column");
        const missing = visible.filter(({angle}) => !occupied.get(magnetic).has(column(angle)));
        compare(missing.length, 0, "Every visible independent magnetic reflection has a tick in its column: " +
                missing.map(({hkl, angle}) => "(" + hkl + ") at " + angle).join(", "));
        for (const [row, isMagnetic] of [[magnetic, true], [nuclear, false]]) {
            const input = PatternProof.braggInputs(Session.project.currentExperiment, isMagnetic).filter(eligible);
            verify(input.length > 0, "The crystallography engine supplies unbinned reflections for each tick row");
            const expectedColumns = new Set(input.map(column));
            const actualColumns = occupied.get(row);
            const missingColumns = [...expectedColumns].filter(index => !actualColumns.has(index));
            compare(missingColumns.length, 0,
                    "Every eligible " + (isMagnetic ? "magnetic" : "nuclear") + " input reflection is represented in its row");
        }
        compare(magneticLabel.segments.find(part => part.text !== undefined)?.text, "cosio", "The magnetic tick row shows the phase name without a magnetic suffix");
        compare(nuclearLabel.segments.find(part => part.text !== undefined)?.text, "cosio", "The nuclear tick row shows the same phase name");
        const magnet = magneticLabel.segments.find(part => part.icon === "magnet");
        const structure = nuclearLabel.segments.find(part => part.icon === "layer-group");
        compare(String(magnet.color), String(magnetic.color), "The magnet icon matches its own magnetic tick shade");
        compare(String(structure.color), String(nuclear.color), "The structure icon matches its own nuclear tick shade");
        chart.destroy();
    }
    function test_phase_contributions_draw_two_independent_curves_and_fills() {
        openMagneticFitExample();
        Preferences.structureCurves = true;
        Preferences.patternLegendShown = true;
        const chart = pattern.createObject(appWindow.contentItem, {
            experiment: Session.project.currentExperiment,
            settingsPage: "pattern"
        });
        verify(chart && waitForPolish(chart), "The contribution check uses the production chart");
        const controller = Probe.objectsWithProperty(chart, "braggLabels")[0];
        verify(controller, "The pattern exposes its presentation controller");
        const areas = () => Render.series(chart).filter(series => /^chart\.series\.structure\.\d+$/.test(series.objectName));
        appWindow.update();
        verify(waitForRendering(chart, 5000), "The chart renders after the phase fills are published");
        tryVerify(() => areas().length === 2 && areas().every(area => area.upperSeries.count > 0 && area.lowerSeries.count > 0)
                  && tickRows(chart).length === 2, 5000, "One magnetic phase draws two populated contribution fills and tick rows");
        const [first, second] = areas();
        verify(controller.plotHeight > 0, "The contribution fills have a rendered plot height");
        const lift = .05 * (controller.yMax - controller.yMin) / controller.plotHeight;
        for (const area of [first, second]) {
            verify(area.outline.count > 0 && area.outline.color.a > 0 && area.color.a > 0, "Each contribution draws a populated visible outline and a visible fill");
            const edges = new Map();
            for (let i = 0; i < area.upperSeries.count; ++i) {
                const upper = area.upperSeries.at(i);
                const lower = area.lowerSeries.at(i);
                compare(upper.x, lower.x, "The two fill edges share the same horizontal sample");
                if (!edges.has(upper.x))
                    edges.set(upper.x, []);
                edges.get(upper.x).push({upper: upper.y, base: lower.y});
            }
            function closesAt(x) {
                const samples = edges.get(x) || [];
                verify(samples.length > 1 && samples.some(edge =>
                    Math.abs(edge.upper - edge.base - lift) < 1e-8),
                    "The fill closes onto its base beside the gap at " + x + "°");
            }
            let previous = null;
            let inGap = false;
            let internalGaps = 0;
            for (let i = 0; i < area.outline.count; ++i) {
                const point = area.outline.at(i);
                if (!Number.isFinite(point.y)) {
                    if (previous && !inGap) {
                        closesAt(previous.x);
                        inGap = true;
                    }
                    continue;
                }
                if (inGap) {
                    closesAt(point.x);
                    ++internalGaps;
                    inGap = false;
                }
                const matches = edges.get(point.x) || [];
                verify(matches.some(edge => Math.abs(edge.upper - Math.max(point.y, edge.base + lift)) < 1e-8),
                       "Each contribution fill follows its own curve at " + point.x + "°");
                previous = point;
            }
            verify(internalGaps > 0, "The example exercises an internal fill closure");
        }
        verify(String(first.outline.color) !== String(second.outline.color), "Nuclear and magnetic contributions use different shades");
        const legend = findChild(chart, "chart.legend");
        verify(legend && legend.visible, "The real chart legend exposes the two phase controls");
        const rows = Render.descendants(legend).filter(item => item.objectName === "chart.legend.entry" && item.visible && item.bragg && item.segments.some(part => part.text === "cosio"));
        compare(rows.length, 2, "The legend presents two independent controls for the same phase");
        const ticks = tickRows(chart);
        const labels = tickLabels(chart);
        for (const glyph of ["layer-group", "magnet"]) {
            const label = labels.find(item => item.segments.some(part => part.icon === glyph));
            const entry = rows.find(item => item.segments.some(part => part.icon === glyph));
            verify(label && entry, "The contribution and its tick row share the approved icon: " + glyph);
            const tick = tickRowFor(ticks, label);
            verify(tick, "Each contribution icon identifies an actual populated tick series");
            compare(String(entry.segments.find(part => part.icon === glyph).color), String(tick.color),
                    "Each contribution control uses its tick row's shade");
            verify(areas().some(area => String(area.outline.color) === String(tick.color)), "Each contribution curve matches its tick shade");
        }
        const magneticControl = () => Render.descendants(legend).find(item => item.objectName === "chart.legend.entry" &&
            item.bragg && item.visible && item.segments.some(part => part.icon === "magnet"));
        const nuclear = rows.find(item => item.segments.some(part => part.icon === "layer-group"));
        const visibleShades = () => areas().filter(area => area.outline.color.a > 0 && area.color.a > 0 &&
            area.outline.count > 0 && area.upperSeries.count > 0 && area.lowerSeries.count > 0 &&
            Number.isFinite(area.outline.at(0).y) && Number.isFinite(area.upperSeries.at(0).y))
            .map(area => String(area.outline.color));
        function toggleMagnetic(hidden) {
            const row = magneticControl();
            verify(row && legend.toggleAt(row, row.width / 2, row.height / 2),
                   "The production legend accepts the magnetic row's click position");
            tryVerify(() => magneticControl()?.hidden === hidden, 2000,
                      "The magnetic legend entry publishes its changed visibility state");
        }
        const nuclearShade = String(nuclear.color);
        toggleMagnetic(true);
        tryVerify(() => String(visibleShades()) === nuclearShade, 2000, "The magnetic legend control leaves only the nuclear curve and fill visible");
        toggleMagnetic(false);
        tryVerify(() => visibleShades().length === 2, 2000, "The magnetic legend control restores its curve and fill");
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
    function clickPropagationControl(name) { Ui.click(test, Probe, appWindow, name, true); }
    function propagationTable(group) {
        const table = findChild(group, "propagationVectors.list");
        verify(table !== null, "Propagation vectors are displayed in the real row table");
        return table;
    }
    function propagationRows(table) {
        return Probe.rows(table.sourceModel).map(row => [row.id, row.vector]);
    }
    function propagationEditor(table, row) {
        const name = "propagationVector.vector." + row;
        tryVerify(() => table.itemAtIndex(row) && findChild(table.itemAtIndex(row), name), 3000,
                  "The displayed propagation row has its actual editable vector field");
        return findChild(table.itemAtIndex(row), name);
    }
    function enterPropagation(table, row, value) {
        const target = propagationEditor(table, row);
        Ui.scrollIntoView(target);
        clickPropagationControl(target.objectName);
        let editor;
        tryVerify(() => {
            editor = findChild(table.itemAtIndex(row), "propagationVector.vector." + row);
            return editor && editor.activeFocus;
        }, 5000, "The current vector delegate receives keyboard focus after the click");
        editor.selectAll();
        const punctuation = {"/": Qt.Key_Slash, ",": Qt.Key_Comma, ".": Qt.Key_Period};
        for (const character of value)
            keyClick(punctuation[character] ?? (Qt.Key_0 + Number(character)));
        compare(editor.text, value, "The typed vector is in the field before Return");
        keyClick(Qt.Key_Return);
        return editor;
    }
    function inlinePropagationDiagnostic(group, matches, expected) {
        tryVerify(() => {
            const label = findChild(group, "propagationVectors.refusal");
            return label && label.visible && matches(label.text);
        }, 3000, "The inline propagation diagnostic matches the attempted change: " + expected);
        return findChild(group, "propagationVectors.refusal").text;
    }
    function propagationRefusal(group, row, vector) {
        const prefix = "propagation vector '" + row + "' (" + vector + "): ";
        const text = inlinePropagationDiagnostic(group,
            value => value.startsWith(prefix) && value.length > prefix.length, prefix);
        return text.slice(prefix.length);
    }
    function test_k_editor_refuses_without_changing_the_saved_model() {
        const propagation = group("parent_propagation_vector");
        const table = propagationTable(propagation);
        compare(propagationRows(table), [["1", "0,0,0"]], "Primitive cobalt starts at the one zero vector");
        verify(Session.save(), "The valid propagation model saves before the refused edit");
        const before = SettingsProof.text(scratch, "structures/cosio.edi");
        const editor = enterPropagation(table, 0, "1/3,0,0");
        const reason = propagationRefusal(propagation, "1", "1/3,0,0");
        verify(/axis is not a period/i.test(reason), "The edit identifies the incompatible magnetic-cell translation");
        tryCompare(editor, "text", "0,0,0", 3000, "The vector field restores zero after Return");
        keyClick(Qt.Key_Tab);
        tryVerify(() => !editor.activeFocus, 3000, "Tab moves focus away from the refused vector editor");
        compare(propagationEditor(table, 0).text, "0,0,0", "The vector field remains zero after focus leaves it");
        compare(propagationRows(table), [["1", "0,0,0"]], "The refused edit leaves the actual table model unchanged");
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
        const table = propagationTable(vectors);
        compare(propagationRows(table), [["1", "0,0,0"]], "Primitive cobalt starts with its one zero propagation row");
        verify(Session.save(), "The primitive model saves before the refused addition");
        const before = SettingsProof.text(scratch, "structures/cosio.edi");
        clickPropagationControl("propagationVectors.append");
        const addReason = propagationRefusal(vectors, "2", "1/2,0,0");
        verify(/axis is not a period/i.test(addReason), "The Add proposal is incompatible with the primitive cell translation");
        compare(propagationRows(table), [["1", "0,0,0"]], "A refused Add keeps the one original propagation vector");
        const editor = enterPropagation(table, 0, "1/2,0,0");
        const editReason = propagationRefusal(vectors, "1", "1/2,0,0");
        compare(addReason, editReason, "The inline Add and Edit diagnostics have the same acceptance-rule reason for the same vector");
        tryCompare(editor, "text", "0,0,0", 3000, "The refused Edit also restores the original field value");
        verify(Session.save(), "The refused Add and Edit preserve a saveable magnetic model");
        compare(SettingsProof.text(scratch, "structures/cosio.edi"), before, "The refused changes preserve every prior row and operator");
    }
    function test_propagation_rows_add_remove_and_refuse_duplicates_data() {
        return [{tag: "fraction-first", first: "1/2", duplicate: "0.5"},
                {tag: "decimal-first", first: "0.5", duplicate: "1/2"}];
    }
    function test_propagation_rows_add_remove_and_refuse_duplicates(data) {
        Session.closeProject();
        scratch = SettingsProof.copyProject(Probe.repoUrl("tests/fixtures/magnetic_pnma/propagation-project"));
        const file = "structures/cosio.edi";
        const original = SettingsProof.text(scratch, file);
        verify(SettingsProof.write(scratch, file, original.replace("1/2,0,0", "0,0,0")),
               "The period-22 control starts with zero and leaves half order available to Add");
        verify(Session.openProject(scratch), "The period-22 add and edit control opens");
        const vectors = group("parent_propagation_vector");
        const table = propagationTable(vectors);
        compare(propagationRows(table), [["1", "0,0,0"]], "The supercell starts with one zero row");
        const removes = () => Render.descendants(vectors).filter(item => /^propagationVector\.remove\.\d+$/.test(item.objectName));
        verify(removes().length === 1 && !removes()[0].enabled, "The final propagation row cannot be removed");
        verify(!Render.descendants(vectors).some(item => /enable|active/i.test(item.objectName || "") && "checked" in item),
               "Propagation rows have no enable toggle");
        const add = findChild(vectors, "propagationVectors.append");
        verify(add && add.width > vectors.width * .6 &&
               add.mapToItem(vectors, 0, 0).y >= table.mapToItem(vectors, 0, table.height).y,
               "A wide Add vector button sits below the propagation table");
        clickPropagationControl(add.objectName);
        const refusal = findChild(vectors, "propagationVectors.refusal");
        tryCompare(table, "count", 2, 3000, "The half-order proposal adds a distinct row in the period-22 supercell" +
                   (refusal && refusal.visible ? ". Inline refusal: " + refusal.text : ""));
        compare(propagationRows(table), [["1", "0,0,0"], ["2", "1/2,0,0"]],
                "Add keeps zero and publishes the exact half-order vector");
        if (data.first !== "1/2") {
            enterPropagation(table, 1, data.first + ",0,0");
            tryVerify(() => propagationRows(table)[1]?.[1] === data.first + ",0,0", 3000,
                      "A decimal spelling of the same row's half-order vector is accepted");
        }
        const held = [["1", "0,0,0"], ["2", data.first + ",0,0"]];
        verify(Session.save(), "The two accepted propagation rows save");
        const before = SettingsProof.text(scratch, file);
        clickPropagationControl(add.objectName);
        inlinePropagationDiagnostic(vectors, text => /'2' and '3' are the same vector/i.test(text), "duplicate rows 2 and 3");
        compare(propagationRows(table), held, "The duplicate Add preserves both accepted rows");
        for (const value of [data.duplicate + ",0,0", "1/3,0,0"]) {
            const editor = enterPropagation(table, 0, value);
            if (value.startsWith("1/3")) {
                verify(/axis is not a period/i.test(propagationRefusal(vectors, "1", value)),
                       "The inline Edit diagnostic identifies the incompatible translation");
            } else {
                inlinePropagationDiagnostic(vectors, text => /'1' and '2' are the same vector/i.test(text), "duplicate rows 1 and 2");
            }
            tryCompare(editor, "text", "0,0,0", 3000, "A refused k edit restores the previous row after Return");
            compare(propagationRows(table), held, "Each refused Edit preserves both accepted rows");
            verify(Session.save(), "The refused Edit keeps a valid saveable row set");
            compare(SettingsProof.text(scratch, file), before, "Duplicate and incompatible edits preserve every saved propagation row");
        }
        verify(removes().length === 2 && removes().every(item => item.enabled), "Every row can be removed while another remains");
        clickPropagationControl("propagationVector.remove.1");
        tryCompare(table, "count", 1, 3000, "Removing a propagation row leaves its peer intact");
        compare(propagationRows(table), [["1", "0,0,0"]], "Removal preserves the original zero vector");
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
