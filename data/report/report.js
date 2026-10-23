// SPDX-License-Identifier: BSD-3-Clause
// The HTML report's figures (edi ADR-0036): each experiment's pattern as a plotly.js chart and each structure as a
// three.js scene, from the report model in this page. The series, panes, error bars, ticks, colours, instances and
// views all come from the model; this file only places them.

const model = JSON.parse(document.getElementById('edi-report-model').textContent);
// A value of the page's stylesheet; empty where no stylesheet is computed, and the chart keeps plotly's own.
const pageStyle = name =>
  typeof getComputedStyle === 'function' ? getComputedStyle(document.documentElement).getPropertyValue(name).trim() : '';

const patternStyle = key => (model.pattern_styles ?? []).find(row => row.key === key) ?? {};
const sceneStyle = key => (model.structure_styles ?? []).find(row => row.key === key) ?? {};

// The Structure page's toolbar icons: Font Awesome Free 5 solid glyphs as SVG paths, [width, height, path] (icons CC
// BY 4.0, https://fontawesome.com/license/free).
const ICONS = {
  'atom': [448, 512,
    'M223.9990234375 224.0C206.341796875 224.00390625 192.0068359375 238.341796875 192.0068359375 256.0' +
    'C192.0068359375 273.6611328125 206.345703125 288.0 224.0068359375 288.0C241.66796875 288.0' +
    ' 256.0068359375 273.6611328125 256.0068359375 256.0C255.9716796875 238.3525390625 241.6474609375' +
    ' 224.03125 223.9990234375 224.0ZM438.1708984375 128.0C427.2939453125 108.5 397.6611328125 77.25' +
    ' 321.8955078125 86.125C300.3916015625 34.875 267.6337890625 0.0 223.9990234375 0.0C180.3642578125' +
    ' 0.0 147.6083984375 34.875 126.1025390625 86.125C50.3369140625 77.375 20.7060546875 108.5' +
    ' 9.8291015625 128.0C-6.5498046875 157.375 -5.1748046875 201.125 34.9580078125 256.0C-5.1748046875' +
    ' 310.875 -6.5498046875 354.625 9.8291015625 384.0C38.9599609375 436.375 111.4755859375 427.625' +
    ' 126.1025390625 425.875C147.6083984375 477.125 180.3642578125 512.0 223.9990234375 512.0' +
    'C267.6337890625 512.0 300.3916015625 477.125 321.8955078125 425.875C336.5244140625 427.625' +
    ' 409.0400390625 436.375 438.1708984375 384.0C454.5498046875 354.625 453.1748046875 310.875' +
    ' 413.0400390625 256.0C453.1748046875 201.125 454.5498046875 157.375 438.1708984375 128.0Z' +
    'M63.3388671875 352.0C59.3388671875 344.75 63.2138671875 327.25 78.3427734375 303.75C85.2197265625' +
    ' 310.25 92.4716796875 316.625 100.2236328125 322.875C101.8486328125 336.625 104.2236328125 350.0' +
    ' 106.9736328125 363.0C82.3447265625 363.875 67.0908203125 358.625 63.3388671875 352.0Z' +
    'M100.2236328125 189.125C92.4716796875 195.375 85.2197265625 201.75 78.3427734375 208.25' +
    'C63.2138671875 184.75 59.3388671875 167.25 63.3388671875 160.0C66.7158203125 153.875 79.7177734375' +
    ' 148.5 101.2236328125 148.5C102.9736328125 148.5 105.0986328125 148.875 106.9736328125 148.875' +
    'C104.0986328125 162.25 101.8486328125 175.625 100.2236328125 189.125ZM223.9990234375 64.0' +
    'C233.5009765625 64.0 246.2548828125 77.5 257.8818359375 101.25C246.6298828125 105.0 235.3779296875' +
    ' 109.25 223.9990234375 114.125C212.6220703125 109.25 201.3701171875 105.0 190.1162109375 101.25' +
    'C201.7451171875 77.5 214.4970703125 64.0 223.9990234375 64.0ZM223.9990234375 448.0C214.4970703125' +
    ' 448.0 201.7451171875 434.5 190.1162109375 410.75C201.3701171875 407.0 212.6220703125 402.75' +
    ' 223.9990234375 397.875C235.3779296875 402.75 246.6298828125 407.0 257.8818359375 410.75' +
    'C246.2548828125 434.5 233.5009765625 448.0 223.9990234375 448.0ZM223.9990234375 336.0C179.845703125' +
    ' 336.0 143.9990234375 300.1533203125 143.9990234375 256.0C143.9990234375 211.8466796875' +
    ' 179.845703125 176.0 223.9990234375 176.0C268.15234375 176.0 303.9990234375 211.8466796875' +
    ' 303.9990234375 256.0C303.9990234375 300.1533203125 268.15234375 336.0 223.9990234375 336.0Z' +
    'M384.6591796875 352.0C381.0341796875 358.625 365.6552734375 363.875 341.0244140625 363.0' +
    'C343.7763671875 350.0 346.1513671875 336.625 347.7763671875 322.875C355.5283203125 316.625' +
    ' 362.7802734375 310.25 369.6552734375 303.75C384.7841796875 327.25 388.6591796875 344.75' +
    ' 384.6591796875 352.0ZM369.6552734375 208.25C362.7802734375 201.75 355.5283203125 195.375' +
    ' 347.7763671875 189.125C346.1513671875 175.625 343.9013671875 162.25 341.0244140625 148.875' +
    'C342.8994140625 148.875 345.0263671875 148.5 346.7763671875 148.5C368.2802734375 148.5' +
    ' 381.2841796875 153.875 384.6591796875 160.0C388.6591796875 167.25 384.7841796875 184.75' +
    ' 369.6552734375 208.25Z'],
  'tag': [512, 512,
    'M0.0 252.1181640625C0.0 265.3642578125 5.3701171875 277.3701171875 14.05859375 286.05859375' +
    'L225.94140625 497.94140625C244.685546875 516.685546875 275.078125 516.685546875 293.8232421875' +
    ' 497.94140625L497.94140625 293.8232421875C516.685546875 275.078125 516.685546875 244.685546875' +
    ' 497.94140625 225.94140625L286.05859375 14.05859375C277.3701171875 5.3701171875 265.3642578125 0.0' +
    ' 252.1181640625 0.0H48.0C21.490234375 0.0 0.0 21.490234375 0.0 48.0ZM112.0 64.0C138.509765625 64.0' +
    ' 160.0 85.490234375 160.0 112.0C160.0 138.509765625 138.509765625 160.0 112.0 160.0C85.490234375' +
    ' 160.0 64.0 138.509765625 64.0 112.0C64.0 85.490234375 85.490234375 64.0 112.0 64.0Z'],
  'link': [512, 512,
    'M326.6123046875 185.390625C320.2607421875 179.0390625 313.4755859375 173.3515625 306.08984375' +
    ' 168.1943359375C299.6884765625 163.7255859375 291.02734375 164.404296875 285.505859375' +
    ' 169.9248046875L264.4521484375 190.98046875C256.1015625 199.330078125 252.3583984375 210.21875' +
    ' 252.75390625 220.7861328125C252.9541015625 226.017578125 255.650390625 230.6103515625' +
    ' 259.701171875 233.3916015625C262.61328125 235.3974609375 266.3408203125 238.2666015625' +
    ' 270.0419921875 241.9609375C298.115234375 270.0341796875 298.2333984375 315.599609375' +
    ' 270.0419921875 343.791015625L202.841796875 410.9814453125C174.6025390625 439.2197265625' +
    ' 128.541015625 439.0498046875 100.5166015625 410.470703125C72.7666015625 382.1708984375' +
    ' 73.646484375 336.537109375 101.671875 308.5107421875L114.7587890625 295.423828125C119.109375' +
    ' 291.07421875 120.5283203125 284.6337890625 118.5419921875 278.8115234375C112.677734375' +
    ' 261.6181640625 109.5 243.8134765625 108.8515625 226.0908203125C108.34375 212.1845703125 91.3984375' +
    ' 205.64453125 81.5576171875 215.4853515625L44.4521484375 252.5908203125C-14.818359375' +
    ' 311.8505859375 -14.818359375 408.291015625 44.4521484375 467.55078125C103.712890625 526.8134765625' +
    ' 200.1416015625 526.8212890625 259.412109375 467.55078125L326.6123046875 400.3505859375' +
    'C326.732421875 400.2314453125 326.8623046875 400.1005859375 326.9716796875 399.9814453125' +
    'C385.5390625 341.0888671875 386.359375 245.2001953125 326.6123046875 185.390625ZM467.546875' +
    ' 44.44921875C408.2861328125 -14.8134765625 311.857421875 -14.8212890625 252.5869140625 44.44921875' +
    'L185.38671875 111.6494140625C185.2666015625 111.7685546875 185.13671875 111.8994140625 185.02734375' +
    ' 112.0185546875C126.4609375 170.9111328125 125.6396484375 266.7998046875 185.38671875 326.609375' +
    'C191.73828125 332.9599609375 198.5224609375 338.6484375 205.908203125 343.8046875C212.3095703125' +
    ' 348.2734375 220.9716796875 347.59375 226.4921875 342.07421875L247.5458984375 321.0185546875' +
    'C255.896484375 312.6689453125 259.6396484375 301.7802734375 259.244140625 291.212890625' +
    'C259.0439453125 285.9814453125 256.34765625 281.388671875 252.296875 278.607421875C249.384765625' +
    ' 276.6015625 245.6572265625 273.732421875 241.9560546875 270.0380859375C213.8828125 241.96484375' +
    ' 213.7646484375 196.3994140625 241.9560546875 168.2080078125L309.15625 101.017578125C337.39453125' +
    ' 72.779296875 383.4560546875 72.94921875 411.4814453125 101.5283203125C439.2314453125 129.828125' +
    ' 438.3525390625 175.4619140625 410.326171875 203.48828125L397.2392578125 216.5751953125' +
    'C392.888671875 220.9248046875 391.4697265625 227.365234375 393.4560546875 233.1865234375' +
    'C399.3203125 250.380859375 402.498046875 268.185546875 403.146484375 285.908203125C403.6552734375' +
    ' 299.814453125 420.599609375 306.353515625 430.4404296875 296.513671875L467.5458984375' +
    ' 259.408203125C526.8173828125 200.1494140625 526.8173828125 103.708984375 467.546875 44.44921875Z'],
  'vector-square': [512, 512,
    'M512 128V32C512.0 14.330078125 497.669921875 0.0 480.0 0.0H384.0C366.330078125 0.0 352.0' +
    ' 14.330078125 352.0 32.0H160.0C160.0 14.330078125 145.669921875 0.0 128.0 0.0H32.0C14.330078125 0.0' +
    ' 0.0 14.330078125 0.0 32.0V128.0C0.0 145.669921875 14.330078125 160.0 32.0 160.0V352.0C14.330078125' +
    ' 352.0 0.0 366.330078125 0.0 384.0V480.0C0.0 497.669921875 14.330078125 512.0 32.0 512.0H128.0' +
    'C145.669921875 512.0 160.0 497.669921875 160.0 480.0H352.0C352.0 497.669921875 366.330078125 512.0' +
    ' 384.0 512.0H480.0C497.669921875 512.0 512.0 497.669921875 512.0 480.0V384.0C512.0 366.330078125' +
    ' 497.669921875 352.0 480.0 352.0V160.0C497.669921875 160.0 512.0 145.669921875 512.0 128.0ZM416.0' +
    ' 64.0H448.0V96.0H416.0ZM64.0 64.0H96.0V96.0H64.0ZM96.0 448.0H64.0V416.0H96.0ZM448.0 448.0H416.0' +
    'V416.0H448.0ZM416.0 352.0H384.0C366.330078125 352.0 352.0 366.330078125 352.0 384.0V416.0H160.0' +
    'V384.0C160.0 366.330078125 145.669921875 352.0 128.0 352.0H96.0V160.0H128.0C145.669921875 160.0' +
    ' 160.0 145.669921875 160.0 128.0V96.0H352.0V128.0C352.0 145.669921875 366.330078125 160.0 384.0' +
    ' 160.0H416.0Z'],
  'location-arrow': [512, 512,
    'M444.51953125 3.51953125 28.740234375 195.419921875C-19.23046875 217.8095703125 -3.240234375' +
    ' 288.169921875 47.9296875 288.169921875H223.83984375V464.080078125C223.83984375 515.25' +
    ' 294.2001953125 531.25 316.58984375 483.26953125L508.490234375 67.490234375C524.48046875' +
    ' 29.099609375 482.900390625 -12.48046875 444.51953125 3.51953125Z'],
  'home': [576, 512,
    'M280.3701171875 148.259765625 96.0 300.1103515625V464.0C96.0 472.8310546875 103.1689453125 480.0' +
    ' 112.0 480.0L224.0595703125 479.7099609375C232.853515625 479.666015625 239.98046875 472.513671875' +
    ' 239.98046875 463.7099609375V368.0C239.98046875 359.1689453125 247.1494140625 352.0 255.98046875' +
    ' 352.0H319.98046875C328.810546875 352.0 335.98046875 359.1689453125 335.98046875 368.0' +
    'V463.6396484375C335.9794921875 463.6572265625 335.9794921875 463.673828125 335.9794921875' +
    ' 463.69140625C335.9794921875 472.521484375 343.1494140625 479.6904296875 351.98046875' +
    ' 479.6904296875L464.0 480.0C472.8310546875 480.0 480.0 472.8310546875 480.0 464.0V300.0' +
    'L295.669921875 148.259765625C293.5791015625 146.57421875 290.9208984375 145.5654296875' +
    ' 288.0283203125 145.5654296875C285.1357421875 145.5654296875 282.4609375 146.57421875' +
    ' 280.3701171875 148.259765625ZM571.599609375 251.4697265625 488.0 182.5595703125V44.0498046875' +
    'C488.0 37.4267578125 482.623046875 32.0498046875 476.0 32.0498046875H420.0C413.376953125' +
    ' 32.0498046875 408.0 37.4267578125 408.0 44.0498046875V116.66015625L318.4697265625 43.0C310.1796875' +
    ' 36.177734375 299.5654296875 32.0791015625 288.0009765625 32.0791015625C276.4365234375' +
    ' 32.0791015625 265.7607421875 36.177734375 257.4697265625 43.0L4.33984375 251.4697265625C1.67578125' +
    ' 253.671875 -0.0224609375 257.0009765625 -0.0224609375 260.7236328125C-0.0224609375 263.6259765625' +
    ' 1.021484375 266.2939453125 2.740234375 268.3701171875L28.240234375 299.3701171875C30.44140625' +
    ' 302.046875 33.779296875 303.755859375 37.51171875 303.755859375C40.4111328125 303.755859375' +
    ' 43.0751953125 302.7138671875 45.150390625 301.0L280.3701171875 107.259765625C282.4609375' +
    ' 105.57421875 285.119140625 104.5654296875 288.01171875 104.5654296875C290.9033203125' +
    ' 104.5654296875 293.5791015625 105.57421875 295.669921875 107.259765625L530.900390625 301.0' +
    'C532.9765625 302.7177734375 535.6396484375 303.7509765625 538.54296875 303.7509765625C542.265625' +
    ' 303.7509765625 545.5986328125 302.0634765625 547.7998046875 299.400390625L573.2998046875' +
    ' 268.400390625C575.0029296875 266.328125 576.025390625 263.6767578125 576.025390625 260.7880859375' +
    'C576.025390625 257.03125 574.306640625 253.6708984375 571.599609375 251.4697265625Z'],
  'camera': [512, 512,
    'M512 144C512.0 117.5 490.5 96.0 464.0 96.0H376.0L363.599609375 63.099609375C356.599609375' +
    ' 44.400390625 338.7001953125 32.0 318.7001953125 32.0H193.2001953125C173.2001953125 32.0' +
    ' 155.2998046875 44.400390625 148.2998046875 63.099609375L136.0 96.0H48.0C21.5 96.0 0.0 117.5 0.0' +
    ' 144.0V432.0C0.0 458.5 21.5 480.0 48.0 480.0H464.0C490.5 480.0 512.0 458.5 512.0 432.0ZM376.0 288.0' +
    'C376.0 354.2001953125 322.2001953125 408.0 256.0 408.0C189.7998046875 408.0 136.0 354.2001953125' +
    ' 136.0 288.0C136.0 221.7998046875 189.7998046875 168.0 256.0 168.0C322.2001953125 168.0 376.0' +
    ' 221.7998046875 376.0 288.0ZM344.0 288.0C344.0 239.5 304.5 200.0 256.0 200.0C207.5 200.0 168.0' +
    ' 239.5 168.0 288.0C168.0 336.5 207.5 376.0 256.0 376.0C304.5 376.0 344.0 336.5 344.0 288.0Z'],
};

// A figure that cannot be drawn says why.
function notice(figure, text) {
  figure.classList?.add('figure-note');
  figure.textContent = text;
}

// --- The pattern charts (edi ADR-0021) ---

const paneAxis = { main: 'y', bragg: 'y2', residual: 'y3' };

// Each pane's y domain, top to bottom: a fixed pane takes its pixels of the plot's height, a stretching one its share
// of what the fixed panes leave.
function paneDomains(layout, plotHeight) {
  const fixed = layout.reduce((sum, pane) => sum + pane.fixed_px, 0);
  const rest = Math.max(0, 1 - fixed / plotHeight);
  const domains = {};
  let top = 1;
  for (const pane of layout) {
    const share = pane.fixed_px > 0 ? pane.fixed_px / plotHeight : pane.stretch * rest;
    domains[pane.pane] = [Math.max(0, top - share), top];
    top -= share;
  }
  return domains;
}

// An axis title as its coloured pieces, each series' word in its colour, as the app draws it; the plain title when it
// has none.
function axisTitle(axis) {
  const segments = axis.segments ?? [];
  return segments.length === 0
    ? axis.title
    : segments.map(segment => (segment.style ? inColour(segment.text, patternStyle(segment.style).light) : segment.text)).join('');
}

// A text in a colour, as plotly writes a styled span.
function inColour(text, colour) {
  return `<span style="color:${colour}">${text}</span>`;
}

// A series as a plotly trace: a null point is a gap, the measured bars are error bars to their ends (a missing lower
// end reaches the bottom of the pane), and a Bragg tick hovers with its Miller indices.
function trace(pattern, series, index) {
  const look = patternStyle(series.style);
  const marks = (look.mark ?? 'line').split('+');
  const out = {
    type: 'scatter',
    // The legend names each series in its colour, as the app's chart legend does: the residual's `meas − calc`
    // coloured as the residual pane's title (edi::legend_label).
    name: series.kind === 'residual' && (pattern.y_residual.segments ?? []).length > 0
      ? `${inColour('Residual (', look.light)}${axisTitle(pattern.y_residual)}${inColour(')', look.light)}`
      : inColour(series.label, look.light),
    x: series.x,
    y: series.y,
    xaxis: 'x',
    yaxis: paneAxis[series.pane],
    mode: marks.includes('markers') ? 'lines+markers' : 'lines',
    connectgaps: false,
    opacity: look.opacity ?? 1,
    line: { color: look.light, width: look.width_px, dash: marks.includes('dash') ? 'dash' : 'solid' },
    hovertemplate: '%{x}, %{y}<extra>%{fullData.name}</extra>',
  };
  if (marks.includes('markers')) {
    out.marker = { color: look.light, size: look.marker_px };
  }
  if (marks.includes('bars') && series.bar_high.length === series.y.length) {
    out.error_y = {
      type: 'data',
      symmetric: false,
      color: look.light,
      thickness: 1,
      width: 0,
      array: series.y.map((y, i) => (y === null || series.bar_high[i] === null ? null : series.bar_high[i] - y)),
      arrayminus: series.y.map((y, i) =>
        y === null ? null : series.bar_low[i] === null ? y - pattern.y_main.min : y - series.bar_low[i]),
    };
  }
  if (series.kind === 'bragg') {
    // Named as the app's legend names a structure's ticks.
    out.name = inColour(`Bragg peaks · ${series.label}`, look.light);
    out.text = pattern.hover[index];
    out.hovertemplate = '%{text}<extra>%{fullData.name}</extra>';
  }
  return out;
}

function drawPattern(figure, pattern) {
  if (!window.Plotly) {
    notice(figure, 'The chart needs plotly.js, which could not be loaded.');
    return;
  }
  if (pattern.series.length === 0) {
    notice(figure, 'No pattern to show');
    return;
  }
  const font = pageStyle('--head-font');
  // diffraction-lib's report's lines: a light grid, the frame in the tables' border colour, no zero lines.
  const grid = pageStyle('--rowshade');
  const frame = pageStyle('--tableborder');
  // The plot starts no closer to the frame's top than to its sides, and plotly's toolbar sits above it, clear of the
  // legend.
  const margin = { l: 16, r: 16, t: 36, b: 16 };
  const domains = paneDomains(pattern.layout, figure.clientHeight - margin.t - margin.b);
  const bottom = 'residual' in domains ? 'y3' : 'bragg' in domains ? 'y2' : 'y';
  const excluded = patternStyle('excluded');
  const axis = { automargin: true, showline: true, mirror: true, linecolor: frame, gridcolor: grid, zeroline: false };
  // Each Bragg row's label at its left, the structure's name in its colour, as the app draws it.
  const braggLabels = 'bragg' in domains
    ? (pattern.bragg_labels ?? []).map(label => ({
        text: inColour(label.text, patternStyle(label.style).light), xref: 'paper', yref: 'y2', x: 0, y: label.centre,
        xanchor: 'right', xshift: -6, showarrow: false, font: { family: font } }))
    : [];
  const layout = {
    height: figure.clientHeight,
    margin,
    font: { family: font },
    // The model says whether a legend is drawn; without one the y titles name the series in their colours.
    showlegend: pattern.legend,
    legend: { x: 1, xanchor: 'right', y: 1, yanchor: 'top', bgcolor: 'rgba(255,255,255,0.8)' },
    hovermode: 'closest',
    // The experiment's reliability in its last fit, above the plot's top left, as the app's selector shows it.
    annotations: (pattern.title
      ? [{ text: pattern.title, xref: 'paper', yref: 'paper', x: 0, y: 1, xanchor: 'left', yanchor: 'bottom',
           showarrow: false, font: { family: font } }]
      : []).concat(braggLabels),
    xaxis: { ...axis, title: { text: pattern.x.title }, range: [pattern.x.min, pattern.x.max], anchor: bottom },
    yaxis: { ...axis, title: { text: axisTitle(pattern.y_main) }, domain: domains.main ?? [0, 1] },
    shapes: pattern.excluded.map(([x0, x1]) => ({
      type: 'rect',
      xref: 'x',
      yref: 'paper',
      x0,
      x1,
      y0: 0,
      y1: 1,
      fillcolor: excluded.light,
      opacity: excluded.opacity,
      line: { width: 0 },
      layer: 'below',
    })),
  };
  if ('bragg' in domains) {
    const rows = pattern.series.filter(series => series.kind === 'bragg').length;
    layout.yaxis2 = {
      ...axis,
      domain: domains.bragg,
      range: [0, rows],
      showticklabels: false,
      showgrid: false,
      fixedrange: true,
    };
  }
  if ('residual' in domains) {
    layout.yaxis3 = { ...axis, title: { text: axisTitle(pattern.y_residual) }, domain: domains.residual };
  }
  const traces = pattern.series.map((series, index) => trace(pattern, series, index));
  window.Plotly.newPlot(figure, traces, layout, { responsive: true, displaylogo: false });
}

// A single crystal's chart (edi ADR-0048), as the app draws it: each reflection's F²meas with its s.u. bar against its
// F²calc, the y = x line a perfect model puts them on, one range on both axes; "Not calculated yet" before a
// calculation.
function drawSingleCrystal(figure, crystal) {
  if (!window.Plotly) {
    notice(figure, 'The chart needs plotly.js, which could not be loaded.');
    return;
  }
  if (crystal.calc.length === 0) {
    notice(figure, 'Not calculated yet');
    return;
  }
  const font = pageStyle('--head-font');
  const grid = pageStyle('--rowshade');
  const frame = pageStyle('--tableborder');
  const style = patternStyle('meas.0');
  let low = 0;
  let high = 0;
  crystal.meas.forEach((meas, i) => {
    for (const end of [meas - crystal.su[i], meas + crystal.su[i], crystal.calc[i]]) {
      if (Number.isFinite(end)) {
        low = Math.min(low, end);
        high = Math.max(high, end);
      }
    }
  });
  const pad = (high - low) * 0.05 || 1;
  const range = [Math.min(0, low - pad), high + pad];
  const axis = { automargin: true, showline: true, mirror: true, linecolor: frame, gridcolor: grid, zeroline: false, range };
  const points = {
    type: 'scatter',
    mode: 'markers',
    name: 'Reflections',
    x: crystal.calc,
    y: crystal.meas,
    error_y: { type: 'data', array: crystal.su, visible: true, thickness: 1, width: 0, color: style.light },
    text: crystal.meas.map((meas, i) => `${crystal.h[i]} ${crystal.k[i]} ${crystal.l[i]}`),
    hovertemplate: '%{text}<br>F²meas %{y}<br>F²calc %{x}<extra></extra>',
    marker: { color: style.light, size: 5 },
  };
  const diagonal = {
    type: 'scatter',
    mode: 'lines',
    x: range,
    y: range,
    hoverinfo: 'skip',
    line: { color: frame, width: 1 },
  };
  const layout = {
    height: figure.clientHeight,
    margin: { l: 16, r: 16, t: 36, b: 16 },
    font: { family: font },
    showlegend: false,
    hovermode: 'closest',
    annotations: crystal.title
      ? [{ text: crystal.title, xref: 'paper', yref: 'paper', x: 0, y: 1, xanchor: 'left', yanchor: 'bottom',
           showarrow: false, font: { family: font } }]
      : [],
    xaxis: { ...axis, title: { text: 'F² calc' } },
    yaxis: { ...axis, title: { text: 'F² meas' } },
  };
  window.Plotly.newPlot(figure, [diagonal, points], layout, { responsive: true, displaylogo: false });
}

// One of a scan's evolution charts (edi ADR-0036): a parameter at each fitted dataset with its s.u. as an error bar,
// titled with its name and units; "No fitted results yet" before any dataset is fitted.
function drawEvolution(figure, series) {
  const font = pageStyle('--head-font');
  const grid = pageStyle('--rowshade');
  const frame = pageStyle('--tableborder');
  const axis = { automargin: true, showline: true, mirror: true, linecolor: frame, gridcolor: grid, zeroline: false };
  if (series.points.length === 0) {
    notice(figure, 'No fitted results yet');
    return;
  }
  if (!window.Plotly) {
    notice(figure, 'The chart needs plotly.js, which could not be loaded.');
    return;
  }
  const style = patternStyle('meas.0');
  const trace = {
    // Points with their s.u. bars and no line, as the Evolution tab draws them.
    type: 'scatter',
    mode: 'markers',
    name: series.name,
    x: series.points.map(point => point.x),
    y: series.points.map(point => point.y),
    error_y: { type: 'data', array: series.points.map(point => point.su), visible: true, thickness: 1, color: style.light },
    text: series.points.map(point => point.text),
    hovertemplate: '%{x}: %{text}<extra></extra>',
    marker: { color: style.light, size: 6 },
  };
  const layout = {
    height: figure.clientHeight,
    // The toolbar stands at the right, clear of the title.
    margin: { l: 16, r: 40, t: 40, b: 16 },
    modebar: { orientation: 'v' },
    font: { family: font },
    title: { text: series.units ? `${series.name} (${series.units})` : series.name, x: 0.02, xanchor: 'left' },
    showlegend: false,
    hovermode: 'closest',
    xaxis: { ...axis, title: { text: series.x_title } },
    yaxis: { ...axis },
  };
  window.Plotly.newPlot(figure, [trace], layout, { responsive: true, displaylogo: false });
}

// --- The structure views (edi ADR-0022) ---

// A toolbar button with an icon (or a letter), its tooltip, and whether it is on.
function button(icon, title, onClick) {
  const element = document.createElement('button');
  element.type = 'button';
  element.className = 'viewer-button';
  element.title = title;
  if (ICONS[icon]) {
    const [width, height, path] = ICONS[icon];
    element.innerHTML = `<svg viewBox="0 0 ${width} ${height}" aria-hidden="true"><path d="${path}"/></svg>`;
  } else {
    element.textContent = icon;
  }
  element.addEventListener('click', onClick);
  return element;
}

async function drawStructure(figure, structure) {
  // three.js as the page provides it: already loaded, else imported through the page's import map.
  let THREE, OrbitControls;
  try {
    THREE = globalThis.THREE ?? (await import('three'));
    OrbitControls =
      globalThis.OrbitControls ?? (await import('three/addons/controls/OrbitControls.js')).OrbitControls;
  } catch {
    notice(figure, 'The structure view needs three.js, which could not be loaded.');
    return;
  }
  const { scene, view, drawing } = structure;
  if (!scene.current || drawing.spheres.length + drawing.shared.length === 0) {
    notice(figure, 'No structure to show');
    return;
  }
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setClearColor(sceneStyle('background').light);
  figure.appendChild(renderer.domElement);
  const world = new THREE.Scene();
  const value = key => sceneStyle(key).value;
  const material = new THREE.MeshPhongMaterial({
    specular: new THREE.Color().setScalar(value('material.specular')),
    shininess: value('material.shininess'),
  });
  const sphere = new THREE.SphereGeometry(1, 32, 16);
  const cylinder = new THREE.CylinderGeometry(1, 1, 1, 16);

  // What the toolbar shows, as the Structure page's features: the atoms (all, the asymmetric unit or none), the labels,
  // the bonds, the cell and the axes.
  const shown = { atoms: 'all', labels: false, bonds: true, cell: true, axes: true };
  const atomShown = index => shown.atoms === 'all' || (shown.atoms === 'asymmetric' && scene.atoms[index].asymmetric);

  // The drawing's instances on unit meshes: a sphere of radius 1, a cylinder of radius 1 and length 1 along +y. The
  // model's quaternions are w, x, y, z; three.js takes x, y, z, w.
  const instanced = (geometry, instances) => {
    const mesh = new THREE.InstancedMesh(geometry, material, Math.max(1, instances.length));
    mesh.count = instances.length;
    const matrix = new THREE.Matrix4();
    const position = new THREE.Vector3();
    const rotation = new THREE.Quaternion();
    const scale = new THREE.Vector3();
    const colour = new THREE.Color();
    instances.forEach((item, i) => {
      const [w, x, y, z] = item.rotation;
      matrix.compose(position.fromArray(item.position), rotation.set(x, y, z, w), scale.fromArray(item.scale));
      mesh.setMatrixAt(i, matrix);
      mesh.setColorAt(i, colour.set(item.color));
    });
    return mesh;
  };
  // The sites several atoms share, as the app draws them: each site's sphere cut into wedges about the home view's
  // direction, each wedge its part's fraction of the turn in the part's colour, the first starting at the plane through
  // that direction and the home view's up. A part of fraction 0 has no wedge.
  const wedgeMaterial = material.clone();
  wedgeMaterial.vertexColors = true;
  const sharedSites = sites => {
    const segments = 32;
    const rings = 16;
    const axis = new THREE.Vector3().fromArray(scene.frame.view_direction).normalize();
    const up = new THREE.Vector3().fromArray(scene.frame.view_up).normalize();
    const right = new THREE.Vector3().crossVectors(up, axis).normalize();
    const positions = [];
    const normals = [];
    const colours = [];
    const indices = [];
    const normal = new THREE.Vector3();
    const colour = new THREE.Color();
    for (const site of sites) {
      const atom = scene.atoms[site];
      const centre = new THREE.Vector3().fromArray(atom.centre);
      let start = 0;
      for (const part of atom.parts) {
        const fraction = Number.isFinite(part.fraction) ? Math.min(Math.max(part.fraction, 0), 1) : 0;
        if (fraction <= 0) {
          continue;
        }
        const span = fraction * 2 * Math.PI;
        const steps = Math.max(1, Math.ceil(fraction * segments));
        colour.set(part.color);
        const base = positions.length / 3;
        for (let i = 0; i <= rings; ++i) {
          const theta = (Math.PI * i) / rings; // from the axis, towards the viewer at 0
          for (let j = 0; j <= steps; ++j) {
            const phi = start + (span * j) / steps; // from up, towards right
            normal
              .copy(axis)
              .multiplyScalar(Math.cos(theta))
              .addScaledVector(up, Math.sin(theta) * Math.cos(phi))
              .addScaledVector(right, Math.sin(theta) * Math.sin(phi));
            normals.push(normal.x, normal.y, normal.z);
            positions.push(...normal.clone().multiplyScalar(atom.radius).add(centre).toArray());
            colours.push(colour.r, colour.g, colour.b);
          }
        }
        const row = steps + 1;
        for (let i = 0; i < rings; ++i) {
          for (let j = 0; j < steps; ++j) {
            const a = base + i * row + j;
            const b = a + row;
            indices.push(a, a + 1, b, a + 1, b + 1, b);
          }
        }
        start += span;
      }
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colours, 3));
    geometry.setIndex(indices);
    return new THREE.Mesh(geometry, wedgeMaterial);
  };
  // The cylinders are the half-bonds, two per bond in the scene's order, then the cell edges.
  const halves = 2 * scene.bonds.length;
  let meshes = new THREE.Group();
  const place = () => {
    world.remove(meshes);
    meshes = new THREE.Group();
    meshes.add(instanced(sphere, drawing.spheres.filter(item => atomShown(item.atom))));
    meshes.add(sharedSites(drawing.shared.filter(atomShown)));
    const bonds = shown.bonds ? drawing.cylinders.slice(0, halves).filter((_, i) => {
      const bond = scene.bonds[Math.floor(i / 2)];
      return atomShown(bond.atom_1) && atomShown(bond.atom_2);
    }) : [];
    meshes.add(instanced(cylinder, bonds));
    meshes.add(instanced(cylinder, shown.cell ? drawing.cylinders.slice(halves) : []));
    triad.visible = shown.axes;
    world.add(meshes);
  };

  // The axis arrows: a shaft and a head along each axis from the origin, the letter beside the head.
  const triad = new THREE.Group();
  const up = new THREE.Vector3(0, 1, 0);
  const overlay = [];
  for (const arrow of drawing.triad) {
    const direction = new THREE.Vector3().fromArray(arrow.direction);
    const turn = new THREE.Quaternion().setFromUnitVectors(up, direction);
    const ink = new THREE.MeshPhongMaterial({ color: arrow.color });
    const origin = new THREE.Vector3().fromArray(arrow.origin);
    const shaft = new THREE.Mesh(cylinder, ink);
    shaft.position.copy(origin).addScaledVector(direction, arrow.shaft_length / 2);
    shaft.quaternion.copy(turn);
    shaft.scale.set(arrow.shaft_radius, arrow.shaft_length, arrow.shaft_radius);
    const head = new THREE.Mesh(new THREE.ConeGeometry(1, 1, 24), ink);
    head.position.copy(origin).addScaledVector(direction, arrow.shaft_length + arrow.head_length / 2);
    head.quaternion.copy(turn);
    head.scale.set(arrow.head_radius, arrow.head_length, arrow.head_radius);
    triad.add(shaft, head);
    const letter = document.createElement('div');
    letter.className = 'axis-letter';
    letter.style.color = arrow.color;
    letter.textContent = arrow.letter;
    figure.appendChild(letter);
    overlay.push({ element: letter, at: new THREE.Vector3().fromArray(arrow.letter_anchor), show: () => shown.axes });
  }
  world.add(triad);
  // The atom labels, shown when asked for.
  for (const label of structure.labels) {
    const element = document.createElement('div');
    element.className = 'atom-label';
    element.style.color = sceneStyle('label').light;
    element.textContent = label.text;
    figure.appendChild(element);
    const at = new THREE.Vector3().fromArray(label.anchor);
    overlay.push({ element, at, show: () => shown.labels && atomShown(label.atom) });
  }

  // The element legend.
  const legend = document.createElement('div');
  legend.className = 'structure-legend';
  for (const entry of scene.legend) {
    const row = document.createElement('div');
    const swatch = document.createElement('span');
    swatch.className = 'swatch';
    swatch.style.background = entry.color;
    row.append(swatch, entry.element);
    legend.appendChild(row);
  }
  figure.appendChild(legend);

  // The view: an orthographic camera looking along a view's direction at the frame's target, its half height the
  // fitted one at the view's magnification. The lights follow the camera.
  const target = new THREE.Vector3().fromArray(scene.frame.target);
  const distance = 4 * (drawing.fitted_half_height + scene.frame.half_width + scene.frame.pad);
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, distance / 100, 3 * distance);
  world.add(new THREE.AmbientLight(0xffffff, value('light.ambient')));
  for (const name of ['key', 'fill']) {
    const light = new THREE.DirectionalLight(0xffffff, value(`light.${name}`));
    light.position.set(value(`light.${name}.right`), value(`light.${name}.up`), value(`light.${name}.toward`));
    camera.add(light, light.target);
  }
  world.add(camera);
  const controls = new OrbitControls(camera, renderer.domElement);
  let halfHeight = 1;

  const render = () => {
    renderer.render(world, camera);
    const size = renderer.getSize(new THREE.Vector2());
    for (const item of overlay) {
      const at = item.at.clone().project(camera);
      item.element.style.display = item.show() ? '' : 'none';
      item.element.style.left = `${((at.x + 1) / 2) * size.x}px`;
      item.element.style.top = `${((1 - at.y) / 2) * size.y}px`;
    }
  };
  const fit = () => {
    const width = figure.clientWidth;
    const height = figure.clientHeight;
    renderer.setSize(width, height);
    const aspect = width / height;
    camera.left = -halfHeight * aspect;
    camera.right = halfHeight * aspect;
    camera.top = halfHeight;
    camera.bottom = -halfHeight;
    camera.updateProjectionMatrix();
    render();
  };
  // The home view and the views along a, b and c are the core's (default_view, view_along).
  const look = chosen => {
    halfHeight = drawing.fitted_half_height / chosen.magnification;
    camera.zoom = 1;
    camera.position.copy(target).addScaledVector(new THREE.Vector3().fromArray(chosen.direction).normalize(), distance);
    camera.up.fromArray(chosen.up);
    camera.lookAt(target);
    controls.target.copy(target);
    controls.update();
    fit();
  };

  // The toolbar, as the Structure page's: the features, then view along a, b and c and home; a snapshot below.
  const toolbar = document.createElement('div');
  toolbar.className = 'viewer-toolbar';
  const toggles = [];
  const toggle = (icon, title, key, next) => {
    const element = button(icon, title, () => {
      shown[key] = next(shown[key]);
      refresh();
    });
    toggles.push({ element, on: () => (key === 'atoms' ? shown.atoms !== 'none' : shown[key]) });
    toolbar.appendChild(element);
  };
  const hasSites = scene.atoms.length > 0;
  if (hasSites) {
    toggle('atom', scene.has_copies ? 'Atoms: all / asymmetric unit / none' : 'Atoms: show / hide', 'atoms',
      now => (now === 'all' ? (scene.has_copies ? 'asymmetric' : 'none') : now === 'asymmetric' ? 'none' : 'all'));
    if (structure.labels.length > 0) {
      toggle('tag', 'Labels', 'labels', now => !now);
    }
    if (scene.bonds.length > 0) {
      toggle('link', 'Bonds', 'bonds', now => !now);
    }
  }
  toggle('vector-square', 'Cell', 'cell', now => !now);
  toggle('location-arrow', 'Axes', 'axes', now => !now);
  const gap = document.createElement('span');
  gap.className = 'gap';
  toolbar.appendChild(gap);
  ['a', 'b', 'c'].forEach((name, axis) => {
    const element = button(name, `View along ${name}`, () => look(structure.along[axis]));
    element.classList.add('axis-button');
    element.style.color = sceneStyle(`axis.${name}`).light;
    toolbar.appendChild(element);
  });
  toolbar.appendChild(button('home', 'Reset view', () => look(view)));
  figure.appendChild(toolbar);
  const snapshot = button('camera', 'Save a picture of the view', () => {
    renderer.domElement.toBlob(blob => {
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `${structure.id}.png`;
      link.click();
      URL.revokeObjectURL(link.href);
    });
  });
  snapshot.classList.add('viewer-snapshot');
  figure.appendChild(snapshot);

  const refresh = () => {
    for (const item of toggles) {
      item.element.setAttribute('aria-pressed', String(item.on()));
    }
    place();
    render();
  };
  controls.addEventListener('change', render);
  new ResizeObserver(fit).observe(figure);
  refresh();
  look(view);
}

for (const figure of document.querySelectorAll('.pattern-figure')) {
  const experiment = model.experiments?.[Number(figure.dataset.index)];
  if (experiment?.single_crystal) {
    drawSingleCrystal(figure, experiment.single_crystal);
  } else if (experiment) {
    drawPattern(figure, experiment.pattern);
  }
}
for (const figure of document.querySelectorAll('.structure-figure')) {
  const structure = model.structures?.[Number(figure.dataset.index)];
  if (structure) {
    drawStructure(figure, structure);
  }
}
const evolution = model.evolution ?? [];
if (evolution.length > 0) {
  for (const figure of document.querySelectorAll('.evolution-figure')) {
    const series = evolution[Number(figure.dataset.index)];
    if (series) drawEvolution(figure, series);
  }
}
