.pragma library
.import "UiInteraction.js" as Ui

function descendants(root) {
    let result = [root];
    (root.children || []).forEach(child => result = result.concat(descendants(child)));
    return result;
}
function find(root, name) {
    return descendants(root).find(item => item.objectName === name && item.visible) || null;
}
function findGroup(root, name) {
    // Use the same horizontal-pane boundary as Ui.groupNames, before scrolling.
    // Basic and Extras retain visible duplicate names outside the active pane.
    return descendants(root).find(item => item.objectName === name && item.visible &&
        Ui.inPane(Ui.target(item))) || null;
}
function textItems(root) {
    return descendants(root).filter(item => item.visible && item.width > 0 && item.height > 0 &&
        typeof item.text === "string" && item.text.length &&
        (typeof item.lineCount === "number" || typeof item.getText === "function") && item.color);
}
function tableProblem(group, rows) {
    // The base TableView is a ListView with a real header and instantiated delegates.
    const tables = descendants(group).filter(item => item.visible && item.headerItem &&
        typeof item.count === "number" && typeof item.itemAtIndex === "function");
    if (!tables.length) return "loop has no table with a header and row delegates";
    if (!tables.some(table => table.count === rows && (rows === 0 || table.itemAtIndex(0))))
        return "table does not display the fixture's row count";
    return "";
}
function themeProblem(light, dark, pairs) {
    return pairs.some(pair => pair[0] === String(light).toLowerCase() &&
                     pair[1] === String(dark).toLowerCase()) ? "" :
        "text does not follow an independent theme token: " + light + " -> " + dark;
}
