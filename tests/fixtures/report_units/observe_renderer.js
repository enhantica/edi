// Observe the actual report program with pinned three.js math and a GPU-free boundary.
const fs = require('fs');
const path = require('path');
const {pathToFileURL} = require('url');
const vm = require('vm');
const [sourcePath, modelPath] = process.argv.slice(2);
const model = JSON.parse(fs.readFileSync(modelPath, 'utf8'));
const records = {plots: [], quaternions: [], matrices: [], cameras: [], geometries: [], rendered: []};
const cameras = [];
const elements = [];
records.axisClicks = [];
const events = [];
let math;
function element(id) {
    const node = {id, listeners: {}, dataset: new Proxy({}, {get: () => '0'}), style: {}, children: [],
        classList: {add() {}, remove() {}},
        clientWidth: 800, clientHeight: 600, offsetWidth: 800, offsetHeight: 600,
        textContent: id === 'edi-report-model' ? JSON.stringify(model) : '',
        getAttribute: () => '0', setAttribute() {},
        append(...items) { this.children.push(...items); },
        appendChild(child) { this.children.push(child); },
        addEventListener(name, action) { this.listeners[name] = action; }, querySelector: selector => element(selector),
        querySelectorAll: selector => [element(selector)],
        getBoundingClientRect: () => ({width: 800, height: 600})};
    elements.push(node);
    return node;
}
class Renderer {
    constructor() { this.domElement = element('canvas'); this.width = 800; this.height = 600; }
    setSize(width, height) { this.width = width; this.height = height; }
    getSize(target) { return target.set(this.width, this.height); }
    setPixelRatio() {}
    setClearColor() {}
    render(scene, camera) {
        scene.updateMatrixWorld();
        camera.updateMatrixWorld();
        records.rendered = [];
        scene.traverseVisible(mesh => {
            if (!mesh.isInstancedMesh) return;
            const matrix = new math.Matrix4();
            for (let index = 0; index < mesh.count; ++index) {
                mesh.getMatrixAt(index, matrix);
                matrix.premultiply(mesh.matrixWorld);
                records.rendered.push({geometry: mesh.geometry.type, elements: matrix.toArray()});
            }
        });
    }
}
(async () => {
    // The published package is shipped as .js; .mjs identifies it as ESM to Node.
    // Only the owned temporary model folder receives a copy. No library math is reimplemented.
    let library = {};
    const THREE = {};
    if (model.structures.length > 0) {
        const modulePath = path.join(path.dirname(modelPath), 'three-observer.mjs');
        fs.copyFileSync(path.join(path.dirname(sourcePath), 'vendor', 'three-0.160.0.module.min.js'), modulePath);
        library = await import(pathToFileURL(modulePath).href);
        math = library;
        const compose = library.Matrix4.prototype.compose;
        library.Matrix4.prototype.compose = function(position, rotation, scale) {
            records.matrices.push({
                position: {x: position.x, y: position.y, z: position.z},
                rotation: {x: rotation.x, y: rotation.y, z: rotation.z, w: rotation.w},
                scale: {x: scale.x, y: scale.y, z: scale.z},
            });
            return compose.call(this, position, rotation, scale);
        };
        const setQuaternion = library.Quaternion.prototype.set;
        library.Quaternion.prototype.set = function(x, y, z, w) {
            records.quaternions.push([x, y, z, w]);
            return setQuaternion.call(this, x, y, z, w);
        };
        Object.assign(THREE, {...library, WebGLRenderer: Renderer,
            OrthographicCamera: class extends library.OrthographicCamera {
                constructor(...args) { super(...args); cameras.push(this); }
            },
        });
        for (const name of ['SphereGeometry', 'CylinderGeometry']) {
            THREE[name] = class extends library[name] {
                constructor(...args) { super(...args); records.geometries.push({name, args}); }
            };
        }
    }
    const document = {readyState: 'complete', body: element('body'),
        getElementById: id => element(id), querySelector: selector => element(selector.replace(/^#/, '')),
        querySelectorAll: selector => [element(selector)], createElement: tag => element(tag),
        addEventListener: (_, action) => events.push(action)};
    const Plotly = {newPlot: (...args) => { records.plots.push(args); return Promise.resolve(); },
        react: (...args) => { records.plots.push(args); return Promise.resolve(); }};
    const sandbox = {document, THREE, Plotly, console, JSON, Math, Promise,
        OrbitControls: library.EventDispatcher ? class extends library.EventDispatcher {
            constructor() { super(); this.target = new library.Vector3(); }
            update() {}
        } : undefined,
        ResizeObserver: class { constructor(action) { this.action = action; } observe() { events.push(this.action); } },
        requestAnimationFrame: () => 0, devicePixelRatio: 1,
        addEventListener: (_, action) => events.push(action),
        setTimeout: action => { events.push(action); return 0; }};
    sandbox.window = sandbox; sandbox.globalThis = sandbox;
    let source = fs.readFileSync(sourcePath, 'utf8');
    source = source.replace(/^\s*import\s+[\s\S]*?\sfrom\s*['"][^'"]+['"];?\s*$/gm, '');
    source = source.replace(/\bexport\s+(?=(?:async\s+)?function|const|let|class)/g, '');
    const context = vm.createContext(sandbox);
    await vm.runInContext('(async()=>{' + source + '\n})()', context, {timeout: 1000});
    for (const action of events) await action();
    // Let rejected async drawing calls surface before publishing an observation.
    await new Promise(resolve => setImmediate(resolve));
    for (const node of (process.argv.includes('--click-axes') ? elements : []).filter(item => /^View along [abc]$/.test(item.title || ''))) {
        try {
            node.listeners.click();
            records.axisClicks.push({title: node.title, position: cameras[0].position.toArray(), up: cameras[0].up.toArray(), top: cameras[0].top});
        } catch (error) {
            records.axisClicks.push({title: node.title, error: String(error)});
        }
    }
    records.cameras = cameras.map(camera => ({
        frustum: [camera.left, camera.right, camera.top, camera.bottom, camera.near, camera.far],
        position: {x: camera.position.x, y: camera.position.y, z: camera.position.z},
        up: {x: camera.up.x, y: camera.up.y, z: camera.up.z},
    }));
    process.stdout.write(JSON.stringify(records));
})().catch(error => { console.error(error.stack); process.exitCode = 1; });
