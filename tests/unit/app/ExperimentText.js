.pragma library

// A calculated value may differ in its final digits between platforms.
// All other writer fields, row order, spacing, and identities stay byte-exact.
const experimentCalculated = new Set([
    "_data.d_spacing", "_data.intensity_calc", "_data.intensity_bkg",
    "_refln.d_spacing", "_refln.sin_theta_over_lambda", "_refln.f_calc",
    "_refln.f_squared_calc", "_refln.two_theta", "_refln.time_of_flight"
]);
const structureCalculated = new Set([
    "_expanded_atom_site.cartn_x", "_expanded_atom_site.cartn_y",
    "_expanded_atom_site.cartn_z", "_geom_bond.distance"
]);
const decimal = /^-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;

function rowProblem(actual, expected, headers, allowed, line) {
    const left = actual.match(/\s+|\S+/g) || [];
    const right = expected.match(/\s+|\S+/g) || [];
    if (left.length !== right.length)
        return "line " + line + ": calculated row token or spacing count changed";
    let column = 0;
    for (let i = 0; i < right.length; ++i) {
        if (/^\s+$/.test(right[i])) {
            if (left[i] !== right[i]) return "line " + line + ": row spacing changed";
            continue;
        }
        if (column >= headers.length)
            return "line " + line + ": extra row field";
        if (left[i] !== right[i]) {
            if (!allowed.has(headers[column]) || !decimal.test(left[i]) ||
                    !decimal.test(right[i]))
                return "line " + line + " " + headers[column] + ": writer token " +
                    JSON.stringify(left[i]) + " != " + JSON.stringify(right[i]);
            const a = Number(left[i]);
            const b = Number(right[i]);
            if (!isFinite(a) || !isFinite(b) ||
                    Math.abs(a - b) > 1e-12 * Math.max(1, Math.abs(a), Math.abs(b)))
                return "line " + line + " " + headers[column] + ": calculated value " +
                    JSON.stringify(left[i]) + " != " + JSON.stringify(right[i]);
        }
        ++column;
    }
    return column === headers.length ? "" : "line " + line + ": missing row field";
}

function writerProblem(actual, expected, allowed, prefixes, kind) {
    if (actual === expected) return "";
    const left = actual.split("\n");
    const right = expected.split("\n");
    if (left.length !== right.length) return kind + " Text line count changed";
    let headers = [];
    let readingHeaders = false;
    let calculatedRows = false;
    for (let i = 0; i < right.length; ++i) {
        const e = right[i];
        const a = left[i];
        if (e === "loop_") {
            if (a !== e) return "line " + (i + 1) + ": loop header changed";
            headers = [];
            readingHeaders = true;
            calculatedRows = false;
            continue;
        }
        if (readingHeaders && e.startsWith("_")) {
            if (a !== e) return "line " + (i + 1) + ": column header changed";
            headers.push(e);
            continue;
        }
        if (readingHeaders) {
            readingHeaders = false;
            calculatedRows = headers.length > 0 && headers.every(h =>
                prefixes.some(prefix => h.startsWith(prefix)));
        }
        if (e === "" || e.startsWith("_") || e.startsWith("data_"))
            calculatedRows = false;
        if (calculatedRows) {
            const difference = rowProblem(a, e, headers, allowed, i + 1);
            if (difference) return difference;
        } else if (a !== e) {
            return "line " + (i + 1) + ": " + kind + " writer bytes " +
                JSON.stringify(a.slice(0, 120)) + " != " + JSON.stringify(e.slice(0, 120));
        }
    }
    return "";
}

function problem(actual, expected) {
    return writerProblem(actual, expected, experimentCalculated,
                         ["_data.", "_refln."], "experiment");
}

function structureProblem(actual, expected) {
    return writerProblem(actual, expected, structureCalculated,
                         ["_expanded_atom_site.", "_geom_bond."], "structure");
}
