import QtQuick
import QtQuick.Controls
import QtTest
import edi.app
import EdiAcceptance 1.0
import "RenderedTable.js" as Render
import "../../fixtures/adp_site_symmetry/oracle.js" as Oracle

Item {
    id: surface
    width: 1200
    height: 700
    focus: true
    Component { id: groupComponent; AtomSiteAdpGroup { width: 1180 } }
    TextMetrics { id: metrics }
    TestCase {
        name: "AdpSiteSymmetry"
        when: windowShown
        property var group: null
        function init() { failOnWarning(/.*/); }
        function cleanup() {
            if (group !== null) group.destroy();
            group = null;
            Session.closeProject();
        }
        function control(name) {
            return Render.descendants(group).find(item => item.objectName === name);
        }
        function values(row) {
            return ["11", "22", "33", "12", "13", "23"].map(suffix => row["ani" + suffix].value);
        }
        function close(actual, expected, message) {
            verify(Math.abs(actual - expected) <= Math.max(2e-12, Math.abs(expected)*2e-10), message);
        }
        function complete(name, kind, values, allowed) {
            const matrix = Oracle.frozen.completion[name][kind][allowed.join(",")];
            verify(matrix !== undefined, "Editable GUI seeds span the independent cctbx site subspace");
            return matrix.map(row => row.reduce((sum, coefficient, i) => sum + coefficient*values[allowed[i]], 0));
        }
        function inspect(name, kind, index, expected) {
            const row = Probe.rows(group.adps)[index];
            const actual = values(row);
            const allowed = [0,1,2,3,4,5].filter(i => row["ani" + ["11", "22", "33", "12", "13", "23"][i]].refinable);
            compare(allowed.length, Oracle.frozen.sites[name].rank, "GUI editability has the independently tabulated tensor rank");
            if (name === "cubic") compare(allowed.join(","), "0", "The owner's m-3m seed is ani11");
            const constrained = complete(name, kind, actual, allowed);
            for (let i = 0; i < 6; ++i) {
                close(actual[i], constrained[i], "The live GUI tensor follows its independent site table");
                if (expected) close(actual[i], expected[i], "Every displayed component follows the edited seed");
            }
            const iso = actual.reduce((sum, value, i) => sum + value*Oracle.frozen.weights[name][kind][i], 0);
            close(row.adpIso.value, iso, "The displayed Beq/Ueq uses every tensor term and the cell metric");
            const shownIso = parseFloat(String(control("atomSiteAdp.iso." + index).text).replace(/−/g, "-"));
            verify(Number.isFinite(shownIso) && Math.abs(shownIso-iso) <= Math.max(2e-12,Math.abs(iso)*0.01), "The rendered equivalent follows the full physical tensor");
            for (let i = 0; i < 6; ++i) {
                const suffix = ["11", "22", "33", "12", "13", "23"][i];
                const item = row["ani" + suffix];

                const cell = control("atomSiteAdp.ani" + suffix + "." + index);
                verify(cell !== undefined, "Every real tensor field is rendered");
                const shown = parseFloat(String(cell.text).replace(/−/g, "-"));
                verify(Number.isFinite(shown) && Math.abs(shown-actual[i]) <= Math.max(2e-12,Math.abs(actual[i])*0.01), "Actual tensor text follows its live physical value");

            }
            return allowed;
        }
        function checkSite(name, kind) {
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/adp_site_symmetry/gui/" + name)), "The independent same-site GUI vehicle opens");
            group = groupComponent.createObject(surface, {structure: Session.project.currentStructure});
            verify(group !== null, "The production ADP group is instantiated");
            const tracked = {};
            for (const label of ["La", "Ba"]) {
                const atom = Probe.rows(group.adps).findIndex(row => row.label === label);
                verify(atom >= 0, "The GUI preserves each authored atom identity");
                group.adps.setType(atom, kind);
                tryVerify(() => Probe.rows(group.adps)[atom].adpType === kind, 2000, "Each same-site atom converts to its declared tensor type");
                wait(0);
                const expected = Oracle.frozen.sites[name].types[kind].positive.map(value => value*(label === "La" ? 1 : 1.7));
                const allowed = inspect(name, kind, atom, expected);
                tracked[label] = expected;
                for (const previous of Object.keys(tracked))
                    inspect(name, kind, Probe.rows(group.adps).findIndex(row => row.label === previous), tracked[previous]);
                for (const i of allowed) {
                    const row = Probe.rows(group.adps)[atom];
                    const edited = values(row);
                    edited[i] = Number((edited[i] + Math.max(Math.abs(edited[i]), 0.0001)*0.17).toFixed(12));
                    const suffix = ["11", "22", "33", "12", "13", "23"][i];
                    const cell = control("atomSiteAdp.ani" + suffix + "." + atom);
                    mouseClick(cell); keyClick(Qt.Key_A, Qt.ControlModifier);
                    for (const character of String(edited[i])) keyClick(character.charCodeAt(0));
                    keyClick(Qt.Key_Return); wait(0);
                    tracked[label] = complete(name, kind, edited, allowed);
                    for (const previous of Object.keys(tracked))
                        inspect(name, kind, Probe.rows(group.adps).findIndex(row => row.label === previous), tracked[previous]);
                }
                for (let i = 0; i < 6; ++i) if (!allowed.includes(i)) {
                    const before = values(Probe.rows(group.adps)[atom]);
                    surface.forceActiveFocus();
                    mouseClick(control("atomSiteAdp.ani" + ["11", "22", "33", "12", "13", "23"][i] + "." + atom));
                    keyClick(Qt.Key_A, Qt.ControlModifier); keyClick(Qt.Key_9); keyClick(Qt.Key_Return); wait(0);
                    inspect(name, kind, atom, before);
                }
                const before = values(Probe.rows(group.adps)[atom]);
                surface.forceActiveFocus(); mouseClick(control("atomSiteAdp.iso." + atom));
                keyClick(Qt.Key_A, Qt.ControlModifier); keyClick(Qt.Key_9); keyClick(Qt.Key_Return); wait(0);
                inspect(name, kind, atom, before);
            }

        }
        function checkLabels(name, kind) {
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/adp_site_symmetry/gui/" + name)), "The independent label vehicle opens");
            group = groupComponent.createObject(surface, {structure: Session.project.currentStructure});
            verify(group !== null, "The production ADP group renders its labels");
            for (let index = 0; index < 2; ++index) {
                group.adps.setType(index, kind); wait(0);
                const row = Probe.rows(group.adps)[index], actual = values(row);
            const isoCell = control("atomSiteAdp.iso." + index);
            verify(isoCell !== undefined, "The real equivalent cell is rendered");
            verify(String(isoCell.ToolTip.text).includes(kind === "Uani" ? "U eq" : "B eq"), "The equivalent tooltip names its exact quantity");
            verify(String(isoCell.ToolTip.text).includes("Å²"), "The equivalent tooltip gives its square-angstrom unit");
            verify(String(isoCell.ToolTip.text).includes("_atom_site.adp_iso"), "The equivalent tooltip names the persisted EDI item");
                for (let i = 0; i < 6; ++i) {
                    const suffix = ["11", "22", "33", "12", "13", "23"][i];
                    const cell = control("atomSiteAdp.ani" + suffix + "." + index);
                    verify(cell !== undefined, "The full component tooltip is rendered");
                const tooltip = String(cell.ToolTip.text);
                verify(tooltip.includes(kind === "beta" ? "β" : kind[0]), "The full component tooltip follows the row type");
                verify(tooltip.includes(kind === "beta" ? "dimensionless" : "Å²"), "The component tooltip gives its exact unit");
                if (kind === "beta" && actual[i] !== 0) {
                    const shown = Number(String(cell.text));
                    verify(Math.abs(shown - actual[i]) <= Math.abs(actual[i])*6e-5, "Small beta values retain useful significant digits");
                    metrics.font = cell.font; metrics.text = String(cell.text);
                    verify(metrics.advanceWidth <= cell.width - (cell.leftPadding || 0) - (cell.rightPadding || 0), "Beta precision must fit the actual cell");
                }
                }
            }
            const table = control("atomSiteAdps.list");
            const headers = Render.texts(table.headerItem).map(item => String(item.text));
            verify(headers.includes("iso/eq"), "The owner-approved common equivalent header is iso/eq");
            for (const suffix of ["11", "22", "33", "12", "13", "23"])
                verify(headers.includes(suffix), "Tensor headers are component indices independent of row type");
        }
        function test_cubic_Uani() { checkSite("cubic", "Uani"); }
        function test_cubic_Bani() { checkSite("cubic", "Bani"); }
        function test_cubic_beta() { checkSite("cubic", "beta"); }
        function test_tetragonal_Uani() { checkSite("tetragonal", "Uani"); }
        function test_tetragonal_Bani() { checkSite("tetragonal", "Bani"); }
        function test_tetragonal_beta() { checkSite("tetragonal", "beta"); }
        function test_hexagonal_Uani() { checkSite("hexagonal", "Uani"); }
        function test_hexagonal_Bani() { checkSite("hexagonal", "Bani"); }
        function test_hexagonal_beta() { checkSite("hexagonal", "beta"); }
        function test_general_Uani() { checkSite("general", "Uani"); }
        function test_general_Bani() { checkSite("general", "Bani"); }
        function test_general_beta() { checkSite("general", "beta"); }
        function test_labels_cubic_Uani() { checkLabels("cubic", "Uani"); }
        function test_labels_cubic_Bani() { checkLabels("cubic", "Bani"); }
        function test_labels_cubic_beta() { checkLabels("cubic", "beta"); }
        function test_labels_tetragonal_Uani() { checkLabels("tetragonal", "Uani"); }
        function test_labels_tetragonal_Bani() { checkLabels("tetragonal", "Bani"); }
        function test_labels_tetragonal_beta() { checkLabels("tetragonal", "beta"); }
        function test_labels_hexagonal_Uani() { checkLabels("hexagonal", "Uani"); }
        function test_labels_hexagonal_Bani() { checkLabels("hexagonal", "Bani"); }
        function test_labels_hexagonal_beta() { checkLabels("hexagonal", "beta"); }
        function test_labels_general_Uani() { checkLabels("general", "Uani"); }
        function test_labels_general_Bani() { checkLabels("general", "Bani"); }
        function test_labels_general_beta() { checkLabels("general", "beta"); }
    }
}
