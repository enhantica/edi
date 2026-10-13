// SPDX-License-Identifier: BSD-3-Clause
// The HTML report's figures (edi ADR-0035): each experiment's pattern as a plotly.js chart and each structure as a
// three.js scene, from the report model in this page. The series, panes, error bars, ticks, colours, instances and
// views all come from the model; this file only places them.

const model = JSON.parse(document.getElementById('edi-report-model').textContent);
const page = getComputedStyle(document.documentElement);

const patternStyle = key => model.pattern_styles.find(row => row.key === key) ?? {};
const sceneStyle = key => model.structure_styles.find(row => row.key === key) ?? {};

// A figure that cannot be drawn says why.
function notice(figure, text) {
  figure.classList.add('figure-note');
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

// A series as a plotly trace: a null point is a gap, the measured bars are error bars to their ends (a missing lower
// end reaches the bottom of the pane), and a Bragg tick hovers with its Miller indices.
function trace(pattern, series, index) {
  const look = patternStyle(series.style);
  const marks = (look.mark ?? 'line').split('+');
  const out = {
    type: 'scatter',
    name: series.label,
    x: series.x,
    y: series.y,
    xaxis: 'x',
    yaxis: paneAxis[series.pane],
    mode: marks.includes('markers') ? 'lines+markers' : 'lines',
    connectgaps: false,
    opacity: look.opacity ?? 1,
    line: { color: look.light, width: look.width_px },
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
  const font = page.getPropertyValue('--head-font');
  const grid = page.getPropertyValue('--tableborder').trim();
  // The plot starts no closer to the frame's top than to its sides.
  const margin = { l: 16, r: 16, t: 16, b: 16 };
  const domains = paneDomains(pattern.layout, figure.clientHeight - margin.t - margin.b);
  const bottom = 'residual' in domains ? 'y3' : 'bragg' in domains ? 'y2' : 'y';
  const excluded = patternStyle('excluded');
  const axis = { automargin: true, showline: true, mirror: true, linecolor: grid, gridcolor: grid, zeroline: false };
  const layout = {
    height: figure.clientHeight,
    margin,
    font: { family: font },
    showlegend: true,
    legend: { x: 1, xanchor: 'right', y: 1, yanchor: 'top', bgcolor: 'rgba(255,255,255,0.8)' },
    hovermode: 'closest',
    xaxis: { ...axis, title: { text: pattern.x.title }, range: [pattern.x.min, pattern.x.max], anchor: bottom },
    yaxis: { ...axis, title: { text: pattern.y_main.title }, domain: domains.main ?? [0, 1] },
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
    layout.yaxis3 = { ...axis, title: { text: pattern.y_residual.title }, domain: domains.residual };
  }
  const traces = pattern.series.map((series, index) => trace(pattern, series, index));
  window.Plotly.newPlot(figure, traces, layout, { responsive: true, displaylogo: false });
}

// --- The structure views (edi ADR-0022) ---

async function drawStructure(figure, structure) {
  let THREE, OrbitControls;
  try {
    THREE = await import('three');
    ({ OrbitControls } = await import('three/addons/controls/OrbitControls.js'));
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

  // The drawing's instances on unit meshes: a sphere of radius 1, a cylinder of radius 1 and length 1 along +y. The
  // model's quaternions are w, x, y, z; three.js takes x, y, z, w.
  const place = (geometry, instances) => {
    if (instances.length === 0) {
      return;
    }
    const mesh = new THREE.InstancedMesh(geometry, material, instances.length);
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
    world.add(mesh);
  };
  const sphere = new THREE.SphereGeometry(1, 32, 16);
  place(sphere, drawing.spheres);
  place(new THREE.CylinderGeometry(1, 1, 1, 16), drawing.cylinders);
  // A site several atoms share, as a sphere in its main part's colour.
  place(sphere, drawing.shared.map(index => {
    const atom = scene.atoms[index];
    const radius = atom.radius;
    const color = atom.parts[atom.major].color;
    return { position: atom.centre, scale: [radius, radius, radius], rotation: [1, 0, 0, 0], color };
  }));

  // The axis arrows: a shaft and a head along each axis from the origin, the letter beside the head.
  const up = new THREE.Vector3(0, 1, 0);
  const letters = [];
  for (const arrow of drawing.triad) {
    const direction = new THREE.Vector3().fromArray(arrow.direction);
    const turn = new THREE.Quaternion().setFromUnitVectors(up, direction);
    const ink = new THREE.MeshPhongMaterial({ color: arrow.color });
    const origin = new THREE.Vector3().fromArray(arrow.origin);
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1, 16), ink);
    shaft.position.copy(origin).addScaledVector(direction, arrow.shaft_length / 2);
    shaft.quaternion.copy(turn);
    shaft.scale.set(arrow.shaft_radius, arrow.shaft_length, arrow.shaft_radius);
    const head = new THREE.Mesh(new THREE.ConeGeometry(1, 1, 24), ink);
    head.position.copy(origin).addScaledVector(direction, arrow.shaft_length + arrow.head_length / 2);
    head.quaternion.copy(turn);
    head.scale.set(arrow.head_radius, arrow.head_length, arrow.head_radius);
    world.add(shaft, head);
    const letter = document.createElement('div');
    letter.className = 'axis-letter';
    letter.style.color = arrow.color;
    letter.textContent = arrow.letter;
    figure.appendChild(letter);
    letters.push({ element: letter, at: new THREE.Vector3().fromArray(arrow.letter_anchor) });
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

  // The home view: an orthographic camera looking along the view's direction at the frame's target, its half height
  // the fitted one at the view's magnification. The lights follow the camera.
  const target = new THREE.Vector3().fromArray(scene.frame.target);
  const halfHeight = drawing.fitted_half_height / view.magnification;
  const distance = 4 * (halfHeight + scene.frame.half_width + scene.frame.pad);
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, distance / 100, 3 * distance);
  camera.position.copy(target).addScaledVector(new THREE.Vector3().fromArray(view.direction).normalize(), distance);
  camera.up.fromArray(view.up);
  camera.lookAt(target);
  world.add(new THREE.AmbientLight(0xffffff, value('light.ambient')));
  for (const name of ['key', 'fill']) {
    const light = new THREE.DirectionalLight(0xffffff, value(`light.${name}`));
    light.position.set(value(`light.${name}.right`), value(`light.${name}.up`), value(`light.${name}.toward`));
    camera.add(light, light.target);
  }
  world.add(camera);

  const render = () => {
    renderer.render(world, camera);
    const size = renderer.getSize(new THREE.Vector2());
    for (const letter of letters) {
      const at = letter.at.clone().project(camera);
      letter.element.style.left = `${((at.x + 1) / 2) * size.x}px`;
      letter.element.style.top = `${((1 - at.y) / 2) * size.y}px`;
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
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.copy(target);
  controls.update();
  controls.addEventListener('change', render);
  new ResizeObserver(fit).observe(figure);
  fit();
}

for (const figure of document.querySelectorAll('.pattern-figure')) {
  drawPattern(figure, model.experiments[Number(figure.dataset.index)].pattern);
}
for (const figure of document.querySelectorAll('.structure-figure')) {
  drawStructure(figure, model.structures[Number(figure.dataset.index)]);
}
