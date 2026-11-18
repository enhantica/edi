// SPDX-License-Identifier: BSD-3-Clause
const fs = require('fs');
const vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = vm.createContext({});
const source = fs.readFileSync(input.module, 'utf8').replace(/^\.pragma library\s*/, '');
vm.runInContext(source, context, {timeout: 1000});
try {
    const result = Array.isArray(input.calls)
        ? input.calls.map(call => context[call.operation](...call.args))
        : context[input.operation](...input.args);
    process.stdout.write(JSON.stringify({result}));
} catch (error) {
    process.stdout.write(JSON.stringify({error: String(error)}));
}
