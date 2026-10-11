.pragma library

function descendants(root) {
    let result = [root];
    for (const child of root.children || []) result = result.concat(descendants(child));
    return result;
}
function cells(root) {
    for (const item of descendants(root)) {
        const row = (item.children || []).filter(child => typeof child.horizontalAlignment === "number");
        if (row.length >= 2) return row;
    }
    return [];
}
function texts(root) {
    return descendants(root).filter(item => item.visible && item.width > 0 && item.height > 0 &&
        typeof item.text === "string" && item.text !== "" && item.font && item.color);
}
function borderLines(root) {
    return descendants(root).filter(item => item.visible && item.height > 0 && item.height <= 2 &&
        item.width >= root.width * 0.8 && item.color && String(item.color) !== "#00000000");
}
