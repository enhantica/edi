import QtQuick
import QtQuick.Controls
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
import "AtomsSelector.js" as Atoms
import "NumericCellInk.js" as Ink
import "ApprovedPalette.js" as Approved

TestCase {
    id: test
    name: "MagneticPreview"
    when: windowShown
    property var appWindow
    property var scratch
    property var repeatFitPreferences: null
    property var priorChartPalette: null
    ProjectTextProof { id: dictionaryProof }
    Component { id: application; Main {} }
    Component { id: preferences; AppPreferencesDialog {} }
    Component { id: fitPublication; SignalSpy { signalName: "finished" } }
    Component { id: analysisParameters; ParametersGroup { width: 760; y: 60; z: 1000; tableViewportHeight: 500 } }
    Component { id: pattern; PatternChart { width: 1200; height: 800 } }
    Component { id: lightFigure; FigureColors { light: true } }
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
        if (priorChartPalette !== null) {
            Preferences.colourScheme = priorChartPalette;
            priorChartPalette = null;
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
        compare(titles, ["Scattering lengths", "Magnetic form factors", "Symmetry operators", "Atoms in the cell",
                         "Bonds", "Magnetic operators", "Moments in the cell", "Appearance"],
                "The rendered 2.3 K Extra groups use the approved names and order");
    }
    function test_magnetic_operators_are_read_only() {
        const operators = group("space_group_symop_magn_operation", "structure", "extras");
        let table = null;
        tryVerify(() => {
            table = Render.descendants(operators).find(item => item.visible && item.count > 1 &&
                typeof item.itemAtIndex === "function");
            return table !== undefined;
        }, 3000, "The real Extra table lists the magnetic operators");
        for (let i = 0; i < table.count; ++i) {
            table.positionViewAtIndex(i, ListView.Contain);
            table.forceLayout();
            tryVerify(() => Ui.rendered(table.itemAtIndex(i)), 1000, "Each magnetic operator row is reachable");
            const row = table.itemAtIndex(i);
            verify(Render.texts(row).some(cell => /^[^,]*[xyz][^,]*,/.test(cell.text)),
                   "Each operator row visibly displays its coordinate expression");
            const editors = Render.descendants(row).filter(item => item.visible &&
                (typeof item.selectAll === "function" || typeof item.currentIndex === "number"));
            for (const cell of editors)
                verify(cell.readOnly === true || !cell.enabled,
                       "The magnetic operator field is read-only: " + cell.objectName);
        }
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
    function openMonoclinicMomentWitness(withUncertainty = true) {
        Session.closeProject();
        const file = "structures/cosio.edi";
        let fixture = Probe.readFile("tests/fixtures/magnetic_pnma/moment-forms-monoclinic.edi");
        if (!withUncertainty)
            fixture = fixture.replace(/^CoWitness 9\.92820323.*$/m, "CoWitness 9.928 4.125 13.856");
        verify(fixture.length > 0 && SettingsProof.write(scratch, file, fixture),
               "The test installs its independent monoclinic moment witness");
        verify(Session.openProject(scratch), "The monoclinic cobalt witness opens in the app");
        tryCompare(Session.project, "calculating", false, 15000, "The monoclinic calculation finishes");
        tryVerify(() => appWindow.pagesWanted > 0 && appWindow.pagesBuilt === appWindow.pagesWanted,
                  10000, "The monoclinic witness builds its workflow pages");
        return file;
    }
    function momentSelector() {
        const moments = group("atom_site_moment");
        const box = findChild(moments, "atomSiteMoments.form");
        verify(box && box.visible, "The group exposes its real moments-as selector");
        compare(Array.from({length: box.count}, (_, i) => box.textAt(i)), ["Crystal axes", "Cartesian", "Spherical"],
                "The selector offers all three coordinate forms");
        return {box, moments};
    }
    function momentFormView(form) {
        const {box, moments} = momentSelector();
        const index = ["Crystal axes", "Cartesian", "Spherical"].indexOf(form);
        if (box.currentIndex !== index)
            box.activated(index);
        tryCompare(box, "currentText", form, 3000, "The selected coordinate form is displayed");
        let table = null;
        tryVerify(() => {
            table = Render.descendants(moments).find(item => item.visible && item.headerItem &&
                typeof item.itemAtIndex === "function" && item.itemAtIndex(0));
            return table !== undefined;
        }, 3000, "The selected coordinate form renders its actual table and first moment row");
        appWindow.update();
        verify(waitForRendering(table, 5000), "The selected moment table reaches a rendered layout");
        const row = table.itemAtIndex(0);
        const headers = Array.from(table.headerItem.contentRowData).filter(cell => cell.visible);
        const crystalAxes = form === "Crystal axes";
        const modulus = findChild(row, crystalAxes ? "atomSiteMoment.modulus.0" : "atomSiteMoment.formModulus.0");
        const editors = (crystalAxes ? ["mx", "my", "mz"] : ["form.0", "form.1", "form.2"])
            .map(name => findChild(row, "atomSiteMoment." + name + ".0"));
        verify(editors.every(cell => cell && cell.visible && cell.enabled && !cell.readOnly),
               form + " presents three editable coordinates on the general site");
        return {box, moments, table, headers, modulus, editors};
    }
    function readMomentToken(text) {
        const match = String(text).trim().replace(/−/g, "-")
            .match(/^([+-]?\d+(?:\.(\d+))?)(?:\(\d+(?:\.\d+)?\))?(?:[eE]([+-]?\d+))?$/);
        verify(match !== null, "The displayed moment cell has a numeric value: " + text);
        const scale = Math.pow(10, Number(match[3] || 0));
        const unit = scale * Math.pow(10, -(match[2] || "").length);
        return {value: Number(match[1]) * scale, unit};
    }
    function momentNear(token, expected, reason) {
        verify(Math.abs(token.value - expected) <= token.unit / 2 + 1e-7,
               reason + " expected " + expected + " observed " + token.value);
    }
    function twoDigitSuUnit(su) {
        const unit = Math.pow(10, Math.floor(Math.log10(su)) - 1);
        return Math.round(su / unit) === 100 ? 10 * unit : unit;
    }
    function test_magnetic_numeric_cells_draw_the_full_value_and_uncertainty() {
        Session.closeProject();
        const path = "structures/cosio.edi";
        const cobalt = Probe.readFile("tests/fixtures/magnetic_pnma/cosio-2k-reference.edi")
            .replace(/^Co1 0\.701.*$/m, "Co1 1.500(29) 2.800(29) -0.697(29) Mx,My,Mz")
            .replace(/^Co2 0 2\.967.*$/m, "Co2 0 2.640(44) 0 0,My,0");
        verify(cobalt.includes("1.500(29)") && cobalt.includes("2.640(44)") && SettingsProof.write(scratch, path, cobalt),
               "The frozen cobalt witness carries independent decimal values and uncertainties");
        verify(Session.openProject(scratch), "The cobalt clipping witness opens at the default sidebar width");
        tryVerify(() => appWindow.pagesBuilt > 0 && appWindow.pagesBuilt === appWindow.pagesWanted,
                  10000, "The reopened project builds its actual sidebar");
        const moments = group("atom_site_moment");
        const table = Render.descendants(moments).find(item => item.visible && item.headerItem &&
            typeof item.itemAtIndex === "function");
        verify(table && table.count >= 2, "The real moments table displays both cobalt rows");

        // The orthogonal norm of (1.500,2.800,-0.697) rounds to 3.252. Equal
        // component uncertainties propagate unchanged to its norm. Co2 lies on y.
        const expected = [["1.500(29)", "2.800(29)", "-0.697(29)", "3.252(29)"],
                          ["0", "2.640(44)", "0", "2.640(44)"]];
        const issues = [];
        for (const [rowIndex, values] of expected.entries()) {
            table.positionViewAtIndex(rowIndex, ListView.Contain);
            table.forceLayout();
            tryVerify(() => table.itemAtIndex(rowIndex) !== null, 2000, "The actual cobalt row is materialised");
            appWindow.update();
            verify(waitForRendering(table, 5000), "The cobalt row reaches a rendered frame at the default width");
            for (const [columnIndex, column] of ["mx", "my", "mz", "modulus"].entries()) {
                const cell = findChild(table.itemAtIndex(rowIndex), "atomSiteMoment." + column + "." + rowIndex);
                verify(cell !== null, "The cobalt row has the numeric column " + column);
                issues.push(...Ink.problems(cell, values[columnIndex], "Co" + (rowIndex + 1) + " " + column));
            }
        }
        compare(issues.length, 0, "Every cobalt cell draws its full value and uncertainty: " + issues.join("; "));
    }
    function test_moment_form_layout_and_alignment() {
        openMonoclinicMomentWitness();
        const differences = [];
        for (const form of ["Crystal axes", "Cartesian", "Spherical"]) {
            const {box, moments, table, headers, modulus, editors} = momentFormView(form);
            const names = headers.map(cell => String(cell.text));
            const magCount = names.filter(name => /^\|\s*M\s*\|$/.test(name)).length;
            if (magCount !== 1 || (form === "Spherical" && modulus?.visible))
                differences.push(form + " shows " + magCount + " magnitude headers or a repeated magnitude cell");
            const magnitude = form === "Spherical" ? editors[0] : modulus;
            if (!magnitude || magnitude.horizontalAlignment !== Text.AlignRight)
                differences.push(form + " magnitude is not right aligned");
            if (Math.abs(box.width - table.width) > 1 ||
                Math.abs(box.mapToItem(moments, 0, 0).x - table.mapToItem(moments, 0, 0).x) > 1)
                differences.push(form + " selector width " + box.width + " differs from group content " + table.width);
            if (box.label !== "Moments as" ||
                box.mapToItem(moments, 0, box.height).y > table.mapToItem(moments, 0, 0).y + 1)
                differences.push(form + " selector is not labelled and placed above the table");
            if (form !== "Spherical" && magnitude) {
                const widths = editors.concat([magnitude]).map(cell => cell.width);
                if (Math.max(...widths) - Math.min(...widths) > 1)
                    differences.push(form + " component and magnitude widths differ: " + widths.join(", "));
            }
            if (names[names.length - 1] !== "Symmetry")
                differences.push("the last " + form + " column is " + names[names.length - 1]);
            if (form === "Cartesian" && (!names.includes("Mx (x ∥ a)") || !names.includes("Mz (z ∥ c*)")))
                differences.push("Cartesian headers do not use U+2225: " + names.join(", "));
        }
        compare(differences.length, 0, "Moment table layout follows the approved forms: " + differences.join("; "));
    }
    function test_derived_moments_use_component_decimals_without_uncertainty() {
        openMonoclinicMomentWitness(false);
        const cartesian = [9.928 - 13.856 / 2, 4.125, 13.856 * Math.sqrt(3) / 2];
        const [x, y, z] = cartesian;
        const norm = Math.hypot(x, y, z);
        const spherical = [norm, Math.atan2(Math.hypot(x, y), z) * 180 / Math.PI,
                           Math.atan2(y, x) * 180 / Math.PI];
        const differences = [];
        for (const form of ["Crystal axes", "Cartesian", "Spherical"]) {
            const {modulus, editors} = momentFormView(form);
            const cells = form === "Crystal axes" ? [[modulus, norm]] :
                form === "Cartesian" ? editors.map((cell, i) => [cell, cartesian[i]]).concat([[modulus, norm]]) :
                editors.map((cell, i) => [cell, spherical[i]]);
            for (const [cell, expected] of cells) {
                verify(cell && cell.visible, form + " shows each derived value");
                const token = readMomentToken(cell.text);
                if (Math.abs(token.unit - .001) > 1e-12 || Math.abs(token.value - expected) > .0005001)
                    differences.push(form + " shows " + cell.text + " for " + expected.toFixed(3));
            }
        }
        compare(differences.length, 0, "Derived values inherit three input decimals without s.u.: " + differences.join("; "));
    }
    function test_monoclinic_moment_form_selector_edits_and_saves_crystal_axes() {
        const structureFile = openMonoclinicMomentWitness();
        momentNear(readMomentToken("13.00(22)"), 13, "Bracketed uncertainty preserves the preceding magnitude");
        function inspect(form, components, magnitude, uncertainties, modulusUncertainty) {
            const {headers, modulus, editors} = momentFormView(form);
            const crystalAxes = form === "Crystal axes";
            const spherical = form === "Spherical";
            compare(headers.filter(cell => /^\|\s*M\s*\|$/.test(String(cell.text).trim())).length,
                    1, "Each form displays the magnitude once");
            if (!spherical) {
                verify(modulus && modulus.visible && modulus.readOnly,
                       "The Cartesian and crystal-axis magnitude cells are read-only");
                const token = readMomentToken(modulus.text);
                momentNear(token, magnitude, form + " reports the physical moment norm");
                if (modulusUncertainty !== undefined)
                    verify(Math.abs(token.unit - twoDigitSuUnit(modulusUncertainty)) < 1e-12,
                           form + " displays the norm at its propagated uncertainty precision");
            }
            for (let axis = 0; axis < 3; ++axis) {
                const cell = editors[axis];
                const token = readMomentToken(cell.text);
                momentNear(token, components[axis], form + " displays component " + axis + " in its selected basis");
                if (uncertainties && crystalAxes) {
                    verify(cell.item.fileSu !== "", form + " shows a separate uncertainty for component " + axis);
                    momentNear(readMomentToken(cell.item.fileSu), uncertainties[axis],
                               form + " shows the independently referenced uncertainty of component " + axis);
                } else if (uncertainties) {
                    verify(Math.abs(token.unit - twoDigitSuUnit(uncertainties[axis])) < 1e-12,
                           form + " displays component " + axis + " at its propagated uncertainty precision");
                    const tooltip = String(cell.ToolTip.text);
                    verify(/^s\.u\.\s+/.test(tooltip), form + " labels the propagated uncertainty");
                    momentNear(readMomentToken(tooltip.replace(/^s\.u\.\s+/, "")), uncertainties[axis],
                               form + " reports the independently propagated uncertainty of component " + axis);
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
        inspect("Crystal axes", crystal, 13, [0.1, 0.2, 0.3], sphericalSu[0]);
        inspect("Spherical", spherical(4), 13, sphericalSu);
        const cartesian = inspect("Cartesian", [3, 4, 12], 13,
                                  [Math.hypot(0.1, 0.15), 0.2, 0.15 * root3], sphericalSu[0]);
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
            momentNear(readMomentToken(rows[0][column]), [crystal[0], 6, crystal[2]][i],
                 "The saved crystal-axis value preserves the cross-view edit");
        }
        Session.closeProject();
        verify(Session.openProject(scratch), "The saved monoclinic project reopens");
        tryCompare(momentSelector().box, "currentText", "Spherical", 3000, "The form choice persists as a project view preference");
    }
    function test_symmetry_form_column_has_room_and_a_gap_after_mz() {
        const moments = group("atom_site_moment");
        const form = findChild(moments, "atomSiteMoment.symmform.0");
        const mx = findChild(moments, "atomSiteMoment.mx.0");
        const my = findChild(moments, "atomSiteMoment.my.0");
        const magnitude = findChild(moments, "atomSiteMoment.modulus.0");
        verify(form && mx && my && magnitude, "The first cobalt row lays out symmetry after its magnitude");
        verify(form.readOnly, "The wider symmetry form remains read-only");
        compare(form.horizontalAlignment, Text.AlignRight, "The symmetry form text is right-aligned");
        const em = form.font.pixelSize;
        verify(Math.abs(form.x + form.width - form.parent.width) <= 1,
               "The final symmetry column fills the remaining row width");
        function extent(input) {
            const first = input.positionToRectangle(0);
            const last = input.positionToRectangle(input.text.length);
            return [input.mapToItem(moments, first.x, 0).x,
                    input.mapToItem(moments, last.x, 0).x];
        }
        const gap = (left, right) => extent(right)[0] - extent(left)[1];
        const normal = gap(mx, my);
        const separated = gap(magnitude, form);
        verify(separated >= normal + em / 4,
               "The rendered text leaves a distinct gap before symmetry: " + separated + " px versus " + normal + " px");
    }
    function test_magnetic_column_shows_none_and_aligns_each_choice() {
        const moments = group("atom_site_moment");
        const table = findChild(moments, "atomSiteMoments.list");
        verify(table !== null, "The moments group exposes its rendered table");
        const headers = Render.cells(table.headerItem);
        verify(headers.some(cell => cell.visible && String(cell.text) === "Magnetic"), "The moment choice column is headed Magnetic");
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
    function test_form_factor_group_edits_and_fits_its_ion_coefficients() {
        Session.closeProject();
        const path = "structures/cosio.edi";
        const witness = Probe.readFile("tests/fixtures/magnetic_pnma/form-factor-ions.edi");
        verify(witness.length > 0 && SettingsProof.write(scratch, path, witness),
               "The scratch structure has two Ho sites, one Er site and a nonmagnetic oxygen");
        verify(Session.openProject(scratch), "The two-ion form-factor witness opens through the app");
        tryVerify(() => appWindow.pagesBuilt > 0 && appWindow.pagesBuilt === appWindow.pagesWanted,
                  10000, "The form-factor witness builds its Structure workflow");
        const factors = group("magnetic_form_factor", "structure", "extras");
        verify(factors.title.startsWith("Magnetic form factors"),
               "Structure Extra names the Magnetic form factors group");
        const table = Render.descendants(factors).find(item => item.visible && item.headerItem &&
            typeof item.itemAtIndex === "function");
        verify(table, "The group lays out its production ion table");
        compare(table.count, 2, "Repeated Ho shares one ion row, Er has one row and oxygen has none");

        const ions = {};
        for (let index = 0; index < table.count; ++index) {
            table.positionViewAtIndex(index, ListView.Contain);
            table.forceLayout();
            tryVerify(() => table.itemAtIndex(index) !== null, 2000, "The ion row has been materialised");
            const row = table.itemAtIndex(index);
            const ion = Render.descendants(row).find(item =>
                item.visible && /^(Ho|Er)(3|³)(\+|⁺)$/.test(String(item.text)));
            verify(ion && (ion.readOnly === true || typeof ion.positionToRectangle !== "function"),
                   "The ion identity is displayed and read-only");
            ions[String(ion.text).slice(0, 2)] = index;
        }
        compare(Object.keys(ions).sort(), ["Er", "Ho"], "Each independently declared ion has one row");
        const rowIndex = ions.Ho;
        table.positionViewAtIndex(rowIndex, ListView.Contain);
        table.forceLayout();

        function row() { return table.itemAtIndex(rowIndex); }
        const combo = Render.descendants(row()).find(item => item.visible && typeof item.textAt === "function");
        verify(combo && combo.count === 3, "The Ho ion row offers three approximation choices");
        const entries = Array.from({length: combo.count}, (_, index) => combo.textAt(index));
        const beyond = entries.findIndex(text => /beyond|j[6₆]/i.test(text));
        const dipole = entries.findIndex((text, index) => index !== beyond && /dipole/i.test(text));
        const j0 = entries.findIndex((text, index) => index !== beyond && index !== dipole && /j[0₀]/i.test(text));
        verify(new Set([j0, dipole, beyond]).size === 3 && Math.min(j0, dipole, beyond) >= 0,
               "The actual choices name j0, dipole and beyond dipole");
        function select(index) {
            if (combo.currentIndex === index)
                return;
            Ui.scrollIntoView(combo);
            tryVerify(() => Ui.exposed(combo), 2000, "The approximation control is exposed");
            mouseClick(combo);
            tryCompare(combo.popup, "opened", true, 2000, "A real click opens the approximation choices");
            const list = combo.popup.contentItem;
            tryVerify(() => list.itemAtIndex(index) && Ui.exposed(list.itemAtIndex(index)), 2000,
                      "The named approximation can be clicked in the popup");
            mouseClick(list.itemAtIndex(index));
            tryCompare(combo, "currentIndex", index, 2000, "Choosing an approximation updates the ion row");
        }
        function editableCoefficients() {
            const result = new Map();
            for (const cell of Render.descendants(row())) {
                const name = String(cell.item?.name ?? cell.objectName ?? "");
                const order = name.match(/(?:j|c)([246])(?:_coefficient)?(?:[.\d]*$)/i);
                if (order && cell.item && cell.visible && cell.enabled && !cell.readOnly)
                    result.set(Number(order[1]), cell);
            }
            return result;
        }
        select(dipole);
        tryVerify(() => editableCoefficients().has(2), 3000, "The dipole row exposes its C2 editor");
        const c2 = editableCoefficients().get(2);
        tryCompare(c2.item, "value", .25, 3000, "The Ho coefficient reads its independently declared starting value");
        const tooltip = [c2.ToolTip.text, ...Render.descendants(c2).map(item => item.text)].join(" ");
        verify(/land[eé]/i.test(tooltip) && /\bg\s*[:=≈]\s*1[.,]6(?:0+)?(?![\d.])/i.test(tooltip),
               "The C2 tooltip gives the matching Landé g of 1.6 from 2/(1+0.25)");

        for (const [choice, expected] of [[j0, []], [dipole, [2]], [beyond, [2, 4, 6]]]) {
            select(choice);
            tryVerify(() => JSON.stringify([...editableCoefficients().keys()].sort()) === JSON.stringify(expected),
                      3000, "Only the coefficients of the selected approximation can be edited: " + entries[choice]);
        }
        for (const order of [2, 4, 6]) {
            const cell = editableCoefficients().get(order);
            verify(cell?.item.fittable, "The active coefficient is fittable: C" + order);
            Ui.scrollIntoView(cell);
            tryVerify(() => Ui.exposed(cell), 2000, "The coefficient editor is reachable: C" + order);
            mouseClick(cell);
            cell.selectAll();
            keyClick(Qt.Key_1);
            keyClick(Qt.Key_Return);
            tryCompare(cell.item, "value", 1, 3000, "A real edit updates the model coefficient: C" + order);
            const fit = cell.fitCheckBox;
            verify(fit && fit.enabled && fit.visible, "The active coefficient has a usable Free control: C" + order);
            if (!cell.item.free)
                mouseClick(fit);
            tryCompare(cell.item, "free", true, 3000, "The Free control publishes the fitting state: C" + order);
        }
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
    function checkVisibilityViews(reference) {
        tryVerify(() => appWindow.pagesBuilt > 0 && appWindow.pagesBuilt === appWindow.pagesWanted,
                  10000, "The Structure pages finish building");
        click("appBar.tab.structure");
        const view = Review.find(Ui.page(appWindow), "structure.view");
        verify(view !== null, "The magnetic case reaches the real structure view");
        tryVerify(() => view.current, 10000, "The magnetic scene is current before visibility edits");
        const controller = view.controller;
        const options = Session.project.structureViewOptions;
        controller.viewAnimationDuration = 0;
        options.momentView = "through_atom";
        const xyz = v => [v.x, v.y, v.z];
        const quaternion = q => [q.scalar, q.x, q.y, q.z];
        const projection = m => [m.m11, m.m22, m.m13, m.m23];
        function cameraState() {
            const camera = view.view3d ? view.view3d.camera : null;
            return [
                xyz(controller.cameraPosition), quaternion(controller.cameraRotation),
                controller.magnification, controller.projection,
                controller.projection === "perspective" ? projection(controller.cameraProjection) : [controller.orthographicMagnification],
                camera ? [xyz(camera.scenePosition), quaternion(camera.sceneRotation),
                          controller.projection === "perspective" ? projection(camera.projection) :
                              [camera.horizontalMagnification, camera.verticalMagnification]] : []
            ];
        }
        function change(control, property, action = null) {
            const before = cameraState();
            const prior = options[property];
            const revision = controller.revision;
            if (action)
                action();
            else
                click("structure.toolbar." + control);
            tryVerify(() => options[property] !== prior && controller.revision > revision, 5000,
                      control + " input publishes changed visibility and scene");
            appWindow.update();
            verify(waitForRendering(view, 5000), control + " reaches a rendered frame with the new visibility");
            compare(cameraState(), before, reference.name + " " + control + " keeps camera position, orientation and zoom");
        }
        function samePoint(left, right) {
            return left.every((coordinate, axis) => Math.abs(coordinate - right[axis]) < 0.0001);
        }
        function verifySites(orbits, positions, context) {
            const hits = orbits.map(() => 0);
            for (const p of positions) {
                const index = orbits.findIndex(orbit => orbit.some(q => samePoint(p, q)));
                verify(index >= 0, context + " draws only reference coordinates: " + JSON.stringify(p));
                ++hits[index];
            }
            compare(hits, orbits.map(() => 1), context + " draws one instance per expected position or orbit");
        }
        const combo = Ui.control(Probe, appWindow, "structure.toolbar.atoms");
        const entries = ["All", "Asymmetric unit (crystal)", "Asymmetric unit (magnetic)", "Magnetic atoms", "None"];
        const spheres = controller.spheres;
        verifySites(reference.all, Array.from({length: spheres.count}, (_, row) => xyz(spheres.instancePosition(row))),
                    reference.name + " default All atoms");
        Atoms.checkEntries(test, combo, entries);
        function select(index) {
            const label = entries[index];
            if (combo.currentText !== label)
                change("atoms", "atoms", () => Atoms.select(test, appWindow, combo, label));
        }
        function verifyView(index, moments, atomOrbits, arrowOrbits) {
            select(index);
            if (moments !== options.showMoments)
                change("moments", "showMoments");
            const context = reference.name + " " + entries[index] + " moments " + (moments ? "on" : "off");
            const spheres = controller.spheres;
            const shafts = controller.triadShafts;
            const heads = controller.triadHeads;
            const centres = Array.from({length: spheres.count}, (_, row) => xyz(spheres.instancePosition(row)));
            verifySites(atomOrbits, centres, context + " atoms");
            compare(shafts.count, heads.count, context + " every arrow has a shaft and a head");
            const anchors = Array.from({length: shafts.count}, (_, row) => {
                // Recover the centre of the whole arrow from the two mesh centres and lengths.
                const shaft = xyz(shafts.instancePosition(row));
                const head = xyz(heads.instancePosition(row));
                const headLength = heads.instanceScale(row).y;
                const fraction = headLength / (shafts.instanceScale(row).y + headLength);
                return shaft.map((v, axis) => v + fraction * (head[axis] - v));
            });
            verifySites(arrowOrbits, anchors, context + " moments");
            if (atomOrbits.length)
                verify(anchors.every(anchor => centres.some(centre => samePoint(anchor, centre))),
                       context + " anchors every arrow on a displayed magnetic atom");
        }
        for (let mode = 0; mode < 2; ++mode) {
            if (mode === 1) {
                const beforeProjection = controller.projection;
                click("structure.toolbar.projection");
                tryVerify(() => controller.projection !== beforeProjection, 5000, "Both projections are exercised");
            }
            const beforeZoom = controller.magnification;
            controller.zoomAt(view.width * 0.42, view.height * 0.58, 120);
            tryVerify(() => controller.magnification !== beforeZoom, 5000, "Visibility starts from an adjusted zoom");
            appWindow.update();
            verify(waitForRendering(view, 5000), "The adjusted camera reaches a rendered frame");
            const [position, orientation, zoom] = cameraState();
            verify(position.concat(orientation, zoom).every(Number.isFinite),
                   "The camera contains finite position, orientation and zoom");
            if (options.axes)
                change("axes", "axes");
            for (const args of [
                [0, false, reference.all, []], [1, false, reference.crystal, []],
                [2, false, reference.magnetic, []], [0, true, reference.all, reference.cobalt],
                [3, true, reference.cobalt, reference.cobalt], [4, true, [], reference.cobalt],
                [1, true, reference.crystal, reference.crystalCobalt],
                [2, true, reference.magnetic, reference.magneticCobalt], [4, true, [], reference.cobalt]
            ])
                verifyView(...args);
            for (const [control, property] of [["bonds", "bonds"], ["labels", "showLabels"],
                                               ["moments", "showMoments"], ["cell", "cell"], ["axes", "axes"]]) {
                if (!Ui.control(Probe, appWindow, "structure.toolbar." + control)) {
                    verify(control === "bonds" && reference.name === "Doubled parent cell",
                           "Every applicable visibility control is available");
                    continue;
                }
                const original = options[property];
                change(control, property);
                change(control, property);
                compare(options[property], original, control + " is tested both hidden and shown");
            }
        }
    }
    function test_visibility_keeps_camera_and_independent_moments_data() {
        return [{tag: "pnma", doubled: false}, {tag: "doubled", doubled: true}];
    }
    function test_visibility_keeps_camera_and_independent_moments(data) {
        const flatten = lists => [].concat(...lists);
        const singletons = points => points.map(point => [point]);
        if (!data.doubled) {
            // ISODISTORT Pnma.1 operations and the published 2.344 K sites.
            const operations = [
                ([x,y,z]) => [x,y,z], ([x,y,z]) => [x+0.5,-y+0.5,-z+0.5],
                ([x,y,z]) => [-x,y+0.5,-z], ([x,y,z]) => [-x+0.5,-y,z+0.5],
                ([x,y,z]) => [-x,-y,-z], ([x,y,z]) => [-x+0.5,y+0.5,z+0.5],
                ([x,y,z]) => [x,-y+0.5,z], ([x,y,z]) => [x+0.5,y,-z+0.5]
            ];
            const sites = [[0,0,0], [0.2809,0.25,0.9836], [0.0933,0.25,0.4278],
                           [0.0896,0.25,0.773], [0.4478,0.25,0.2179], [0.1639,0.0321,0.2805]];
            const periodic = sites.map(site => [...new Set(operations.map(op =>
                op(site).map(x => (x - Math.floor(x)).toFixed(6)).join(",")))].map(key => key.split(",").map(Number)));
            compare(periodic.map(orbit => orbit.length), [4,4,4,4,4,8],
                    "Independent Pnma and Pnma.1 operations give the published Wyckoff multiplicities");
            // A closed cell includes the adjacent image on each face of a boundary site.
            const images = x => x === 0 ? [0, 1] : [x];
            const display = periodic.map(orbit => {
                const points = [];
                for (const [x, y, z] of orbit)
                    for (const a of images(x))
                        for (const b of images(y))
                            for (const c of images(z))
                                points.push([a*10.308064, b*6.002187, c*4.787394]);
                return points;
            });
            checkVisibilityViews({
                name: "2.344 K cobalt olivine", all: singletons(flatten(display)),
                crystal: display, magnetic: display, cobalt: singletons(flatten(display.slice(0, 2))),
                crystalCobalt: display.slice(0, 2), magneticCobalt: display.slice(0, 2)
            });
            return;
        }

        Session.closeProject();
        const file = Probe.readFile("tests/fixtures/magnetic_pnma/doubled-atom-orbits.edi");
        verify(file.length > 0 && SettingsProof.write(scratch, "structures/cosio.edi", file),
               "The scratch project carries the doubled parent-cell witness");
        verify(Session.openProject(scratch), "The doubled parent-cell project opens");
        // The P1 child's magnetic identity leaves each site alone. Parent translation
        // (1/2,0,0) in the child basis pairs the two Co and two O sites.
        const positions = [[1,1.5,3], [5,1.5,3], [2,3,6], [6,3,6]];
        const magnetic = singletons(positions);
        checkVisibilityViews({
            name: "Doubled parent cell", all: magnetic, magnetic: magnetic,
            crystal: [positions.slice(0, 2), positions.slice(2)], cobalt: magnetic.slice(0, 2),
            crystalCobalt: [positions.slice(0, 2)], magneticCobalt: magnetic.slice(0, 2)
        });
        for (const label of ["Asymmetric unit (crystal)", "Asymmetric unit (magnetic)", "Magnetic atoms", "None", "All"]) {
            const combo = Ui.control(Probe, appWindow, "structure.toolbar.atoms");
            Atoms.select(test, appWindow, combo, label);
            const selected = Session.project.structureViewOptions.atoms;
            verify(Session.save(), "The project saves with the selected Atoms view");
            Session.closeProject();
            verify(Session.openProject(scratch), "The saved Atoms view reopens from disk");
            tryCompare(Session.project.structureViewOptions, "atoms", selected, 2000,
                       "The selected appearance value survives save and reload");
            tryVerify(() => appWindow.pagesBuilt > 0 && appWindow.pagesBuilt === appWindow.pagesWanted, 10000,
                      "The saved Structure pages rebuild before reading the Atoms selector");
            click("appBar.tab.structure");
            tryVerify(() => {
                const reopened = Ui.control(Probe, appWindow, "structure.toolbar.atoms");
                return reopened && reopened.currentText === label;
            }, 5000, "The toolbar restores the selected view after reload");
        }
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
        openCobaltProject("pd-neut-cwl_cosio-d20_2k", true);
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
        priorChartPalette = Preferences.colourScheme;
        Preferences.colourScheme = "earth";
        const expectedPalette = Approved.colours(Probe, "earth", "structures", 2, false,
                                                 {experiments: 1, structures: 2});
        Preferences.structureCurves = true;
        Preferences.patternLegendShown = true;
        const chart = pattern.createObject(appWindow.contentItem, {
            experiment: Session.project.currentExperiment,
            settingsPage: "pattern",
            colors: createTemporaryObject(lightFigure, appWindow)
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
        const actualPalette = [];
        const rgb = colour => [colour.r, colour.g, colour.b];
        for (const glyph of ["layer-group", "magnet"]) {
            const label = labels.find(item => item.segments.some(part => part.icon === glyph));
            const entry = rows.find(item => item.segments.some(part => part.icon === glyph));
            verify(label && entry, "The contribution and its tick row share the approved icon: " + glyph);
            const tick = tickRowFor(ticks, label);
            verify(tick, "Each contribution icon identifies an actual populated tick series");
            compare(String(entry.segments.find(part => part.icon === glyph).color), String(tick.color),
                    "Each contribution control uses its tick row's shade");
            const area = areas().find(candidate => String(candidate.outline.color) === String(tick.color));
            verify(area, "Each contribution curve matches its tick shade");
            compare(rgb(area.color), rgb(tick.color), "The fill shares its contribution's colour with the tick and outline");
            actualPalette.push(String(tick.color).toLowerCase());
        }
        compare(actualPalette, expectedPalette, "Nuclear and magnetic contributions take consecutive approved phase palette colours");
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
    function openCobaltProject(example, fixedMoments = false) {
        const project = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/" + example + "/project"));
        if (fixedMoments) {
            const frozen = Probe.readFile("tests/fixtures/magnetic_pnma/cosio-2k-reference.edi");
            verify(frozen.length > 0 && SettingsProof.write(project, "structures/cosio.edi", frozen),
                   "The fixed-parameter replay uses the structure that supplied its independent reference");
        }
        verify(Session.openProject(project), "The gate opens a disposable copy of the documented cobalt project");
        tryCompare(Session.project, "calculating", false, 15000, "The example's initial measured pattern finishes");
        return project;
    }
    function openMagneticFitExample() {
        return openCobaltProject("pd-neut-cwl_cosio-d20_2k");
    }
    function experimentReflectionTable() {
        tryVerify(() => appWindow.pagesWanted > 0 && appWindow.pagesBuilt === appWindow.pagesWanted,
                  10000, "The new project's workflow pages finish rebuilding before navigation");
        Ui.click(test, Probe, appWindow, "appBar.tab.experiment", true);
        Ui.click(test, Probe, appWindow, "sideBar.tab.extras", true);
        let extra = null;
        tryVerify(() => {
            extra = Review.findGroup(Ui.page(appWindow), "group.refln");
            return extra !== null;
        }, 5000, "Experiment Extra exposes the powder Reflections group");
        extra.collapsed = false;
        Ui.scrollIntoView(extra);
        let table = null;
        tryVerify(() => {
            table = findChild(extra, "reflections.list");
            return table !== null && table.headerItem !== null;
        }, 5000, "The powder reflection table is rendered in the Experiment Extra group");
        return table;
    }
    function test_experiment_reflections_match_crysta_data() {
        return [
            {tag: "magnetic", example: "pd-neut-cwl_cosio-d20_2k", magnetic: true},
            {tag: "nuclear", example: "pd-neut-cwl_cosio-d20", magnetic: false}
        ];
    }
    function test_experiment_reflections_match_crysta(data) {
        openCobaltProject(data.example, data.magnetic);
        const text = SettingsProof.text(Probe.repoUrl("tests/fixtures/magnetic_pnma"), "reflection-table.json");
        const expected = new Map(JSON.parse(text)[data.example].map(([hkl, ...values]) => [hkl, values]));
        const table = experimentReflectionTable();
        const cells = row => Array.from(row.contentRowData).filter(cell => typeof cell.text === "string" && cell.visible);
        const titles = ["", "h k l", "d (Å)", "2θ (deg)", "F² calc"];
        if (data.magnetic) {
            titles.push("|F_M⊥|² calc");
            titles.push(Session.label("refln.f_squared_total_calc"));
        }
        compare(cells(table.headerItem).map(cell => cell.text), titles,
                "Experiment Extra labels the powder reflection columns with their crystallographic quantities and units");
        tryCompare(table, "count", expected.size, 5000, "The table lists all reflections in crysta's independent loop");
        if (data.magnetic) {
            for (const hkl of ["1 0 0", "0 0 1"]) {
                const reference = expected.get(hkl);
                verify(reference && reference[2] === 0 && reference[3] > 0,
                       "The crysta loop includes the nuclear-forbidden magnetic reflection " + hkl);
            }
        }
        const seen = new Set();
        for (let i = 0; i < table.count; ++i) {
            table.positionViewAtIndex(i, ListView.Contain);
            table.forceLayout();
            tryVerify(() => Ui.rendered(table.itemAtIndex(i)), 1000, "Each reflection row is reachable after scrolling to row " + (i + 1));
            const row = cells(table.itemAtIndex(i));
            compare(row.length, titles.length, "The rendered reflection matches the column layout");
            const hkl = row[1].text.trim().replace(/\s+/g, " ");
            const reference = expected.get(hkl);
            verify(reference && !seen.has(hkl), "Each rendered reflection matches one unique crysta row: " + hkl);
            seen.add(hkl);
            for (let column = 0; column < reference.length; ++column) {
                const cell = row[column + 2];
                const full = Number(cell.full);
                const value = reference[column];
                const tolerance = Math.abs(value) * 5.01e-6 + 1e-12;
                verify(typeof cell.full === "string" && cell.full !== "" && Math.abs(full - value) <= tolerance,
                       "The " + titles[column + 2] + " cell matches crysta's six-significant-digit loop for " + hkl);
                if (column === 3) {
                    verify(/^-?\d+\.\d{3}$/.test(cell.number) && Math.abs(Number(cell.number) - full) <= .00050001,
                           "The magnetic squared factor uses the table's three-decimal number style for " + hkl);
                }
            }
            if (data.magnetic) {
                const [nuclear, magnetic, total] = row.slice(4).map(cell => Number(cell.full));
                verify(total === nuclear + magnetic,
                       "The calculated row displays the total beside its two factors for " + hkl);
            }
        }
    }
    function test_reflection_table_reads_the_stored_total() {
        const project = SettingsProof.copyProject(Probe.repoUrl("docs/user/cli/pd-neut-cwl_cosio-d20_2k/project"));
        const file = "experiments/d20.edi";
        const original = SettingsProof.text(project, file);
        const data = original.indexOf("loop_\n_data.two_theta");
        verify(data > 0, "The published example supplies the measured loop boundary");
        // A calculation-only bank keeps the file's carried reflection rows in the table.
        // The independent sentinel differs from F² + |F_M⊥|² so a GUI sum fails this check.
        const input = original.slice(0, data) + [
            "_data_range.two_theta_min 10",
            "_data_range.two_theta_max 30",
            "_data_range.two_theta_step 0.5",
            "",
            "loop_",
            "_refln.id",
            "_refln.structure_id",
            "_refln.d_spacing",
            "_refln.sin_theta_over_lambda",
            "_refln.index_h",
            "_refln.index_k",
            "_refln.index_l",
            "_refln.f_calc",
            "_refln.f_squared_calc",
            "_refln.f_m_perp_squared_calc",
            "_refln.f_squared_total_calc",
            "_refln.two_theta",
            "1 cosio 4.78739 0.104441 0 0 1 0 0 29.25 42.125 22.8194",
            ""
        ].join("\n");
        verify(SettingsProof.write(project, file, input) && Session.openProject(project),
               "The app opens the isolated project with an explicitly stored total");
        const table = experimentReflectionTable();
        const headers = Array.from(table.headerItem.contentRowData).filter(cell => typeof cell.text === "string" && cell.visible);
        const index = headers.findIndex(cell => cell.uid === "refln.f_squared_total_calc");
        verify(index > 0 && headers[index - 1].uid === "refln.f_m_perp_squared_calc",
               "The dictionary's total column follows the magnetic factor in Experiment Extra");
        compare(headers[index].text, Session.label("refln.f_squared_total_calc"),
                "The total column shows its dictionary title");
        tryCompare(table, "count", 1, 5000, "The table exposes the one carried reflection");
        tryVerify(() => table.itemAtIndex(0) !== null, 5000, "The stored reflection has its rendered delegate");
        const cells = Array.from(table.itemAtIndex(0).contentRowData).filter(cell => typeof cell.text === "string" && cell.visible);
        compare(cells[1].text.trim(), "0 0 1", "The table reads the carried nuclear-forbidden reflection");
        compare(Number(cells[index].full), 42.125, "The rendered total comes from the saved cell");
        compare(cells[index].number, "42.125", "The total uses the dictionary's three-decimal style");
    }
    function test_fitted_experiment_saves_magnetic_squared_factors() {
        const project = openMagneticFitExample();
        const factor = "_refln.f_m_perp_squared_calc";
        verify(!SettingsProof.text(project, "experiments/d20.edi").includes(factor),
               "The input experiment has no previously saved magnetic reflection loop");
        const fit = Session.project.fit;
        verify(fit.available, "The published 2.3 K example admits its fit");
        fit.start();
        tryVerify(() => !fit.running && fit.outcome !== "", 55000, "The app publishes the completed 2.3 K fit");
        compare(fit.outcome, "success", "The 2.3 K fit succeeds before saving its experiment");
        verify(Session.save(), "The app saves the fitted project into its disposable directory");
        const lines = SettingsProof.text(project, "experiments/d20.edi").trim().split(/\r?\n/);
        const first = lines.findIndex(line => line.trim() === "_refln.id");
        verify(first >= 0, "The post-fit experiment file contains a calculated reflection loop");
        const headings = [];
        while (lines[first + headings.length]?.trim().startsWith("_refln."))
            headings.push(lines[first + headings.length].trim());
        const magnetic = headings.indexOf(factor);
        verify(magnetic >= 0, "The post-fit experiment reflection loop saves the magnetic squared factor item");
        const indices = ["h", "k", "l"].map(axis => headings.indexOf("_refln.index_" + axis));
        const nuclear = headings.indexOf("_refln.f_squared_calc");
        verify(indices.every(index => index >= 0) && nuclear >= 0, "The saved magnetic factors retain their reflection identities and nuclear factors");
        const rows = new Map();
        for (const line of lines.slice(first + headings.length)) {
            const values = line.trim().split(/\s+/);
            if (values.length !== headings.length || !/^\d+$/.test(values[0]))
                break;
            rows.set(indices.map(index => values[index]).join(" "), values);
        }
        for (const hkl of ["1 0 0", "0 0 1"]) {
            const row = rows.get(hkl);
            verify(row && Number(row[nuclear]) === 0 && Number(row[magnetic]) > 0,
                   "The saved fit contains a positive magnetic factor for the nuclear-forbidden reflection " + hkl);
        }
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
    function test_published_magnetic_start_reaches_the_reference_minimum() {
        openMagneticFitExample();
        const moments = Probe.rows(Session.project.parameters).filter(row => row.category === "atom_site_moment" && row.free);
        const start = new Map(moments.map(row => [row.rowLabel + "." + row.name, row.parameter.value]));
        const expected = [["Co1.crystalaxis_x", 0], ["Co1.crystalaxis_y", 1],
                          ["Co1.crystalaxis_z", 0], ["Co2.crystalaxis_y", 1]];
        compare(start.size, expected.length, "The published project declares four free moment starts");
        compare(expected.map(([key]) => start.get(key)), expected.map(([, value]) => value),
                "The published project starts at Co1 (0, 1, 0) and Co2 My = 1 μB");
        repeatFitPreferences = {threads: Preferences.engineThreads, showResults: Preferences.showFitResults};
        Preferences.engineThreads = 1;
        Preferences.showFitResults = false;
        const fit = Session.project.fit;
        verify(fit.available, "The published one-magneton model admits its fit");
        fit.start();
        tryVerify(() => !fit.running && fit.outcome !== "", 55000, "The app publishes the fit from the published start");
        compare(fit.outcome, "success", "The published start converges");
        const result = Probe.rows(fit.results.agreement).find(row => row.place >= 0);
        verify(result, "The fit publishes the observed bank's agreement");
        const rwp = Number(result.values[1]);
        verify(Number.isFinite(rwp) && rwp.toFixed(2) === "4.73",
               "The fit reaches the owner's 4.73 percent reference minimum: Rwp=" + rwp);
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
            const values = moments().map(row => row.parameter.value);
            verify(zero ? values.every(value => value === 0) : values.some(value => value !== 0),
                   "The fit receives either the published magnetic start or an all-zero start");
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
