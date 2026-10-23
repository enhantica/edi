.pragma library

// Closed-form image geometry. No production renderer or resampler supplies an
// expected pixel: the current physical curve is projected onto the observed axes.
function project(point, box) {
    return {x: box.x + (point.x - box.left) * box.width / (box.right - box.left),
            y: box.y + (box.top - point.y) * box.height / (box.top - box.bottom)};
}
function distance(point, a, b) {
    const dx = b.x - a.x, dy = b.y - a.y;
    const length = dx * dx + dy * dy;
    const t = length > 0 ? Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / length)) : 0;
    return Math.hypot(point.x - a.x - t * dx, point.y - a.y - t * dy);
}
function indexCurve(points, box, radius) {
    const projected = points.map(point => project(point, box));
    const bins = {};
    for (let i = 1; i < projected.length; ++i) {
        const a = projected[i - 1], b = projected[i];
        const begin = Math.max(Math.floor(box.x), Math.floor(Math.min(a.x, b.x) - radius));
        const end = Math.min(Math.ceil(box.x + box.width), Math.ceil(Math.max(a.x, b.x) + radius));
        for (let x = begin; x <= end; ++x) {
            if (!bins[x]) bins[x] = [];
            bins[x].push([a, b]);
        }
    }
    return bins;
}
function nearest(point, bins) {
    let best = Infinity;
    for (const segment of bins[Math.floor(point.x)] || [])
        best = Math.min(best, distance(point, segment[0], segment[1]));
    return best;
}
function rgb(colour) { return [colour.r * 255, colour.g * 255, colour.b * 255]; }
function close(actual, expected, tolerance) {
    return actual.every((value, index) => Math.abs(value - expected[index]) <= tolerance);
}
function calculatedPixels(image, box, points, colour, initial, background) {
    const radius = 3 * box.ratio;
    const bins = indexCurve(points, box, radius);
    const expected = rgb(colour), base = rgb(background || {r:1,g:1,b:1});
    const direction = expected.map((value, i) => value - base[i]);
    const length = direction.reduce((sum, value) => sum + value * value, 0);
    const channel = direction.map(Math.abs).indexOf(Math.max(...direction.map(Math.abs)));

    let pixels = 0, extra = 0, worst = 0, separated = 0;
    for (let y = Math.ceil(box.y + radius); y < box.y + box.height - radius; ++y) {
        for (let x = Math.ceil(box.x + radius); x < box.x + box.width - radius; ++x) {
            const first = channel === 0 ? image.red(x,y) : channel === 1 ? image.green(x,y) : image.blue(x,y);
            if (Math.abs(first - base[channel]) < Math.abs(direction[channel]) * 0.15 - 4) continue;
            const actual = [image.red(x,y), image.green(x,y), image.blue(x,y)];
            const alpha = length > 0 ? actual.reduce((sum, value, i) => sum + (value - base[i]) * direction[i], 0) / length : 0;
            if (alpha < 0.15 || alpha > 1.05 || !close(actual, direction.map((value, i) => base[i] + alpha * value), 4)) continue;
            ++pixels;
            const away = nearest({x:x, y:y}, bins);
            if (away > radius) ++extra;
            worst = Math.max(worst, away);
        }
    }
    for (const point of initial || []) {
        const p = project(point, box);
        if (p.x > box.x + radius && p.x < box.x + box.width - radius && p.y > box.y + radius && p.y < box.y + box.height - radius && nearest(p, bins) > 2 * radius)
            ++separated;
    }
    return {pixels:pixels, offCurve:extra, worst:worst, separatedInitial:separated};
}
function fillPixels(image, box, lower, upper, colour, opacity, background) {
    const alpha = colour.a * opacity;
    const base = rgb(background), ink = rgb(colour);
    const blended = ink.map((value, i) => alpha * value + (1 - alpha) * base[i]);
    let candidates = 0, hits = 0;
    // Interior samples cannot be satisfied by an outline or a baseline. The
    // explicit colour separation prevents an empty background being accepted.
    if (alpha <= 0 || close(blended, base, 12)) return {candidates:0, hits:0};
    for (let i = 0; i < Math.min(lower.length, upper.length); ++i) {
        const a = project(lower[i], box), b = project(upper[i], box);
        if (Math.abs(a.x - b.x) > box.ratio || Math.abs(a.y - b.y) < 12 * box.ratio) continue;
        for (const fraction of [0.3, 0.5, 0.7]) {
            const x = Math.round(a.x), y = Math.round(a.y + fraction * (b.y - a.y));
            if (x <= box.x + 4 * box.ratio || x >= box.x + box.width - 4 * box.ratio || y <= box.y + 4 * box.ratio || y >= box.y + box.height - 4 * box.ratio) continue;
            ++candidates;
            if (close([image.red(x, y), image.green(x, y), image.blue(x, y)], blended, 4)) ++hits;
        }
    }
    return {candidates:candidates, hits:hits};
}
function currentVisible(result) { return result.pixels >= 40 && result.offCurve === 0; }
function fillVisible(result) { return result.candidates >= 20 && result.hits >= 10; }
