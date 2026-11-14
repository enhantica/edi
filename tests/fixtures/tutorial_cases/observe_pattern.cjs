// Observe the delivered Plotly call. This boundary supplies no layout calculation.
const fs = require('fs');
const vm = require('vm');
const [source, input] = process.argv.slice(2);
const fixture = JSON.parse(fs.readFileSync(input, 'utf8'));
function element(tagName) {
  return {
    tagName, dataset: {}, style: {}, children: [], attributes: {}, listeners: {},
    appendChild(child) { this.children.push(child); return child; },
    setAttribute(name, value) { this.attributes[name] = value; },
    addEventListener(name, callback) { this.listeners[name] = callback; },
  };
}
const figure = Object.assign(element('figure'), {dataset: {index: '0'}, clientHeight: fixture.height});
const model = {structures: [], experiments: [{pattern: fixture.pattern}]};
const captured = [];
const sandbox = {
  document: {
    documentElement: {},
    createElement: element,
    getElementById: () => ({textContent: JSON.stringify(model)}),
    querySelectorAll: selector => selector === '.pattern-figure' ? [figure] : [],
  },
  getComputedStyle: () => ({fontSize: String(fixture.em) + 'px', getPropertyValue: () => '#888'}),
  window: {Plotly: {newPlot: (_figure, traces, layout) => captured.push({traces, layout})}},
  console,
};
const program = fs.readFileSync(source, 'utf8')
  .replace(/^\s*import\s+[\s\S]*?\sfrom\s*['"][^'"]+['"];?\s*$/gm, '');
vm.runInNewContext(program, sandbox, {timeout: 1000});
process.stdout.write(JSON.stringify(captured));
