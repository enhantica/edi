const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
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
const context = vm.createContext({bar: {fit: request.fit}, EaStyle: {Colors: {red: "#cc0000", green: "#009900", orange: "#cc9900", themeForeground: "#111111", themeForegroundMinor: "#666666", chartForegroundsExtra: ["#000000", "#009900"]}}});
vm.runInContext('String.prototype.arg = function(value) { return this.replace("%1", value); }; function qsTr(text) { return text; }; this.NumberText = this;', context);
const names = new Set([...request.functions, ...Array.from(source.matchAll(/^\s*function (\w+)\(/gm), match => match[1])]);
vm.runInContext(Array.from(names, name => extract(source, name)).join("\n"), context);
if (request.consumer === "scan") {
    // Execute the real text producer, Repeater model, and rendered Text binding. No formatter copy.
    function binding(id, declaration) {
        const match = new RegExp("\\bid:\\s*" + id + "\\b").exec(source);
        if (!match) throw new Error("The displayed QML consumer is absent: " + id);
        const tail = source.slice(match.index + match[0].length);
        const value = new RegExp("^\\s*" + declaration + ":\\s*", "m").exec(tail);
        if (!value) throw new Error("The displayed consumer binding is absent: " + declaration);
        const start = match.index + match[0].length + value.index + value[0].length;
        if (source[start] !== "{") return source.slice(start, source.indexOf("\n", start)).trim();
        let depth = 1, end = start + 1;
        for (; depth && end < source.length; ++end) {
            if (source[end] === "{") ++depth;
            else if (source[end] === "}") --depth;
        }
        if (depth) throw new Error("The displayed binding is incomplete");
        return "(function() " + source.slice(start, end) + ")()";
    }
    const outcomes = fs.readFileSync(path.resolve(path.dirname(request.source), "../Globals/FitOutcomes.qml"), "utf8");
    const separator = /^\s*readonly property string separator:\s*([^\n]+)/m.exec(outcomes);
    if (!separator) throw new Error("The actual fit singleton separator binding is absent");
    context.FitOutcomes = {separator: vm.runInContext(separator[1], context)};
    context.Text = {StyledText: 1, RichText: 2, PlainText: 0};
    context.fitArea = {counts: context.counts, joined: context.joined};
    for (const property of ["running", "scanning", "chi", "iterations"])
        context.fitArea[property] = vm.runInContext(binding("fitArea", "readonly property (?:bool|string) " + property), context);
    context.fitValues = {text: vm.runInContext(binding("fitValues", "readonly property string text"), context)};
    const repeater = /Repeater\s*\{\s*model:\s*([^\n]+)/.exec(source.slice(source.indexOf("id: valuePieces")));
    if (!repeater) throw new Error("The displayed scan repeater is absent");
    const pieces = vm.runInContext(repeater[1], context);
    const result = pieces.map((modelData, index) => {
        context.valuePart = {modelData, index};
        return {text: vm.runInContext(binding("numberText", "text"), context),
            format: vm.runInContext(binding("numberText", "textFormat"), context),
            color: vm.runInContext(binding("numberText", "color"), context)};
    });
    console.log(JSON.stringify(result));
} else {
    console.log(JSON.stringify(request.calls.map(call => context[call.name](...call.args))));
}
