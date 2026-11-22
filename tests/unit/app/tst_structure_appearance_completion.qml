import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import ReportAcceptance 1.0
import "UiInteraction.js" as Ui
import "RenderedTable.js" as Render

Item {
    id: surface
    width: 1200
    height: 900
    Component {
        id: pageFactory
        StructurePage {
            width: 1200
            height: 900
            current: true
            visible: true
        }
    }
    TestCase {
        id: test
        name: "StructureAppearanceCompletion"
        when: windowShown
        visible: true
        property var page
        property var view
        property var root
        property var projectA
        property var projectB
        function cleanup() {
            retire();
            Session.closeProject();
        }
        function retire() {
            if (page)
                page.destroy();
            view = page = null;
            verify(waitForRendering(surface), "Retired Structure views complete their actual frame before the project closes");
        }
        function click(item) {
            verify(item !== null && item !== undefined && item.visible && item.enabled, "Appearance input reaches a real visible enabled control");
            let morePopup = null;
            if (item.objectName.startsWith("structure.toolbar.") && item.x < -1000) {
                const original = item;
                click(findChild(view, "structure.toolbar.more"));
                morePopup = findChild(view, "structure.toolbar.more.popup");
                tryCompare(morePopup, "opened", true, 1000, "Actual More input opens the hidden toolbar actions");
                tryVerify(() => {
                    item = Render.descendants(morePopup.contentItem).find(control => control.objectName === original.objectName + ".overflow" && control.visible && control.enabled);
                    return item !== undefined;
                }, 1000, "The production overflow popup exposes the requested toolbar action");
            }
            Ui.scrollIntoView(Ui.target(item));
            verify(waitForPolish(surface), "Appearance input follows the completed real layout");
            tryVerify(() => Ui.clickPoint(Ui.target(item)) !== null, 1000, "The real appearance control has an exposed pointer target after its actual tab transition: " + item.objectName);
            const point = Ui.clickPoint(Ui.target(item));
            const globalPoint = Ui.target(item).mapToItem(surface, point.x, point.y);
            verify(globalPoint.x >= 0 && globalPoint.y >= 0 && globalPoint.x < surface.width && globalPoint.y < surface.height, "Actual appearance pointer input lies inside the real test window");
            mouseClick(Ui.target(item), point.x, point.y);
            verify(waitForPolish(surface), "The actual appearance control completes its layout after input");
            if (morePopup && morePopup.visible) {
                keyClick(Qt.Key_Escape);
                tryCompare(morePopup, "visible", false, 1000, "Real Escape closes More before the next appearance action");
            }
        }
        function expand(name = "appearance") {
            click(findChild(page, "sideBar.tab.extras"));
            let group;
            tryVerify(() => {
                group = Ui.find(page, "group." + name, true);
                return group !== null;
            }, 1500, "Structure Extra exposes its current Appearance or Polyhedra group");
            if (group.collapsed)
                click(group);
            tryVerify(() => !group.collapsed, 1500, "The real Appearance group reaches its expanded geometry");
            tryVerify(() => !group.folding, 1500, "Sidebar input waits for the real group to finish folding");
            return group;
        }
        function bind(render = true) {
            page = pageFactory.createObject(surface);
            verify(page !== null && waitForPolish(page), "The appearance witness uses the production Structure page");
            click(findChild(page, "mainArea.tab.structure"));
            view = findChild(page, "structure.view");
            tryVerify(() => view && view.has3D && view.current && view.atomCount > 0, 10000, "The production Structure page renders its own real main-view structure");
            verify(waitForRendering(view), "The page's actual 3D structure completes a frame before appearance input");
            return expand();
        }
        function open(render = true) {
            Preferences.resetToDefaults();
            root = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/legacy_structure_project/compact-project"));
            verify(SettingsProof.write(root, "structures/cosio.edi", SettingsProof.repoText("tests/fixtures/structure_features/cubic-bonded.edi")), "Appearance uses the independently declared cubic FeO6 input");
            verify(SettingsProof.write(root, "experiments/d20.edi", SettingsProof.repoText("tests/fixtures/structure_features/neutron.edi")), "Appearance uses the independently declared zero-scale pattern input");
            verify(SettingsProof.write(root, "analysis/analysis.edi", "_edi.schema_version 3\n_fitting_mode.type single\n"), "The appearance input has no dangling site aliases");
            verify(Session.openProject(root), "The actual loader opens the independent appearance project");
            tryCompare(Session.project, "calculating", false, 10000, "The independent cubic geometry finishes calculating");
            bind(render);
        }
        function named(group, pattern, predicate) {
            const item = Render.descendants(group).find(control => control.visible && pattern.test(control.objectName) && predicate(control));
            verify(item !== undefined, "Appearance exposes the requested real polyhedra or atom-view control");
            return item;
        }
        function choose(box, pattern) {
            const index = Array.from({
                length: box.count
            }, (_, i) => box.textAt(i)).findIndex(text => pattern.test(text));
            verify(index >= 0, "The real appearance selector offers the requested existing style");
            click(box);
            tryCompare(box.popup, "opened", true, 1000, "Real input opens the appearance selector");
            const list = box.popup.contentItem;
            list.positionViewAtIndex(index, ListView.Contain);
            tryVerify(() => list.itemAtIndex(index) && Ui.exposed(list.itemAtIndex(index)), 1000, "The actual appearance popup exposes the requested choice");
            const entry = list.itemAtIndex(index);
            mouseClick(entry, entry.width / 2, entry.height / 2);
            tryCompare(box.popup, "visible", false, 1000, "The actual appearance choice closes its popup");
        }
        function textInput(field) {
            const input = typeof field.selectAll === "function" ? field : Render.descendants(field).find(item => typeof item.selectAll === "function" && !item.readOnly);
            verify(input !== undefined && !input.readOnly && input.enabled, "An appearance value is edited through its real text input");
            return input;
        }
        function edit(field, value) {
            const input = textInput(field);
            click(input);
            keyClick(Qt.Key_A, Qt.ControlModifier);
            for (const character of String(value))
                keyClick(character);
            keyClick(Qt.Key_Return);
            if (typeof value === "number")
                tryVerify(() => Math.abs(Number(input.text.replace(/[%\s]/g, "")) - value) < 1e-12, 1000, "The real appearance input accepts the independently supplied numeric value");
        }
        function polyToggle() {
            return named(findChild(page, "group.appearance"), /polyhedr/i, item => typeof item.checked === "boolean" || item.popup !== undefined);
        }
        function setPoly(shown) {
            expand("appearance");
            const control = polyToggle();
            if (typeof control.checked === "boolean") {
                if (control.checked !== shown)
                    click(control);
                compare(control.checked, shown, "The real Extra toggle takes the requested polyhedra visibility");
            } else
                choose(control, shown ? /^(?:show|shown|on|yes|true)$/i : /^(?:hide|hidden|off|no|false)$/i);
        }
        function opacityControl() {
            return findChild(expand("polyhedra"), "structure.polyhedra.opacity");
        }
        function setOpacity(fraction) {
            const field = opacityControl();
            const percent = /%/.test(String(field.unit || field.units || ""));
            edit(field, percent ? fraction * 100 : fraction);
        }
        function colourControl() {
            return findChild(expand("polyhedra"), "structure.polyhedra.colour");
        }
        function setColour(value) {
            const control = colourControl();
            choose(control, value === "atom" ? /atom/i : /grey/i);
            tryCompare(Session.project.structureViewOptions, "polyhedraColour", value, 1000, "The actual colour selector commits the declared polyhedra colour mode");
            verify(waitForRendering(surface), "The actual polyhedra colour input reaches a rendered frame");
        }
        function picture() {
            verify(view !== null && waitForRendering(view), "A real structure frame exists before the appearance comparison");
            const image = grabImage(view), samples = [];
            for (let y = Math.round(image.height * .2); y < image.height * .8; y += 12)
                for (let x = Math.round(image.width * .15); x < image.width * .85; x += 12)
                    samples.push(String(image.pixel(x, y)));
            return samples.join(",");
        }
        function projectSnapshot(location) {
            const bytes = SettingsProof.projectBytes(location);
            verify(bytes.error === undefined && Object.keys(bytes).length > 0, "The actual saved project snapshot contains readable files with only metadata clocks normalised");
            return JSON.stringify(bytes);
        }
        function uiSnapshot() {
            expand("appearance");
            const toggle = findChild(page, "structure.appearance.polyhedra");
            verify(toggle !== null, "Appearance retains the actual polyhedra state even when an unbonded legacy structure hides its toggle");
            const opacity = textInput(opacityControl()), colour = colourControl();
            return JSON.stringify({
                checked: typeof toggle.checked === "boolean" ? toggle.checked : toggle.currentText,
                opacity: opacity.text,
                colour: colour.currentText,
                centres: textInput(findChild(expand("polyhedra"), "structure.polyhedra.centres")).text,
                corners: textInput(findChild(page, "structure.polyhedra.corners")).text,
                distance: textInput(findChild(page, "structure.polyhedra.maxDistance")).text,
                extent: findChild(page, "structure.polyhedra.extent").currentText
            });
        }
        function test_existing_toolbar_switches_have_the_same_full_extra_settings() {
            open();
            const supplemental = findChild(page, "group.structure_view");
            if (supplemental !== null && supplemental.visible && supplemental.collapsed)
                click(supplemental);
            for (const item of [
                {
                    name: "labels",
                    property: "showLabels"
                },
                {
                    name: "bonds",
                    property: "bonds"
                },
                {
                    name: "cell",
                    property: "cell"
                },
                {
                    name: "axes",
                    property: "axes"
                }
            ]) {
                const quick = findChild(view, "structure.toolbar." + item.name);
                verify(quick !== null && quick.visible && quick.enabled, "The real structure toolbar exposes each supported existing appearance switch");
                const extra = Render.descendants(page).find(control => control.visible && control.enabled && (control.uid === "structure_view." + item.name || /(?:appearance|structure_view)\./i.test(control.objectName) && new RegExp("\\.(?:show_?)?" + item.name + "$", "i").test(control.objectName)) && (typeof control.checked === "boolean" || control.popup !== undefined));
                verify(extra !== undefined, "The full Extra appearance settings expose each existing toolbar switch before any edit");
                const before = quick.checked;
                click(quick);
                tryCompare(Session.project.structureViewOptions, item.property, !before, 1000, "The real toolbar action changes the project's shared appearance state");
                if (typeof extra.checked === "boolean") {
                    tryCompare(extra, "checked", !before, 1000, "The actual full Extra setting follows the toolbar switch");
                    click(extra);
                } else
                    choose(extra, before ? /^(?:show|shown|on|yes|true)$/i : /^(?:hide|hidden|off|no|false)$/i);
                tryCompare(quick, "checked", before, 1000, "The real Extra action restores the same toolbar setting");
                compare(Session.project.structureViewOptions[item.property], before, "The legacy quick switch and full Extra setting share the actual project-owned value");
            }
        }
        function test_atom_view_toolbar_and_extra_share_saved_state() {
            open();
            const toolbar = findChild(view, "structure.toolbar.atomView");
            verify(toolbar !== null && toolbar.visible && toolbar.enabled && toolbar.count > 1, "Atom view is a real toolbar combobox, alongside the existing drawn-Atoms choice");
            expand("appearance");
            const extra = findChild(page, "structure.appearance.atomView");
            verify(extra !== null && extra.visible && extra.enabled, "Extra exposes the same atom-view setting as the toolbar");
            choose(toolbar, /ionic/i);
            tryCompare(Session.project.structureViewOptions, "atomView", "ionic", 1000, "The toolbar's actual choice changes the shared appearance state");
            verify(/ionic/i.test(extra.currentText), "The actual Extra control follows the toolbar's atom-view choice");
            choose(extra, /covalent/i);
            tryCompare(Session.project.structureViewOptions, "atomView", "covalent", 1000, "The Extra atom-view choice changes the shared appearance state");
            verify(/covalent/i.test(toolbar.currentText), "The actual toolbar follows the Extra atom-view choice");
            edit(findChild(page, "structure.appearance.atomScale"), .41);
            verify(Session.save(), "The actual session saves the atom-view and scale choices");
            const saved = SettingsProof.fileObservation(root, "structures/cosio.edi").base64;
            retire();
            Session.closeProject();
            verify(Session.openProject(root), "The saved appearance project reopens through the real loader");
            bind(false);
            compare(Session.project.structureViewOptions.atomView, "covalent", "The actual restored atom-view option retains the chosen style");
            verify(Math.abs(Session.project.structureViewOptions.atomScale - .41) < 1e-12, "The actual restored atom scale retains the nontrivial selected value");
            verify(Session.save(), "The restored appearance saves through the actual session");
            compare(SettingsProof.fileObservation(root, "structures/cosio.edi").base64, saved, "Appearance save and reload retain every structure byte after the edit");
        }
        function test_polyhedra_toolbar_and_extra_change_actual_geometry_visibility() {
            open();
            const quick = findChild(view, "structure.toolbar.polyhedra");
            verify(quick !== null && quick.visible && quick.enabled, "The real Structure toolbar exposes its polyhedra quick switch");
            setPoly(false);
            const hidden = picture();
            click(quick);
            verify(typeof polyToggle().checked !== "boolean" || polyToggle().checked, "The actual Extra toggle follows the polyhedra toolbar quick switch");
            const shown = picture();
            verify(shown !== hidden, "Showing polyhedra changes the actual central 3D scene, away from toolbar and legend controls");
            setPoly(false);
            verify(!quick.checked, "The actual polyhedra toolbar follows the Extra visibility control");
            compare(picture(), hidden, "Hiding polyhedra restores the same actual 3D scene without them");
        }
        function test_polyhedra_colour_and_opacity_affect_the_actual_3d_render() {
            open();
            setPoly(true);
            setColour("atom");
            setOpacity(.37);
            const blue = picture();
            setColour("grey");
            const warm = picture();
            verify(warm !== blue, "The real colour chooser changes rendered polyhedra, beyond the sidebar and toolbar");
            setOpacity(.63);
            verify(picture() !== warm, "A nontrivial opacity edit changes the actual polyhedra rendering");
        }
        function test_polyhedra_settings_survive_reload_and_do_not_leak_to_another_project() {
            Preferences.resetToDefaults();
            projectB = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/legacy_structure_project/compact-project"));
            verify(Session.openProject(projectB), "The isolation witness first opens the unchanged saved project");
            tryCompare(Session.project, "calculating", false, 10000, "The unchanged legacy input finishes calculating before Appearance is visited");
            bind(false);
            const defaults = uiSnapshot(), untouched = projectSnapshot(projectB);
            retire();
            Session.closeProject();
            open(false);
            projectA = root;
            setPoly(true);
            setColour("grey");
            setOpacity(.37);
            const poly = expand("polyhedra");
            edit(findChild(poly, "structure.polyhedra.centres"), "Fe");
            edit(findChild(poly, "structure.polyhedra.corners"), "O");
            edit(findChild(poly, "structure.polyhedra.maxDistance"), 1.7);
            choose(findChild(poly, "structure.polyhedra.extent"), /complete/i);
            const selected = uiSnapshot();
            verify(selected !== defaults, "The explicit polyhedra appearance differs from the other project's observed defaults");
            verify(Session.save(), "The actual session saves the explicit polyhedra appearance");
            const saved = projectSnapshot(projectA);
            retire();
            Session.closeProject();
            verify(Session.openProject(projectB), "The unchanged second project opens after the edited appearance");
            bind(false);
            compare(uiSnapshot(), defaults, "Another project's actual appearance controls retain their own prior default-state invariant");
            verify(Session.save(), "The unchanged second project saves through the actual session");
            compare(projectSnapshot(projectB), untouched, "Visiting the new Appearance controls adds no fields or byte changes anywhere in an unchanged saved project");
            retire();
            Session.closeProject();
            verify(Session.openProject(projectA), "The saved project with polyhedra settings reopens after the other project");
            bind(false);
            compare(uiSnapshot(), selected, "The actual polyhedra visibility, colour and opacity controls restore the project's own saved state");
            verify(Session.save(), "The restored polyhedra project saves through the actual session");
            compare(projectSnapshot(projectA), saved, "Polyhedra appearance survives actual save and reload without rewriting any project bytes beyond the two metadata clocks");
        }
    }
}
