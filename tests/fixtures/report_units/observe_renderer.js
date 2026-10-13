// Observe the report's actual drawing program at its browser/library boundary.
const fs = require('fs');
const vm = require('vm');
const [sourcePath, modelPath] = process.argv.slice(2);
const model = JSON.parse(fs.readFileSync(modelPath, 'utf8'));
const records = {plots: [], quaternions: [], matrices: [], cameras: [], geometries: []};
class Vector {
    constructor(x = 0, y = 0, z = 0) { this.set(x, y, z); }
    set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
    fromArray(a) { return this.set(...a); }
    copy(v) { return this.set(v.x, v.y, v.z); }
    clone() { return new Vector(this.x, this.y, this.z); }
    add(v) { this.x += v.x; this.y += v.y; this.z += v.z; return this; }
    multiplyScalar(s) { this.x *= s; this.y *= s; this.z *= s; return this; }
    normalize() { return this.multiplyScalar(1 / Math.hypot(this.x, this.y, this.z)); }
}
class Quaternion {
    constructor(x = 0, y = 0, z = 0, w = 1) { this.set(x, y, z, w); }
    set(x, y, z, w) { Object.assign(this, {x, y, z, w}); records.quaternions.push([x, y, z, w]); return this; }
    fromArray(a) { return this.set(...a); }
}
class Matrix {
    compose(position, rotation, scale) {
        this.value = {position: {...position}, rotation: {...rotation}, scale: {...scale}};
        records.matrices.push(this.value);
        return this;
    }
}
class Object3D {
    constructor() {
        this.position = new Vector(); this.scale = new Vector(1, 1, 1);
        this.quaternion = new Quaternion(); this.up = new Vector(0, 1, 0);
        this.matrix = new Matrix(); this.instanceMatrix = {}; this.children = [];
    }
    add(...items) { this.children.push(...items); }
    updateMatrix() { this.matrix.compose(this.position, this.quaternion, this.scale); }
    setMatrixAt(index, matrix) { this.instanceMatrix[index] = matrix; }
    setColorAt() {}
    lookAt(...args) { this.target = args; }
    updateProjectionMatrix() {}
}
class Camera extends Object3D {
    constructor(...args) { super(); this.frustum = args; records.cameras.push(this); }
}
class Renderer {
    constructor() { this.domElement = element('canvas'); }
    setSize() {}
    setPixelRatio() {}
    render() {}
}
const THREE = new Proxy({Vector3: Vector, Quaternion, Matrix4: Matrix, Object3D,
    OrthographicCamera: Camera, WebGLRenderer: Renderer}, {
    get(target, name) {
        if (name in target) return target[name];
        if (name.endsWith('Geometry')) return class {
            constructor(...args) { records.geometries.push({name, args}); }
        };
        if (name === 'Color') return class { constructor(...args) { this.args = args; } };
        return Object3D;
    }
});
function element(id) {
    return {id, dataset: new Proxy({}, {get: () => '0'}), style: {}, children: [],
        clientWidth: 800, clientHeight: 600, offsetWidth: 800, offsetHeight: 600,
        textContent: id === 'edi-report-model' ? JSON.stringify(model) : '',
        getAttribute: () => '0', setAttribute() {}, appendChild(child) { this.children.push(child); },
        addEventListener() {}, querySelector: s => element(s),
        querySelectorAll: s => [element(s)], getBoundingClientRect: () => ({width: 800, height: 600})};
}
const events = [];
const document = {readyState: 'complete', body: element('body'),
    getElementById: id => element(id), querySelector: s => element(s.replace(/^#/, '')),
    querySelectorAll: s => [element(s)], createElement: s => element(s),
    addEventListener: (_, action) => events.push(action)};
const Plotly = {newPlot: (...args) => { records.plots.push(args); return Promise.resolve(); },
    react: (...args) => { records.plots.push(args); return Promise.resolve(); }};
const sandbox = {document, THREE, Plotly, console, JSON, Math, Promise,
    OrbitControls: class { constructor() { this.target = new Vector(); } update() {} },
    requestAnimationFrame: () => 0, devicePixelRatio: 1,
    addEventListener: (_, action) => events.push(action), setTimeout: action => { events.push(action); return 0; }};
sandbox.window = sandbox; sandbox.globalThis = sandbox;
let source = fs.readFileSync(sourcePath, 'utf8');
source = source.replace(/^\s*import\s+[\s\S]*?\sfrom\s*['"][^'"]+['"];?\s*$/gm, '');
source = source.replace(/\bexport\s+(?=(?:async\s+)?function|const|let|class)/g, '');
(async () => {
    const context = vm.createContext(sandbox);
    await vm.runInContext('(async()=>{' + source + '\n})()', context, {timeout: 1000});
    for (const action of events) await action();
    process.stdout.write(JSON.stringify(records));
})().catch(error => { console.error(error.stack); process.exitCode = 1; });
