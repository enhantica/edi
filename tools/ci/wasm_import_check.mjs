// Refuse a web build whose JavaScript and WebAssembly module come from different links (ADR-0023): every
// function the module imports must be one the script's import object provides. A mismatched pair
// aborts at start with a LinkError ("import function ... must be callable").
//   node tools/ci/wasm_import_check.mjs <folder holding edi_app.js and edi_app.wasm>...
import { readFileSync } from 'node:fs';

let failed = false;
for (const folder of process.argv.slice(2)) {
  const module = new WebAssembly.Module(readFileSync(`${folder}/edi_app.wasm`));
  const wanted = WebAssembly.Module.imports(module).filter((i) => i.kind === 'function').map((i) => i.name);
  const script = readFileSync(`${folder}/edi_app.js`, 'utf8');
  const object = script.match(/wasmImports\s*=\s*\{([^}]*)\}/);
  if (!object) {
    console.error(`wasm-import-check: ${folder}/edi_app.js holds no wasmImports object`);
    failed = true;
    continue;
  }
  const provided = new Set([...object[1].matchAll(/([A-Za-z_$][\w$]*)\s*:/g)].map((m) => m[1]));
  const missing = wanted.filter((name) => !provided.has(name));
  if (wanted.length === 0 || missing.length > 0) {
    console.error(`wasm-import-check: ${folder}: the module imports ${missing.length} of ${wanted.length} functions the script does not provide (${missing.slice(0, 5).join(', ')}): not one link`);
    failed = true;
  } else {
    console.log(`wasm-import-check: ${folder}: the script provides all ${wanted.length} functions the module imports`);
  }
}
process.exit(failed ? 1 : 0);
