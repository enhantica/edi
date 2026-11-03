.pragma library

// The text property survives TextInput scrolling. The start and end caret
// positions locate the rendered run after alignment and scroll are applied.
function problems(cell, expected, context) {
    const issues = [];
    if (cell.text !== expected)
        issues.push(context + " shows " + cell.text + ", expected " + expected);
    if (!cell.visible || typeof cell.positionToRectangle !== "function")
        return issues.concat([context + " has no visible text editor"]);
    const start = cell.positionToRectangle(0);
    const end = cell.positionToRectangle(cell.text.length);
    if (start.x < -0.5 || end.x > cell.width + 0.5 || end.x <= start.x)
        issues.push(context + " places " + cell.text + " at " + start.x + " to " + end.x + " in " + cell.width + " px");
    for (let ancestor = cell.parent; ancestor; ancestor = ancestor.parent) {
        if (!ancestor.clip)
            continue;
        const left = cell.mapToItem(ancestor, start.x, start.y).x;
        const right = cell.mapToItem(ancestor, end.x, end.y).x;
        if (left < -0.5 || right > ancestor.width + 0.5)
            issues.push(context + " clips " + cell.text + " against a viewport");
    }
    return issues;
}

function number(text) {
    return typeof text === "string" && /^[+−-]?\d+(?:\.\d+)?(?:\(\d+(?:\.\d+)?\))?(?:[eE][+−-]?\d+)?$/.test(text.trim());
}
