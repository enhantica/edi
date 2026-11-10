.pragma library

// Read the native glyph renderer, never a model row, parameter.value, currentIndex,
// fieldValue or displayText. ComboBox.displayText alone cannot prove that its
// content item uses that property. TextField is itself a native TextInput.
function problem(item, expected, numeric) {
    if (!item || typeof item.text !== "string") return "missing text renderer";
    if (typeof item.getText !== "function" && typeof item.lineCount !== "number")
        return "not a native text renderer";
    if (!item.visible || item.width <= 0 || item.height <= 0) return "hidden text renderer";
    for (let ancestor = item; ancestor; ancestor = ancestor.parent) {
        if (!ancestor.visible || ancestor.opacity <= 0) return "invisible text ancestor";
        if (ancestor.clip && ancestor !== item) {
            const rect = item.mapToItem(ancestor, 0, 0, item.width, item.height);
            if (rect.x + rect.width <= 0 || rect.y + rect.height <= 0 ||
                    rect.x >= ancestor.width || rect.y >= ancestor.height)
                return "text outside clipped viewport";
        }
    }
    if (item.color && item.color.a <= 0) return "transparent text";
    const actual = item.text;
    if (numeric) {
        if (!actual.trim() || !isFinite(Number(actual))) return "blank or nonnumeric text: " + actual;
        if (Math.abs(Number(actual) - expected) > 1e-11 * Math.max(1, Math.abs(expected)))
            return "numeric text " + actual + " != " + expected;
    } else if (actual !== String(expected)) {
        return "text " + JSON.stringify(actual) + " != " + JSON.stringify(String(expected));
    }
    return "";
}
