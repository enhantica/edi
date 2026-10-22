import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
import EdiStructureReference 1.0
import EasyApplication.Gui.Style as Style
import "RenderedTable.js" as Render

Rectangle {
    id: surface
    color: Style.Colors.mainContentBackground
    width: 1000
    height: 900
    Component {
        id: tableFactory
        AtomSitesGroup {
            width: 950
        }
    }
    Component {
        id: viewFactory
        StructureView {
            width: 950
            height: 700
        }
    }
    TestCase {
        name: "ElementContrast"
        when: windowShown
        property int oldTheme
        property var reference
        function initTestCase() {
            oldTheme = Style.Colors.theme;
            const lines = Probe.readFile(Qt.resolvedUrl("../../fixtures/e04_t10/published-elements.tsv").toString().replace("file://", "")).trim().split("\n");
            reference = lines.slice(1).map(line => {
                const cells = line.split("\t");
                return {
                    symbol: cells[0],
                    jmol: cells[1].toLowerCase(),
                    vesta: (cells[2] || cells[1]).toLowerCase()
                };
            });
            compare(reference.length, 118, "The independent published inventory covers every element H through Og");
        }
        function cleanup() {
            Session.closeProject();
            Style.Colors.theme = oldTheme;
        }
        function test_observe_data() {
            const rows = [];
            for (const scheme of ["jmol", "vesta"])
                for (const dark of [false, true])
                    rows.push({
                        tag: scheme + (dark ? "-dark" : "-light"),
                        scheme,
                        dark
                    });
            return rows;
        }
        function test_observe(data) {
            Style.Colors.theme = data.dark ? Style.Colors.DarkTheme : Style.Colors.LightTheme;
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/element_contrast/project")), "The complete independent element input opens through the real project reader: " + Session.lastError);
            Session.project.structureViewOptions.colorScheme = data.scheme;
            const table = createTemporaryObject(tableFactory, surface, {
                structure: Session.project.currentStructure
            });
            verify(table !== null, "The colour witness instantiates the real atom-sites table");
            const list = findChild(table, "atomSites.list");
            verify(list !== null, "The real table exposes its list for the complete inventory");
            list.maxRowCountShow = 1;
            verify(waitForPolish(table), "The complete table performs its real delegate layout");
            const view = createTemporaryObject(viewFactory, surface, {
                structure: Session.project.currentStructure,
                options: Session.project.structureViewOptions
            });
            verify(view !== null, "The witness creates the production structure view and its legend");
            tryVerify(() => view.current && view.atomCount === 118, 10000, "The sparse P1 scene contains one real sphere per independent element");
            const legend = findChild(view, "structure.view.legend");
            verify(legend !== null, "The colour witness reaches the real structure legend");
            let entries = [];
            tryVerify(() => {
                entries = Render.descendants(legend).filter(item => item.objectName === "chart.legend.entry");
                return entries.length === 118;
            }, 3000, "Every element creates its real legend mark and label");
            const instanceTable = findChild(view, "structure.view.spheres");
            const spheres = StructureOracle.instances(instanceTable).map((point, index) => {
                const shade = instanceTable.instanceColor(index);
                return {
                    x: point.x,
                    y: point.y,
                    z: point.z,
                    linear: [shade.r, shade.g, shade.b]
                };
            });
            compare(spheres.length, 118, "The 3D observer reads every actual instance colour before shading");
            const report = createTemporaryObject(viewFactory, surface, {
                report: Session.project.report,
                reportStructure: "elements"
            });
            verify(report !== null, "The report witness uses the same production structure figure as preview and print");
            report.colors.light = true;
            tryVerify(() => report.current && report.atomCount === 118, 10000, "The real report model publishes every element in its light figure");
            const reportLegend = findChild(report, "structure.view.legend");
            let reportEntries = [];
            tryVerify(() => {
                reportEntries = Render.descendants(reportLegend).filter(item => item.objectName === "chart.legend.entry");
                return reportEntries.length === 118;
            }, 3000, "The report figure produces a real legend entry for every element");
            const liveColours = entries.map(entry => ({
                        symbol: entry.label,
                        color: String(entry.segments[0].color)
                    }));
            const printColours = reportEntries.map(entry => ({
                        symbol: entry.label,
                        color: String(entry.segments[0].color)
                    }));
            view.shown = false;
            report.shown = false;
            const facts = [];
            for (let i = 0; i < reference.length; ++i) {
                const row = reference[i];
                table.sites.setText(0, "typeSymbol", row.symbol);
                const icon = findChild(table, "atomSite.icon.0");
                verify(icon !== null && icon.segments.length >= 2, "Every published element reaches its real table icon and label: " + row.symbol);
                const entry = liveColours.find(item => item.symbol === row.symbol);
                const printEntry = printColours.find(item => item.symbol === row.symbol);
                verify(entry !== undefined && printEntry !== undefined, "Live and report legends both retain the independent element identity: " + row.symbol);
                const position = [3 + 6 * (i % 5), 3 + 6 * (Math.floor(i / 5) % 5), 3 + 6 * Math.floor(i / 25)];
                const sphere = spheres.find(point => Math.abs(point.x - position[0]) < 1e-5 && Math.abs(point.y - position[1]) < 1e-5 && Math.abs(point.z - position[2]) < 1e-5);
                verify(sphere !== undefined, "The independent P1 Cartesian position identifies each real sphere: " + row.symbol);
                compare(icon.segments[1].text, row.symbol, "The reused production table delegate observes the requested element identity");
                const parameter = ParameterNames.segments({
                    elementSymbol: row.symbol,
                    phaseIndex: -1,
                    blockKind: "structure",
                    blockIndex: 0,
                    categoryIcon: "atom",
                    rowLabel: row.symbol,
                    name: "fract_x",
                    shortName: "x"
                });
                facts.push({
                    symbol: row.symbol,
                    source: row[data.scheme],
                    table: String(icon.segments[0].color),
                    accessor: String(AppColors.element(row.symbol)),
                    parameter: String(parameter[1].color),
                    parameterLabel: String(parameter[2].color),
                    legend: entry.color,
                    report: printEntry.color,
                    sphereLinear: sphere.linear,
                    background: String(surface.color),
                    viewBackground: String(view.color),
                    legendFill: String(legend.color),
                    reportBackground: String(report.color),
                    reportLegendFill: String(reportLegend.color)
                });
            }
            const selector = findChild(view, "structure.toolbar.colors");
            verify(selector !== null, "The production structure view retains its scheme selector");
            console.log("ELEMENT_CONTRAST " + JSON.stringify({
                tag: data.tag,
                facts,
                names: [selector.textAt(0), selector.textAt(1)],
                tooltip: selector.toolTip
            }));
        }
    }
}
