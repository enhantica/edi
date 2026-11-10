// SPDX-License-Identifier: BSD-3-Clause
// The report's pattern chart has the app's panel structure (edi ADR-0021): the measured and calculated pattern,
// the Bragg tick rows and measured minus calculated, as three panes one em apart, each framed on its four sides,
// the tick rows without a grid and the x labels under the lowest pane only. Its toolbar has the app's buttons, with
// their icons, order and tooltips, and plotly's own toolbar is hidden. report.js draws a synthetic three-pane
// pattern here against a stub plotly and a minimal page, and what it hands plotly and the page is compared with the
// app's chart (app/qml/Components/PatternChart.qml: its three frames and its one-em pane gap) and its toolbar
// (app/qml/Components/ChartToolbar.qml).
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const root = new URL('../../', import.meta.url);
const failures = [];
const expect = (ok, what) => { if (!ok) failures.push(what); };

const qml = readFileSync(new URL('app/qml/Components/PatternChart.qml', root), 'utf8');
for (const pane of ['main', 'bragg', 'residual']) {
  expect(qml.includes(`objectName: "chart.frame.${pane}"`), `the app's chart has no ${pane} frame`);
}
expect(/readonly property real paneGap: em\b/.test(qml), "the app's pane gap is no longer one em");

// The app's toolbar: each button's icon and its first tooltip, in order. The report draws one
// dataset per chart, so the app's dataset highlight has no counterpart there.
const APP_ONLY = new Set(['highlighter']);
const toolbarQml = readFileSync(new URL('app/qml/Components/ChartToolbar.qml', root), 'utf8');
const appButtons = [...toolbarQml.matchAll(/fontIcon: "([a-z-]+)"\s*\n\s*toolTip: [^\n]*?qsTr\("([^"]+)"\)/g)].map(
  ([, icon, tip]) => [icon, tip]).filter(([icon]) => !APP_ONLY.has(icon));
expect(appButtons.length === 8, `the app's toolbar has ${appButtons.length} buttons, not the 8 this check knows`);
// Save image is the toolbar's last button, from its own component.
const saveQml = readFileSync(new URL('app/qml/Components/SaveImageButton.qml', root), 'utf8');
const save = saveQml.match(/fontIcon: "([a-z-]+)"\s*\n\s*toolTip: [^\n]*?qsTr\("([^"]+)"\)/);
expect(save && toolbarQml.includes('SaveImageButton {'), "the app's toolbar has no Save image button");
if (save) appButtons.push([save[1], save[2]]);

const EM = 16;
let drawn = null;
let config = null;
const element = () => ({ children: [], dataset: {}, style: {}, classList: { add() {} }, attributes: {},
  setAttribute(name, value) { this.attributes[name] = value; }, appendChild(child) { this.children.push(child); },
  addEventListener() {} });
const context = {
  document: { getElementById: () => ({ textContent: '{}' }), querySelectorAll: () => [], readyState: 'complete',
    addEventListener() {}, documentElement: {}, createElement: element },
  getComputedStyle: () => ({ fontSize: `${EM}px`, getPropertyValue: () => '' }),
  window: { Plotly: { newPlot: (_figure, traces, layout, options) => { drawn = { traces, layout }; config = options; },
    relayout() {}, restyle() {} } },
  console,
};
vm.createContext(context);
try {
  vm.runInContext(readFileSync(new URL('data/report/report.js', root), 'utf8'), context);
} catch (error) {
  failures.push(`report.js does not load: ${error.message}`);
}
const pattern = {
  series: [{ kind: 'measured' }, { kind: 'background' }, { kind: 'structure' }, { kind: 'bragg' }, { kind: 'residual' }],
  legend: true,
  x: { min: 10, max: 160, title: '2θ (deg)' },
  layout: [{ pane: 'main', stretch: 0.7, fixed_px: 0 }, { pane: 'bragg', stretch: 0, fixed_px: 32 },
    { pane: 'residual', stretch: 0.3, fixed_px: 0 }],
  browser: { traces: [{ yaxis: 'y' }, { yaxis: 'y' }, { yaxis: 'y' }, { yaxis: 'y2' }, { yaxis: 'y3' }]
    .map(trace => ({ ...trace, x: [10, 20], y: [1, 2] })), shapes: [{ type: 'rect', x0: 0, x1: 5 }],
    annotations: [], main_title: 'meas, calc', residual_title: 'meas − calc', bottom_axis: 'y3', bragg_rows: 1,
    fixed_height: 32 },
};
const plot = 600 - 48 - 16;
const figure = { ...element(), clientHeight: 600 };
if (typeof context.drawPattern === 'function') {
  context.drawPattern(figure, pattern);
}
expect(config?.displayModeBar === false, "plotly's own toolbar is shown");
const toolbar = figure.children.find(child => child.className === 'viewer-toolbar');
expect(toolbar, 'the pattern chart has no toolbar');
if (toolbar) {
  const shown = toolbar.children.filter(child => child.className === 'viewer-button')
    .map(child => [child.dataset.icon, child.title]);
  expect(JSON.stringify(shown) === JSON.stringify(appButtons),
    `the toolbar's buttons ${JSON.stringify(shown)} are not the app's ${JSON.stringify(appButtons)}`);
}
expect(drawn !== null, 'report.js drew no pattern chart');
if (drawn) {
  const { layout, traces } = drawn;
  const panes = ['y', 'y2', 'y3'];
  for (const y of panes) {
    const yaxis = layout[y.replace('y', 'yaxis')];
    const xaxis = layout[y.replace('y', 'xaxis')];
    expect(yaxis && xaxis, `pane ${y} has no axis pair`);
    if (!yaxis || !xaxis) continue;
    expect(xaxis.anchor === y, `pane ${y}'s x axis is not on its pane`);
    for (const axis of [xaxis, yaxis]) expect(axis.showline && axis.mirror === true, `pane ${y} is not framed on four sides`);
    expect(xaxis.showticklabels === (y === 'y3'), `pane ${y}: x labels belong under the lowest pane only`);
    expect(layout.shapes.some(s => s.xref === xaxis.anchor.replace('y', 'x') && s.yref === `${y} domain`),
      `pane ${y} has no excluded band of its own`);
  }
  expect(layout.xaxis2?.showgrid === false, 'the tick rows have a grid');
  expect(traces.every(t => t.xaxis === t.yaxis.replace('y', 'x')), 'a trace is not drawn on its own pane');
  for (const [upper, lower] of [['yaxis', 'yaxis2'], ['yaxis2', 'yaxis3']]) {
    const gap = (layout[upper].domain[0] - layout[lower].domain[1]) * plot;
    expect(Math.abs(gap - EM) < 0.5, `the gap under ${upper} is ${gap.toFixed(1)} px, not one em (${EM} px)`);
  }
}
for (const failure of failures) console.error(`report-pattern-panes: ${failure}`);
if (failures.length) process.exit(1);
console.log("report-pattern-panes: the report's pattern panes and toolbar follow the app's chart");
