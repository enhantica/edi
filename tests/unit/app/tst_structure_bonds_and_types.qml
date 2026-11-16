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
        id: viewFactory
        StructureView {
            x: 0
            width: 600
            height: 900
            shown: true
        }
    }
    TestCase {
        id: test
        name: "StructureBondsAndTypes"
        when: windowShown
        visible: true
        width: 1200
        height: 900
        property var view
        property var page
        property var root
        readonly property var reference: JSON.parse(SettingsProof.repoText("tests/fixtures/structure_features/reference.json"))
        Component {
            id: pageFactory
            StructurePage {
                current: true
                visible: true
            }
        }
        function cleanup() {
            if (view)
                view.destroy();
            if (page)
                page.destroy();
            view = page = null;
            verify(waitForRendering(surface), "Retired Structure feature views complete their actual frame before the project closes");
            Session.closeProject();
        }
        function click(item) {
            verify(item !== null && item.visible && item.enabled, "The Structure feature uses a real visible enabled control");
            Ui.scrollIntoView(Ui.target(item));
            verify(waitForPolish(page), "Structure input follows the actual sidebar layout");
            const at = Ui.clickPoint(Ui.target(item));
            verify(at !== null, "The Structure feature control has an exposed pointer target");
            const globalPoint = Ui.target(item).mapToItem(surface, at.x, at.y);
            verify(globalPoint.x >= 0 && globalPoint.y >= 0 && globalPoint.x < surface.width && globalPoint.y < surface.height, "Actual Structure pointer input lies inside the real test window");
            mouseClick(Ui.target(item), at.x, at.y);
            verify(waitForRendering(page), "The actual Structure feature input renders");
        }
        function expand(name) {
            const group = findChild(page, "group." + name);
            verify(group !== null && group.visible, "The Structure sidebar exposes the requested bond or atom group");
            if (group.collapsed)
                click(group);
            tryVerify(() => !group.collapsed, 1500, "The actual Structure group reaches its expanded geometry");
            return group;
        }
        function open(probe) {
            Preferences.resetToDefaults();
            root = SettingsProof.copyProject(Qt.resolvedUrl("../../fixtures/legacy_structure_project/compact-project"));
            verify(SettingsProof.write(root, "structures/cosio.edi", SettingsProof.repoText("tests/fixtures/structure_features/cubic.edi")), "The Structure witness supplies its independent seven-site cubic geometry");
            verify(SettingsProof.write(root, "experiments/d20.edi", SettingsProof.repoText("tests/fixtures/structure_features/" + probe + ".edi")), "The Structure witness declares its active probe and scattering source");
            verify(SettingsProof.write(root, "analysis/analysis.edi", "_edi.schema_version 3\n_fitting_mode.type single\n"), "The cubic input has no dangling site aliases");
            verify(Session.openProject(root), "The real loader opens the independent cubic Structure input");
            tryCompare(Session.project, "calculating", false, 10000, "The actual cubic calculation completes before Structure input");
            page = pageFactory.createObject(test, {
                width: 1200,
                height: test.height
            });
            verify(page !== null && waitForPolish(page) && waitForRendering(page), "The production Structure page renders the independent input");
            view = viewFactory.createObject(surface, {
                structure: Session.project.currentStructure,
                options: Session.project.structureViewOptions
            });
            verify(view !== null && waitForPolish(view), "The bond and type witness creates the real Structure view");
            tryVerify(() => view.has3D && view.current && view.atomCount === 7, 10000, "The actual 3D renderer prepares every atom of the independently declared cubic structure");
        }
        function edit(group, name, value) {
            const field = Render.descendants(group).find(item => item.visible && (item.uid === "geom." + name || item.objectName.endsWith("." + name)));
            verify(field !== undefined && field.enabled, "Bond settings expose the dictionary's minimum-distance and tolerance fields");
            let input = field;
            if (typeof input.selectAll !== "function")
                input = Render.descendants(field).find(item => typeof item.selectAll === "function");
            verify(input !== undefined && !input.readOnly, "A bond cutoff is edited through its actual text input");
            click(input);
            keyClick(Qt.Key_A, Qt.ControlModifier);
            for (const character of String(value))
                keyClick(character);
            keyClick(Qt.Key_Return);
            tryCompare(Session.project, "calculating", false, 10000, "The real bond-setting edit completes its geometry update");
        }
        function checkBonds(expected) {
            const group = expand("geom_bond");
            let list;
            tryVerify(() => {
                list = findChild(group, "generated.geom_bond.list");
                return list !== null && list.count === expected.length;
            }, 3000, "The displayed bond table has the independent cubic pair count after each cutoff edit");
            const seen = [];
            for (let index = 0; index < expected.length; ++index) {
                list.positionViewAtIndex(index, ListView.Contain);
                Ui.scrollIntoView(list);
                verify(waitForPolish(list), "The actual bond output table finishes positioning its requested row");
                const get = name => findChild(group, "generated.geom_bond." + name + "." + index);
                tryVerify(() => get("distance") !== null && get("atom_site_label_1") !== null && get("atom_site_label_2") !== null, 1000, "The actual visible bond row contains both site names and its distance");
                const first = String(get("atom_site_label_1").text), second = String(get("atom_site_label_2").text);
                const pair = [first, second].sort().join("|");
                const row = expected.find(item => item.sites.slice().sort().join("|") === pair);
                verify(row !== undefined && !seen.includes(pair), "Every displayed bond is one unique independently predicted cubic pair");
                seen.push(pair);
                const distance = Number(String(get("distance").text).replace(/−/g, "-"));
                verify(Number.isFinite(distance) && Math.abs(distance - row.distance) <= 0.0000500001, "The rendered bond distance agrees with the independent Euclidean distance within its four-decimal display rounding");
            }
        }
        function test_bond_cutoffs_change_displayed_cubic_distances_and_persist() {
            open("neutron");
            click(findChild(page, "sideBar.tab.extras"));
            const settings = expand("geom");
            edit(settings, "min_bond_distance_cutoff", reference.min_distance);
            edit(settings, "bond_distance_inc", reference.distance_increment);
            checkBonds(reference.bonds);
            edit(expand("geom"), "min_bond_distance_cutoff", 1.1);
            const expected = reference.bonds.filter(row => row.distance >= 1.1);
            checkBonds(expected);
            verify(Session.save(), "The actual session saves the edited bond-distance settings");
            view.destroy();
            page.destroy();
            view = page = null;
            verify(waitForRendering(surface), "The real Structure view retires before the edited project closes");
            Session.closeProject();
            verify(Session.openProject(root), "The saved bond-distance project reopens through the real loader");
            tryCompare(Session.project, "calculating", false, 10000, "The reopened cubic geometry finishes calculating");
            page = pageFactory.createObject(test, {
                width: 1200,
                height: test.height
            });
            verify(page !== null && waitForPolish(page), "The actual reopened Structure page binds the saved geometry settings");
            view = viewFactory.createObject(surface, {
                structure: Session.project.currentStructure,
                options: Session.project.structureViewOptions
            });
            tryVerify(() => view !== null && view.current, 10000, "The reopened real Structure view prepares its saved bond geometry");
            click(findChild(page, "sideBar.tab.extras"));
            checkBonds(expected);
        }
        function test_active_probe_types_and_element_colour_regression_pin_data() {
            return [
                {
                    tag: "neutron",
                    probe: "neutron",
                    element: "Gd",
                    selected: "157Gd"
                },
                {
                    tag: "neutron-sears",
                    probe: "neutron-sears",
                    element: "Fe",
                    selected: "56Fe"
                },
                {
                    tag: "xray",
                    probe: "xray",
                    element: "Fe",
                    selected: "Fe2+"
                }
            ];
        }
        function choose(box, token) {
            const index = Array.from({
                length: box.count
            }, (_, i) => box.textAt(i)).indexOf(token);
            verify(index >= 0, "The actual atom-type selector offers the independent natural, isotope or ion token");
            click(box);
            tryCompare(box.popup, "opened", true, 1000, "Actual pointer input opens the atom-type list");
            const list = box.popup.contentItem;
            list.positionViewAtIndex(index, ListView.Contain);
            tryVerify(() => list.itemAtIndex(index) && Ui.exposed(list.itemAtIndex(index)), 1000, "The requested active-profile type is visible in the real popup");
            const entry = list.itemAtIndex(index);
            mouseClick(entry, entry.width / 2, entry.height / 2);
            tryCompare(box.popup, "visible", false, 1000, "The actual atom-type selection closes its popup");
            tryVerify(() => Probe.rows(Session.project.currentStructure.atomSites)[0].typeSymbol === token, 2000, "Choosing an active-profile type edits the actual atom-site model");
        }
        function test_active_probe_types_and_element_colour_regression_pin(data) {
            open(data.probe);
            click(findChild(page, "sideBar.tab.basic"));
            expand("atom_site");
            const box = findChild(page, "atomSite.typeSymbol.0");
            verify(box !== null && box.visible && box.enabled, "The actual first atom site has an editable type selector");
            const actual = Array.from({
                length: box.count
            }, (_, i) => box.textAt(i)).sort();
            compare(JSON.stringify(actual), JSON.stringify(reference.atom_types[data.probe]), "The type selector lists exactly the independently committed active probe scattering table, including supported isotopes or ions");
            choose(box, data.element);
            const natural = findChild(page, "atomSite.icon.0").segments.find(part => part.icon !== undefined);
            verify(natural !== undefined && natural.color.a > 0, "The actual natural element has a visible atom icon for the regression pin");
            const colourRegressionPin = String(natural.color);
            choose(box, data.selected);
            const changed = findChild(page, "atomSite.icon.0").segments.find(part => part.icon !== undefined);
            verify(changed !== undefined && String(changed.color) === colourRegressionPin, "The isotope or ion retains the corresponding natural element's existing icon-colour regression pin");
            verify(Session.save(), "The real project saves its selected isotope or ion");
            view.destroy();
            page.destroy();
            view = page = null;
            verify(waitForRendering(surface), "The real Structure view retires before the edited project closes");
            Session.closeProject();
            verify(Session.openProject(root), "The saved active-profile type reopens through the actual loader");
            compare(Probe.rows(Session.project.currentStructure.atomSites)[0].typeSymbol, data.selected, "The exact isotope or ion token survives real save and reload");
        }
    }
}
