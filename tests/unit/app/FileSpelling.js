.pragma library

function words(line) {
    return (line.match(/"[^"]*"|'[^']*'|[^\s]+/g) || []).map(word =>
        word.replace(/^(['"])(.*)\1$/, "$2"));
}
function valuePart(word) {
    return word.replace(/\([^)]*\)$/, "");
}
function values(text, tag) {
    const lines = text.split(/\r?\n/);
    let found = [];
    for (let i = 0; i < lines.length; ++i) {
        const row = words(lines[i]);
        if (row[0] === tag && row.length === 2) found.push(row[1]);
        if (row[0] !== "loop_") continue;
        let headers = [];
        while (i + 1 < lines.length && lines[i + 1].trim().startsWith("_"))
            headers.push(lines[++i].trim());
        const column = headers.indexOf(tag);
        while (i + 1 < lines.length) {
            const next = lines[i + 1].trim();
            if (!next || next.startsWith("_") || next === "loop_" || next.startsWith("data_")) break;
            const cells = words(lines[++i]);
            if (column >= 0 && cells.length === headers.length) found.push(cells[column]);
        }
    }
    return found;
}
function parameter(text, uid, row) {
    const found = values(text, "_" + uid);
    const index = row === undefined ? 0 : row;
    if (!found.length || index >= found.length) throw new Error("File/Text item is absent: " + uid);
    return valuePart(found[index]);
}
function block(project, parameter) {
    if (parameter.blockKind === "structure") return project.currentStructure.text.text;
    if (parameter.blockKind === "experiment") return project.currentExperiment.text.text;
    return project.analysis.text.text;
}
function range(text, leaf, derivedStep) {
    for (const axis of ["two_theta", "time_of_flight"]) {
        const part = {minimum: "min", maximum: "max", step: "step"}[leaf];
        const scalar = values(text, "_data_range." + axis + "_" + part);
        if (scalar.length) return valuePart(scalar[0]);
        const points = values(text, "_data." + axis);
        if (!points.length) continue;
        if (leaf === "minimum") return valuePart(points[0]);
        if (leaf === "maximum") return valuePart(points[points.length - 1]);
        if (leaf === "points") return String(points.length);
        return String(derivedStep);
    }
    throw new Error("Range witness has no file/Text axis");
}
