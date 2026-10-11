const fs = require("node:fs");
const vm = require("node:vm");
const request = JSON.parse(fs.readFileSync(0, "utf8"));
function extract(source, name) {
    const start = source.indexOf("function " + name + "(");
    if (start < 0) throw new Error("The actual QML function is absent: " + name);
    const brace = source.indexOf("{", start);
    let depth = 1, end = brace + 1;
    for (; depth && end < source.length; ++end) {
        if (source[end] === "{") ++depth;
        else if (source[end] === "}") --depth;
    }
    if (depth) throw new Error("The actual QML function is incomplete: " + name);
    return source.slice(start, end);
}
const source = fs.readFileSync(request.source, "utf8");
const context = vm.createContext({bar: {fit: request.fit}, EaStyle: {Colors: {red: "#cc0000", green: "#009900", orange: "#cc9900", chartForegroundsExtra: ["#000000", "#009900"]}}});
vm.runInContext('String.prototype.arg = function(value) { return this.replace("%1", value); }; function qsTr(text) { return text; }; this.NumberText = this;', context);
const names = new Set([...request.functions, ...Array.from(source.matchAll(/^\s*function (\w+)\(/gm), match => match[1])]);
vm.runInContext(Array.from(names, name => extract(source, name)).join("\n"), context);
console.log(JSON.stringify(request.calls.map(call => context[call.name](...call.args))));
