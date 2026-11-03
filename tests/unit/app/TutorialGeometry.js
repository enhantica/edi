.pragma library

// Scene coordinates, independent of the production locator and outline rectangle.
// Two text heights is the acceptance tolerance for "next to", not a placement formula.
function rect(item, scene) {
    return item.mapToItem(scene, 0, 0, item.width, item.height);
}
function distance(a, b) {
    const dx = Math.max(a.x - b.x - b.width, b.x - a.x - a.width, 0);
    const dy = Math.max(a.y - b.y - b.height, b.y - a.y - a.height, 0);
    return Math.hypot(dx, dy);
}
function pointDistance(point, box) {
    return distance({x: point.x, y: point.y, width: 0, height: 0}, box);
}
function center(box) {
    return {x: box.x + box.width / 2, y: box.y + box.height / 2};
}
function buttonComponent(button) {
    return String(button).split("(")[0].replace(/_QML.*$/, "");
}

function overlap(a, b) {
    return Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x)) *
           Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));
}
function pointerTapers(image, baseline, horizontal, positive) {
    function ink(fraction) {
        let count = 0;
        const along = Math.floor((horizontal ? image.width - 1 : image.height - 1) * (positive ? fraction : 1 - fraction));
        const cross = horizontal ? image.height : image.width;
        for (let n = 0; n < cross; ++n)
            if (image.pixel(horizontal ? along : n, horizontal ? n : along) !==
                baseline.pixel(horizontal ? along : n, horizontal ? n : along)) ++count;
        return count;
    }
    return ink(0.25) >= 3 && ink(0.75) > 0 && ink(0.75) < ink(0.25);
}
