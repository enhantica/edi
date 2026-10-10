.pragma library

// Observe the clipping of the actual intersecting row. The independently supplied
// magenta ink is attached to that row, so every effective ancestor clip applies.
// Calibrate both samples with clipping removed; an occluded/offscreen sample is
// a failed witness, never evidence that the lower part of the row is hidden.
function check(test, table, next, captureRoot) {
    const top = next.mapToItem(table, 0, 0).y;
    test.verify(Math.abs((table.height - top) / next.height - 0.5) < 0.06,
        "Owner note 28 requires half of the actual next row at the table boundary");
    let bottom = next.height;
    const clips = [];
    for (let ancestor = next; ancestor; ancestor = ancestor.parent) {
        if (!ancestor.clip) continue;
        clips.push(ancestor);
        const edge = ancestor.mapToItem(next, 0, ancestor.height).y;
        bottom = Math.min(bottom, edge);
    }
    test.verify(Math.abs(bottom / next.height - 0.5) < 0.06,
        "Owner note 28 requires an effective ancestor clip at the half-row boundary");
    const marker = Qt.createQmlObject('import QtQuick; Rectangle { width: 12; color: "#e817b3"; z: 10000 }', next);
    marker.height = next.height;
    marker.x = next.mapFromItem(table, table.width * 0.6, 0).x;
    try {
        const edge = table.mapToItem(captureRoot, table.width * 0.6 + 6, table.height);
        const x = Math.round(edge.x), above = Math.floor(edge.y - 4), below = Math.ceil(edge.y + 4);
        test.verify(x >= 0 && x < captureRoot.width && above >= 0 && below < captureRoot.height,
            "Both actual row boundary samples must be inside the captured window");
        test.verify(test.waitForRendering(marker), "The actual intersecting row paints the supplied boundary witness");
        const clipped = test.grabImage(captureRoot);
        test.compare(clipped.pixel(x, above), marker.color,
            "The visible half of the actual next delegate must paint inside the table");
        test.verify(clipped.pixel(x, below) !== marker.color,
            "The hidden half of the actual next delegate must not paint beyond the table");
        for (const ancestor of clips) ancestor.clip = false;
        test.verify(test.waitForRendering(marker), "The no-clipping escape completes a rendered frame");
        const escaped = test.grabImage(captureRoot);
        test.compare(escaped.pixel(x, above), marker.color,
            "The no-clipping control retains the visible part of the actual row");
        test.compare(escaped.pixel(x, below), marker.color,
            "The no-clipping escape exposes the actual next row beyond the boundary");
    } finally {
        for (const ancestor of clips) ancestor.clip = true;
        marker.destroy();
    }
}
